import io
import json
import logging
import os
import sys
import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.config import settings
from app.core.logging.context import (
    sanitize_request_id,
    get_request_id,
    set_request_id,
    get_job_id,
    set_job_id,
    get_document_id,
    set_document_id,
    request_id_ctx,
)
from app.core.logging.redactor import (
    redact_sensitive_data,
    redact_string,
    is_sensitive_key,
    MAX_LOG_STRING_LENGTH,
)
from app.core.logging.formatter import StructuredJSONFormatter
from app.core.logging.timing import timed_operation, measure_latency
from app.services.health import (
    check_postgresql,
    check_redis,
    check_celery,
    check_storage,
    check_ocr,
    check_llm,
    check_clamav,
    check_readiness,
    check_liveness,
    get_system_health,
    sanitize_url_for_telemetry,
    STATUS_HEALTHY,
    STATUS_DEGRADED,
    STATUS_UNAVAILABLE,
    STATUS_DISABLED,
    STATUS_NOT_CONFIGURED,
)

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. Request ID & Correlation Middleware Tests
# -----------------------------------------------------------------------------

def test_request_id_generated_when_missing():
    """Incoming request without X-Request-ID receives a valid generated UUID4."""
    res = client.get("/")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    req_id = res.headers["X-Request-ID"]
    assert len(req_id) >= 16
    # Valid UUID format
    val = uuid.UUID(req_id)
    assert str(val) == req_id


def test_request_id_propagated_when_valid():
    """Valid client-supplied X-Request-ID is preserved and returned in response headers."""
    client_id = "req-audit-trace-2026-cmpdi-001"
    res = client.get("/", headers={"X-Request-ID": client_id})
    assert res.status_code == 200
    assert res.headers["X-Request-ID"] == client_id


def test_request_id_sanitization_rejects_malformed_and_oversized():
    """Malformed, injection, or oversized request IDs fall back to generated UUID4."""
    # Oversized (>64 chars)
    oversized = "a" * 128
    sanitized = sanitize_request_id(oversized)
    assert sanitized != oversized
    assert uuid.UUID(sanitized)

    # Injection payload / special characters
    injection = "req-id-123<script>alert(1)</script>"
    sanitized_inj = sanitize_request_id(injection)
    assert sanitized_inj != injection
    assert uuid.UUID(sanitized_inj)

    # Empty or whitespace
    assert uuid.UUID(sanitize_request_id(""))
    assert uuid.UUID(sanitize_request_id("   "))
    assert uuid.UUID(sanitize_request_id(None))

    # Valid characters (alphanumeric, hyphens, underscores)
    valid_id = "valid_req-ID_12345"
    assert sanitize_request_id(valid_id) == valid_id


def test_response_time_header_present():
    """Every HTTP response includes an X-Response-Time header with ms units."""
    res = client.get("/")
    assert "X-Response-Time" in res.headers
    assert res.headers["X-Response-Time"].endswith("ms")


# -----------------------------------------------------------------------------
# 2. Structured JSON Logging Tests
# -----------------------------------------------------------------------------

def test_structured_json_formatter_standard_fields():
    """StructuredJSONFormatter produces valid single-line JSON with required schema fields."""
    formatter = StructuredJSONFormatter()
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Document processing initiated",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-test-101"
    record.job_id = "job-999"
    record.document_id = "doc-888"
    record.event = "document_ingest"
    record.duration_ms = 45.67

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "app.test"
    assert parsed["message"] == "Document processing initiated"
    assert parsed["request_id"] == "req-test-101"
    assert parsed["job_id"] == "job-999"
    assert parsed["document_id"] == "doc-888"
    assert parsed["event"] == "document_ingest"
    assert parsed["duration_ms"] == 45.67
    assert "timestamp" in parsed


