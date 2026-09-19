from sqlalchemy import Column, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import UUIDMixin
from app.db.database import Base

class Role(UUIDMixin, Base):
    __tablename__ = "roles"
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(255))
    permissions = Column(JSON, default=[])

class User(UUIDMixin, Base):
    __tablename__ = "users"
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id"))
    is_active = Column(Boolean, default=True)
    
    organization = relationship("Organization", back_populates="users")
    roles = relationship("Role", secondary="user_roles")

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    role_id = Column(String(36), ForeignKey("roles.id"), primary_key=True)
