import os
import textwrap

files = {
    "backend/app/__init__.py": "",
    "backend/app/core/__init__.py": "",
    "backend/app/db/__init__.py": "",
    "backend/app/models/__init__.py": "",
    "backend/app/schemas/__init__.py": "",
    "backend/app/services/__init__.py": "",
    "backend/app/api/__init__.py": "",
    "backend/app/api/v1/__init__.py": "",
    
    "backend/app/core/config.py": """
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "CIL/CMPDI Reporting Intelligence"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "supersecretkey_for_local_prototype_only"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    DATABASE_URL: str = "sqlite:///./koyla.db"
    
settings = Settings()
""",
    "backend/app/core/security.py": """
import hashlib
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def hash_document(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
""",
    "backend/app/db/database.py": """
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
""",
    "backend/app/models/base.py": """
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from app.db.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class UUIDMixin:
    id = Column(String(36), primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=datetime.utcnow)
""",
    "backend/app/models/organization.py": """
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
""",
    "backend/app/models/user.py": """
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
""",
    "backend/app/models/document.py": """
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, BigInteger
from app.models.base import UUIDMixin
from app.db.database import Base

class Document(UUIDMixin, Base):
    __tablename__ = "documents"
    organization_id = Column(String(36), ForeignKey("organizations.id"))
    title = Column(String(255), nullable=False)
    document_type = Column(String(100), nullable=False)
    source_tier = Column(String(20), default="TIER_B")
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    status = Column(String(50), default="QUEUED")
    is_demo_data = Column(Boolean, default=False)
    created_by = Column(String(36), ForeignKey("users.id"))
    updated_at = Column(DateTime)
    
class DocumentVersion(UUIDMixin, Base):
    __tablename__ = "document_versions"
    document_id = Column(String(36), ForeignKey("documents.id"))
    version_number = Column(Integer, nullable=False)
    supersedes_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    file_path = Column(String(500), nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    change_summary = Column(String(1000))
    
class ProcessingJob(UUIDMixin, Base):
    __tablename__ = "processing_jobs"
    document_id = Column(String(36), ForeignKey("documents.id"))
    job_type = Column(String(50))
    status = Column(String(50), default="QUEUED")
    progress_pct = Column(Integer, default=0)
    error_message = Column(String(1000))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
""",
    "backend/app/models/audit.py": """
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
""",
    "backend/app/models/system.py": """
from sqlalchemy import Column, String, JSON, DateTime
from datetime import datetime
from app.db.database import Base

class SystemSettings(Base):
    __tablename__ = "system_settings"
    key = Column(String(100), primary_key=True)
    value = Column(JSON, default={})
    description = Column(String(255))
    updated_at = Column(DateTime, default=datetime.utcnow)
""",
    "backend/app/schemas/auth.py": """
from pydantic import BaseModel
from typing import List, Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict
    
class TokenData(BaseModel):
    username: Optional[str] = None
""",
    "backend/app/services/audit_service.py": """
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
""",
    "backend/app/api/deps.py": """
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
""",
    "backend/app/api/v1/auth.py": """
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.core.security import verify_password, create_access_token
from app.schemas.auth import Token
from app.services.audit_service import log_audit

router = APIRouter()

@router.post("/login", response_model=Token)
def login_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token = create_access_token(subject=user.username)
    role = user.roles[0].code if user.roles else "NONE"
    
    log_audit(db, actor_id=user.id, actor_name=user.username, role_code=role, 
              org_id=user.organization_id, action="AUTH_LOGIN")
              
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": role,
            "organization": {
                "id": user.organization.id if user.organization else None,
                "code": user.organization.code if user.organization else None,
                "name": user.organization.name if user.organization else None,
            }
        }
    }

@router.get("/me")
def read_users_me(current_user: User = Depends(from app.api.deps import get_current_active_user)):
    return {"username": current_user.username, "full_name": current_user.full_name}
""",
    "backend/app/api/v1/system.py": """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from sqlalchemy import text

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "UP"
    except Exception:
        db_status = "DOWN"
        
    return {
        "status": "UP" if db_status == "UP" else "DEGRADED",
        "services": {
            "api": "UP",
            "database": db_status,
            "vector_store": "DOWN",
            "ocr_engine": "DOWN",
            "llm_service": "DOWN"
        }
    }
""",
    "backend/app/api/v1/dashboard.py": """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.models.audit import AuditEvent

router = APIRouter()

@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    docs_count = db.query(Document).count()
    audit_count = db.query(AuditEvent).count()
    
    return {
        "documents_ingested": docs_count,
        "documents_processed": docs_count,
        "verification_backlog": 0,
        "extraction_success_rate": 100,
        "audit_events": audit_count,
        "is_demo_data": True
    }
""",
    "backend/app/main.py": """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import engine, Base

import app.models.organization
import app.models.user
import app.models.document
import app.models.audit
import app.models.system

Base.metadata.create_all(bind=engine)

from app.api.v1 import auth, system, dashboard

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(system.router, prefix=f"{settings.API_V1_STR}/system", tags=["system"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])

@app.get("/")
def root():
    return {"message": "Welcome to KOYLA API"}
""",
    "backend/scripts/seed.py": """
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal, Base, engine
from app.models.organization import Organization
from app.models.user import User, Role
from app.core.security import get_password_hash

def seed_data():
    db = SessionLocal()
    
    if db.query(Organization).count() > 0:
        print("Database already seeded.")
        return
        
    print("Seeding Organizations...")
    cil = Organization(code="CIL", name="Coal India Limited", org_type="APEX")
    db.add(cil)
    db.commit()
    
    cmpdi = Organization(code="CMPDI_HQ", name="CMPDI HQ - Ranchi", org_type="HQ", parent_id=cil.id)
    db.add(cmpdi)
    db.commit()
    
    ri1 = Organization(code="RI_1", name="Regional Institute - I (Asansol)", org_type="REGIONAL_INSTITUTE", parent_id=cmpdi.id)
    ecl = Organization(code="ECL", name="Eastern Coalfields Limited", org_type="SUBSIDIARY", parent_id=cil.id)
    db.add_all([ri1, ecl])
    db.commit()
    
    print("Seeding Roles...")
    role_cmpdi_hq = Role(code="CMPDI_HQ_OFFICER", name="CMPDI HQ Officer")
    role_ri_analyst = Role(code="RI_ANALYST", name="Regional Institute Analyst")
    db.add_all([role_cmpdi_hq, role_ri_analyst])
    db.commit()
    
    print("Seeding Users...")
    u1 = User(
        username="hq_officer",
        email="hq@cmpdi.gov.in",
        full_name="HQ Admin",
        hashed_password=get_password_hash("Admin123!"),
        organization_id=cmpdi.id
    )
    u2 = User(
        username="ri1_analyst",
        email="ri1@cmpdi.gov.in",
        full_name="RI-1 Analyst",
        hashed_password=get_password_hash("Password123!"),
        organization_id=ri1.id
    )
    
    u1.roles.append(role_cmpdi_hq)
    u2.roles.append(role_ri_analyst)
    
    db.add_all([u1, u2])
    db.commit()
    
    print("Seeding Complete!")

if __name__ == "__main__":
    seed_data()
"""
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content.strip() + "\n")

print("Backend scaffolded successfully.")
