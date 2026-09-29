import re
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

from fastapi import HTTPException
from sqlalchemy import update, or_
from sqlalchemy.orm import Session

from app.models.verification import StatutoryReserveVerification
from app.models.extraction import ExtractedField
from app.models.user import User
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)

MAKER_ROLES = {
    "SUBSIDIARY_ANALYST",
    "RI_OFFICER",
    "CMPDI_HQ_OFFICER",
    "MINISTRY_OFFICER",
    "SYSTEM_ADMIN",
    "VERIFICATION_OFFICER",
}

CHECKER_ROLES = {
    "VERIFICATION_OFFICER",
    "CMPDI_HQ_OFFICER",
    "MINISTRY_OFFICER",
    "SYSTEM_ADMIN",
}

ENTERPRISE_ROLES = {
    "CMPDI_HQ_OFFICER",
    "MINISTRY_OFFICER",
    "SYSTEM_ADMIN",
}

RESERVE_COMPATIBLE_UNITS = {
    "mt": {"mt", "tonne", "tonnes", "million tonnes", "metric tonnes", "m.t."},
    "tonne": {"mt", "tonne", "tonnes", "million tonnes", "metric tonnes", "m.t."},
    "tonnes": {"mt", "tonne", "tonnes", "million tonnes", "metric tonnes", "m.t."},
    "m": {"m", "metre", "metres", "meters", "meter"},
    "%": {"%"},
    "cum/tonne": {"cum/tonne", "m3/tonne", "cum/t"},
}


