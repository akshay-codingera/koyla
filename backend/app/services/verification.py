import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.verification import VerificationTask
from app.models.extraction import ExtractedField, ReconciliationGroup
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)

class VerificationService:
    """
    Manages the Human Verification Queue and applies governance decisions.
    Supports APPROVE, CORRECT, REJECT, and DEFER actions with audit trails.
    Preserves original uncorrected values for integrity.
    """

    @staticmethod
    def process_action(
        db: Session,
        task_id: str,
        user_id: str,
        action: str,
        corrected_value: Optional[str] = None,
        review_notes: Optional[str] = None
    ) -> VerificationTask:
        task = db.query(VerificationTask).filter(VerificationTask.id == task_id).first()
        if not task:
            raise ValueError(f"VerificationTask {task_id} not found.")

        action = action.upper().strip()
        if action not in ["APPROVE", "CORRECT", "REJECT", "DEFER"]:
            raise ValueError(f"Invalid verification action '{action}'. Must be APPROVE, CORRECT, REJECT, or DEFER.")

        task.action_taken = action
        task.reviewed_at = datetime.utcnow()
        task.assigned_to = user_id
        if review_notes:
            task.review_notes = review_notes

        status_mapping = {
            "APPROVE": "APPROVED",
            "CORRECT": "CORRECTED",
            "REJECT": "REJECTED",
            "DEFER": "DEFERRED"
        }
        task.status = status_mapping[action]

        previous_val = None
        # Handle linked ExtractedField
        if task.field_id:
            field = db.query(ExtractedField).filter(ExtractedField.id == task.field_id).first()
            if field:
                previous_val = field.raw_value
                if action == "APPROVE":
                    field.verification_status = "VERIFIED"
                elif action == "CORRECT":
                    if not corrected_value:
                        raise ValueError("corrected_value must be provided for CORRECT action.")
                    field.verification_status = "CORRECTED"
                    field.is_corrected = True
                    field.corrected_value = corrected_value
                    field.corrected_by = user_id
                    field.corrected_at = datetime.utcnow()
                    task.corrected_value = corrected_value
                elif action == "REJECT":
                    field.verification_status = "REJECTED"

        # Handle linked ReconciliationGroup
        if task.reconciliation_group_id:
            group = db.query(ReconciliationGroup).filter(ReconciliationGroup.id == task.reconciliation_group_id).first()
            if group:
                if action in ["APPROVE", "CORRECT"]:
                    group.resolution_status = "RESOLVED"
                    group.resolved_by = user_id
                    group.resolved_at = datetime.utcnow()
                    group.resolution_notes = review_notes or f"Resolved via verification task {task.id}"
                elif action == "DEFER":
                    group.resolution_status = "DEFERRED"

        # Write immutable audit log
        log_audit_event(
            db=db,
            action=f"VERIFICATION_{action}",
            actor_id=user_id,
            organization_id=task.organization_id,
            object_type="verification_task",
            object_id=task.id,
            details={
                "task_type": task.task_type,
                "field_id": task.field_id,
                "reconciliation_group_id": task.reconciliation_group_id,
                "action": action,
                "previous_value": previous_val,
                "corrected_value": corrected_value if action == "CORRECT" else None,
                "review_notes": review_notes
            }
        )

        db.commit()
        db.refresh(task)
        return task
