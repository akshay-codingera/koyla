from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.models.verification import VerificationTask
from app.models.extraction import ExtractedField, ValidationResult
from app.schemas.extraction import (
    VerificationTaskResponse,
    VerificationActionRequest,
    ExtractedFieldResponse,
    ValidationResultResponse
)
from app.services.verification import VerificationService

router = APIRouter()

@router.get("/queue", response_model=List[VerificationTaskResponse])
def get_verification_queue(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves all tasks in the Human Verification Queue within user organization scope."""
    query = db.query(VerificationTask)

    user_roles = [r.code for r in current_user.roles]
    if not any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN", "VERIFICATION_OFFICER"] for r in user_roles):
        query = query.filter(
            (VerificationTask.organization_id == current_user.organization_id) |
            (VerificationTask.organization_id.is_(None))
        )

    if status:
        query = query.filter(VerificationTask.status == status.upper())
    else:
        query = query.filter(VerificationTask.status == "PENDING")

    if task_type:
        query = query.filter(VerificationTask.task_type == task_type)

    tasks = query.order_by(VerificationTask.created_at.desc()).all()

    response = []
    for t in tasks:
        doc = db.query(Document).filter(Document.id == t.document_id).first() if t.document_id else None
        
        field_resp = None
        if t.field_id:
            f = db.query(ExtractedField).filter(ExtractedField.id == t.field_id).first()
            if f:
                vr_models = db.query(ValidationResult).filter(ValidationResult.field_id == f.id).all()
                field_resp = ExtractedFieldResponse.model_validate(f)
                field_resp.validation_results = [ValidationResultResponse.model_validate(vr) for vr in vr_models]

        item = VerificationTaskResponse(
            id=t.id,
            task_type=t.task_type,
            organization_id=t.organization_id,
            document_id=t.document_id,
            document_title=doc.title if doc else "Document",
            field_id=t.field_id,
            reconciliation_group_id=t.reconciliation_group_id,
            status=t.status,
            action_taken=t.action_taken,
            corrected_value=t.corrected_value,
            evidence_context=t.evidence_context,
            review_notes=t.review_notes,
            reviewed_at=t.reviewed_at,
            created_at=t.created_at,
            field_details=field_resp
        )
        response.append(item)

    return response

@router.get("/tasks/{task_id}", response_model=VerificationTaskResponse)
def get_verification_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves a single verification task by ID."""
    t = db.query(VerificationTask).filter(VerificationTask.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Verification task not found")

    user_roles = [r.code for r in current_user.roles]
    if not any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN", "VERIFICATION_OFFICER"] for r in user_roles):
        if t.organization_id and t.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Unauthorized access to verification task outside organization scope")

    doc = db.query(Document).filter(Document.id == t.document_id).first() if t.document_id else None
    field_resp = None
    if t.field_id:
        f = db.query(ExtractedField).filter(ExtractedField.id == t.field_id).first()
        if f:
            vr_models = db.query(ValidationResult).filter(ValidationResult.field_id == f.id).all()
            field_resp = ExtractedFieldResponse.model_validate(f)
            field_resp.validation_results = [ValidationResultResponse.model_validate(vr) for vr in vr_models]

    return VerificationTaskResponse(
        id=t.id,
        task_type=t.task_type,
        organization_id=t.organization_id,
        document_id=t.document_id,
        document_title=doc.title if doc else "Document",
        field_id=t.field_id,
        reconciliation_group_id=t.reconciliation_group_id,
        status=t.status,
        action_taken=t.action_taken,
        corrected_value=t.corrected_value,
        evidence_context=t.evidence_context,
        review_notes=t.review_notes,
        reviewed_at=t.reviewed_at,
        created_at=t.created_at,
        field_details=field_resp
    )

@router.post("/tasks/{task_id}/action", response_model=VerificationTaskResponse)
def apply_verification_action(
    task_id: str,
    req: VerificationActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Applies a human verification decision (APPROVE, CORRECT, REJECT, DEFER)."""
    t = db.query(VerificationTask).filter(VerificationTask.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Verification task not found")

    user_roles = [r.code for r in current_user.roles]
    if not any(r in ["VERIFICATION_OFFICER", "MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Permission denied. Only Verification Officers may review tasks.")

    if not any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN", "VERIFICATION_OFFICER"] for r in user_roles):
        if t.organization_id and t.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Unauthorized access to verification task outside organization scope")

    try:
        updated_task = VerificationService.process_action(
            db=db,
            task_id=task_id,
            user_id=current_user.id,
            action=req.action,
            corrected_value=req.corrected_value,
            review_notes=req.review_notes
        )
        
        doc = db.query(Document).filter(Document.id == updated_task.document_id).first() if updated_task.document_id else None
        field_resp = None
        if updated_task.field_id:
            f = db.query(ExtractedField).filter(ExtractedField.id == updated_task.field_id).first()
            if f:
                vr_models = db.query(ValidationResult).filter(ValidationResult.field_id == f.id).all()
                field_resp = ExtractedFieldResponse.model_validate(f)
                field_resp.validation_results = [ValidationResultResponse.model_validate(vr) for vr in vr_models]

        return VerificationTaskResponse(
            id=updated_task.id,
            task_type=updated_task.task_type,
            organization_id=updated_task.organization_id,
            document_id=updated_task.document_id,
            document_title=doc.title if doc else "Document",
            field_id=updated_task.field_id,
            reconciliation_group_id=updated_task.reconciliation_group_id,
            status=updated_task.status,
            action_taken=updated_task.action_taken,
            corrected_value=updated_task.corrected_value,
            evidence_context=updated_task.evidence_context,
            review_notes=updated_task.review_notes,
            reviewed_at=updated_task.reviewed_at,
            created_at=updated_task.created_at,
            field_details=field_resp
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification action failed: {str(e)}")
