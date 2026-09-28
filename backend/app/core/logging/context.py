import re
import uuid
from contextvars import ContextVar
from typing import Optional

# Request & execution context variables for distributed correlation
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
job_id_ctx: ContextVar[Optional[str]] = ContextVar("job_id", default=None)
document_id_ctx: ContextVar[Optional[str]] = ContextVar("document_id", default=None)

# Pattern: alphanumeric, hyphens, and underscores, between 1 and 64 characters
REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


def sanitize_request_id(incoming_id: Optional[str]) -> str:
    """
    Validates and sanitizes incoming Request ID header.
    Rejects malformed, oversized, or suspicious injection payloads and falls back to a clean UUID4.
    """
    if incoming_id and isinstance(incoming_id, str):
        cleaned = incoming_id.strip()
        if len(cleaned) <= 64 and REQUEST_ID_REGEX.match(cleaned):
            return cleaned
    return str(uuid.uuid4())


def get_request_id() -> Optional[str]:
    """Returns current request ID from context if set."""
    return request_id_ctx.get()


def set_request_id(req_id: Optional[str]) -> None:
    """Sets current request ID in context."""
    request_id_ctx.set(req_id)


def get_job_id() -> Optional[str]:
    """Returns current job ID from context if set."""
    return job_id_ctx.get()


def set_job_id(job_id: Optional[str]) -> None:
    """Sets current job ID in context."""
    job_id_ctx.set(job_id)


def get_document_id() -> Optional[str]:
    """Returns current document ID from context if set."""
    return document_id_ctx.get()


def set_document_id(doc_id: Optional[str]) -> None:
    """Sets current document ID in context."""
    document_id_ctx.set(doc_id)


def get_user_id() -> Optional[str]:
    """Returns current user ID from context if set."""
    return user_id_ctx.get()


def set_user_id(uid: Optional[str]) -> None:
    """Sets current user ID in context."""
    user_id_ctx.set(uid)