class StatutoryVerificationService:
    """
    Two-Tier 4-Eyes (Maker-Checker) Verification Service for Statutory Reserve Edits.
    
    Guarantees:
    - Maker cannot approve own proposed edits (strict server-side four-eyes separation)
    - Authoritative reserve values remain unmodified until independent checker approval
    - Atomic concurrency control prevents double-approval
    - Stale / already-resolved edit transitions are rejected
    - Strict tenant isolation across organizations
    - Immutable audit trail capturing proposals, approvals, rejections, and blocked self-approvals
    """

    @staticmethod
    def validate_numeric_reserve(
        value_str: str,
        current_unit: Optional[str] = None,
        requested_unit: Optional[str] = None
    ) -> Tuple[float, Optional[str]]:
        """
        Extracts and validates a numeric statutory reserve value and unit.
        Rejects negative quantities and unit incompatibilities.
        """
        if not value_str or not value_str.strip():
            raise ValueError("Proposed value cannot be empty.")

        cleaned = value_str.strip()
        # Extract numeric prefix (supports thousands separators and decimals)
        num_match = re.search(r"[-+]?\d+(?:,\d+)*(?:\.\d+)?", cleaned)
        if not num_match:
            raise ValueError(f"Invalid numeric value '{value_str}' for statutory reserve.")

        num_str = num_match.group(0).replace(",", "")
        try:
            numeric_val = float(num_str)
        except ValueError:
            raise ValueError(f"Could not parse numeric reserve value '{num_str}'.")

        if numeric_val < 0:
            raise ValueError("Statutory reserve value cannot be negative.")

        # Unit detection
        detected_unit = requested_unit or current_unit
        after_num = cleaned[num_match.end():].strip()
        if after_num:
            # Check if there is an explicit unit suffix e.g. "MT"
            unit_candidate = re.sub(r"[()\[\]]", "", after_num).strip()
            if unit_candidate:
                detected_unit = unit_candidate

        # Unit compatibility check
        if current_unit and detected_unit:
            curr_norm = current_unit.strip().lower()
            det_norm = detected_unit.strip().lower()
            if curr_norm in RESERVE_COMPATIBLE_UNITS:
                allowed = RESERVE_COMPATIBLE_UNITS[curr_norm]
                if det_norm not in allowed and curr_norm not in det_norm and det_norm not in curr_norm:
                    raise ValueError(f"Incompatible unit '{detected_unit}' for metric with standard unit '{current_unit}'.")

        return numeric_val, detected_unit

    @classmethod
    def check_maker_permission(cls, user: User, org_id: str) -> None:
        """Enforces RBAC and tenant scope for proposing reserve edits."""
        user_roles = {r.code for r in user.roles}
        if not user_roles.intersection(MAKER_ROLES):
            raise HTTPException(
                status_code=403,
                detail="Permission denied: user does not have permission to propose statutory reserve edits."
            )

        if not user_roles.intersection(ENTERPRISE_ROLES):
            if user.organization_id != org_id:
                raise HTTPException(
                    status_code=403,
                    detail="Unauthorized access: cannot propose edits outside assigned organization scope."
                )

    @classmethod
    def check_checker_permission(cls, user: User, org_id: str) -> None:
        """Enforces RBAC and tenant scope for reviewing/approving reserve edits."""
        user_roles = {r.code for r in user.roles}
        if not user_roles.intersection(CHECKER_ROLES):
            raise HTTPException(
                status_code=403,
                detail="Permission denied: user does not have permission to review or verify statutory reserve edits."
            )

        if not user_roles.intersection(ENTERPRISE_ROLES):
            if user.organization_id != org_id:
                raise HTTPException(
                    status_code=403,
                    detail="Unauthorized access: cannot verify edits outside assigned organization scope."
                )

    @classmethod
    def propose_edit(
        cls,
        db: Session,
        user: User,
        reserve_id: str,
        proposed_value: str,
        reason: str,
        comment: Optional[str] = None,
        unit: Optional[str] = None
    ) -> StatutoryReserveVerification:
        """
        Step 1 (Maker): Proposes a statutory reserve edit.
        Leaves authoritative record unmodified while recording proposed values in PENDING_VERIFICATION.
        """
        field = db.query(ExtractedField).filter(ExtractedField.id == reserve_id).first()
        if not field:
            raise HTTPException(status_code=404, detail="Statutory reserve record not found.")

        cls.check_maker_permission(user, field.organization_id)

        try:
            numeric_val, detected_unit = cls.validate_numeric_reserve(
                value_str=proposed_value,
                current_unit=field.unit,
                requested_unit=unit
            )
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

        entity_name = None
        if field.metadata_json and isinstance(field.metadata_json, dict):
            entity_name = field.metadata_json.get("entity_name")

        verif = StatutoryReserveVerification(
            id=str(uuid.uuid4()),
            organization_id=field.organization_id,
            reserve_record_id=field.id,
            field_name=field.field_name,
            entity_name=entity_name,
            original_value=field.raw_value,
            original_numeric_value=field.numeric_value,
            proposed_value=str(numeric_val),
            proposed_numeric_value=numeric_val,
            unit=detected_unit or field.unit,
            status="PENDING_VERIFICATION",
            maker_user_id=user.id,
            maker_comment=comment,
            reason=reason,
            created_at=datetime.utcnow()
        )
        db.add(verif)
        db.flush()

        # Audit event
        log_audit_event(
            db=db,
            action="STATUTORY_RESERVE_EDIT_PROPOSED",
            actor_id=user.id,
            actor_name=user.username,
            role_code=user.roles[0].code if user.roles else "UNKNOWN",
            organization_id=field.organization_id,
            object_type="statutory_reserve_verification",
            object_id=verif.id,
            details={
                "reserve_record_id": field.id,
                "field_name": field.field_name,
                "original_value": field.raw_value,
                "proposed_numeric_value": numeric_val,
                "unit": detected_unit or field.unit,
                "reason": reason,
                "maker_user_id": user.id,
            }
        )

        db.commit()
        db.refresh(verif)
        return verif

    @classmethod
    def approve_edit(
        cls,
        db: Session,
        user: User,
        edit_id: str,
        comment: Optional[str] = None
    ) -> StatutoryReserveVerification:
        """
        Step 2 (Checker): Independently approves a proposed statutory reserve edit.
        Enforces four-eyes separation (maker != checker) and atomically applies the proposed value.
        """
        verif = db.query(StatutoryReserveVerification).filter(
            StatutoryReserveVerification.id == edit_id
        ).first()
        if not verif:
            raise HTTPException(status_code=404, detail="Statutory reserve verification request not found.")

        # MANDATORY 4-EYES RULE: maker_user_id != verifier_user_id
        if verif.maker_user_id == user.id:
            log_audit_event(
                db=db,
                action="STATUTORY_RESERVE_SELF_APPROVAL_BLOCKED",
                actor_id=user.id,
                actor_name=user.username,
                role_code=user.roles[0].code if user.roles else "UNKNOWN",
                organization_id=verif.organization_id,
                object_type="statutory_reserve_verification",
                object_id=verif.id,
                details={
                    "maker_user_id": verif.maker_user_id,
                    "attempted_verifier_id": user.id,
                    "violation": "maker_user_id == verifier_user_id",
                    "reason": "Four-eyes policy violation: maker cannot approve own statutory reserve edit."
                }
            )
            db.commit()
            raise HTTPException(
                status_code=403,
                detail="Four-eyes policy violation: maker cannot approve own statutory reserve edit."
            )

        cls.check_checker_permission(user, verif.organization_id)

        if verif.status != "PENDING_VERIFICATION":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve statutory edit in status '{verif.status}'. Only PENDING_VERIFICATION edits can be approved."
            )

        now = datetime.utcnow()
        # Atomic transition to prevent concurrent double-approval
        stmt = (
            update(StatutoryReserveVerification)
            .where(
                StatutoryReserveVerification.id == edit_id,
                StatutoryReserveVerification.status == "PENDING_VERIFICATION"
            )
            .values(
                status="VERIFIED",
                verifier_user_id=user.id,
                verified_at=now,
                verifier_comment=comment
            )
        )
        res = db.execute(stmt)
        if res.rowcount == 0:
            raise HTTPException(
                status_code=409,
                detail="Concurrent conflict: this statutory edit was already resolved by another checker."
            )

        # Apply proposed value to authoritative reserve record
        field = db.query(ExtractedField).filter(
            ExtractedField.id == verif.reserve_record_id
        ).first()
        if field:
            field.raw_value = str(verif.proposed_numeric_value)
            field.normalized_value = str(verif.proposed_numeric_value)
            field.numeric_value = verif.proposed_numeric_value
            if verif.unit:
                field.unit = verif.unit
            field.is_corrected = True
            field.corrected_value = str(verif.proposed_numeric_value)
            field.corrected_by = user.id
            field.corrected_at = now
            field.verification_status = "VERIFIED"
            db.add(field)

        # Audit event
        log_audit_event(
            db=db,
            action="STATUTORY_RESERVE_EDIT_APPROVED",
            actor_id=user.id,
            actor_name=user.username,
            role_code=user.roles[0].code if user.roles else "UNKNOWN",
            organization_id=verif.organization_id,
            object_type="statutory_reserve_verification",
            object_id=verif.id,
            details={
                "reserve_record_id": verif.reserve_record_id,
                "maker_user_id": verif.maker_user_id,
                "verifier_user_id": user.id,
                "applied_value": verif.proposed_numeric_value,
                "unit": verif.unit,
                "verified_at": now.isoformat(),
                "verifier_comment": comment
            }
        )

        db.commit()
        db.refresh(verif)
        return verif

    @classmethod
    def reject_edit(
        cls,
        db: Session,
        user: User,
        edit_id: str,
        comment: Optional[str] = None
    ) -> StatutoryReserveVerification:
        """
        Step 2 (Checker): Rejects a proposed statutory reserve edit.
        Preserves rejection rationale while leaving authoritative reserve record intact.
        """
        verif = db.query(StatutoryReserveVerification).filter(
            StatutoryReserveVerification.id == edit_id
        ).first()
        if not verif:
            raise HTTPException(status_code=404, detail="Statutory reserve verification request not found.")

        # Independent resolution rule: maker cannot resolve own edit
        if verif.maker_user_id == user.id:
            log_audit_event(
                db=db,
                action="STATUTORY_RESERVE_SELF_APPROVAL_BLOCKED",
                actor_id=user.id,
                actor_name=user.username,
                role_code=user.roles[0].code if user.roles else "UNKNOWN",
                organization_id=verif.organization_id,
                object_type="statutory_reserve_verification",
                object_id=verif.id,
                details={
                    "maker_user_id": verif.maker_user_id,
                    "attempted_verifier_id": user.id,
                    "violation": "maker_user_id == verifier_user_id",
                    "reason": "Four-eyes policy violation: maker cannot reject/resolve own statutory reserve edit."
                }
            )
            db.commit()
            raise HTTPException(
                status_code=403,
                detail="Four-eyes policy violation: maker cannot resolve own statutory reserve edit."
            )

        cls.check_checker_permission(user, verif.organization_id)

        if verif.status != "PENDING_VERIFICATION":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reject statutory edit in status '{verif.status}'. Only PENDING_VERIFICATION edits can be rejected."
            )

        now = datetime.utcnow()
        stmt = (
            update(StatutoryReserveVerification)
            .where(
                StatutoryReserveVerification.id == edit_id,
                StatutoryReserveVerification.status == "PENDING_VERIFICATION"
            )
            .values(
                status="REJECTED",
                verifier_user_id=user.id,
                rejected_at=now,
                verifier_comment=comment
            )
        )
        res = db.execute(stmt)
        if res.rowcount == 0:
            raise HTTPException(
                status_code=409,
                detail="Concurrent conflict: this statutory edit was already resolved."
            )

        # Authoritative reserve record remains completely untouched

        # Audit event
        log_audit_event(
            db=db,
            action="STATUTORY_RESERVE_EDIT_REJECTED",
            actor_id=user.id,
            actor_name=user.username,
            role_code=user.roles[0].code if user.roles else "UNKNOWN",
            organization_id=verif.organization_id,
            object_type="statutory_reserve_verification",
            object_id=verif.id,
            details={
                "reserve_record_id": verif.reserve_record_id,
                "maker_user_id": verif.maker_user_id,
                "verifier_user_id": user.id,
                "rejection_comment": comment,
                "rejected_at": now.isoformat()
            }
        )

        db.commit()
        db.refresh(verif)
        return verif

    @classmethod
    def get_pending_edits(
        cls,
        db: Session,
        user: User,
        organization_id: Optional[str] = None
    ) -> List[StatutoryReserveVerification]:
        """Lists pending reserve edits scoped to user organization."""
        query = db.query(StatutoryReserveVerification).filter(
            StatutoryReserveVerification.status == "PENDING_VERIFICATION"
        )

        user_roles = {r.code for r in user.roles}
        is_enterprise = bool(user_roles.intersection(ENTERPRISE_ROLES))

        if not is_enterprise:
            query = query.filter(StatutoryReserveVerification.organization_id == user.organization_id)
        elif organization_id:
            query = query.filter(StatutoryReserveVerification.organization_id == organization_id)

        return query.order_by(StatutoryReserveVerification.created_at.desc()).all()

    @classmethod
    def get_edit_detail(
        cls,
        db: Session,
        user: User,
        edit_id: str
    ) -> StatutoryReserveVerification:
        """Retrieves a single statutory reserve edit detail with tenant isolation."""
        verif = db.query(StatutoryReserveVerification).filter(
            StatutoryReserveVerification.id == edit_id
        ).first()
        if not verif:
            raise HTTPException(status_code=404, detail="Statutory reserve verification request not found.")

        user_roles = {r.code for r in user.roles}
        is_enterprise = bool(user_roles.intersection(ENTERPRISE_ROLES))

        if not is_enterprise and verif.organization_id != user.organization_id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized access: statutory edit belongs to another organization."
            )

        return verif

    @classmethod
    def get_reserve_edit_history(
        cls,
        db: Session,
        user: User,
        reserve_id: str
    ) -> List[StatutoryReserveVerification]:
        """Returns the immutable historical sequence of proposals for a given reserve record."""
        field = db.query(ExtractedField).filter(ExtractedField.id == reserve_id).first()
        if not field:
            raise HTTPException(status_code=404, detail="Statutory reserve record not found.")

        user_roles = {r.code for r in user.roles}
        is_enterprise = bool(user_roles.intersection(ENTERPRISE_ROLES))

        if not is_enterprise and field.organization_id != user.organization_id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized access: record belongs to another organization."
            )

        return (
            db.query(StatutoryReserveVerification)
            .filter(StatutoryReserveVerification.reserve_record_id == reserve_id)
            .order_by(StatutoryReserveVerification.created_at.asc())
            .all()
        )
