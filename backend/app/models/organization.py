from sqlalchemy import Column, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import UUIDMixin
from app.db.database import Base

class Organization(UUIDMixin, Base):
    __tablename__ = "organizations"
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    org_type = Column(String(50), nullable=False)
    parent_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    metadata_ = Column("metadata", JSON, default={})
    
    parent = relationship("Organization", remote_side="Organization.id", backref="children")
    users = relationship("User", back_populates="organization")

class OrganizationRelationship(UUIDMixin, Base):
    __tablename__ = "organization_relationships"
    source_org_id = Column(String(36), ForeignKey("organizations.id"))
    target_org_id = Column(String(36), ForeignKey("organizations.id"))
    relationship_type = Column(String(50), nullable=False)
