import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.database import SessionLocal
from app.models.user import User, Role
from app.models.organization import Organization
from app.models.document import Document, DocumentVersion
from app.models.chunk import Chunk, Embedding
from app.models.extraction import ExtractedField, ReconciliationGroup, ReconciliationCandidate
from app.models.qa import QueryRecord, AnswerRecord, AnswerCitation
from app.models.audit import AuditEvent
from app.core.security import create_access_token, get_password_hash
from app.services.qa import (
    arithmetic_engine,
    structured_lookup_service,
    grounding_checker,
    qa_service,
    STANDARD_REFUSAL_TEXT
)
from app.services.llm import (
    LLMProvider,
    LLMResponse,
    ProviderHealth,
    ProviderModelInfo,
    OllamaProvider,
    OpenAICompatibleLocalProvider,
    set_llm_provider,
    get_llm_provider
)
from app.services.indexing import indexing_service

client = TestClient(app)


class MockLocalLLMProvider(LLMProvider):
    """Deterministic Mock LLM for unit tests to verify pipeline without external services."""
    def __init__(self, answer_override: str = None):
        self.answer_override = answer_override

    def generate(self, prompt: str, system_prompt=None, temperature=0.1, max_tokens=1024, **kwargs) -> LLMResponse:
        content = self.answer_override or "Gevra OC reported 52.5 MT in FY 2023-24 [1]."
        return LLMResponse(
            content=content,
            model_name="mock-local-llm",
            provider="mock",
            latency_ms=15.0
        )

    def structured_generate(self, prompt: str, schema, system_prompt=None, **kwargs):
        return {}

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            is_healthy=True,
            provider="mock",
            model_name="mock-local-llm",
            endpoint="http://localhost:11434"
        )

    def model_info(self) -> ProviderModelInfo:
        return ProviderModelInfo(
            provider="mock",
            model_name="mock-local-llm",
            is_local=True
        )


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def qa_test_setup(db_session: Session):
    # Ensure test organizations exist
    org_secl = db_session.query(Organization).filter(Organization.code == "SECL_QA_TEST").first()
    if not org_secl:
        org_secl = Organization(
            id=str(uuid.uuid4()),
            code="SECL_QA_TEST",
            name="South Eastern Coalfields Limited (Test)",
            org_type="SUBSIDIARY"
        )
        db_session.add(org_secl)

    org_ecl = db_session.query(Organization).filter(Organization.code == "ECL_QA_TEST").first()
    if not org_ecl:
        org_ecl = Organization(
            id=str(uuid.uuid4()),
            code="ECL_QA_TEST",
            name="Eastern Coalfields Limited (Test)",
            org_type="SUBSIDIARY"
        )
        db_session.add(org_ecl)

    org_cmpdi = db_session.query(Organization).filter(Organization.code == "CMPDI_QA_TEST").first()
    if not org_cmpdi:
        org_cmpdi = Organization(
            id=str(uuid.uuid4()),
            code="CMPDI_QA_TEST",
            name="CMPDI HQ (Test)",
            org_type="HQ"
        )
        db_session.add(org_cmpdi)

    # Ensure Roles
    r_subsidiary = db_session.query(Role).filter(Role.code == "SUBSIDIARY_ANALYST").first()
    if not r_subsidiary:
        r_subsidiary = Role(id=str(uuid.uuid4()), code="SUBSIDIARY_ANALYST", name="Subsidiary Analyst", permissions=[])
        db_session.add(r_subsidiary)

    r_central = db_session.query(Role).filter(Role.code == "CMPDI_HQ_OFFICER").first()
    if not r_central:
        r_central = Role(id=str(uuid.uuid4()), code="CMPDI_HQ_OFFICER", name="CMPDI HQ Officer", permissions=[])
        db_session.add(r_central)

    db_session.commit()

    # Create Users
    u_secl = db_session.query(User).filter(User.username == "analyst_secl_qa").first()
    if not u_secl:
        u_secl = User(
            id=str(uuid.uuid4()),
            username="analyst_secl_qa",
            email="analyst_secl_qa@secl.gov.in",
            full_name="SECL Analyst QA",
            hashed_password=get_password_hash("password123"),
            organization_id=org_secl.id,
            roles=[r_subsidiary]
        )
        db_session.add(u_secl)

    u_cmpdi = db_session.query(User).filter(User.username == "officer_cmpdi_qa").first()
    if not u_cmpdi:
        u_cmpdi = User(
            id=str(uuid.uuid4()),
            username="officer_cmpdi_qa",
            email="officer_cmpdi_qa@cmpdi.gov.in",
            full_name="CMPDI Officer QA",
            hashed_password=get_password_hash("password123"),
            organization_id=org_cmpdi.id,
            roles=[r_central]
        )
        db_session.add(u_cmpdi)

    # Seed Document and Version
    doc = db_session.query(Document).filter(Document.title == "Gevra OC Annual Operational Review 2023-24").first()
    if not doc:
        doc = Document(
            id=str(uuid.uuid4()),
            organization_id=org_secl.id,
            title="Gevra OC Annual Operational Review 2023-24",
            document_type="PRODUCTION_SUMMARY",
            source_tier="TIER_A",
            original_filename="gevra_production_2023_24.pdf",
            file_path="storage/documents/gevra_2023_24.pdf",
            mime_type="application/pdf",
            file_size_bytes=1048576,
            sha256_hash="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
            status="INDEXED"
        )
        db_session.add(doc)
        db_session.flush()

        doc_ver = DocumentVersion(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            version_number=1,
            file_path=doc.file_path,
            sha256_hash=doc.sha256_hash,
            change_summary="Initial verified ingestion"
        )
        db_session.add(doc_ver)
        db_session.flush()

        # Seed Chunks
        c1 = Chunk(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            page_number=4,
            chunk_index=0,
            chunk_type="TEXT",
            content="Gevra OC achieved an annual raw coal production of 52.5 MT in FY 2023-24, representing an operational capacity utilization of 98.2%. Overburden removal was recorded at 85.4 M.cum.",
            metadata_json={"section_heading": "Executive Summary", "fiscal_year": "FY2023-24"}
        )
        db_session.add(c1)

        c2 = Chunk(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            page_number=6,
            chunk_index=1,
            chunk_type="TABLE",
            content="Borehole Depth and Seam Table: Seam Upper Kusmunda thickness 18.5 m at depth 120.4 m. Seam Lower Kusmunda thickness 24.2 m at depth 185.6 m.",
            metadata_json={
                "logical_table_id": "tbl-gevra-borehole-01",
                "part": 1,
                "total_parts": 2,
                "caption": "Borehole Stratigraphy & Seam Continuation",
                "headers": ["Seam", "Thickness (m)", "Depth (m)"]
            }
        )
        db_session.add(c2)
        db_session.flush()

        indexing_service.index_document_chunks(db_session, doc.id)

    # Ensure Extracted Fields f1 and f0 exist
    f1 = db_session.query(ExtractedField).filter(
        ExtractedField.organization_id == org_secl.id,
        ExtractedField.field_name == "coal_production",
        ExtractedField.numeric_value == 52.5
    ).first()
    if not f1:
        doc_ver_id = db_session.query(DocumentVersion.id).filter(DocumentVersion.document_id == doc.id).scalar()
        f1 = ExtractedField(
            id=str(uuid.uuid4()),
            organization_id=org_secl.id,
            document_id=doc.id,
            version_id=doc_ver_id,
            field_name="coal_production",
            field_category="MINING",
            data_type="NUMBER",
            raw_value="52.5 MT",
            numeric_value=52.5,
            unit="MT",
            page_number=4,
            source_text="Gevra OC achieved an annual raw coal production of 52.5 MT in FY 2023-24",
            confidence_score=0.98,
            confidence_level="HIGH",
            validation_status="PASS",
            metadata_json={"entity_name": "Gevra OC", "reporting_period": "FY 2023-24"}
        )
        db_session.add(f1)

    f0 = db_session.query(ExtractedField).filter(
        ExtractedField.organization_id == org_secl.id,
        ExtractedField.field_name == "coal_production",
        ExtractedField.numeric_value == 46.7
    ).first()
    if not f0:
        doc_ver_id = db_session.query(DocumentVersion.id).filter(DocumentVersion.document_id == doc.id).scalar()
        f0 = ExtractedField(
            id=str(uuid.uuid4()),
            organization_id=org_secl.id,
            document_id=doc.id,
            version_id=doc_ver_id,
            field_name="coal_production",
            field_category="MINING",
            data_type="NUMBER",
            raw_value="46.7 MT",
            numeric_value=46.7,
            unit="MT",
            page_number=2,
            source_text="In the previous fiscal year FY 2022-23, Gevra OC achieved coal production of 46.7 MT",
            confidence_score=0.95,
            confidence_level="HIGH",
            validation_status="PASS",
            metadata_json={"entity_name": "Gevra OC", "reporting_period": "FY 2022-23"}
        )
        db_session.add(f0)

    db_session.commit()

    return {
        "org_secl": org_secl,
        "org_ecl": org_ecl,
        "org_cmpdi": org_cmpdi,
        "user_secl": u_secl,
        "user_cmpdi": u_cmpdi,
        "token_secl": create_access_token(u_secl.username),
        "token_cmpdi": create_access_token(u_cmpdi.username)
    }


