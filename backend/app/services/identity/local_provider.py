import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.core.security import verify_password
from app.services.identity.base import IdentityProvider, UserIdentity

logger = logging.getLogger(__name__)

class LocalIdentityProvider(IdentityProvider):
    """
    Default Local Database Identity Provider.
    Authenticates against Koyla's PostgreSQL / SQLite database using bcrypt.
    Preserves all existing local users, credentials, roles, and JWT claims.
    """
    name: str = "local"

    def authenticate(
        self,
        username: str,
        password: str,
        db: Session
    ) -> Optional[UserIdentity]:
        if not username or not password:
            return None

        user = db.query(User).filter(User.username == username.strip()).first()
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        roles = [r.code for r in user.roles] if user.roles else []

        org_id = user.organization.id if user.organization else None
        org_code = user.organization.code if user.organization else None
        org_name = user.organization.name if user.organization else None

        return UserIdentity(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            organization_id=org_id,
            organization_code=org_code,
            organization_name=org_name,
            roles=roles,
            is_active=bool(user.is_active),
            auth_provider="local",
            raw_attributes={"id": user.id, "created_at": str(user.created_at)}
        )

    def get_user(
        self,
        username_or_id: str,
        db: Session
    ) -> Optional[UserIdentity]:
        user = db.query(User).filter(
            (User.username == username_or_id) | (User.id == username_or_id)
        ).first()

        if not user:
            return None

        roles = [r.code for r in user.roles] if user.roles else []
        org_id = user.organization.id if user.organization else None
        org_code = user.organization.code if user.organization else None
        org_name = user.organization.name if user.organization else None

        return UserIdentity(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            organization_id=org_id,
            organization_code=org_code,
            organization_name=org_name,
            roles=roles,
            is_active=bool(user.is_active),
            auth_provider="local"
        )

    def resolve_roles(
        self,
        user_identity: UserIdentity,
        raw_groups: Optional[List[str]] = None
    ) -> List[str]:
        return user_identity.roles

    def health(self) -> Dict[str, Any]:
        return {
            "status": "UP",
            "type": "local_database",
            "provider": "local",
            "message": "Local database identity provider active."
        }
