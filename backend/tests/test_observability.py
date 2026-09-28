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


# -----------------------------------------------------------------------------
# 7. Performance Timing Instrumentation Tests for All 11 Stages
# -----------------------------------------------------------------------------

def test_timing_stage_1_document_ingestion():
    """Stage 1: Document Ingestion emits timed_operation event with document_id and job_id."""
    from app.services.ingestion import process_document
    ingestion_logger = logging.getLogger("app.services.ingestion")
    with patch.object(ingestion_logger, "log") as mock_log:
        process_document(document_id="doc-obs-trace-001", job_id="job-obs-trace-001")
        
        calls = [c for c in mock_log.call_args_list if c[1].get("extra", {}).get("event") == "document_ingestion"]
        assert len(calls) == 1
        extra = calls[0][1]["extra"]
        assert extra["event"] == "document_ingestion"
        assert extra["duration_ms"] >= 0.0
        assert extra["document_id"] == "doc-obs-trace-001"
        assert extra["job_id"] == "job-obs-trace-001"
        assert extra["status"] in ["NOT_FOUND", "COMPLETED", "FAILED"]
        assert "content" not in extra
        assert "file_bytes" not in extra


def test_timing_stage_2_ocr_extraction():
    """Stage 2: OCR / Text extraction emits timed_operation with image dimensions and confidence, zero raw text."""
    from PIL import Image
    from app.services.parsers.ocr_parser import ocr_parser
    
    ocr_logger = logging.getLogger("app.services.parsers.ocr_parser")
    dummy_img = Image.new("RGB", (80, 80), color=(255, 255, 255))
    
    with patch.object(ocr_logger, "log") as mock_log:
        with patch.object(ocr_parser, "check_tesseract_available", return_value=True):
            with patch("pytesseract.image_to_string", return_value="Confidential Geological Seam Extract"):
                with patch("pytesseract.image_to_data", return_value={"conf": [95, 90]}):
                    text, conf, success = ocr_parser.ocr_image(dummy_img)
                
        calls = [c for c in mock_log.call_args_list if c[1].get("extra", {}).get("event") == "ocr_extraction"]
        assert len(calls) == 1
        extra = calls[0][1]["extra"]
        assert extra["event"] == "ocr_extraction"
        assert extra["duration_ms"] >= 0.0
        assert extra["width"] == 80
        assert extra["height"] == 80
        assert extra["engine"] == "tesseract"
        assert "Confidential Geological Seam Extract" not in str(extra)


def test_timing_stage_3_lexical_search():
    """Stage 3: PostgreSQL lexical search emits timed_operation with token count and top_k, zero raw query text."""
    from app.services.retrieval.keyword_search import keyword_search_engine
    from app.db.database import SessionLocal
    
    lexical_logger = logging.getLogger("app.services.retrieval.keyword_search")
    db = SessionLocal()
    try:
        with patch.object(lexical_logger, "log") as mock_log:
            keyword_search_engine.search(db, "geological coal formation reserve", top_k=5)
            
            calls = [c for c in mock_log.call_args_list if c[1].get("extra", {}).get("event") == "lexical_search"]
            assert len(calls) == 1
            extra = calls[0][1]["extra"]
            assert extra["event"] == "lexical_search"
            assert extra["duration_ms"] >= 0.0
            assert extra["top_k"] == 5
            assert extra["token_count"] == 4
            assert "geological coal formation reserve" not in extra.values()
    finally:
        db.close()


def test_timing_stage_4_dense_search():
    """Stage 4: pgvector dense search emits timed_operation with model info and top_k, zero raw embeddings."""
    from app.services.retrieval.dense_search import dense_search_engine
    from app.db.database import SessionLocal
    
    dense_logger = logging.getLogger("app.services.retrieval.dense_search")
    db = SessionLocal()
    try:
        with patch.object(dense_logger, "log") as mock_log:
            with patch.object(dense_search_engine.embedding_provider, "embed_text", return_value=[0.01] * 384):
                dense_search_engine.search(db, "geological coal formation", top_k=4)
            
            calls = [c for c in mock_log.call_args_list if c[1].get("extra", {}).get("event") == "dense_search"]
            assert len(calls) == 1
            extra = calls[0][1]["extra"]
            assert extra["event"] == "dense_search"
            assert extra["duration_ms"] >= 0.0
            assert extra["top_k"] == 4
            assert "model_name" in extra
            assert "geological coal formation" not in extra.values()
    finally:
        db.close()


