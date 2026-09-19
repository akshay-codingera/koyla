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

from app.api.deps import get_current_active_user

@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return {"username": current_user.username, "full_name": current_user.full_name}
