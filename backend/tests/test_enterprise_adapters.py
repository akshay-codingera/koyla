import os
import sys
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.services.adapters.base import (
    ExternalSystemAdapter,
    AdapterStatus,
    ExternalDocument,
    ExternalRecord,
    ExternalMetadata,
)
from app.services.adapters.exceptions import (
    AdapterError,
    ExternalSystemNotConfiguredError,
    ExternalSystemUnavailableError,
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

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. Interface & Contract Tests
# -----------------------------------------------------------------------------
def test_adapter_subclass_contract():
    """Verify SAP, CoalNet, and DMS adapters inherit from ExternalSystemAdapter."""
    sap = SAPAdapter()
    coalnet = CoalNetAdapter()
    dms = DMSAdapter()

    assert isinstance(sap, ExternalSystemAdapter)
    assert isinstance(coalnet, ExternalSystemAdapter)
    assert isinstance(dms, ExternalSystemAdapter)

    assert sap.system_name == "sap"
    assert sap.system_type == "erp"
    assert coalnet.system_name == "coalnet"
    assert coalnet.system_type == "dispatch"
    assert dms.system_name == "dms"
    assert dms.system_type == "dms"


# -----------------------------------------------------------------------------
# 2. Canonical Data Contract Tests
# -----------------------------------------------------------------------------
def test_canonical_data_models():
    """Verify canonical representation preserves provenance, timestamps, identifiers, and metadata."""
    now = datetime.utcnow()
    meta = ExternalMetadata(
        source_system="sap",
        external_id="REC-9001",
        organization_id="SECL",
        mine_id="GEVRA_OC",
        block_id="BLOCK_IV",
        source_uri="https://sap.internal/odata/Items('REC-9001')",
        raw_properties={"raw_k1": "v1", "api_key": "sensitive_leaked_key"},
        provenance={"batch_id": "BATCH_01", "operator": "auto"}
    )
    meta_dict = meta.to_dict()
    assert meta_dict["source_system"] == "sap"
    assert meta_dict["external_id"] == "REC-9001"
    assert meta_dict["organization_id"] == "SECL"
    assert meta_dict["mine_id"] == "GEVRA_OC"
    assert meta_dict["block_id"] == "BLOCK_IV"
    assert meta_dict["source_uri"] == "https://sap.internal/odata/Items('REC-9001')"
    # Sensitive raw property must be sanitized
    assert meta_dict["raw_properties"]["api_key"] == "[REDACTED]"
    assert meta_dict["raw_properties"]["raw_k1"] == "v1"

    # Canonical Record
    record = ExternalRecord(
        source_system="sap",
        external_id="REC-9001",
        record_type="production_metric",
        title="Daily Raw Coal Extraction",
        data={"quantity_mt": 12450.5, "grade": "G11", "client_secret": "my_super_secret"},
        metadata=meta
    )
    rec_dict = record.to_dict()
    assert rec_dict["record_type"] == "production_metric"
    assert rec_dict["title"] == "Daily Raw Coal Extraction"
    assert rec_dict["data"]["quantity_mt"] == 12450.5
    assert rec_dict["data"]["client_secret"] == "[REDACTED]"
    assert rec_dict["metadata"]["external_id"] == "REC-9001"

    # Canonical Document
    doc = ExternalDocument(
        source_system="dms",
        external_id="DOC-501",
        document_type="geological_log",
        title="Borehole Log BH-501",
        file_name="BH501.pdf",
        mime_type="application/pdf",
        content_bytes=b"%PDF-1.4 Mock Borehole Data",
        metadata=meta
    )
    doc_dict = doc.to_dict()
    assert doc_dict["source_system"] == "dms"
    assert doc_dict["document_type"] == "geological_log"
    assert doc_dict["file_name"] == "BH501.pdf"
    assert doc_dict["checksum_sha256"] is not None
    assert doc_dict["size_bytes"] == len(b"%PDF-1.4 Mock Borehole Data")


# -----------------------------------------------------------------------------
# 3. Security, Sanitization & SSRF Defense Tests
# -----------------------------------------------------------------------------
def test_security_url_validation_prohibited_schemes():
    """Verify endpoint validation rejects dangerous schemes (file, ftp, gopher, javascript)."""
    with pytest.raises(ExternalSystemSecurityError) as exc1:
        validate_endpoint_url("file:///etc/passwd")
    assert "Prohibited URL scheme 'file'" in str(exc1.value)

    with pytest.raises(ExternalSystemSecurityError) as exc2:
        validate_endpoint_url("gopher://evil.host:70/")
    assert "Prohibited URL scheme 'gopher'" in str(exc2.value)

    with pytest.raises(ExternalSystemSecurityError) as exc3:
        validate_endpoint_url("ftp://ftp.example.com")
    assert "Prohibited URL scheme 'ftp'" in str(exc3.value)


def test_security_url_validation_ssrf_metadata_rejection():
    """Verify endpoint validation rejects cloud metadata IP (SSRF defense)."""
    with pytest.raises(ExternalSystemSecurityError) as exc:
        validate_endpoint_url("http://169.254.169.254/latest/meta-data")
    assert "SSRF violation" in str(exc.value)


def test_security_url_embedded_credential_stripping():
    """Verify endpoint validation strips embedded user:pass credentials from URL strings."""
    cleaned = validate_endpoint_url("https://user:password123@enterprise.sap.corp:8443/odata")
    assert "password123" not in cleaned
    assert "user" not in cleaned
    assert cleaned == "https://enterprise.sap.corp:8443/odata"


def test_security_credential_sanitization():
    """Verify recursive credential sanitization neutralizes tokens and secrets."""
    payload = {
        "endpoint": "https://sap.internal",
        "client_id": "koyla_client",
        "client_secret": "SuperSecretPass99!",
        "auth_token": "Bearer eyJhbGciOi...",
        "nested": {
            "api_key": "SECRET_KEY_VAL",
            "safe_val": 42
        }
    }
    sanitized = sanitize_credentials(payload)
    assert sanitized["client_secret"] == "[REDACTED]"
    assert sanitized["auth_token"] == "[REDACTED]"
    assert sanitized["nested"]["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["safe_val"] == 42
    assert sanitized["client_id"] == "koyla_client"


# -----------------------------------------------------------------------------
# 4. Fail-Closed Unconfigured Adapter Tests
# -----------------------------------------------------------------------------
def test_unconfigured_adapters_report_not_configured():
    """Verify unconfigured adapters report NOT_CONFIGURED and fail fast on calls."""
    sap = SAPAdapter()
    coalnet = CoalNetAdapter()
    dms = DMSAdapter()

    assert not sap.is_configured
    assert not coalnet.is_configured
    assert not dms.is_configured

    sap_health = sap.health()
    assert sap_health["status"] == AdapterStatus.NOT_CONFIGURED.value
    assert sap_health["configured"] is False

    coalnet_health = coalnet.health()
    assert coalnet_health["status"] == AdapterStatus.NOT_CONFIGURED.value
    assert coalnet_health["configured"] is False

    dms_health = dms.health()
    assert dms_health["status"] == AdapterStatus.NOT_CONFIGURED.value
    assert dms_health["configured"] is False

    # Invocations on unconfigured adapters must raise ExternalSystemNotConfiguredError
    with pytest.raises(ExternalSystemNotConfiguredError):
        sap.connect()

    with pytest.raises(ExternalSystemNotConfiguredError):
        coalnet.fetch_records()

    with pytest.raises(ExternalSystemNotConfiguredError):
        dms.fetch_documents()

    with pytest.raises(ExternalSystemNotConfiguredError):
        sap.fetch_incremental(datetime.utcnow())


def test_configured_but_unreachable_adapter_reports_unavailable():
    """Verify configured adapter without live network connection reports UNAVAILABLE without leaking creds."""
    sap = SAPAdapter(config_override={
        "SAP_ENABLED": True,
        "SAP_ENDPOINT": "https://sap-test-host.corp:8443",
        "SAP_CLIENT_ID": "client_id_01",
        "SAP_CLIENT_SECRET": "secret_pass_xyz"
    })
    assert sap.is_configured is True
    h = sap.health()
    assert h["status"] == AdapterStatus.UNAVAILABLE.value
    assert h["configured"] is True
    assert "secret_pass_xyz" not in str(h)

    with pytest.raises(ExternalSystemUnavailableError):
        sap.connect()


# -----------------------------------------------------------------------------
# 5. Deterministic Mock Adapter Tests
# -----------------------------------------------------------------------------
def test_mock_sap_adapter():
    """Verify MockSAPAdapter produces deterministic canonical records and documents."""
    mock_sap = MockSAPAdapter()
    assert mock_sap.is_mock is True
    assert mock_sap.is_configured is True

    health = mock_sap.health()
    assert health["status"] == AdapterStatus.MOCK_OPERATIONAL.value
    assert health["is_mock"] is True

    assert mock_sap.connect() is True

    records = mock_sap.fetch_records(limit=10)
    assert len(records) > 0
    rec = records[0]
    assert isinstance(rec, ExternalRecord)
    assert rec.source_system == "sap"
    assert "quantity_mt" in rec.data
    assert rec.metadata.organization_id is not None

    docs = mock_sap.fetch_documents(limit=5)
    assert len(docs) > 0
    doc = docs[0]
    assert isinstance(doc, ExternalDocument)
    assert doc.source_system == "sap"
    assert doc.content_bytes is not None

    delta = mock_sap.fetch_incremental(since=datetime.utcnow())
    assert "records" in delta
    assert "documents" in delta
    assert "cursor" in delta


def test_mock_coalnet_adapter():
    """Verify MockCoalNetAdapter produces deterministic weighbridge and dispatch records."""
    mock_cn = MockCoalNetAdapter()
    assert mock_cn.is_mock is True
    assert mock_cn.is_configured is True

    health = mock_cn.health()
    assert health["status"] == AdapterStatus.MOCK_OPERATIONAL.value
    assert health["is_mock"] is True

    records = mock_cn.fetch_records()
    assert len(records) > 0
    rec = records[0]
    assert isinstance(rec, ExternalRecord)
    assert rec.source_system == "coalnet"
    assert "net_weight_mt" in rec.data

    docs = mock_cn.fetch_documents()
    assert len(docs) > 0
    doc = docs[0]
    assert isinstance(doc, ExternalDocument)
    assert doc.source_system == "coalnet"
    assert doc.document_type == "weighment_challan"


def test_mock_dms_adapter():
    """Verify MockDMSAdapter produces deterministic canonical documents and handles incremental sync."""
    mock_dms = MockDMSAdapter()
    assert mock_dms.is_mock is True
    assert mock_dms.is_configured is True

    health = mock_dms.health()
    assert health["status"] == AdapterStatus.MOCK_OPERATIONAL.value
    assert health["is_mock"] is True

    docs = mock_dms.fetch_documents()
    assert len(docs) > 0
    doc = docs[0]
    assert isinstance(doc, ExternalDocument)
    assert doc.source_system == "dms"
    assert doc.mime_type == "application/pdf"
    assert doc.checksum_sha256 is not None

    delta = mock_dms.fetch_incremental(since=datetime.utcnow())
    assert len(delta["documents"]) > 0


# -----------------------------------------------------------------------------
# 6. Adapter Manager & Registry Tests
# -----------------------------------------------------------------------------
def test_manager_registration_and_lookup():
    """Verify ExternalSystemManager registers, lists, and retrieves adapters by system name."""
    mgr = ExternalSystemManager(use_mocks=False)

    assert mgr.has_adapter("sap")
    assert mgr.has_adapter("coalnet")
    assert mgr.has_adapter("dms")
    assert not mgr.has_adapter("nonexistent_system")

    sap_adapter = mgr.get_adapter("sap")
    assert sap_adapter.system_name == "sap"

    with pytest.raises(ExternalSystemNotConfiguredError):
        mgr.get_adapter("unknown_system")

    # In unconfigured mode, require_configured raises ExternalSystemNotConfiguredError
    with pytest.raises(ExternalSystemNotConfiguredError):
        mgr.get_adapter("sap", require_configured=True)


def test_manager_mock_initialization():
    """Verify ExternalSystemManager initializes mock adapters when use_mocks is True."""
    mgr = ExternalSystemManager(use_mocks=True)

    adapters = mgr.list_adapters()
    assert len(adapters) == 3
    for a in adapters:
        assert a["is_mock"] is True
        assert a["is_configured"] is True

    sap_adapter = mgr.get_adapter("sap", require_configured=True)
    assert sap_adapter.is_mock is True
    records = sap_adapter.fetch_records()
    assert len(records) > 0


def test_manager_health_reporting_and_incremental():
    """Verify ExternalSystemManager gathers health and coordinates incremental delta sync."""
    mgr = ExternalSystemManager(use_mocks=True)
    all_health = mgr.get_all_health()

    assert "sap" in all_health
    assert "coalnet" in all_health
    assert "dms" in all_health
    assert all_health["sap"]["status"] == AdapterStatus.MOCK_OPERATIONAL.value

    delta = mgr.fetch_all_incremental(since=datetime.utcnow())
    assert "systems" in delta
    assert "sap" in delta["systems"]
    assert "coalnet" in delta["systems"]
    assert "dms" in delta["systems"]


# -----------------------------------------------------------------------------
# 7. System Health & API Telemetry Integration Tests
# -----------------------------------------------------------------------------
def test_api_system_health_telemetry_includes_enterprise_adapters():
    """Verify /api/v1/system/health exposes genuine enterprise adapter telemetry."""
    res = client.get("/api/v1/system/health")
    assert res.status_code == 200
    data = res.json()
    assert "enterprise_adapters" in data
    adapters = data["enterprise_adapters"]
    assert "sap" in adapters
    assert "coalnet" in adapters
    assert "dms" in adapters


def test_api_system_adapters_endpoint():
    """Verify /api/v1/system/adapters returns registered adapter postures and health."""
    res = client.get("/api/v1/system/adapters")
    assert res.status_code == 200
    data = res.json()
    assert "adapters" in data
    assert "health" in data
    assert len(data["adapters"]) >= 3
    names = [a["system_name"] for a in data["adapters"]]
    assert "sap" in names
    assert "coalnet" in names
    assert "dms" in names
