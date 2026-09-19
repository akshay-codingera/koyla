from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.audit import AuditEvent
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class AuditEventResponse(BaseModel):
    id: str
    created_at: Optional[datetime] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    role_code: Optional[str] = None
    organization_id: Optional[str] = None
    action: str
    object_type: Optional[str] = None
    object_id: Optional[str] = None
    sha256_hash: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[dict] = None

    class Config:
        from_attributes = True

@router.get("/logs", response_model=List[AuditEventResponse])
def get_audit_logs(
    action: Optional[str] = None,
    object_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    user_roles = [r.code for r in current_user.roles]
    is_hq_or_admin = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)

    query = db.query(AuditEvent)
    if not is_hq_or_admin and current_user.organization_id:
        query = query.filter(
            (AuditEvent.organization_id == current_user.organization_id) |
            (AuditEvent.organization_id.is_(None))
        )

    if action:
        query = query.filter(AuditEvent.action == action)
    if object_type:
        query = query.filter(AuditEvent.object_type == object_type)

    events = query.order_by(AuditEvent.created_at.desc()).offset(skip).limit(limit).all()
    return events
