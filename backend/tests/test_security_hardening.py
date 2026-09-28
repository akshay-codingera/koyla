import os
import sys
import io
import socket
import struct
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
from app.core.config import Settings, settings
from app.core.rate_limit import RateLimiter
from app.services.storage import storage_service
from app.services.security.antivirus import ClamAVScanner, ScanResult

client = TestClient(app)

# -----------------------------------------------------------------------------
# 1. Production Secret Security Tests
# -----------------------------------------------------------------------------
def test_production_secret_enforcement_missing_or_default():
    """Verify production fails fast if SECRET_KEY is default or weak."""
    # Production with default insecure secret must raise ValueError
    s_prod_default = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="supersecretkey_for_local_prototype_only",
        CORS_ORIGINS=["http://localhost:5173"]
    )
    with pytest.raises(ValueError) as exc:
        s_prod_default.validate_security()
    assert "Insecure default/fallback secrets are strictly prohibited" in str(exc.value)

    # Production with short secret (< 32 chars) must raise ValueError
    s_prod_short = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="tooshortsecret",
        CORS_ORIGINS=["http://localhost:5173"]
    )
    with pytest.raises(ValueError) as exc:
        s_prod_short.validate_security()
    assert "cryptographically secure SECRET_KEY of at least 32 characters" in str(exc.value)


def test_production_cors_wildcard_rejection():
    """Verify production fails fast if wildcard CORS is used with credentials."""
    s_prod_wildcard = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a" * 32,
        CORS_ORIGINS=["*"]
    )
    with pytest.raises(ValueError) as exc:
        s_prod_wildcard.validate_security()
    assert "Wildcard CORS origin ('*') is prohibited in production" in str(exc.value)


def test_production_security_valid_config():
    """Verify production validation succeeds with strong secret and explicit origins."""
    s_prod_valid = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="koyla_production_secure_key_1234567890_strong",
        CORS_ORIGINS=["https://koyla.cmpdi.gov.in", "https://reports.cil.in"]
    )
    # Must not raise
    s_prod_valid.validate_security()


def test_development_secret_behavior():
    """Verify development mode allows safe default prototype secret."""
    s_dev = Settings(
        ENVIRONMENT="development",
        SECRET_KEY="supersecretkey_for_local_prototype_only",
        CORS_ORIGINS=["http://localhost:5173"]
    )
    # Must not raise in development
    s_dev.validate_security()


# -----------------------------------------------------------------------------
# 2. Security Headers Middleware Tests
# -----------------------------------------------------------------------------
def test_security_headers_present_on_responses():
    """Verify defensive HTTP security headers are attached to responses."""
    res = client.get("/")
    assert res.status_code == 200
    headers = res.headers

    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert headers.get("X-XSS-Protection") == "1; mode=block"


# -----------------------------------------------------------------------------
# 3. CORS Configuration Tests
# -----------------------------------------------------------------------------
def test_cors_configured_origins():
    """Verify CORS headers respond correctly to allowed origins."""
    # Preflight request from allowed origin
    res = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type"
        }
    )
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert res.headers.get("access-control-allow-credentials") == "true"


def test_cors_disallows_untrusted_origin():
    """Verify CORS does not reflect untrusted origins."""
    res = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://untrusted-attacker-site.com",
            "Access-Control-Request-Method": "POST",
        }
    )
    assert res.headers.get("access-control-allow-origin") != "http://untrusted-attacker-site.com"


# -----------------------------------------------------------------------------
# 4. Rate Limiter Tests
# -----------------------------------------------------------------------------
def test_rate_limiter_in_memory_and_enforcement():
    """Verify sliding-window rate limiter enforces limit and provides Retry-After."""
    limiter = RateLimiter(requests_per_minute=3, scope="test_unit_scope")
    limiter.reset()

    # First 3 requests should pass
    assert limiter.check_rate_limit("test_client_1") is None
    assert limiter.check_rate_limit("test_client_1") is None
    assert limiter.check_rate_limit("test_client_1") is None

    # 4th request must be rejected with retry_after
    retry_after = limiter.check_rate_limit("test_client_1")
    assert retry_after is not None
    assert retry_after > 0

    # Different client must have independent bucket
    assert limiter.check_rate_limit("test_client_2") is None

    # Reset cleans up state
    limiter.reset()
    assert limiter.check_rate_limit("test_client_1") is None


