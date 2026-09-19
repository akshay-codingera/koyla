from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.extraction import ExtractedField, ValidationResult
from app.schemas.extraction import ValidationResultResponse

router = APIRouter()

@router.get("/issues", response_model=List[dict])
def list_validation_issues(
    document_id: Optional[str] = None,
    status: Optional[str] = None,  # 'ERROR', 'WARNING'
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves all domain validation issues (errors/warnings) across documents."""
    query = db.query(ValidationResult, ExtractedField).join(
        ExtractedField, ValidationResult.field_id == ExtractedField.id
    )

    user_roles = [r.code for r in current_user.roles]
    if not any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN", "VERIFICATION_OFFICER"] for r in user_roles):
        query = query.filter(ExtractedField.organization_id == current_user.organization_id)

    if document_id:
        query = query.filter(ExtractedField.document_id == document_id)
    if status:
        query = query.filter(ValidationResult.status == status.upper())
    else:
        # By default return non-pass issues
        query = query.filter(ValidationResult.status.in_(["WARNING", "ERROR"]))
    if severity:
        query = query.filter(ValidationResult.severity == severity.upper())

    results = query.all()
    issues = []
    for vr, field in results:
        issues.append({
            "id": vr.id,
            "field_id": field.id,
            "field_name": field.field_name,
            "raw_value": field.raw_value,
            "unit": field.unit,
            "document_id": field.document_id,
            "page_number": field.page_number,
            "rule_name": vr.rule_name,
            "rule_category": vr.rule_category,
            "status": vr.status,
            "severity": vr.severity,
            "message": vr.message,
            "observed_value": vr.observed_value,
            "expected_constraint": vr.expected_constraint
        })
    return issues
