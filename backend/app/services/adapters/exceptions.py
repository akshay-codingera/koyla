"""
Enterprise System Integration Adapter Exceptions.
Defines explicit, typed error states for external enterprise system interactions
(SAP, CoalNet, DMS) without exposing sensitive tokens or internal tracebacks.
"""

class AdapterError(Exception):
    """Base exception for all enterprise adapter operations."""
    def __init__(self, message: str, system_name: str = "unknown"):
        super().__init__(message)
        self.system_name = system_name
        self.message = message


class ExternalSystemNotConfiguredError(AdapterError):
    """Raised when an external system adapter is invoked without required configuration."""
    pass


class ExternalSystemUnavailableError(AdapterError):
    """Raised when an external system is unreachable, down, or returning 5xx responses."""
    pass


class ExternalSystemAuthenticationError(AdapterError):
    """Raised when authentication against an external enterprise system fails."""
    pass


class ExternalSystemTimeoutError(AdapterError):
    """Raised when an external enterprise system call exceeds its configured timeout deadline."""
    pass


class ExternalSystemSecurityError(AdapterError):
    """Raised when an external system endpoint fails security checks (SSRF, forbidden scheme, etc.)."""
    pass
