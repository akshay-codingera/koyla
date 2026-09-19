import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.audit import AuditEvent

def log_audit_event(
    db: Session,
    action: str,
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = None,
    role_code: Optional[str] = None,
    organization_id: Optional[str] = None,
    object_type: Optional[str] = None,
    object_id: Optional[str] = None,
    sha256_hash: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    """
    Centralized, reusable audit logging service.
    Persists immutable audit events directly to the database.
    """
    event = AuditEvent(
        id=str(uuid.uuid4()),
        action=action,
        actor_id=actor_id,
        actor_name=actor_name,
        role_code=role_code,
        organization_id=organization_id,
        object_type=object_type,
        object_id=object_id,
        sha256_hash=sha256_hash,
        ip_address=ip_address,
        details=details or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