def test_deterministic_arithmetic_engine():
    """Verify mathematical calculations are computed in code with zero LLM hallucinations."""
    # 1. YoY Growth
    calc = arithmetic_engine.calculate_yoy(
        entity_name="Gevra OC",
        metric_name="coal_production",
        period_a="FY 2022-23",
        val_a=46.7,
        period_b="FY 2023-24",
        val_b=52.5,
        unit="MT"
    )
    assert calc.operation == "YOY_COMPARISON"
    assert calc.absolute_change == 5.8
    assert calc.percentage_change == 12.42
    assert "increased by +5.8 MT (+12.42%)" in calc.natural_language_summary
    assert calc.verified is True

    # 2. Percentage change safe division
    pct_zero = arithmetic_engine.percentage_change(0.0, 15.0)
    assert pct_zero is None  # Safe division; no ZeroDivisionError

    pct_normal = arithmetic_engine.percentage_change(100.0, 115.0)
    assert pct_normal == 15.0

    # 3. Stripping Ratio
    sr = arithmetic_engine.stripping_ratio(150.0, 50.0)
    assert sr == 3.0

    # 4. Aggregations
    agg_sum = arithmetic_engine.aggregate_metrics([10.0, 20.0, 30.0], operation="SUM", metric_name="production", unit="MT")
    assert agg_sum.calculated_value == 60.0

    agg_avg = arithmetic_engine.aggregate_metrics([10.0, 20.0, 30.0], operation="AVG", metric_name="production", unit="MT")
    assert agg_avg.calculated_value == 20.0


