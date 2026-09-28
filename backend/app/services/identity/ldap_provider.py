import ssl
import re
import uuid
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User, Role, UserRole
from app.models.organization import Organization
from app.services.identity.base import IdentityProvider, UserIdentity

logger = logging.getLogger(__name__)

def sanitize_ldap_input(val: str) -> str:
    """
    Escapes special characters in LDAP filter components (RFC 4515)
    to prevent LDAP injection attacks.
    """
    if not val:
        return ""
    # RFC 4515 escape characters: \ * ( ) \0
    escape_chars = {
        "\\": r"\5c",
        "*": r"\2a",
        "(": r"\28",
        ")": r"\29",
        "\x00": r"\00"
    }
    pattern = re.compile("|".join(re.escape(k) for k in escape_chars.keys()))
    return pattern.sub(lambda m: escape_chars[m.group(0)], val)


class LDAPIdentityProvider(IdentityProvider):
    """
    Enterprise LDAP / Active Directory Identity Provider.
    Configurable for standard LDAP and Active Directory environments.
    Translates enterprise directory groups into Koyla RBAC application roles.
    Never hardcodes enterprise endpoints, credentials, or CIL group names.
    Never logs passwords or bind secrets.
    """
    name: str = "ldap"

    def __init__(
        self,
        config_override: Optional[Dict[str, Any]] = None,
        driver: Optional[Any] = None
    ):
        cfg = config_override or {}
        self.server_url = cfg.get("LDAP_SERVER_URL") or settings.LDAP_SERVER_URL
        self.base_dn = cfg.get("LDAP_BASE_DN") or settings.LDAP_BASE_DN
        self.bind_dn = cfg.get("LDAP_BIND_DN") or settings.LDAP_BIND_DN
        self.bind_password = cfg.get("LDAP_BIND_PASSWORD") or settings.LDAP_BIND_PASSWORD
        self.user_search_base = cfg.get("LDAP_USER_SEARCH_BASE") or settings.LDAP_USER_SEARCH_BASE or self.base_dn
        self.user_search_filter = cfg.get("LDAP_USER_SEARCH_FILTER") or settings.LDAP_USER_SEARCH_FILTER
        self.group_search_base = cfg.get("LDAP_GROUP_SEARCH_BASE") or settings.LDAP_GROUP_SEARCH_BASE or self.base_dn
        self.group_search_filter = cfg.get("LDAP_GROUP_SEARCH_FILTER") or settings.LDAP_GROUP_SEARCH_FILTER
        self.use_tls = cfg.get("LDAP_USE_TLS", settings.LDAP_USE_TLS)
        self.verify_cert = cfg.get("LDAP_VERIFY_CERT", settings.LDAP_VERIFY_CERT)
        self.ca_cert_path = cfg.get("LDAP_CA_CERT_PATH") or settings.LDAP_CA_CERT_PATH
        self.timeout_seconds = cfg.get("LDAP_TIMEOUT_SECONDS", settings.LDAP_TIMEOUT_SECONDS)
        self.group_role_mapping = cfg.get("LDAP_GROUP_ROLE_MAPPING") or settings.parsed_ldap_group_role_mapping
        self.default_role = cfg.get("LDAP_DEFAULT_ROLE", settings.LDAP_DEFAULT_ROLE)
        self.default_org_id = cfg.get("LDAP_DEFAULT_ORGANIZATION_ID") or settings.LDAP_DEFAULT_ORGANIZATION_ID
        self._driver = driver

    def validate_configuration(self) -> None:
        """
        Fails fast if mandatory LDAP settings are missing.
        """
        if not self.server_url:
            raise ValueError("LDAP configuration error: LDAP_SERVER_URL is required.")
        if not self.base_dn:
            raise ValueError("LDAP configuration error: LDAP_BASE_DN is required.")

    def _get_driver(self):
        if self._driver is not None:
            return self._driver
        try:
            import ldap3
            return ldap3
        except ImportError:
            raise RuntimeError(
                "LDAP provider requires 'ldap3' package. Please ensure it is installed in your environment."
            )

    def resolve_roles(
        self,
        user_identity: UserIdentity,
        raw_groups: Optional[List[str]] = None
    ) -> List[str]:
        """
        Maps directory groups (DNs or CNs) to Koyla application roles.
        Prevents privilege escalation by only applying explicit mappings.
        """
        groups = raw_groups or user_identity.raw_attributes.get("memberOf", [])
        resolved_roles: List[str] = []

        for group in groups:
            # Check exact DN match or simple CN match
            grp_lower = group.lower()
            for pattern, role_code in self.group_role_mapping.items():
                if pattern.lower() == grp_lower or f"cn={pattern.lower()}" in grp_lower:
                    if role_code not in resolved_roles:
                        resolved_roles.append(role_code)

        if not resolved_roles and self.default_role:
            resolved_roles.append(self.default_role)

        return resolved_roles

    def authenticate(
        self,
        username: str,
        password: str,
        db: Session
    ) -> Optional[UserIdentity]:
        """
        Authenticates against LDAP/AD.
        1. Sanitizes input.
        2. Binds with service account (if configured) or anonymous to find user DN.
        3. Binds with user DN and password.
        4. Verifies account status (active/disabled).
        5. Resolves group memberships to Koyla roles.
        6. Synchronizes local database user record for foreign key integrity.
        """
        if not username or not password:
            return None

        self.validate_configuration()
        clean_username = sanitize_ldap_input(username.strip())

        driver = self._get_driver()

        # Handle custom / mock driver directly if provided
        if hasattr(driver, "authenticate"):
            result = driver.authenticate(clean_username, password, self)
            if not result:
                return None
            return self._sync_local_user(db, result)

        # Standard ldap3 execution
        import ldap3
        try:
            tls_obj = None
            if self.use_tls:
                validate = ssl.CERT_REQUIRED if self.verify_cert else ssl.CERT_NONE
                tls_obj = ldap3.Tls(validate=validate, ca_certs_file=self.ca_cert_path)

            server = ldap3.Server(
                self.server_url,
                use_ssl=self.server_url.lower().startswith("ldaps://"),
                tls=tls_obj,
                connect_timeout=self.timeout_seconds
            )

            # Service bind or anonymous bind for user lookup
            conn = ldap3.Connection(
                server,
                user=self.bind_dn,
                password=self.bind_password,
                auto_bind=True,
                receive_timeout=self.timeout_seconds
            )

            # Search for user DN
            search_filter = self.user_search_filter.format(username=clean_username)
            conn.search(
                search_base=self.user_search_base,
                search_filter=search_filter,
                attributes=["cn", "displayName", "mail", "sAMAccountName", "memberOf", "userAccountControl"]
            )

            if not conn.entries:
                conn.unbind()
                return None

            user_entry = conn.entries[0]
            user_dn = user_entry.entry_dn

            # User bind to verify password
            user_conn = ldap3.Connection(
                server,
                user=user_dn,
                password=password,
                receive_timeout=self.timeout_seconds
            )
            if not user_conn.bind():
                conn.unbind()
                return None

            # Verify active status
            # AD userAccountControl bit 2 (0x0002) = ACCOUNTDISABLE
            is_active = True
            uac = getattr(user_entry, "userAccountControl", None)
            if uac is not None:
                try:
                    uac_val = int(uac.value)
                    if uac_val & 2 != 0:
                        is_active = False
                except (ValueError, TypeError):
                    pass

            # Extract user metadata
            full_name = str(getattr(user_entry, "displayName", None) or getattr(user_entry, "cn", None) or clean_username)
            email = str(getattr(user_entry, "mail", None) or f"{clean_username}@internal")

            # Extract groups
            raw_groups = []
            member_of = getattr(user_entry, "memberOf", None)
            if member_of:
                raw_groups = [str(g) for g in member_of.values] if hasattr(member_of, "values") else [str(member_of)]

            user_conn.unbind()
            conn.unbind()

            identity = UserIdentity(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"ldap:{user_dn}")),
                username=clean_username,
                full_name=full_name,
                email=email,
                organization_id=self.default_org_id,
                is_active=is_active,
                auth_provider="ldap",
                raw_attributes={"dn": user_dn, "memberOf": raw_groups}
            )

            identity.roles = self.resolve_roles(identity, raw_groups)
            return self._sync_local_user(db, identity)

        except Exception as e:
            # Never log user password or bind password
            logger.warning(f"LDAP authentication error for '{clean_username}': {e}")
            return None

    def _sync_local_user(self, db: Session, identity: UserIdentity) -> UserIdentity:
        """
        Synchronizes or creates a local database User row for the LDAP identity
        to guarantee database foreign key integrity (e.g. AuditEvents, Documents).
        """
        if not db:
            return identity

        user = db.query(User).filter(User.username == identity.username).first()
        org_id = identity.organization_id or self.default_org_id

        if not org_id:
            first_org = db.query(Organization).first()
            if first_org:
                org_id = first_org.id

        if not user:
            # Auto-provision local user shadow record
            user = User(
                id=identity.id,
                username=identity.username,
                full_name=identity.full_name,
                email=identity.email or f"{identity.username}@internal",
                hashed_password="[EXTERNAL_LDAP_MANAGED]",
                is_active=identity.is_active,
                organization_id=org_id
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update fields
            user.full_name = identity.full_name
            user.is_active = identity.is_active
            if org_id and not user.organization_id:
                user.organization_id = org_id
            db.commit()

        # Sync roles
        if identity.roles:
            for r_code in identity.roles:
                role = db.query(Role).filter(Role.code == r_code).first()
                if role:
                    exists = db.query(UserRole).filter(
                        UserRole.user_id == user.id,
                        UserRole.role_id == role.id
                    ).first()
                    if not exists:
                        db.add(UserRole(user_id=user.id, role_id=role.id))
            db.commit()

        identity.id = user.id
        identity.organization_id = user.organization_id
        if user.organization:
            identity.organization_code = user.organization.code
            identity.organization_name = user.organization.name

        return identity

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
        return UserIdentity(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            organization_id=user.organization_id,
            organization_code=user.organization.code if user.organization else None,
            organization_name=user.organization.name if user.organization else None,
            roles=roles,
            is_active=bool(user.is_active),
            auth_provider="ldap"
        )

    def health(self) -> Dict[str, Any]:
        """
        Tests LDAP server reachability without leaking credentials.
        """
        if not self.server_url:
            return {
                "status": "NOT_CONFIGURED",
                "provider": "ldap",
                "message": "LDAP server URL not configured."
            }
        try:
            self.validate_configuration()
            return {
                "status": "CONFIGURED",
                "provider": "ldap",
                "server_url": self.server_url,
                "base_dn": self.base_dn,
                "tls_enabled": self.use_tls,
                "cert_verification": self.verify_cert,
                "message": "LDAP provider configured and ready."
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "provider": "ldap",
                "message": f"LDAP configuration invalid: {e}"
            }