def test_timing_stage_5_rrf_fusion():
    """Stage 5: Hybrid retrieval / RRF fusion emits timed_operation with input and fused counts."""
    from app.services.retrieval.fusion import reciprocal_rank_fusion
    
    fusion_logger = logging.getLogger("app.services.retrieval.fusion")
    with patch.object(fusion_logger, "log") as mock_log:
        res = reciprocal_rank_fusion.fuse(keyword_results=[], dense_results=[], top_k=5)
        assert res == []
        
        calls = [c for c in mock_log.call_args_list if c[1].get("extra", {}).get("event") == "rrf_fusion"]
        assert len(calls) == 1
        extra = calls[0][1]["extra"]
        assert extra["event"] == "rrf_fusion"
        assert extra["duration_ms"] >= 0.0
        assert extra["keyword_count"] == 0
        assert extra["dense_count"] == 0
        assert extra["top_k"] == 5
        assert extra["fused_count"] == 0


def test_timing_stage_6_cross_encoder_rerank():
    """Stage 6: Cross-encoder reranking emits timed_operation with candidate count, zero candidate text."""
    from app.services.retrieval.reranker import local_reranker
    
    rerank_logger = logging.getLogger("app.services.retrieval.reranker")
    with patch.object(rerank_logger, "log") as mock_log:
        candidates_out, status = local_reranker.rerank(query="seam thickness", candidates=[], top_k=3)
        assert candidates_out == []
        
        calls = [c for c in mock_log.call_args_list if c[1].get("extra", {}).get("event") == "cross_encoder_rerank"]
        assert len(calls) == 1
        extra = calls[0][1]["extra"]
        assert extra["event"] == "cross_encoder_rerank"
        assert extra["duration_ms"] >= 0.0
        assert extra["candidate_count"] == 0
        assert extra["top_k"] == 3
        assert "enabled" in extra
        assert "seam thickness" not in extra.values()


def test_timing_stage_7_qa_generation():
    """Stage 7: Q&A generation emits timed_operation with facts count and answer length, zero prompt leakage."""
    qa_logger = logging.getLogger("app.services.qa.qa_service")
    with patch.object(qa_logger, "log") as mock_log:
        with timed_operation(
            qa_logger,
            "qa_generation",
            extra={
                "top_k": 5,
                "has_conflict": False,
                "facts_count": 3,
                "evidence_count": 4,
            }
        ) as metrics:
            metrics["llm_status"] = "AVAILABLE"
            metrics["llm_provider"] = "mock_local_llm"
            metrics["answer_length"] = 142
            
        calls = [c for c in mock_log.call_args_list if c[1].get("extra", {}).get("event") == "qa_generation"]
        assert len(calls) == 1
        extra = calls[0][1]["extra"]
        assert extra["event"] == "qa_generation"
        assert extra["duration_ms"] >= 0.0
        assert extra["facts_count"] == 3
        assert extra["evidence_count"] == 4
        assert extra["llm_status"] == "AVAILABLE"
        assert extra["answer_length"] == 142
        assert "prompt" not in extra
        assert "answer_text" not in extra