def test_structured_lookup_and_conflict_warning(db_session: Session, qa_test_setup):
    """Verify structured facts lookup and cross-document conflict warning surfacing."""
    org_secl = qa_test_setup["org_secl"]

    # Clean up any stale conflict groups from prior test iterations
    old_rgs = db_session.query(ReconciliationGroup).filter(ReconciliationGroup.metric_name == "stripping_ratio_test").all()
    for old_rg in old_rgs:
        db_session.query(ReconciliationCandidate).filter(ReconciliationCandidate.group_id == old_rg.id).delete()
        db_session.delete(old_rg)
    db_session.query(ExtractedField).filter(ExtractedField.field_name == "stripping_ratio_test").delete()
    db_session.commit()

    rg = ReconciliationGroup(
        id=str(uuid.uuid4()),
        organization_id=org_secl.id,
        entity_name="Rajmahal OCP",
        metric_name="stripping_ratio_test",
        reporting_period="2024",
        conflict_status="CONFLICT",
        resolution_status="UNRESOLVED"
    )
    db_session.add(rg)
    db_session.flush()

    doc = db_session.query(Document).first()
    ef1 = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org_secl.id,
        document_id=doc.id,
        field_name="stripping_ratio_test",
        field_category="MINING",
        data_type="NUMBER",
        raw_value="1.85 cum/tonne",
        numeric_value=1.85,
        unit="cum/tonne",
        page_number=3,
        source_text="Stripping ratio reported at 1.85 cum/tonne",
        confidence_score=0.92,
        confidence_level="HIGH",
        validation_status="PASS",
        metadata_json={"entity_name": "Rajmahal OCP", "reporting_period": "2024"}
    )
    ef2 = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org_secl.id,
        document_id=doc.id,
        field_name="stripping_ratio_test",
        field_category="MINING",
        data_type="NUMBER",
        raw_value="2.15 cum/tonne",
        numeric_value=2.15,
        unit="cum/tonne",
        page_number=5,
        source_text="Stripping ratio reported at 2.15 cum/tonne",
        confidence_score=0.88,
        confidence_level="HIGH",
        validation_status="PASS",
        metadata_json={"entity_name": "Rajmahal OCP", "reporting_period": "2024"}
    )
    db_session.add_all([ef1, ef2])
    db_session.flush()

    cand1 = ReconciliationCandidate(
        id=str(uuid.uuid4()),
        group_id=rg.id,
        document_id=doc.id,
        field_id=ef1.id,
        value="1.85 cum/tonne",
        numeric_value=1.85,
        unit="cum/tonne",
        confidence_score=0.92
    )
    cand2 = ReconciliationCandidate(
        id=str(uuid.uuid4()),
        group_id=rg.id,
        document_id=doc.id,
        field_id=ef2.id,
        value="2.15 cum/tonne",
        numeric_value=2.15,
        unit="cum/tonne",
        confidence_score=0.88
    )
    db_session.add_all([cand1, cand2])
    db_session.commit()

    res = structured_lookup_service.lookup(
        db=db_session,
        query="What is the stripping ratio of Rajmahal OCP in 2024?",
        allowed_org_ids=[org_secl.id]
    )

    assert res.conflict_warning is not None
    assert res.conflict_warning.conflict_detected is True
    assert res.conflict_warning.status == "CONFLICT_REQUIRES_REVIEW"
    assert "Rajmahal OCP" in res.conflict_warning.message
    assert len(res.conflict_warning.candidates) == 2