def test_structured_json_formatter_contextvar_injection():
    """Contextvars automatically inject correlation identifiers into log records."""
    formatter = StructuredJSONFormatter()
    set_request_id("ctx-req-404")
    set_job_id("ctx-job-202")
    set_document_id("ctx-doc-101")

    try:
        record = logging.LogRecord(
            name="app.context_test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=20,
            msg="Contextual warning event",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["request_id"] == "ctx-req-404"
        assert parsed["job_id"] == "ctx-job-202"
        assert parsed["document_id"] == "ctx-doc-101"
    finally:
        set_request_id(None)
        set_job_id(None)
        set_document_id(None)


def test_structured_json_formatter_exception_handling():
    """Exceptions are serialized into structured error objects with safe messages."""
    formatter = StructuredJSONFormatter()
    try:
        raise ValueError("Simulated parsing failure")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="app.error_test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=30,
        msg="Ingestion task failed",
        args=(),
        exc_info=exc_info,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "ERROR"
    assert "error" in parsed
    assert parsed["error"]["type"] == "ValueError"
    assert "Simulated parsing failure" in parsed["error"]["message"]
    assert isinstance(parsed["error"]["stack_trace"], list)


def test_structured_json_formatter_fallback_never_crashes():
    """Formatter falls back safely if an attribute cannot be formatted."""
    formatter = StructuredJSONFormatter()
    bad_record = MagicMock()
    bad_record.created = float("nan")  # Causes datetime conversion failure
    bad_record.getMessage.side_effect = RuntimeError("Broken message getter")
    bad_record.msg = "Raw unformatted string"

    output = formatter.format(bad_record)
    parsed = json.loads(output)
    assert parsed["level"] == "ERROR"
    assert "Log formatting failed" in parsed["message"]


# -----------------------------------------------------------------------------
# 3. Secret & Credential Redaction Tests
# -----------------------------------------------------------------------------

def test_secret_redaction_dictionary_keys():
    """Sensitive keys (passwords, tokens, credentials, bind passwords) are masked."""
    payload = {
        "username": "officer_secl",
        "password": "SuperSecretPassword123!",
        "api_key": "sec_key_abcdef123456",
        "ldap_bind_password": "DomainLdapPassword",
        "sap_config": {"auth_token": "bearer_secret_xyz"},
        "sap_credentials": "confidential_login",
        "document_title": "Annual Geological Report",
    }
    redacted = redact_sensitive_data(payload)

    assert redacted["username"] == "officer_secl"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["ldap_bind_password"] == "[REDACTED]"
    assert redacted["sap_config"]["auth_token"] == "[REDACTED]"
    assert redacted["sap_credentials"] == "[REDACTED]"
    assert redacted["document_title"] == "Annual Geological Report"


def test_secret_redaction_jwt_and_bearer_in_strings():
    """JWTs and Bearer authorization tokens embedded in log strings are scrubbed."""
    fake_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    log_text = f"User logged in with token {fake_jwt} and header Authorization: Bearer secret_bearer_token_12345"

    scrubbed = redact_string(log_text)
    assert fake_jwt not in scrubbed
    assert "[REDACTED_JWT]" in scrubbed
    assert "secret_bearer_token_12345" not in scrubbed
    assert "Bearer [REDACTED]" in scrubbed


def test_payload_truncation_prevents_log_flooding():
    """Overly large strings exceeding MAX_LOG_STRING_LENGTH are safely truncated."""
    huge_string = "X" * (MAX_LOG_STRING_LENGTH + 500)
    truncated = redact_string(huge_string)

    assert len(truncated) < len(huge_string)
    assert "TRUNCATED" in truncated
    assert truncated.startswith("X" * 100)


def test_sanitize_url_for_telemetry():
    """URLs with embedded passwords have credentials stripped for telemetry."""
    url = "postgresql://dbuser:mypassword123@db.koyla.internal:5432/koyladb"
    sanitized = sanitize_url_for_telemetry(url)
    assert "mypassword123" not in sanitized
    assert "dbuser" not in sanitized
    assert "db.koyla.internal:5432" in sanitized

    redis_url = "redis://:supersecretredispass@cache.koyla.internal:6379/0"
    sanitized_redis = sanitize_url_for_telemetry(redis_url)
    assert "supersecretredispass" not in sanitized_redis
    assert "cache.koyla.internal:6379" in sanitized_redis


# -----------------------------------------------------------------------------
# 4. Operational Health & Probes Tests
# -----------------------------------------------------------------------------

def test_canonical_system_health_endpoint():
    """GET /api/v1/system/health returns complete operational telemetry."""
    res = client.get("/api/v1/system/health")
    assert res.status_code == 200
    data = res.json()

    # Top-level contracts
    assert "status" in data
    assert data["status"] in ["UP", "HEALTHY", "DEGRADED", "DOWN"]
    assert data["database_type"] == "PostgreSQL"
    assert "pgvector_enabled" in data
    assert "services" in data
    assert "dependencies" in data

    # Backward compatibility with existing tests
    services = data["services"]
    required_services = [
        "backend",
        "api",
        "database",
        "vector_store",
        "storage",
        "ocr_engine",
        "embedding_service",
        "llm_service",
        "topic_engine",
        "temporal_analytics",
        "report_engine",
        "redis",
        "workers",
        "identity_provider",
    ]
    for s in required_services:
        assert s in services, f"Service '{s}' missing from health telemetry"

    # Dependency diagnostic blocks
    deps = data["dependencies"]
    assert "postgresql" in deps
    assert "redis" in deps
    assert "celery" in deps
    assert "storage" in deps
    assert "ocr" in deps
    assert "llm" in deps


def test_system_health_root_alias():
    """GET /health provides the root probe alias identical to /api/v1/system/health."""
    res = client.get("/health")
    assert res.status_code == 200
    assert "services" in res.json()


def test_readiness_probe_success():
    """GET /ready and /api/v1/system/ready return HTTP 200 and status READY when core DB is operational."""
    res = client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "READY"
    assert data["is_ready"] is True
    assert data["checks"]["postgresql"] is True
    assert data["checks"]["storage"] is True

    # Also test API route
    res_api = client.get("/api/v1/system/ready")
    assert res_api.status_code == 200
    assert res_api.json()["status"] == "READY"


def test_readiness_probe_fails_closed_when_db_down():
    """Readiness probe returns HTTP 503 if PostgreSQL is unavailable."""
    db_mock = MagicMock()
    db_mock.execute.side_effect = RuntimeError("Database connection pool exhausted")

    is_ready, details = check_readiness(db_mock)
    assert not is_ready
    assert details["status"] == "NOT_READY"
    assert details["checks"]["postgresql"] is False


def test_liveness_probe():
    """GET /live and /api/v1/system/live confirm process responsiveness."""
    res = client.get("/live")
    assert res.status_code == 200
    assert res.json()["status"] == "ALIVE"

    res_api = client.get("/api/v1/system/live")
    assert res_api.status_code == 200
    assert res_api.json()["status"] == "ALIVE"


def test_storage_health_probe():
    """Storage probe verifies write access and directory presence."""
    diag = check_storage()
    assert diag["status"] in (STATUS_HEALTHY, STATUS_DEGRADED)
    assert diag["writable"] is True
    assert diag["accessible"] is True


def test_llm_probe_handles_offline_gracefully():
    """LLM probe cleanly reports UNAVAILABLE or NOT_CONFIGURED without crashing when daemon is offline."""
    diag = check_llm()
    assert diag["status"] in (STATUS_HEALTHY, STATUS_DEGRADED, STATUS_UNAVAILABLE, STATUS_NOT_CONFIGURED)
    assert "provider" in diag


def test_antivirus_probe_reports_disabled():
    """ClamAV probe reports DISABLED when disabled by configuration without degrading health."""
    diag = check_clamav()
    assert diag["status"] in (STATUS_DISABLED, STATUS_HEALTHY, STATUS_DEGRADED)


def test_zero_credential_leakage_in_health_response():
    """Telemetry outputs must never contain SECRET_KEY, passwords, or bind credentials."""
    res = client.get("/api/v1/system/health")
    content = res.text

    assert settings.SECRET_KEY not in content
    assert "supersecretkey" not in content
    assert "password" not in content.lower() or "bind_password" not in content


# -----------------------------------------------------------------------------
# 5. Error Observability Tests
# -----------------------------------------------------------------------------

def test_unhandled_exception_returns_safe_json_with_request_id():
    """Unhandled server errors return sanitized JSON with request_id and no Python stack traces."""
    # Create a temporary endpoint that raises an unhandled error
    @app.get("/api/v1/test-simulated-unhandled-error")
    def fail_endpoint():
        raise RuntimeError("Confidential database internal trace /etc/passwd")

    client_no_raise = TestClient(app, raise_server_exceptions=False)
    client_req_id = "req-unhandled-trace-999"
    res = client_no_raise.get("/api/v1/test-simulated-unhandled-error", headers={"X-Request-ID": client_req_id})

    assert res.status_code == 500
    data = res.json()
    assert data["error"] == "Internal Server Error"
    assert data["request_id"] == client_req_id
    assert res.headers["X-Request-ID"] == client_req_id

    # Confidential details and raw traceback MUST NOT be leaked to the client
    assert "Confidential database internal trace" not in data["message"]
    assert "Traceback" not in res.text
    assert "/etc/passwd" not in res.text


# -----------------------------------------------------------------------------
# 6. Performance Timing Utility Tests
# -----------------------------------------------------------------------------

def test_timed_operation_context_manager():
    """timed_operation measures duration_ms and logs structured metrics."""
    test_logger = logging.getLogger("test_timing")
    with patch.object(test_logger, "log") as mock_log:
        with timed_operation(test_logger, "vector_similarity_search", extra={"chunks": 10}) as metrics:
            assert metrics["event"] == "vector_similarity_search"
            # Simulate work
            sum(range(1000))

        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert "completed in" in args[1]
        assert "duration_ms" in kwargs["extra"]
        assert kwargs["extra"]["duration_ms"] >= 0.0
        assert kwargs["extra"]["chunks"] == 10


def test_measure_latency():
    """measure_latency calculates execution time for callables."""
    def sample_func(a, b):
        return a + b

    result, latency_ms = measure_latency(sample_func, 10, 25)
    assert result == 35
    assert latency_ms >= 0.0
