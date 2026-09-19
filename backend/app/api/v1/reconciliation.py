from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.models.extraction import ReconciliationGroup, ReconciliationCandidate, ExtractedField
from app.schemas.extraction import (
    ReconciliationGroupResponse,
    ReconciliationCandidateResponse,
    ReconciliationResolveRequest
)
from app.services.audit import log_audit_event

router = APIRouter()

@router.get("/conflicts", response_model=List[ReconciliationGroupResponse])
def list_reconciliation_conflicts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves all cross-document reconciliation conflicts."""
    query = db.query(ReconciliationGroup)
    user_roles = [r.code for r in current_user.roles]
    if not any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN", "VERIFICATION_OFFICER"] for r in user_roles):
        query = query.filter(ReconciliationGroup.organization_id == current_user.organization_id)

    groups = query.filter(ReconciliationGroup.conflict_status == "CONFLICT").all()
    
    response = []
    for g in groups:
        candidates = db.query(ReconciliationCandidate).filter(ReconciliationCandidate.group_id == g.id).all()
        cand_resp = []
        for c in candidates:
            doc = db.query(Document).filter(Document.id == c.document_id).first()
            cand_item = ReconciliationCandidateResponse(
                id=c.id,
                group_id=c.group_id,
                document_id=c.document_id,
                document_title=doc.title if doc else "Document",
                field_id=c.field_id,
                value=c.value,
                numeric_value=c.numeric_value,
                unit=c.unit,
                confidence_score=c.confidence_score
            )
            cand_resp.append(cand_item)

        g_resp = ReconciliationGroupResponse(
            id=g.id,
            organization_id=g.organization_id,
            entity_name=g.entity_name,
            metric_name=g.metric_name,
            reporting_period=g.reporting_period,
            conflict_status=g.conflict_status,
            resolution_status=g.resolution_status,
            resolved_by=g.resolved_by,
            resolved_at=g.resolved_at,
            resolution_notes=g.resolution_notes,
            candidates=cand_resp
        )
        response.append(g_resp)
        
    return response

@router.post("/groups/{group_id}/resolve", response_model=ReconciliationGroupResponse)
def resolve_conflict(
    group_id: str,
    req: ReconciliationResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Resolves a cross-document reconciliation conflict."""
    group = db.query(ReconciliationGroup).filter(ReconciliationGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Reconciliation group not found")

    user_roles = [r.code for r in current_user.roles]
    if not any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN", "VERIFICATION_OFFICER"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Permission denied. Only Verification Officers and Admins may resolve conflicts.")

    group.resolution_status = req.resolution_status
    group.resolved_by = current_user.id
    group.resolved_at = datetime.utcnow()
    group.resolution_notes = req.resolution_notes

    log_audit_event(
        db=db,
        action="RECONCILIATION_CONFLICT_RESOLVED",
        actor_id=current_user.id,
        organization_id=group.organization_id,
        object_type="reconciliation_group",
        object_id=group.id,
        details={
            "metric_name": group.metric_name,
            "entity_name": group.entity_name,
            "resolution": req.resolution_status,
            "notes": req.resolution_notes,
            "chosen_candidate": req.chosen_candidate_id
        }
    )
    db.commit()
    db.refresh(group)

    candidates = db.query(ReconciliationCandidate).filter(ReconciliationCandidate.group_id == group.id).all()
    cand_resp = []
    for c in candidates:
        doc = db.query(Document).filter(Document.id == c.document_id).first()
        cand_resp.append(ReconciliationCandidateResponse(
            id=c.id,
            group_id=c.group_id,
            document_id=c.document_id,
            document_title=doc.title if doc else "Document",
            field_id=c.field_id,
            value=c.value,
            numeric_value=c.numeric_value,
            unit=c.unit,
            confidence_score=c.confidence_score
        ))

    return ReconciliationGroupResponse(
        id=group.id,
        organization_id=group.organization_id,
        entity_name=group.entity_name,
        metric_name=group.metric_name,
        reporting_period=group.reporting_period,
        conflict_status=group.conflict_status,
        resolution_status=group.resolution_status,
        resolved_by=group.resolved_by,
        resolved_at=group.resolved_at,
        resolution_notes=group.resolution_notes,
        candidates=cand_resp
    )
