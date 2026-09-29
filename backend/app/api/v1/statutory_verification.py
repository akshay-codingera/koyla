from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.verification import StatutoryReserveVerification
from app.schemas.statutory_verification import (
    StatutoryReserveEditCreate,
    StatutoryReserveApprovalRequest,
    StatutoryReserveRejectionRequest,
    StatutoryReserveVerificationResponse
)
from app.services.statutory_verification import StatutoryVerificationService

router = APIRouter()


def _format_verification_response(verif: StatutoryReserveVerification, db: Session) -> StatutoryReserveVerificationResponse:
    maker_name = None
    if verif.maker_user_id:
        maker = db.query(User).filter(User.id == verif.maker_user_id).first()
        if maker:
            maker_name = maker.full_name or maker.username

    verifier_name = None
    if verif.verifier_user_id:
        verifier = db.query(User).filter(User.id == verif.verifier_user_id).first()
        if verifier:
            verifier_name = verifier.full_name or verifier.username

    return StatutoryReserveVerificationResponse(
        id=verif.id,
        organization_id=verif.organization_id,
        reserve_record_id=verif.reserve_record_id,
        field_name=verif.field_name,
        entity_name=verif.entity_name,
        original_value=verif.original_value,
        original_numeric_value=verif.original_numeric_value,
        proposed_value=verif.proposed_value,
        proposed_numeric_value=verif.proposed_numeric_value,
        unit=verif.unit,
        status=verif.status,
        maker_user_id=verif.maker_user_id,
        maker_name=maker_name,
        maker_comment=verif.maker_comment,
        reason=verif.reason,
        verifier_user_id=verif.verifier_user_id,
        verifier_name=verifier_name,
        verifier_comment=verif.verifier_comment,
        created_at=verif.created_at,
        verified_at=verif.verified_at,
        rejected_at=verif.rejected_at,
        metadata_json=verif.metadata_json
    )


@router.post("/reserves/{reserve_id}/edits", response_model=StatutoryReserveVerificationResponse, status_code=status.HTTP_201_CREATED)
def propose_statutory_reserve_edit(
    reserve_id: str,
    req: StatutoryReserveEditCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Step 1 (Maker): Proposes a statutory reserve edit.
    Leaves original authoritative record unchanged and queues the edit for independent verification.
    """
    verif = StatutoryVerificationService.propose_edit(
        db=db,
        user=current_user,
        reserve_id=reserve_id,
        proposed_value=req.proposed_value,
        reason=req.reason,
        comment=req.comment,
        unit=req.unit
    )
    return _format_verification_response(verif, db)


@router.get("/reserve-edits/pending", response_model=List[StatutoryReserveVerificationResponse])
def list_pending_reserve_edits(
    organization_id: Optional[str] = Query(None, description="Optional organization scope filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lists all pending statutory reserve verification requests within user's organization scope.
    """
    pending = StatutoryVerificationService.get_pending_edits(
        db=db,
        user=current_user,
        organization_id=organization_id
    )
    return [_format_verification_response(v, db) for v in pending]


@router.get("/reserve-edits/{edit_id}", response_model=StatutoryReserveVerificationResponse)
def get_reserve_edit_detail(
    edit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieves full detail of a specific statutory reserve verification request.
    """
    verif = StatutoryVerificationService.get_edit_detail(
        db=db,
        user=current_user,
        edit_id=edit_id
    )
    return _format_verification_response(verif, db)


@router.post("/reserve-edits/{edit_id}/approve", response_model=StatutoryReserveVerificationResponse)
def approve_statutory_reserve_edit(
    edit_id: str,
    req: Optional[StatutoryReserveApprovalRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Step 2 (Checker): Independently approves a proposed statutory reserve edit.
    Enforces four-eyes separation (maker cannot approve own edit) and atomically applies the proposed value.
    """
    comment = req.comment if req else None
    verif = StatutoryVerificationService.approve_edit(
        db=db,
        user=current_user,
        edit_id=edit_id,
        comment=comment
    )
    return _format_verification_response(verif, db)


@router.post("/reserve-edits/{edit_id}/reject", response_model=StatutoryReserveVerificationResponse)
def reject_statutory_reserve_edit(
    edit_id: str,
    req: Optional[StatutoryReserveRejectionRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Step 2 (Checker): Rejects a proposed statutory reserve edit.
    Leaves original authoritative record intact and captures rejection rationale in immutable audit trail.
    """
    comment = req.comment if req else None
    verif = StatutoryVerificationService.reject_edit(
        db=db,
        user=current_user,
        edit_id=edit_id,
        comment=comment
    )
    return _format_verification_response(verif, db)


@router.get("/reserves/{reserve_id}/history", response_model=List[StatutoryReserveVerificationResponse])
def get_reserve_edit_history(
    reserve_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieves the complete immutable audit history of all edit proposals for a statutory reserve record.
    """
    history = StatutoryVerificationService.get_reserve_edit_history(
        db=db,
        user=current_user,
        reserve_id=reserve_id
    )
    return [_format_verification_response(v, db) for v in history]
