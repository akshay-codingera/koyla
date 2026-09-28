from app.services.adapters.base import (
    ExternalSystemAdapter,
    AdapterStatus,
    ExternalMetadata,
    ExternalRecord,
    ExternalDocument,
)
from app.services.adapters.exceptions import (
    AdapterError,
    ExternalSystemNotConfiguredError,
    ExternalSystemUnavailableError,
    ExternalSystemAuthenticationError,
    ExternalSystemTimeoutError,
    ExternalSystemSecurityError,
)
from app.services.adapters.security import (
    validate_endpoint_url,
    sanitize_credentials,
    sanitize_url_for_logging,
)
from app.services.adapters.sap_adapter import SAPAdapter, MockSAPAdapter
from app.services.adapters.coalnet_adapter import CoalNetAdapter, MockCoalNetAdapter
from app.services.adapters.dms_adapter import DMSAdapter, MockDMSAdapter
from app.services.adapters.manager import ExternalSystemManager, get_system_manager

__all__ = [
    "ExternalSystemAdapter",
    "AdapterStatus",
    "ExternalMetadata",
    "ExternalRecord",
    "ExternalDocument",
    "AdapterError",
    "ExternalSystemNotConfiguredError",
    "ExternalSystemUnavailableError",
    "ExternalSystemAuthenticationError",
    "ExternalSystemTimeoutError",
    "ExternalSystemSecurityError",
    "validate_endpoint_url",
    "sanitize_credentials",
    "sanitize_url_for_logging",
    "SAPAdapter",
    "MockSAPAdapter",
    "CoalNetAdapter",
    "MockCoalNetAdapter",
    "DMSAdapter",
    "MockDMSAdapter",
    "ExternalSystemManager",
    "get_system_manager",
]
