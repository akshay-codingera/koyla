from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

@dataclass
class UserIdentity:
    """
    Normalized, provider-agnostic user identity model.
    """
    id: str
    username: str
    full_name: str
    email: Optional[str] = None
    organization_id: Optional[str] = None
    organization_code: Optional[str] = None
    organization_name: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    is_active: bool = True
    auth_provider: str = "local"
    raw_attributes: Dict[str, Any] = field(default_factory=dict)

    @property
    def primary_role(self) -> str:
        return self.roles[0] if self.roles else "NONE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.primary_role,
            "roles": self.roles,
            "is_active": self.is_active,
            "auth_provider": self.auth_provider,
            "organization": {
                "id": self.organization_id,
                "code": self.organization_code,
                "name": self.organization_name,
            } if self.organization_id else None
        }

class IdentityProvider(ABC):
    """
    Abstract Identity Provider Contract.
    Decouples authentication, directory queries, and role resolution from
    application routes and authorization dependencies.
    """
    name: str = "abstract"

    @abstractmethod
    def authenticate(
        self,
        username: str,
        password: str,
        db: Session
    ) -> Optional[UserIdentity]:
        """
        Authenticates user credentials against the directory or database.
        Returns UserIdentity if credentials are valid and user is active, or None.
        Never logs credentials.
        """
        pass

    @abstractmethod
    def get_user(
        self,
        username_or_id: str,
        db: Session
    ) -> Optional[UserIdentity]:
        """
        Retrieves user identity by username or unique identifier.
        """
        pass

    @abstractmethod
    def resolve_roles(
        self,
        user_identity: UserIdentity,
        raw_groups: Optional[List[str]] = None
    ) -> List[str]:
        """
        Maps directory groups/authorities to Koyla application roles.
        """
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """
        Returns technical health/status of the identity provider backend.
        """
        pass
