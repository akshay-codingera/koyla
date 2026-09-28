import re
import urllib.parse
from typing import Dict, Any, Optional
from app.services.adapters.exceptions import ExternalSystemSecurityError

SENSITIVE_KEY_PATTERNS = re.compile(r"(secret|password|token|api_?key|credential|private|auth_?header)", re.IGNORECASE)

BLOCKED_SCHEMES = {"file", "ftp", "gopher", "data", "javascript", "expect", "php", "dict"}
DISALLOWED_INTERNAL_HOSTS = {"169.254.169.254", "metadata.google.internal"}  # Cloud metadata endpoints

def validate_endpoint_url(
    url: Optional[str],
    enforce_https: bool = False,
    allow_local_for_testing: bool = True
) -> str:
    """
    Validates external system endpoint URL to prevent SSRF, protocol smuggling,
    and credential leakage via URL-embedded authentication.
    """
    if not url or not isinstance(url, str):
        raise ExternalSystemSecurityError("External system endpoint URL must be a non-empty string.")

    url = url.strip()
    try:
        parsed = urllib.parse.urlsplit(url)
    except Exception as e:
        raise ExternalSystemSecurityError(f"Invalid URL structure: {e}")

    scheme = parsed.scheme.lower()
    if scheme in BLOCKED_SCHEMES:
        raise ExternalSystemSecurityError(f"Prohibited URL scheme '{scheme}' detected. Only HTTP/HTTPS are allowed.")

    if scheme not in ("http", "https"):
        raise ExternalSystemSecurityError(f"Unsupported URL scheme '{scheme}'. Must be http or https.")

    if enforce_https and scheme != "https":
        raise ExternalSystemSecurityError("Security policy strictly enforces HTTPS for enterprise system endpoints.")

    if not parsed.hostname:
        raise ExternalSystemSecurityError("External endpoint URL must contain a valid hostname or IP address.")

    hostname = parsed.hostname.lower()
    if hostname in DISALLOWED_INTERNAL_HOSTS:
        raise ExternalSystemSecurityError(f"SSRF violation: Hostname '{hostname}' is prohibited.")

    if not allow_local_for_testing and hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise ExternalSystemSecurityError(f"Production security policy prohibits loopback target '{hostname}'.")

    # Strip any embedded credentials (e.g., http://user:pass@host)
    if parsed.username or parsed.password:
        clean_netloc = parsed.hostname
        if parsed.port:
            clean_netloc = f"{clean_netloc}:{parsed.port}"
        url = urllib.parse.urlunsplit((parsed.scheme, clean_netloc, parsed.path, parsed.query, parsed.fragment))

    return url


def sanitize_credentials(data: Any) -> Any:
    """
    Deep-sanitizes dictionaries and data structures to prevent token/secret leakage
    in health telemetry, audit trails, and logs.
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if SENSITIVE_KEY_PATTERNS.search(str(k)):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_credentials(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_credentials(item) for item in data]
    return data


def sanitize_url_for_logging(url: Optional[str]) -> Optional[str]:
    """
    Strips embedded credentials and query strings from URLs for safe logging.
    """
    if not url:
        return None
    try:
        parsed = urllib.parse.urlsplit(url)
        clean_netloc = parsed.hostname or ""
        if parsed.port:
            clean_netloc = f"{clean_netloc}:{parsed.port}"
        # Strip query string and fragment to avoid leaking tokens passed in URLs
        return urllib.parse.urlunsplit((parsed.scheme, clean_netloc, parsed.path, "", ""))
    except Exception:
        return "[UNPARSEABLE_URL]"
