from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.document import Document, DocumentPage, Table
from app.models.chunk import Chunk
from app.models.extraction import ExtractedField, ReconciliationGroup
from app.models.visual import VisualAsset
from app.models.geology import BoreholeStratum
from app.models.verification import VerificationTask
from app.models.audit import AuditEvent
from app.models.organization import Organization
from app.models.report import Report
from app.models.qa import QueryRecord
from app.models.topic import Topic, TopicDocument

router = APIRouter()

MIME_LABELS: Dict[str, str] = {
    "application/pdf": "Geological Reports & Folios (PDF)",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Reserve & Production Spreadsheets (XLSX)",
    "application/vnd.ms-excel": "Legacy Spreadsheets (XLS)",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Administrative & Technical Briefs (DOCX)",
    "text/csv": "Time-Series & Production Logs (CSV)",
    "text/plain": "Geological Drill Logs & Notes (TXT)",
    "image/png": "Borehole & Seam Cross-Sections (PNG)",
    "image/jpeg": "Geological Maps & Figures (JPEG)",
}

@router.get("/metrics")
def get_metrics(
    org_filter: Optional[str] = None,
    mime_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns comprehensive live metrics computed directly from PostgreSQL database records.
    Applies organization-level scoping based on user role and hierarchy.
    """
    # Sanitize filter inputs
    if org_filter and not isinstance(org_filter, str):
        org_filter = None
    if mime_filter and not isinstance(mime_filter, str):
        mime_filter = None
    if status_filter and not isinstance(status_filter, str):
        status_filter = None

    user_roles = [r.code for r in current_user.roles]
    is_hq_or_admin = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)
    
    # Base Document query with role scoping
    doc_query = db.query(Document)
    if not is_hq_or_admin and current_user.organization_id:
        doc_query = doc_query.filter(Document.organization_id == current_user.organization_id)
    elif org_filter:
        doc_query = doc_query.filter(Document.organization_id == org_filter)
        
    if mime_filter:
        doc_query = doc_query.filter(Document.mime_type == mime_filter)
    if status_filter:
        doc_query = doc_query.filter(Document.status == status_filter)
        
    total_docs = doc_query.count()
    processed_docs = doc_query.filter(Document.status == "PROCESSED").count()
    awaiting_verification = doc_query.filter(Document.status == "AWAITING_VERIFICATION").count()
    failed_docs = doc_query.filter(Document.status == "FAILED").count()
    
    # Verification tasks
    v_query = db.query(VerificationTask)
    verification_backlog = v_query.filter(VerificationTask.status == "PENDING").count()
    verification_approved = v_query.filter(VerificationTask.status == "APPROVED").count()
    verification_rejected = v_query.filter(VerificationTask.status == "REJECTED").count()
    total_verifications = v_query.count()
    
    # Audit events
    audit_query = db.query(AuditEvent)
    if not is_hq_or_admin and current_user.organization_id:
        audit_query = audit_query.filter(AuditEvent.organization_id == current_user.organization_id)
    total_audit_events = audit_query.count()
    
    # Extraction success rate
    if total_docs > 0:
        success_rate = round((processed_docs / total_docs) * 100, 1)
    else:
        success_rate = 100.0

    # Extended repository metrics
    total_reports = db.query(Report).count()
    total_queries = db.query(QueryRecord).count()
    total_chunks = db.query(Chunk).count()
    total_tables = db.query(Table).count()
    total_fields = db.query(ExtractedField).count()
    total_visuals = db.query(VisualAsset).count()
    total_strata = db.query(BoreholeStratum).count()
    total_reconciliation = db.query(ReconciliationGroup).count()

    # Document type distribution
    mime_counts = db.query(
        Document.mime_type, 
        func.count(Document.id)
    ).group_by(Document.mime_type).all()
    
    document_types = []
    for mime, count in mime_counts:
        label = MIME_LABELS.get(mime, mime or "Unknown")
        pct = round((count / total_docs * 100), 1) if total_docs > 0 else 0
        document_types.append({
            "mime_type": mime,
            "label": label,
            "count": count,
            "percentage": pct
        })
    document_types.sort(key=lambda x: x["count"], reverse=True)

    # Organization distribution (top 10 active)
    org_counts = db.query(
        Organization.id,
        Organization.name,
        Organization.code,
        func.count(Document.id).label("doc_count")
    ).join(Document, Document.organization_id == Organization.id)\
     .group_by(Organization.id, Organization.name, Organization.code)\
     .order_by(desc("doc_count"))\
     .limit(10).all()
     
    org_distribution = [
        {
            "id": o.id,
            "name": o.name,
            "code": o.code,
            "document_count": o.doc_count
        }
        for o in org_counts
    ]

    # Topic highlights (top 6 topics by document frequency)
    topic_rows = db.query(
        Topic.id,
        Topic.label,
        Topic.document_count,
        Topic.prevalence_pct
    ).filter(Topic.label.isnot(None))\
     .order_by(desc(Topic.document_count))\
     .limit(6).all()

    topic_highlights = [
        {
            "id": t.id,
            "name": t.label or "Geological Pattern",
            "document_count": t.document_count or 0,
            "prevalence_pct": round(t.prevalence_pct or 0.0, 1)
        }
        for t in topic_rows
    ]

    # Recent Audit Activity (top 8)
    recent_audits = db.query(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(8).all()
    recent_activity = [
        {
            "id": a.id,
            "action": a.action,
            "actor_name": a.actor_name or "System Daemon",
            "role_code": a.role_code or "SYSTEM",
            "object_type": a.object_type or "ENTITY",
            "hash": a.sha256_hash[:12] + "..." if a.sha256_hash else "SHA-256",
            "timestamp": a.created_at.strftime("%Y-%m-%d %H:%M:%S") if a.created_at else ""
        }
        for a in recent_audits
    ]

    # Available organizations for filter
    all_orgs = db.query(Organization.id, Organization.code, Organization.name).order_by(Organization.name).all()
    available_orgs = [{"id": o.id, "code": o.code, "name": o.name} for o in all_orgs]

    return {
        # Core standard metrics
        "documents_ingested": total_docs,
        "documents_processed": processed_docs,
        "documents_awaiting_verification": awaiting_verification,
        "documents_failed": failed_docs,
        "verification_backlog": verification_backlog,
        "extraction_success_rate": success_rate,
        "audit_events": total_audit_events,
        
        # Extended intelligence metrics
        "total_reports": total_reports,
        "total_queries": total_queries,
        "total_chunks": total_chunks,
        "total_tables": total_tables,
        "total_structured_fields": total_fields,
        "total_visual_assets": total_visuals,
        "total_strata": total_strata,
        "total_reconciliation_groups": total_reconciliation,
        
        # Distributions & Activity
        "document_types": document_types,
        "organization_distribution": org_distribution,
        "verification_status": {
            "pending": verification_backlog,
            "approved": verification_approved,
            "rejected": verification_rejected,
            "total": total_verifications
        },
        "topic_highlights": topic_highlights,
        "recent_activity": recent_activity,
        "available_organizations": available_orgs,
        
        "organization_scope": {
            "id": current_user.organization.id if current_user.organization else None,
            "code": current_user.organization.code if current_user.organization else "GLOBAL",
            "name": current_user.organization.name if current_user.organization else "All Organizations",
            "is_unrestricted": is_hq_or_admin
        },
        "is_demo_data": True,
        "data_source": "PostgreSQL 16 (koyla)"
    }
