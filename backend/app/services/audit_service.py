from sqlalchemy.orm import Session
from app.models.audit import AuditEvent

def log_audit(db: Session, actor_id: str, actor_name: str, role_code: str, org_id: str, 
              action: str, obj_type: str = None, obj_id: str = None, details: dict = None, ip: str = None):
    event = AuditEvent(
        actor_id=actor_id,
        actor_name=actor_name,
        role_code=role_code,
        organization_id=org_id,
        action=action,
        object_type=obj_type,
        object_id=obj_id,
        details=details or {},
        ip_address=ip
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
