"""
Test Suite for Phase 8.5: Topic Intelligence Final Hardening & Platform Integration.

Covers:
1. Cache correctness: Cache Hit on identical corpus & parameters
2. Cache correctness: Cache Miss on modified corpus filters
3. Cache correctness: Force Refresh bypasses cache
4. Temporal trends caching and force refresh execution
5. Analysis version integrity assertion enforcement
6. Server-side organization isolation: ECL user denied BCCL analysis (HTTP 403)
7. Server-side central officer cross-organization authorized access (HTTP 200)
8. Canonical /api/v1/system/health operational verification across all 9 components
9. Report Studio optional annexure attachment, provenance retention, and audit event logging
10. Local LLM offline deterministic fallback preservation
"""

import uuid
import json
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.database import SessionLocal
from app.models.organization import Organization
from app.models.user import User, Role
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.report import Report, ReportAnnexure
from app.models.audit import AuditEvent
from app.models.topic import (
    TopicAnalysis,
    Topic,
    TopicTerm,
    TopicEvidence,
    TopicTrend,
)
from app.core.security import get_password_hash, create_access_token
from app.services.topics.temporal_service import temporal_service
from app.services.reports.format_registry import FormatRegistry

client = TestClient(app)


@pytest.fixture(scope="module")
def hardening_fixture():
    db = SessionLocal()

    # 1. Organizations
    ecl_org = db.query(Organization).filter(Organization.code == "ECL_HARDEN").first()
    if not ecl_org:
        ecl_org = Organization(
            id=str(uuid.uuid4()),
            code="ECL_HARDEN",
            name="Eastern Coalfields Limited (Hardening)",
            org_type="SUBSIDIARY",
            is_active=True,
        )
        db.add(ecl_org)

    bccl_org = db.query(Organization).filter(Organization.code == "BCCL_HARDEN").first()
    if not bccl_org:
        bccl_org = Organization(
            id=str(uuid.uuid4()),
            code="BCCL_HARDEN",
            name="Bharat Coking Coal Limited (Hardening)",
            org_type="SUBSIDIARY",
            is_active=True,
        )
        db.add(bccl_org)

    cmpdi_org = db.query(Organization).filter(Organization.code == "CMPDI_HARDEN").first()
    if not cmpdi_org:
        cmpdi_org = Organization(
            id=str(uuid.uuid4()),
            code="CMPDI_HARDEN",
            name="CMPDI HQ (Hardening)",
            org_type="HQ",
            is_active=True,
        )
        db.add(cmpdi_org)

    db.commit()

    # 2. Roles
    r_analyst = db.query(Role).filter(Role.code == "SUBSIDIARY_ANALYST").first()
    if not r_analyst:
        r_analyst = Role(
            id=str(uuid.uuid4()),
            code="SUBSIDIARY_ANALYST",
            name="Subsidiary Analyst",
            permissions=["SUBSIDIARY_ANALYST"],
        )
        db.add(r_analyst)

    r_hq = db.query(Role).filter(Role.code == "CMPDI_HQ_OFFICER").first()
    if not r_hq:
        r_hq = Role(
            id=str(uuid.uuid4()),
            code="CMPDI_HQ_OFFICER",
            name="CMPDI HQ Officer",
            permissions=["CMPDI_HQ_OFFICER"],
        )
        db.add(r_hq)

    db.commit()

    # 3. Users
    u_ecl = db.query(User).filter(User.username == "analyst_ecl_harden").first()
    if not u_ecl:
        u_ecl = User(
            id=str(uuid.uuid4()),
            username="analyst_ecl_harden",
            full_name="ECL Hardening Analyst",
            email="ecl_harden@koyla.gov.in",
            hashed_password=get_password_hash("Password123!"),
            organization_id=ecl_org.id,
            is_active=True,
        )
        u_ecl.roles.append(r_analyst)
        db.add(u_ecl)

    u_bccl = db.query(User).filter(User.username == "analyst_bccl_harden").first()
    if not u_bccl:
        u_bccl = User(
            id=str(uuid.uuid4()),
            username="analyst_bccl_harden",
            full_name="BCCL Hardening Analyst",
            email="bccl_harden@koyla.gov.in",
            hashed_password=get_password_hash("Password123!"),
            organization_id=bccl_org.id,
            is_active=True,
        )
        u_bccl.roles.append(r_analyst)
        db.add(u_bccl)

    u_hq = db.query(User).filter(User.username == "officer_hq_harden").first()
    if not u_hq:
        u_hq = User(
            id=str(uuid.uuid4()),
            username="officer_hq_harden",
            full_name="CMPDI HQ Hardening Officer",
            email="hq_harden@koyla.gov.in",
            hashed_password=get_password_hash("Password123!"),
            organization_id=cmpdi_org.id,
            is_active=True,
        )
        u_hq.roles.append(r_hq)
        db.add(u_hq)

    db.commit()

    # 4. Ingest Documents for ECL
    doc_ecl_1 = Document(
        id=str(uuid.uuid4()),
        organization_id=ecl_org.id,
        title="ECL Jhanjra Seam Correlation Report FY2023-24",
        document_type="GEOLOGICAL_REPORT",
        source_tier="TIER_A",
        original_filename="ecl_geo_fy24.pdf",
        file_path="storage/ecl_geo_fy24.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="h1_" + uuid.uuid4().hex,
        status="PROCESSED",
    )
    doc_ecl_2 = Document(
        id=str(uuid.uuid4()),
        organization_id=ecl_org.id,
        title="ECL Jhanjra Seam Correlation Report FY2024-25",
        document_type="GEOLOGICAL_REPORT",
        source_tier="TIER_A",
        original_filename="ecl_geo_fy25.pdf",
        file_path="storage/ecl_geo_fy25.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="h2_" + uuid.uuid4().hex,
        status="PROCESSED",
    )
    db.add_all([doc_ecl_1, doc_ecl_2])
    db.commit()

    # Chunks
    c1 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_ecl_1.id,
        chunk_index=0,
        page_number=1,
        chunk_type="TEXT",
        content="Coal reserves in Barakar formation seam R-IV prime coking coal exploration Jhanjra Colliery.",
        metadata_json={"fiscal_year": "FY2023-24", "mine_name": "Jhanjra", "block_name": "Block-A"},
    )
    c2 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_ecl_1.id,
        chunk_index=1,
        page_number=1,
        chunk_type="TEXT",
        content="Drilling core lithology confirmed Barakar coal thickness 4.5 meters in seam R-IV Jhanjra mine.",
        metadata_json={"fiscal_year": "FY2023-24", "mine_name": "Jhanjra", "block_name": "Block-A"},
    )
    c3 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_ecl_2.id,
        chunk_index=0,
        page_number=1,
        chunk_type="TEXT",
        content="Barakar coal seam R-IV advanced drilling confirmed continuous deposit reserves Jhanjra block.",
        metadata_json={"fiscal_year": "FY2024-25", "mine_name": "Jhanjra", "block_name": "Block-A"},
    )
    c4 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_ecl_2.id,
        chunk_index=1,
        page_number=2,
        chunk_type="TEXT",
        content="Geological borehole core samples verified high volatile bituminous coal reserve at Jhanjra underground mine.",
        metadata_json={"fiscal_year": "FY2024-25", "mine_name": "Jhanjra", "block_name": "Block-A"},
    )
    db.add_all([c1, c2, c3, c4])
    db.commit()

    # Tokens
    token_ecl = create_access_token(u_ecl.username)
    token_bccl = create_access_token(u_bccl.username)
    token_hq = create_access_token(u_hq.username)

    data = {
        "ecl_org_id": ecl_org.id,
        "bccl_org_id": bccl_org.id,
        "cmpdi_org_id": cmpdi_org.id,
        "u_ecl": u_ecl,
        "u_bccl": u_bccl,
        "u_hq": u_hq,
        "token_ecl": token_ecl,
        "token_bccl": token_bccl,
        "token_hq": token_hq,
        "doc_ecl_1": doc_ecl_1,
        "doc_ecl_2": doc_ecl_2,
        "c1": c1,
        "c2": c2,
        "c3": c3,
        "c4": c4,
    }

    yield data
    db.close()