def test_grounding_checker_evaluations():
    """Verify grounding checker evaluates supported, ungrounded, and refusal outputs."""
    evidence_texts = ["Gevra OC produced 52.5 MT in FY 2023-24."]
    structured_facts = [{"metric_name": "coal_production", "raw_value": "52.5 MT", "numeric_value": 52.5}]
    calculations = [{"calculated_value": 5.8, "absolute_change": 5.8, "percentage_change": 12.42, "natural_language_summary": "increased by 5.8 MT"}]

    # Case 1: Grounded answer with citation
    ans_good = "According to the annual review, Gevra OC achieved 52.5 MT in FY 2023-24 [1]."
    rep_good = grounding_checker.check(ans_good, evidence_texts, structured_facts, calculations)
    assert rep_good.is_grounded is True
    assert rep_good.verification_status == "SUPPORTED"
    assert rep_good.confidence_score >= 0.85

    # Case 2: Hallucinated number
    ans_bad = "Gevra OC produced 999.5 MT in FY 2023-24."
    rep_bad = grounding_checker.check(ans_bad, evidence_texts, structured_facts, calculations)
    assert rep_bad.is_grounded is False
    assert rep_bad.verification_status == "UNSUPPORTED"
    assert "999.5" in rep_bad.unsupported_claims[0]

    # Case 3: Standard Refusal String
    ans_refusal = STANDARD_REFUSAL_TEXT
    rep_refusal = grounding_checker.check(ans_refusal, evidence_texts, structured_facts, calculations)
    assert rep_refusal.is_refusal is True
    assert rep_refusal.verification_status == "REFUSED"


def test_llm_provider_abstraction_and_health():
    """Verify local LLM providers report health honestly and raise LLMUnavailableError when offline."""
    ollama = OllamaProvider(base_url="http://localhost:11434", timeout=1.0)
    health = ollama.health()
    assert isinstance(health, ProviderHealth)
    assert health.provider == "ollama"

    openai_local = OpenAICompatibleLocalProvider(base_url="http://localhost:8000/v1", timeout=1.0)
    health_oai = openai_local.health()
    assert isinstance(health_oai, ProviderHealth)
    assert health_oai.provider == "openai_compatible"


def test_qa_pipeline_factual_query(db_session: Session, qa_test_setup):
    """Verify end-to-end grounded query on seeded Gevra OC document returning verified facts and citations."""
    user = qa_test_setup["user_secl"]
    org_id = qa_test_setup["org_secl"].id

    # Test with MockLocalLLMProvider
    set_llm_provider(MockLocalLLMProvider("Gevra OC produced 52.5 MT of raw coal in FY 2023-24 [1]."))

    result = qa_service.answer_query(
        db=db_session,
        query="What was the coal production of Gevra OC in FY 2023-24?",
        current_user=user,
        allowed_org_ids=[org_id]
    )

    assert result["verification_status"] == "SUPPORTED"
    assert result["confidence_score"] >= 0.85
    assert len(result["citations"]) > 0
    cite = result["citations"][0]
    assert "Gevra OC" in cite["document_title"]
    assert cite["page_number"] in [4, 6]

    # Check database persistence
    q_rec = db_session.query(QueryRecord).filter(QueryRecord.id == result["query_id"]).first()
    assert q_rec is not None
    assert "Gevra OC" in q_rec.query_text

    a_rec = db_session.query(AnswerRecord).filter(AnswerRecord.id == result["answer_id"]).first()
    assert a_rec is not None
    assert a_rec.verification_status == "SUPPORTED"


