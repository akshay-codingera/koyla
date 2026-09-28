from typing import Optional
from app.core.config import settings
from app.services.identity.base import IdentityProvider, UserIdentity
from app.services.identity.local_provider import LocalIdentityProvider
from app.services.identity.ldap_provider import LDAPIdentityProvider

_cached_providers = {}

def get_identity_provider(provider_name: Optional[str] = None) -> IdentityProvider:
    """
    Factory resolving the active identity provider.
    Fails fast if an unsupported identity provider is configured.
    """
    name = (provider_name or settings.IDENTITY_PROVIDER).lower().strip()
    if name == "local":
        return LocalIdentityProvider()
    elif name == "ldap":
        ldap_prov = LDAPIdentityProvider()
        ldap_prov.validate_configuration()
        return ldap_prov
    else:
        raise ValueError(
            f"Invalid IDENTITY_PROVIDER '{name}'. Supported identity providers: 'local', 'ldap'."
        )
