from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.models.verification import VerificationTask
from app.models.audit import AuditEvent

router = APIRouter()

@router.get("/metrics")
def get_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns live metrics computed directly from PostgreSQL database records.
    Applies organization-level scoping based on user role and hierarchy.
    """
    user_roles = [r.code for r in current_user.roles]
    is_hq_or_admin = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)
    
    # Query documents with organization scope
    doc_query = db.query(Document)
    if not is_hq_or_admin and current_user.organization_id:
        doc_query = doc_query.filter(Document.organization_id == current_user.organization_id)
        
    total_docs = doc_query.count()
    processed_docs = doc_query.filter(Document.status == "PROCESSED").count()
    awaiting_verification = doc_query.filter(Document.status == "AWAITING_VERIFICATION").count()
    failed_docs = doc_query.filter(Document.status == "FAILED").count()
    
    # Verification backlog
    v_query = db.query(VerificationTask).filter(VerificationTask.status == "PENDING")
    verification_backlog = v_query.count()
    
    # Audit events
    audit_query = db.query(AuditEvent)
    if not is_hq_or_admin and current_user.organization_id:
        audit_query = audit_query.filter(AuditEvent.organization_id == current_user.organization_id)
    total_audit_events = audit_query.count()
    
    # Calculate real extraction success rate
    if total_docs > 0:
        success_rate = round((processed_docs / total_docs) * 100, 1)
    else:
        success_rate = 100.0

    return {
        "documents_ingested": total_docs,
        "documents_processed": processed_docs,
        "documents_awaiting_verification": awaiting_verification,
        "documents_failed": failed_docs,
        "verification_backlog": verification_backlog,
        "extraction_success_rate": success_rate,
        "audit_events": total_audit_events,
        "organization_scope": {
            "id": current_user.organization.id if current_user.organization else None,
            "code": current_user.organization.code if current_user.organization else "GLOBAL",
            "name": current_user.organization.name if current_user.organization else "All Organizations",
            "is_unrestricted": is_hq_or_admin
        },
        "is_demo_data": True,
        "data_source": "PostgreSQL 16 (koyla)"
    }