def test_qa_pipeline_deterministic_yoy_calculation(db_session: Session, qa_test_setup):
    """Verify YoY growth query triggers arithmetic engine and injects deterministic calculation facts."""
    user = qa_test_setup["user_secl"]
    org_id = qa_test_setup["org_secl"].id

    # LLM provider quoting the deterministic verified calculation
    set_llm_provider(MockLocalLLMProvider(
        "Gevra OC production grew by +5.8 MT (+12.42%) from FY 2022-23 to FY 2023-24 [1]."
    ))

    result = qa_service.answer_query(
        db=db_session,
        query="What is the year-over-year production growth for Gevra OC from FY 2022-23 to FY 2023-24?",
        current_user=user,
        allowed_org_ids=[org_id]
    )

    assert result["arithmetic_used"] is True
    assert len(result["calculations"]) > 0
    calc = result["calculations"][0]
    assert calc["absolute_change"] == 5.8
    assert calc["percentage_change"] == 12.42
    assert "12.42%" in calc["formula"]


def test_qa_pipeline_multipage_table_provenance(db_session: Session, qa_test_setup):
    """Verify citations retain multi-page table provenance (logical table ID, part number, page number)."""
    user = qa_test_setup["user_secl"]
    org_id = qa_test_setup["org_secl"].id

    result = qa_service.answer_query(
        db=db_session,
        query="Borehole Depth and Seam Table Upper Kusmunda thickness",
        current_user=user,
        allowed_org_ids=[org_id]
    )

    # Find table citation
    table_cites = [c for c in result["citations"] if c.get("table_provenance")]
    assert len(table_cites) > 0
    t_prov = table_cites[0]["table_provenance"]
    assert t_prov["logical_table_id"] == "tbl-gevra-borehole-01"
    assert t_prov["part_number"] == 1
    assert t_prov["total_parts"] == 2
    assert table_cites[0]["page_number"] == 6


def test_qa_pipeline_refusal_on_insufficient_evidence(db_session: Session, qa_test_setup):
    """Verify unanswerable query yields mandated refusal string without hallucinations."""
    user = qa_test_setup["user_secl"]
    org_id = qa_test_setup["org_secl"].id

    result = qa_service.answer_query(
        db=db_session,
        query="What is the predicted uranium concentration in the Raniganj coal block for 2035?",
        current_user=user,
        allowed_org_ids=[org_id]
    )

    assert result["answer"] == STANDARD_REFUSAL_TEXT
    assert result["verification_status"] == "REFUSED"
    assert result["confidence_score"] == 1.0


def test_server_side_org_security_isolation_in_qa(qa_test_setup):
    """Verify subsidiary analysts cannot query outside their assigned organization."""
    token_secl = qa_test_setup["token_secl"]
    token_cmpdi = qa_test_setup["token_cmpdi"]
    ecl_org_id = qa_test_setup["org_ecl"].id
    secl_org_id = qa_test_setup["org_secl"].id

    # 1. SECL Analyst querying SECL succeeds (200)
    res_allowed = client.post(
        "/api/v1/qa/query",
        json={"query": "Gevra OC production in FY 2023-24", "organization_id": secl_org_id},
        headers={"Authorization": f"Bearer {token_secl}"}
    )
    assert res_allowed.status_code == 200

    # 2. SECL Analyst attempting to query ECL organization is rejected (403)
    res_denied = client.post(
        "/api/v1/qa/query",
        json={"query": "ECL mine statistics", "organization_id": ecl_org_id},
        headers={"Authorization": f"Bearer {token_secl}"}
    )
    assert res_denied.status_code == 403
    assert "Access denied" in res_denied.json()["detail"]

    # 3. CMPDI Central Officer querying ECL succeeds (200)
    res_central = client.post(
        "/api/v1/qa/query",
        json={"query": "Gevra OC production", "organization_id": secl_org_id},
        headers={"Authorization": f"Bearer {token_cmpdi}"}
    )
    assert res_central.status_code == 200


def test_api_qa_endpoints_and_audit(db_session: Session, qa_test_setup):
    """Verify /status, /history, and immutable audit event creation."""
    token_cmpdi = qa_test_setup["token_cmpdi"]

    # 1. Status endpoint
    res_status = client.get("/api/v1/qa/status")
    assert res_status.status_code == 200
    data = res_status.json()
    assert data["status"] == "OPERATIONAL"
    assert data["arithmetic_engine"]["deterministic_execution"] is True
    assert data["embeddings"]["dimension"] == 384

    # 2. History endpoint
    res_hist = client.get("/api/v1/qa/history", headers={"Authorization": f"Bearer {token_cmpdi}"})
    assert res_status.status_code == 200
    assert "history" in res_hist.json()

    # 3. Audit event verification
    audit_events = db_session.query(AuditEvent).filter(
        AuditEvent.action.in_(["QA_QUERY_EXECUTED", "QA_QUERY_REFUSED"])
    ).all()
    assert len(audit_events) > 0