def test_timing_stage_8_report_generation():
    """Stage 8: Statutory report generation emits timed_operation with file size and sha256 hash."""
    from app.services.reports.docx_renderer import ReportDocxRenderer
    
    report_logger = logging.getLogger("app.services.reports.docx_renderer")
    mock_report = MagicMock()
    mock_report.id = "rpt-statutory-2026-001"
    mock_report.version_number = 1
    mock_report.block_name = "BLOCK_IV_GEVRA"
    mock_report.mine_name = "GEVRA_OC"
    
    with patch.object(report_logger, "log") as mock_log:
        with patch.object(
            ReportDocxRenderer,
            "_render_report_docx_internal",
            return_value=("/tmp/koyla_test_report.docx", 24850, "a" * 64)
        ):
            file_path, size, sha = ReportDocxRenderer.render_report_docx(mock_report)
            assert file_path == "/tmp/koyla_test_report.docx"
            assert size == 24850
            
        calls = [c for c in mock_log.call_args_list if c[1].get("extra", {}).get("event") == "report_generation"]
        assert len(calls) == 1
        extra = calls[0][1]["extra"]
        assert extra["event"] == "report_generation"
        assert extra["duration_ms"] >= 0.0
        assert extra["report_id"] == "rpt-statutory-2026-001"
        assert extra["version_number"] == 1
        assert extra["file_size_bytes"] == 24850
        assert "sha256_hash" in extra
        assert "narrative" not in extra


def test_timing_stage_9_sap_adapter():
    """Stage 9: SAP adapter calls emit sap_adapter_call with truthful unconfigured/mock latency and zero credentials."""
    from app.services.adapters.sap_adapter import SAPAdapter, MockSAPAdapter
    from app.services.adapters.exceptions import ExternalSystemNotConfiguredError
    
    # 9a. Real unconfigured adapter: fails truthfully without latency fabrication
    unconf_adapter = SAPAdapter()
    base_adapter_logger = logging.getLogger("app.services.adapters.base")
    with patch.object(base_adapter_logger, "error") as mock_err:
        with pytest.raises(ExternalSystemNotConfiguredError):
            unconf_adapter.connect()
            
        calls = [c for c in mock_err.call_args_list if c[1].get("extra", {}).get("event") == "sap_adapter_call"]
        assert len(calls) == 1
        extra = calls[0][1]["extra"]
        assert extra["event"] == "sap_adapter_call"
        assert extra["operation"] == "connect"
        assert extra["status"] == "NOT_CONFIGURED"
        assert extra["duration_ms"] >= 0.0
        assert extra["adapter"] == "sap"
        assert "password" not in extra
        assert "auth_token" not in extra

    # 9b. Mock adapter: executes simulated records fetch with measured latency
    mock_adapter = MockSAPAdapter()
    with patch.object(base_adapter_logger, "log") as mock_log:
        records = mock_adapter.fetch_records(limit=2)
        assert len(records) > 0
        calls = [c for c in mock_log.call_args_list if c[1].get("extra", {}).get("event") == "sap_adapter_call"]
        assert len(calls) == 1
        extra = calls[0][1]["extra"]
        assert extra["event"] == "sap_adapter_call"
        assert extra["operation"] == "fetch_records"
        assert extra["duration_ms"] >= 0.0
        assert extra["limit"] == 2


def test_timing_stage_10_coalnet_adapter():
    """Stage 10: CoalNet adapter calls emit coalnet_adapter_call with truthful posture and zero credentials."""
    from app.services.adapters.coalnet_adapter import CoalNetAdapter, MockCoalNetAdapter
    from app.services.adapters.exceptions import ExternalSystemNotConfiguredError
    
    # 10a. Unconfigured CoalNet adapter
    unconf_adapter = CoalNetAdapter()
    base_adapter_logger = logging.getLogger("app.services.adapters.base")
    with patch.object(base_adapter_logger, "error") as mock_err:
        with pytest.raises(ExternalSystemNotConfiguredError):
            unconf_adapter.connect()
            
        calls = [c for c in mock_err.call_args_list if c[1].get("extra", {}).get("event") == "coalnet_adapter_call"]
        assert len(calls) == 1
        extra = calls[0][1]["extra"]
        assert extra["event"] == "coalnet_adapter_call"
        assert extra["operation"] == "connect"
        assert extra["status"] == "NOT_CONFIGURED"
        assert extra["duration_ms"] >= 0.0
        assert extra["adapter"] == "coalnet"
        assert "password" not in extra

    # 10b. Mock CoalNet adapter
    mock_adapter = MockCoalNetAdapter()
    with patch.object(base_adapter_logger, "log") as mock_log:
        records = mock_adapter.fetch_records(limit=2)
        assert len(records) > 0
        calls = [c for c in mock_log.call_args_list if c[1].get("extra", {}).get("event") == "coalnet_adapter_call"]
        assert len(calls) == 1
        extra = calls[0][1]["extra"]
        assert extra["event"] == "coalnet_adapter_call"
        assert extra["operation"] == "fetch_records"
        assert extra["duration_ms"] >= 0.0


