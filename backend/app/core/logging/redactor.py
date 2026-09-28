import re
from typing import Any, Dict, List, Set, Union

MAX_LOG_STRING_LENGTH = 1024
REDACTED_PLACEHOLDER = "[REDACTED]"

# Case-insensitive substring match for sensitive dictionary keys
SENSITIVE_KEY_SUBSTRINGS: Set[str] = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "credential",
    "bind_pw",
    "bind_password",
    "private_key",
    "jwt",
    "cookie",
    "session",
    "access_token",
    "refresh_token",
}

# Regex to detect JWT tokens in strings (header.payload.signature)
JWT_REGEX = re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}")

# Regex to detect Bearer tokens
BEARER_REGEX = re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{15,}")


def is_sensitive_key(key: str) -> bool:
    """Checks if a dictionary key name indicates sensitive contents."""
    k_lower = str(key).lower()
    return any(sub in k_lower for sub in SENSITIVE_KEY_SUBSTRINGS)


def redact_string(val: str, max_length: int = MAX_LOG_STRING_LENGTH) -> str:
    """
    Sanitizes string values: masks JWTs and bearer tokens, and truncates overly large values.
    """
    if not isinstance(val, str):
        return val

    # Mask JWTs
    val = JWT_REGEX.sub("[REDACTED_JWT]", val)

    # Mask Bearer tokens
    val = BEARER_REGEX.sub("Bearer [REDACTED]", val)

    # Truncate if too long to prevent log flooding
    if len(val) > max_length:
        return val[:max_length] + f"... [TRUNCATED {len(val) - max_length} chars]"

    return val


def redact_sensitive_data(obj: Any, max_depth: int = 5) -> Any:
    """
    Recursively redacts sensitive values and truncates oversized payloads from logging objects.
    Safe against cycles via max_depth limit.
    """
    if max_depth <= 0:
        return "[DEPTH_LIMIT_EXCEEDED]"

    if isinstance(obj, dict):
        cleaned_dict: Dict[str, Any] = {}
        for k, v in obj.items():
            if is_sensitive_key(k):
                cleaned_dict[k] = REDACTED_PLACEHOLDER
            else:
                cleaned_dict[k] = redact_sensitive_data(v, max_depth=max_depth - 1)
        return cleaned_dict

    elif isinstance(obj, (list, tuple, set)):
        return [redact_sensitive_data(item, max_depth=max_depth - 1) for item in obj]

    elif isinstance(obj, str):
        return redact_string(obj)

    elif isinstance(obj, (int, float, bool)) or obj is None:
        return obj

    else:
        # Generic object representation
        try:
            return redact_string(str(obj))
        except Exception:
            return "[UNPRINTABLE_OBJECT]"
