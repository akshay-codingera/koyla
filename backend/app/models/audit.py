from sqlalchemy import Column, String, JSON
from app.models.base import UUIDMixin
from app.db.database import Base

class AuditEvent(UUIDMixin, Base):
    __tablename__ = "audit_events"
    actor_id = Column(String(36))
    actor_name = Column(String(255))
    role_code = Column(String(50))
    organization_id = Column(String(36))
    action = Column(String(100), nullable=False)
    object_type = Column(String(100))
    object_id = Column(String(36))
    sha256_hash = Column(String(64))
    ip_address = Column(String(50))
    details = Column(JSON, default={})
