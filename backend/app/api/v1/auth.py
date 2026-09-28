from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.core.security import verify_password, create_access_token
from app.schemas.auth import Token
from app.services.audit_service import log_audit

from app.core.rate_limit import RateLimiter
from app.core.config import settings

router = APIRouter()
auth_rate_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_AUTH_PER_MINUTE, scope="auth")

from app.services.identity import get_identity_provider

@router.post("/login", response_model=Token, dependencies=[Depends(auth_rate_limiter)])
def login_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    provider = get_identity_provider()
    identity = provider.authenticate(form_data.username, form_data.password, db)
    if not identity:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not identity.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token = create_access_token(subject=identity.username)
    role = identity.primary_role
    
    log_audit(db, actor_id=identity.id, actor_name=identity.username, role_code=role, 
              org_id=identity.organization_id, action="AUTH_LOGIN")
              
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": identity.id,
            "username": identity.username,
            "full_name": identity.full_name,
            "role": role,
            "organization": {
                "id": identity.organization_id,
                "code": identity.organization_code,
                "name": identity.organization_name,
            } if identity.organization_id else None
        }
    }

from app.api.deps import get_current_active_user

@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return {"username": current_user.username, "full_name": current_user.full_name}