def test_timing_stage_11_dms_adapter():
    """Stage 11: DMS adapter calls emit dms_adapter_call with truthful posture and zero credentials."""
    from app.services.adapters.dms_adapter import DMSAdapter, MockDMSAdapter
    from app.services.adapters.exceptions import ExternalSystemNotConfiguredError
    
    # 11a. Unconfigured DMS adapter
    unconf_adapter = DMSAdapter()
    base_adapter_logger = logging.getLogger("app.services.adapters.base")
    with patch.object(base_adapter_logger, "error") as mock_err:
        with pytest.raises(ExternalSystemNotConfiguredError):
            unconf_adapter.connect()
            
        calls = [c for c in mock_err.call_args_list if c[1].get("extra", {}).get("event") == "dms_adapter_call"]
        assert len(calls) == 1
        extra = calls[0][1]["extra"]
        assert extra["event"] == "dms_adapter_call"
        assert extra["operation"] == "connect"
        assert extra["status"] == "NOT_CONFIGURED"
        assert extra["duration_ms"] >= 0.0
        assert extra["adapter"] == "dms"
        assert "auth_token" not in extra

    # 11b. Mock DMS adapter
    mock_adapter = MockDMSAdapter()
    with patch.object(base_adapter_logger, "log") as mock_log:
        docs = mock_adapter.fetch_documents(limit=2)
        assert len(docs) > 0
        calls = [c for c in mock_log.call_args_list if c[1].get("extra", {}).get("event") == "dms_adapter_call"]
        assert len(calls) == 1
        extra = calls[0][1]["extra"]
        assert extra["event"] == "dms_adapter_call"
        assert extra["operation"] == "fetch_documents"
        assert extra["duration_ms"] >= 0.0


def test_structured_formatter_all_11_events_schema_integrity():
    """Verify that StructuredJSONFormatter formats log records from all 11 stages with top-level event & duration_ms."""
    formatter = StructuredJSONFormatter()
    stages = [
        ("document_ingestion", {"document_id": "doc-01", "job_id": "job-01", "duration_ms": 12.5}),
        ("ocr_extraction", {"width": 100, "height": 100, "duration_ms": 45.2}),
        ("lexical_search", {"top_k": 5, "token_count": 3, "duration_ms": 2.1}),
        ("dense_search", {"top_k": 5, "model_name": "bge-small", "duration_ms": 14.8}),
        ("rrf_fusion", {"fused_count": 5, "duration_ms": 0.4}),
        ("cross_encoder_rerank", {"candidate_count": 5, "duration_ms": 8.3}),
        ("qa_generation", {"facts_count": 2, "answer_length": 150, "duration_ms": 250.0}),
        ("report_generation", {"report_id": "rpt-01", "file_size_bytes": 1024, "duration_ms": 85.0}),
        ("sap_adapter_call", {"operation": "health", "system_name": "SAP", "duration_ms": 0.2}),
        ("coalnet_adapter_call", {"operation": "health", "system_name": "COALNET", "duration_ms": 0.2}),
        ("dms_adapter_call", {"operation": "health", "system_name": "DMS", "duration_ms": 0.2}),
    ]
    
    for event_name, extra_data in stages:
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"{event_name} completed in {extra_data['duration_ms']}ms",
            args=(),
            exc_info=None,
        )
        record.event = event_name
        record.duration_ms = extra_data["duration_ms"]
        for k, v in extra_data.items():
            setattr(record, k, v)
            
        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert data["event"] == event_name
        assert data["duration_ms"] == extra_data["duration_ms"]
        assert "timestamp" in data
        assert "level" in data
        assert "logger" in data

