from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.models.extraction import ExtractedField, ExtractionRun, ValidationResult
from app.schemas.extraction import (
    ExtractedFieldResponse,
    ValidationResultResponse,
    ExtractionRunResponse
)
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.audit import log_audit_event

router = APIRouter()

def check_org_access(user: User, org_id: str) -> bool:
    user_roles = [r.code for r in user.roles]
    if any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN", "VERIFICATION_OFFICER"] for r in user_roles):
        return True
    return user.organization_id == org_id

@router.post("/run/{document_id}", response_model=ExtractionRunResponse)
def trigger_extraction(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Triggers the extraction and validation pipeline on a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not check_org_access(current_user, doc.organization_id):
        raise HTTPException(status_code=403, detail="Unauthorized access to document outside organization scope")

    pipeline = ExtractionPipeline()
    try:
        run = pipeline.run_pipeline(db, document_id, doc.organization_id)
        log_audit_event(
            db=db,
            action="EXTRACTION_RUN_TRIGGERED",
            actor_id=current_user.id,
            organization_id=doc.organization_id,
            object_type="extraction_run",
            object_id=run.id,
            sha256_hash=doc.sha256_hash,
            details={"document_id": document_id, "fields_count": run.fields_extracted_count}
        )
        return run
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction pipeline failed: {str(e)}")

@router.get("/documents/{document_id}/fields", response_model=List[ExtractedFieldResponse])
def get_document_fields(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves all structured extracted fields with provenance and validation status."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not check_org_access(current_user, doc.organization_id):
        raise HTTPException(status_code=403, detail="Unauthorized access to document outside organization scope")

    fields = db.query(ExtractedField).filter(ExtractedField.document_id == document_id).all()
    
    response = []
    for f in fields:
        vr_models = db.query(ValidationResult).filter(ValidationResult.field_id == f.id).all()
        f_resp = ExtractedFieldResponse.model_validate(f)
        f_resp.validation_results = [ValidationResultResponse.model_validate(vr) for vr in vr_models]
        response.append(f_resp)
        
    return response

@router.get("/fields/{field_id}", response_model=ExtractedFieldResponse)
def get_field_detail(
    field_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves single field detail with validation results and exact provenance."""
    field = db.query(ExtractedField).filter(ExtractedField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Extracted field not found")

    if not check_org_access(current_user, field.organization_id):
        raise HTTPException(status_code=403, detail="Unauthorized access to field outside organization scope")

    vr_models = db.query(ValidationResult).filter(ValidationResult.field_id == field.id).all()
    f_resp = ExtractedFieldResponse.model_validate(field)
    f_resp.validation_results = [ValidationResultResponse.model_validate(vr) for vr in vr_models]
    return f_resp