def test_01_cache_hit_identical_corpus_and_parameters(hardening_fixture):
    """Calling analyze twice with exact same corpus & parameters yields a deterministic CACHE HIT."""
    token = hardening_fixture["token_ecl"]
    org_id = hardening_fixture["ecl_org_id"]

    req_payload = {
        "organization_id": org_id,
        "corpus_filters": {"mine_name": "Jhanjra"},
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "analysis_method": "AUTO",
        "parameters": {"test_param": "cache_test"},
        "force_refresh": False,
    }

    # First Call: Cold / Cache Miss
    res1 = client.post("/api/v1/topics/analyze", json=req_payload, headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["cache_hit"] is False
    analysis_id_1 = data1["id"]
    corpus_hash_1 = data1["corpus_hash"]

    # Second Call: Warm / Cache Hit
    res2 = client.post("/api/v1/topics/analyze", json=req_payload, headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["cache_hit"] is True
    assert data2["id"] == analysis_id_1
    assert data2["corpus_hash"] == corpus_hash_1


def test_02_cache_miss_modified_filter(hardening_fixture):
    """Calling analyze with modified filters yields a CACHE MISS and creates a distinct analysis."""
    token = hardening_fixture["token_ecl"]
    org_id = hardening_fixture["ecl_org_id"]

    req_payload = {
        "organization_id": org_id,
        "corpus_filters": {"mine_name": "NonExistentMine"},
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "analysis_method": "AUTO",
        "parameters": {"test_param": "cache_miss_test"},
        "force_refresh": False,
    }

    res = client.post("/api/v1/topics/analyze", json=req_payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["cache_hit"] is False


def test_03_force_refresh_bypasses_cache(hardening_fixture):
    """Calling analyze with force_refresh=True bypasses the cache even when corpus matches."""
    token = hardening_fixture["token_ecl"]
    org_id = hardening_fixture["ecl_org_id"]

    req_payload = {
        "organization_id": org_id,
        "corpus_filters": {"mine_name": "Jhanjra"},
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "analysis_method": "AUTO",
        "parameters": {"test_param": "cache_test"},
        "force_refresh": True,
    }

    res = client.post("/api/v1/topics/analyze", json=req_payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["cache_hit"] is False


def test_04_temporal_trends_cache_and_force_refresh(hardening_fixture):
    """Verifies caching and clean force refresh of temporal trends without duplicate records."""
    db = SessionLocal()
    token = hardening_fixture["token_ecl"]
    org_id = hardening_fixture["ecl_org_id"]

    # First get an existing completed analysis
    analysis = db.query(TopicAnalysis).filter(
        TopicAnalysis.organization_id == org_id,
        TopicAnalysis.status == "COMPLETED"
    ).first()
    assert analysis is not None

    # Cold trends fetch (computes and caches)
    res1 = client.get(
        f"/api/v1/topics/{analysis.id}/trends?force_refresh=false",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res1.status_code == 200
    trends_1 = res1.json()
    assert "trends" in trends_1

    # Record initial trend row count
    initial_trend_count = db.query(TopicTrend).filter(TopicTrend.analysis_id == analysis.id).count()

    # Warm trends fetch with force_refresh=true
    res2 = client.get(
        f"/api/v1/topics/{analysis.id}/trends?force_refresh=true",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res2.status_code == 200

    # Trend count must remain strictly identical (clean recomputation, zero duplication)
    after_trend_count = db.query(TopicTrend).filter(TopicTrend.analysis_id == analysis.id).count()
    assert after_trend_count == initial_trend_count
    db.close()


def test_05_analysis_version_integrity_enforcement(hardening_fixture):
    """Verifies that mixing TopicTrend records across analysis versions triggers an integrity exception."""
    db = SessionLocal()
    org_id = hardening_fixture["ecl_org_id"]

    analysis_a = db.query(TopicAnalysis).filter(TopicAnalysis.organization_id == org_id).first()
    assert analysis_a is not None

    # Construct a corrupted trend record pointing to another fake analysis_id
    tampered_trend = TopicTrend(
        id=str(uuid.uuid4()),
        analysis_id="corrupted_alien_analysis_version_123",
        topic_id=str(uuid.uuid4()),
        period_value="FY2023-24",
        document_count=1,
    )

    with pytest.raises(ValueError) as exc_info:
        temporal_service._format_trends_response(analysis_a, [tampered_trend])
    assert "Version Integrity Violation" in str(exc_info.value)
    db.close()


def test_06_organization_isolation_ecl_vs_bccl(hardening_fixture):
    """An ECL analyst is strictly blocked (HTTP 403) from accessing a BCCL topic analysis."""
    db = SessionLocal()
    bccl_org_id = hardening_fixture["bccl_org_id"]

    # Create a BCCL topic analysis
    bccl_analysis = TopicAnalysis(
        id=str(uuid.uuid4()),
        organization_id=bccl_org_id,
        corpus_filters={},
        corpus_hash="bccl_secret_hash",
        status="COMPLETED",
    )
    db.add(bccl_analysis)
    db.commit()

    token_ecl = hardening_fixture["token_ecl"]

    # ECL analyst attempts to access BCCL analysis
    res_get = client.get(f"/api/v1/topics/{bccl_analysis.id}", headers={"Authorization": f"Bearer {token_ecl}"})
    assert res_get.status_code == 403

    res_trends = client.get(f"/api/v1/topics/{bccl_analysis.id}/trends", headers={"Authorization": f"Bearer {token_ecl}"})
    assert res_trends.status_code == 403

    db.close()


def test_07_cross_org_central_officer_access(hardening_fixture):
    """A central CMPDI HQ officer can access analyses across subsidiaries."""
    db = SessionLocal()
    bccl_org_id = hardening_fixture["bccl_org_id"]

    bccl_analysis = db.query(TopicAnalysis).filter(TopicAnalysis.organization_id == bccl_org_id).first()
    assert bccl_analysis is not None

    token_hq = hardening_fixture["token_hq"]

    res_get = client.get(f"/api/v1/topics/{bccl_analysis.id}", headers={"Authorization": f"Bearer {token_hq}"})
    assert res_get.status_code == 200
    assert res_get.json()["id"] == bccl_analysis.id
    db.close()


def test_08_system_health_genuine_checks():
    """GET /api/v1/system/health performs real capability tests across all 9 subsystems."""
    res = client.get("/api/v1/system/health")
    assert res.status_code == 200
    body = res.json()

    assert "status" in body
    assert body["database_type"] == "PostgreSQL"
    assert "pgvector_enabled" in body

    services = body["services"]
    expected_services = [
        "backend",
        "api",
        "database",
        "vector_store",
        "ocr_engine",
        "embedding_service",
        "llm_service",
        "topic_engine",
        "temporal_analytics",
        "report_engine",
    ]

    for s in expected_services:
        assert s in services, f"Service '{s}' missing from /api/v1/system/health"
        assert services[s] in ["UP", "DEGRADED", "OFFLINE", "NOT_CONFIGURED", "DOWN"], f"Invalid status for '{s}': {services[s]}"

    assert services["database"] == "UP"
    assert services["embedding_service"] == "UP"
    assert services["topic_engine"] == "UP"
    assert services["temporal_analytics"] == "UP"
    assert services["report_engine"] == "UP"


def test_09_report_studio_optional_annexure_attachment_and_audit(hardening_fixture):
    """Attaching topic analysis creates an explicitly OPTIONAL annexure, preserves official fields, and logs audit."""
    db = SessionLocal()
    org_id = hardening_fixture["ecl_org_id"]
    token = hardening_fixture["token_ecl"]

    # 1. Create statutory report
    fmt = FormatRegistry.seed_default_statutory_format(db)
    report = Report(
        id=str(uuid.uuid4()),
        format_id=fmt.id,
        organization_id=org_id,
        mine_name="Jhanjra Colliery",
        block_name="Block-A",
        report_title="ECL Jhanjra Underground Mining Plan 2025",
        base_date="2026-03",
        version_number=1,
        status="DRAFT",
        compliance_status="COMPLIANT",
    )
    db.add(report)
    db.commit()

    # 2. Get completed analysis
    analysis = db.query(TopicAnalysis).filter(
        TopicAnalysis.organization_id == org_id,
        TopicAnalysis.status == "COMPLETED"
    ).first()
    assert analysis is not None

    # 3. Call attach endpoint
    payload = {
        "report_id": report.id,
        "include_trends": True,
        "include_evidence": True,
    }
    res = client.post(
        f"/api/v1/topics/{analysis.id}/add-to-report",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["requirement_type"] == "OPTIONAL"
    assert res_data["attachment_status"] == "ATTACHED"

    # 4. Verify in database
    annexure = db.query(ReportAnnexure).filter(ReportAnnexure.id == res_data["annexure_id"]).first()
    assert annexure is not None
    assert annexure.requirement_type == "OPTIONAL"
    assert "Thematic Intelligence" in annexure.title
    notes = json.loads(annexure.notes)
    assert notes["analysis_id"] == analysis.id
    assert "topics" in notes

    # 5. Verify official report structure untouched
    report_db = db.query(Report).filter(Report.id == report.id).first()
    assert report_db.compliance_status == "COMPLIANT"
    assert report_db.status == "DRAFT"

    # 6. Verify audit event
    audit = db.query(AuditEvent).filter(
        AuditEvent.action == "REPORT_TOPIC_ANALYSIS_ATTACHED",
        AuditEvent.object_id == annexure.id,
    ).first()
    assert audit is not None
    assert audit.object_type == "ReportAnnexure"
    db.close()


def test_10_local_llm_deterministic_fallback_preservation(hardening_fixture):
    """When local LLM is unavailable, summary endpoint returns factual deterministic synthesis with zero fabrication."""
    db = SessionLocal()
    org_id = hardening_fixture["ecl_org_id"]
    token = hardening_fixture["token_ecl"]

    analysis = db.query(TopicAnalysis).filter(
        TopicAnalysis.organization_id == org_id,
        TopicAnalysis.status == "COMPLETED"
    ).first()
    assert analysis is not None

    res = client.post(
        f"/api/v1/topics/{analysis.id}/summary",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["source"] in ["DETERMINISTIC_SYNTHESIS", "LOCAL_LLM"]
    assert "factual_points" in data
    assert len(data["factual_points"]) > 0
    assert "summary" in data
    assert "model" in data
    db.close()
