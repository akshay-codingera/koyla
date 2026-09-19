from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.organization import Organization

router = APIRouter()

@router.get("")
@router.get("/")
def list_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    user_roles = [r.code for r in current_user.roles]
    is_hq_or_admin = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)
    
    query = db.query(Organization).filter(Organization.is_active == True)
    if not is_hq_or_admin and current_user.organization_id:
        query = query.filter(
            (Organization.id == current_user.organization_id) |
            (Organization.parent_id == current_user.organization_id)
        )
        
    orgs = query.order_by(Organization.code).all()
    return [
        {
            "id": o.id,
            "code": o.code,
            "name": o.name,
            "org_type": o.org_type,
            "parent_id": o.parent_id
        }
        for o in orgs
    ]