# -----------------------------------------------------------------------------
# 5. File Upload & Magic Byte Security Tests
# -----------------------------------------------------------------------------
def test_forbidden_file_extensions_rejected():
    """Verify forbidden executable/script extensions are immediately rejected."""
    for bad_ext in [".exe", ".bat", ".sh", ".ps1", ".vbs", ".dll", ".py"]:
        with pytest.raises(HTTPException) as exc:
            storage_service.validate_file(f"malicious{bad_ext}")
        assert exc.value.status_code == 400
        assert "Security violation" in exc.value.detail or "forbidden" in exc.value.detail


def test_forbidden_binary_headers_rejected():
    """Verify binary executable headers (PE/ELF/Mach-O) are rejected even with valid extension."""
    # PE Header MZ
    with pytest.raises(HTTPException) as exc_pe:
        storage_service.validate_content(b"MZ\x90\x00\x03\x00\x00\x00", ".pdf")
    assert exc_pe.value.status_code == 400
    assert "Forbidden executable binary signature" in exc_pe.value.detail

    # Linux ELF Header
    with pytest.raises(HTTPException) as exc_elf:
        storage_service.validate_content(b"\x7fELF\x02\x01\x01\x00", ".pdf")
    assert exc_elf.value.status_code == 400
    assert "Forbidden executable binary signature" in exc_elf.value.detail


def test_mime_content_mismatch_detection():
    """Verify content/magic-byte mismatch against file extension is rejected."""
    # A .pdf containing PNG image magic bytes
    with pytest.raises(HTTPException) as exc_pdf_png:
        storage_service.validate_content(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", ".pdf")
    assert exc_pdf_png.value.status_code == 400
    assert "MIME/content signature mismatch" in exc_pdf_png.value.detail

    # A .docx without valid ZIP header
    with pytest.raises(HTTPException) as exc_docx:
        storage_service.validate_content(b"This is not a zip or docx archive", ".docx")
    assert exc_docx.value.status_code == 400
    assert "MIME/content signature mismatch" in exc_docx.value.detail

    # A .png without valid PNG header
    with pytest.raises(HTTPException) as exc_png:
        storage_service.validate_content(b"Fake PNG content", ".png")
    assert exc_png.value.status_code == 400
    assert "MIME/content signature mismatch" in exc_png.value.detail

    # A .csv with embedded binary null bytes
    with pytest.raises(HTTPException) as exc_csv:
        storage_service.validate_content(b"col1,col2\x00evil_binary_payload\n", ".csv")
    assert exc_csv.value.status_code == 400
    assert "Binary null bytes detected" in exc_csv.value.detail


def test_empty_file_rejected():
    """Verify empty (0 byte) file is rejected."""
    with pytest.raises(HTTPException) as exc:
        storage_service.validate_content(b"", ".pdf")
    assert exc.value.status_code == 400
    assert "File is empty" in exc.value.detail


# -----------------------------------------------------------------------------
# 6. ClamAV Integration & Status Honesty Tests
# -----------------------------------------------------------------------------
def test_clamav_scanner_status_reporting():
    """Verify ClamAV scanner accurately reports status and never claims active if unreachable."""
    # When disabled
    disabled_scanner = ClamAVScanner(enabled=False)
    res_disabled = disabled_scanner.scan_file("dummy_path")
    assert res_disabled.scanner_status == "DISABLED"
    assert res_disabled.scanned is False
    assert disabled_scanner.health()["status"] == "DISABLED"

    # When enabled but port 3310 is offline/unreachable
    unreachable_scanner = ClamAVScanner(host="127.0.0.1", port=33109, timeout=0.1, enabled=True)
    res_unreachable = unreachable_scanner.scan_file("dummy_path")
    assert res_unreachable.scanner_status == "UNAVAILABLE"
    assert res_unreachable.scanned is False
    assert unreachable_scanner.health()["status"] == "UNAVAILABLE"
    # Must NOT claim ACTIVE
    assert res_unreachable.scanner_status != "ACTIVE"


def test_clamav_malware_detection_handling(tmp_path):
    """Verify ClamAV response parser flags malware if detected."""
    test_file = tmp_path / "test_doc.pdf"
    test_file.write_bytes(b"%PDF-1.4 test document content")

    scanner = ClamAVScanner(enabled=True)

    # Mock socket communication with clamd returning malware FOUND
    mock_socket = MagicMock()
    mock_socket.__enter__.return_value = mock_socket
    mock_socket.recv.return_value = b"stream: Eicar-Test-Signature FOUND\n"

    with patch("socket.create_connection", return_value=mock_socket):
        scan_res = scanner.scan_file(str(test_file))
        assert scan_res.scanner_status == "ACTIVE"
        assert scan_res.is_clean is False
        assert "Eicar-Test-Signature" in scan_res.virus_name
        assert scan_res.scanned is True
