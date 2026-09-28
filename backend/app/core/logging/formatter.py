import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.logging.context import (
    get_request_id,
    get_user_id,
    get_job_id,
    get_document_id,
)
from app.core.logging.redactor import redact_sensitive_data, redact_string

# Standard LogRecord attributes that should not be dumped into "extra"
STANDARD_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}


class StructuredJSONFormatter(logging.Formatter):
    """
    Standardized, high-performance JSON log formatter for backend application logs.
    Captures request correlation, processing job context, timing, and error details,
    while systematically redacting sensitive credentials and passwords.
    """

    def format(self, record: logging.LogRecord) -> str:
        try:
            # 1. Base log structure
            log_data: Dict[str, Any] = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": redact_string(record.getMessage()),
            }

            # 2. Contextual identifiers (contextvars or record attributes)
            request_id = getattr(record, "request_id", None) or get_request_id()
            if request_id:
                log_data["request_id"] = request_id

            job_id = getattr(record, "job_id", None) or get_job_id()
            if job_id:
                log_data["job_id"] = job_id

            document_id = getattr(record, "document_id", None) or get_document_id()
            if document_id:
                log_data["document_id"] = document_id

            user_id = getattr(record, "user_id", None) or get_user_id()
            if user_id:
                log_data["user_id"] = user_id

            # 3. Known operational extras
            if hasattr(record, "event") and record.event:
                log_data["event"] = record.event

            if hasattr(record, "duration_ms") and record.duration_ms is not None:
                log_data["duration_ms"] = round(float(record.duration_ms), 2)

            # 4. Custom extras passed via extra={...}
            extra_data = {}
            for key, val in record.__dict__.items():
                if key not in STANDARD_RECORD_ATTRS and key not in log_data:
                    extra_data[key] = val

            if extra_data:
                log_data["extra"] = redact_sensitive_data(extra_data)

            # 5. Exception & stack trace handling
            if record.exc_info and record.exc_info[0]:
                exc_type = record.exc_info[0].__name__
                exc_val = str(record.exc_info[1])
                log_data["error"] = {
                    "type": exc_type,
                    "message": redact_string(exc_val),
                    "stack_trace": traceback.format_exception(*record.exc_info),
                }

            return json.dumps(log_data, default=str)

        except Exception as e:
            # Fallback guarantee: logging MUST NEVER crash the host application
            fallback = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "ERROR",
                "logger": "app.core.logging.formatter",
                "message": f"Log formatting failed: {str(e)}",
                "raw_message": str(getattr(record, "msg", "")),
            }
            return json.dumps(fallback)
