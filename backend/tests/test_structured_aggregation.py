import pytest
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.database import get_db, SessionLocal
from app.models.organization import Organization
from app.models.document import Document
from app.models.user import User
from app.models.extraction import (
    ExtractedField,
    ReconciliationGroup,
    ReconciliationCandidate,
)
from app.services.qa.structured_lookup import (
    structured_lookup_service,
    AggregationIntent,
    AggregatedMetricResult,
)
from app.services.qa.qa_service import qa_service
from app.services.qa.arithmetic_engine import arithmetic_engine


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def test_env(db_session: Session):
    """
    Creates isolated test organizations and user for structured aggregation tests.
    """
    # Pre-cleanup in case of prior aborted run
    existing_orgs = db_session.query(Organization).filter(Organization.code.in_(["SECL_AGG_TEST", "BCCL_AGG_TEST"])).all()
    for ex in existing_orgs:
        db_session.query(ReconciliationCandidate).filter(
            ReconciliationCandidate.document_id.in_(
                db_session.query(Document.id).filter(Document.organization_id == ex.id)
            )
        ).delete(synchronize_session=False)
        db_session.query(ReconciliationGroup).filter(ReconciliationGroup.organization_id == ex.id).delete(synchronize_session=False)
        db_session.query(ExtractedField).filter(ExtractedField.organization_id == ex.id).delete(synchronize_session=False)
        db_session.query(Document).filter(Document.organization_id == ex.id).delete(synchronize_session=False)
        db_session.query(User).filter(User.organization_id == ex.id).delete(synchronize_session=False)
        db_session.delete(ex)
    db_session.commit()

    org_a = Organization(
        id=str(uuid.uuid4()),
        code="SECL_AGG_TEST",
        name="South Eastern Coalfields Limited Aggregation Test Unit",
        org_type="SUBSIDIARY",
        is_active=True
    )
    org_b = Organization(
        id=str(uuid.uuid4()),
        code="BCCL_AGG_TEST",
        name="Bharat Coking Coal Limited Aggregation Test Unit",
        org_type="SUBSIDIARY",
        is_active=True
    )
    db_session.add_all([org_a, org_b])
    db_session.commit()

    test_user = User(
        id=str(uuid.uuid4()),
        username="agg_officer",
        email="agg_officer@koyla.gov.in",
        full_name="Aggregation Officer",
        hashed_password="hashed_pw_dummy",
        organization_id=org_a.id,
        is_active=True
    )
    db_session.add(test_user)
    db_session.commit()

    yield {
        "org_a": org_a,
        "org_b": org_b,
        "user": test_user,
    }

    # Cleanup
    db_session.query(ReconciliationCandidate).filter(
        ReconciliationCandidate.document_id.in_(
            db_session.query(Document.id).filter(Document.organization_id.in_([org_a.id, org_b.id]))
        )
    ).delete(synchronize_session=False)
    db_session.query(ReconciliationGroup).filter(
        ReconciliationGroup.organization_id.in_([org_a.id, org_b.id])
    ).delete(synchronize_session=False)
    db_session.query(ExtractedField).filter(
        ExtractedField.organization_id.in_([org_a.id, org_b.id])
    ).delete(synchronize_session=False)
    db_session.query(Document).filter(
        Document.organization_id.in_([org_a.id, org_b.id])
    ).delete(synchronize_session=False)
    db_session.query(User).filter(User.id == test_user.id).delete(synchronize_session=False)
    db_session.query(Organization).filter(Organization.id.in_([org_a.id, org_b.id])).delete(synchronize_session=False)
    db_session.commit()


def test_aggregation_intent_detection():
    """Verify that detect_aggregation_intent accurately classifies operations, metrics, and scopes."""
    # 1. SUM query
    intent1 = structured_lookup_service.detect_aggregation_intent(
        "What was total raw coal production across all SECL mines in FY 2023-24?"
    )
    assert intent1.is_aggregation is True
    assert intent1.operation == "SUM"
    assert "production_quantity" in intent1.canonical_fields
    assert intent1.target_subsidiary == "SECL"
    assert "2023-24" in (intent1.target_period or "")

    # 2. AVG query
    intent2 = structured_lookup_service.detect_aggregation_intent(
        "What is the average stripping ratio across open cast mines in FY24?"
    )
    assert intent2.is_aggregation is True
    assert intent2.operation == "AVG"
    assert "stripping_ratio" in intent2.canonical_fields

    # 3. Area and Dispatch query
    intent3 = structured_lookup_service.detect_aggregation_intent(
        "Total coal dispatch from Korba area in 2023-24?"
    )
    assert intent3.is_aggregation is True
    assert intent3.operation == "SUM"
    assert "dispatch_quantity" in intent3.canonical_fields
    assert intent3.target_entity == "Korba"

    # 4. MIN and MAX query
    intent4 = structured_lookup_service.detect_aggregation_intent("What is the minimum ash content reported?")
    assert intent4.is_aggregation is True
    assert intent4.operation == "MIN"
    assert "ash_content" in intent4.canonical_fields

    intent5 = structured_lookup_service.detect_aggregation_intent("Find maximum gross calorific value")
    assert intent5.is_aggregation is True
    assert intent5.operation == "MAX"
    assert "gcv" in intent5.canonical_fields

    # 5. COUNT query
    intent6 = structured_lookup_service.detect_aggregation_intent("How many mines reported production in FY24?")
    assert intent6.is_aggregation is True
    assert intent6.operation == "COUNT"

    # 6. Non-aggregation queries
    intent_non = structured_lookup_service.detect_aggregation_intent("What is the seam thickness of Seam III?")
    assert intent_non.is_aggregation is False

    # 7. YoY growth should NOT be classified as multi-document aggregation
    intent_yoy = structured_lookup_service.detect_aggregation_intent(
        "Compare the raw coal production growth from FY23 to FY24"
    )
    assert intent_yoy.is_aggregation is False


def test_multi_document_sum_aggregation(db_session: Session, test_env: dict):
    """
    Test deterministic SQL SUM aggregation over multiple documents with provenance tracing.
    """
    org_a = test_env["org_a"]

    # Create 3 documents
    doc1 = Document(
        id=str(uuid.uuid4()),
        organization_id=org_a.id,
        title="Gevra OC Production Review FY 2023-24",
        document_type="PRODUCTION_REPORT",
        original_filename="gevra.pdf",
        file_path="/app/storage/gevra.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="hash1",
        status="PROCESSED"
    )
    doc2 = Document(
        id=str(uuid.uuid4()),
        organization_id=org_a.id,
        title="Kusmunda OC Monthly Summary FY 2023-24",
        document_type="PRODUCTION_REPORT",
        original_filename="kusmunda.pdf",
        file_path="/app/storage/kusmunda.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="hash2",
        status="PROCESSED"
    )
    doc3 = Document(
        id=str(uuid.uuid4()),
        organization_id=org_a.id,
        title="Dipka OC Annual Return FY 2023-24",
        document_type="PRODUCTION_REPORT",
        original_filename="dipka.pdf",
        file_path="/app/storage/dipka.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="hash3",
        status="PROCESSED"
    )
    db_session.add_all([doc1, doc2, doc3])
    db_session.commit()

    # Create ExtractedFields
    ef1 = ExtractedField(
        id=str(uuid.uuid4()),
        document_id=doc1.id,
        organization_id=org_a.id,
        field_name="production_quantity",
        raw_value="52.5 MT",
        numeric_value=52.5,
        unit="MT",
        page_number=3,
        source_text="Gevra OC produced 52.5 MT in FY 2023-24",
        metadata_json={"entity_name": "Gevra", "reporting_period": "2023-24"},
        verification_status="VERIFIED"
    )
    ef2 = ExtractedField(
        id=str(uuid.uuid4()),
        document_id=doc2.id,
        organization_id=org_a.id,
        field_name="production_quantity",
        raw_value="43.0 MT",
        numeric_value=43.0,
        unit="MT",
        page_number=5,
        source_text="Kusmunda OC achieved 43.0 MT in FY 2023-24",
        metadata_json={"entity_name": "Kusmunda", "reporting_period": "2023-24"},
        verification_status="VERIFIED"
    )
    ef3 = ExtractedField(
        id=str(uuid.uuid4()),
        document_id=doc3.id,
        organization_id=org_a.id,
        field_name="production_quantity",
        raw_value="35.5 MT",
        numeric_value=35.5,
        unit="MT",
        page_number=2,
        source_text="Dipka OC total output 35.5 MT in FY 2023-24",
        metadata_json={"entity_name": "Dipka", "reporting_period": "2023-24"},
        verification_status="UNVERIFIED"
    )
    db_session.add_all([ef1, ef2, ef3])
    db_session.commit()

    intent = AggregationIntent(
        is_aggregation=True,
        operation="SUM",
        metric_label="raw coal production",
        canonical_fields=["production_quantity", "coal_production"],
        target_subsidiary=None,
        target_entity=None,
        target_period="2023-24",
        scope_description="FY 2023-24"
    )

    result = structured_lookup_service.execute_aggregation(
        db=db_session,
        intent=intent,
        allowed_org_ids=[org_a.id]
    )

    assert result is not None
    assert result.calculated_value == 131.0  # 52.5 + 43.0 + 35.5
    assert result.record_count == 3
    assert result.unit == "MT"
    assert "52.5" in result.formula
    assert "43.0" in result.formula
    assert "35.5" in result.formula
    assert len(result.contributing_records) == 3

    # Check provenance
    doc_titles = [c.document_title for c in result.contributing_records]
    assert "Gevra OC Production Review FY 2023-24" in doc_titles
    assert "Kusmunda OC Monthly Summary FY 2023-24" in doc_titles
    assert "Dipka OC Annual Return FY 2023-24" in doc_titles


def test_multi_document_avg_and_min_max(db_session: Session, test_env: dict):
    """
    Test AVG, MIN, MAX and COUNT operations over stripping ratio.
    """
    org_a = test_env["org_a"]

    doc = Document(
        id=str(uuid.uuid4()),
        organization_id=org_a.id,
        title="Stripping Ratio Consolidated FY 2023-24",
        document_type="STATUTORY_REPORT",
        original_filename="sr.pdf",
        file_path="/app/storage/sr.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="hash_sr",
        status="PROCESSED"
    )
    db_session.add(doc)
    db_session.commit()

    ef1 = ExtractedField(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        organization_id=org_a.id,
        field_name="stripping_ratio",
        raw_value="2.0",
        numeric_value=2.0,
        unit="cum/tonne",
        page_number=1,
        source_text="Pit A SR was 2.0 cum/tonne in FY 2023-24",
        metadata_json={"entity_name": "Pit A", "reporting_period": "2023-24"}
    )
    ef2 = ExtractedField(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        organization_id=org_a.id,
        field_name="stripping_ratio",
        raw_value="4.0",
        numeric_value=4.0,
        unit="cum/tonne",
        page_number=2,
        source_text="Pit B SR was 4.0 cum/tonne in FY 2023-24",
        metadata_json={"entity_name": "Pit B", "reporting_period": "2023-24"}
    )
    db_session.add_all([ef1, ef2])
    db_session.commit()

    # AVG
    avg_intent = AggregationIntent(
        is_aggregation=True,
        operation="AVG",
        metric_label="stripping ratio",
        canonical_fields=["stripping_ratio"],
        target_period="2023-24",
        scope_description="FY 2023-24"
    )
    avg_res = structured_lookup_service.execute_aggregation(db_session, avg_intent, allowed_org_ids=[org_a.id])
    assert avg_res.calculated_value == 3.0
    assert avg_res.record_count == 2

    # MIN
    min_intent = AggregationIntent(
        is_aggregation=True,
        operation="MIN",
        metric_label="stripping ratio",
        canonical_fields=["stripping_ratio"],
        target_period="2023-24",
        scope_description="FY 2023-24"
    )
    min_res = structured_lookup_service.execute_aggregation(db_session, min_intent, allowed_org_ids=[org_a.id])
    assert min_res.calculated_value == 2.0

    # MAX
    max_intent = AggregationIntent(
        is_aggregation=True,
        operation="MAX",
        metric_label="stripping ratio",
        canonical_fields=["stripping_ratio"],
        target_period="2023-24",
        scope_description="FY 2023-24"
    )
    max_res = structured_lookup_service.execute_aggregation(db_session, max_intent, allowed_org_ids=[org_a.id])
    assert max_res.calculated_value == 4.0

    # COUNT
    count_intent = AggregationIntent(
        is_aggregation=True,
        operation="COUNT",
        metric_label="stripping ratio",
        canonical_fields=["stripping_ratio"],
        target_period="2023-24",
        scope_description="FY 2023-24"
    )
    count_res = structured_lookup_service.execute_aggregation(db_session, count_intent, allowed_org_ids=[org_a.id])
    assert count_res.calculated_value == 2.0


def test_tenant_isolation_in_sql_aggregation(db_session: Session, test_env: dict):
    """
    Verify server-side tenant isolation: Org A user cannot aggregate or access Org B records.
    """
    org_a = test_env["org_a"]
    org_b = test_env["org_b"]

    doc_b = Document(
        id=str(uuid.uuid4()),
        organization_id=org_b.id,
        title="BCCL Internal Secret Document FY 2023-24",
        document_type="PRODUCTION_REPORT",
        original_filename="bccl_secret.pdf",
        file_path="/app/storage/bccl_secret.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="hash_b",
        status="PROCESSED"
    )
    db_session.add(doc_b)
    db_session.commit()

    ef_b = ExtractedField(
        id=str(uuid.uuid4()),
        document_id=doc_b.id,
        organization_id=org_b.id,
        field_name="production_quantity",
        raw_value="999.0 MT",
        numeric_value=999.0,
        unit="MT",
        page_number=1,
        source_text="Secret production was 999.0 MT in FY 2023-24",
        metadata_json={"entity_name": "Secret Mine", "reporting_period": "2023-24"},
        verification_status="VERIFIED"
    )
    db_session.add(ef_b)
    db_session.commit()

    # User with allowed_org_ids=[org_a.id] queries total production
    intent = AggregationIntent(
        is_aggregation=True,
        operation="SUM",
        metric_label="raw coal production",
        canonical_fields=["production_quantity"],
        target_period="2023-24",
        scope_description="FY 2023-24"
    )
    res = structured_lookup_service.execute_aggregation(
        db=db_session,
        intent=intent,
        allowed_org_ids=[org_a.id]
    )

    # Org B's 999.0 must NOT be in the result
    assert 999.0 not in [c.numeric_value for c in res.contributing_records]
    assert all(c.document_id != doc_b.id for c in res.contributing_records)

    # If query explicitly targets BCCL_AGG_TEST when user only has access to Org A
    intent_b = AggregationIntent(
        is_aggregation=True,
        operation="SUM",
        metric_label="raw coal production",
        canonical_fields=["production_quantity"],
        target_subsidiary="BCCL_AGG_TEST",
        target_period="2023-24",
        scope_description="BCCL FY 2023-24"
    )
    res_b = structured_lookup_service.execute_aggregation(
        db=db_session,
        intent=intent_b,
        allowed_org_ids=[org_a.id]
    )
    assert res_b.record_count == 0
    assert "permissions" in res_b.natural_language_summary.lower()


def test_verification_status_and_conflict_exclusion(db_session: Session, test_env: dict):
    """
    Verify that:
    1. REJECTED fields are excluded.
    2. Unresolved ReconciliationGroup conflict candidates are excluded with an advisory.
    """
    org_a = test_env["org_a"]

    doc = Document(
        id=str(uuid.uuid4()),
        organization_id=org_a.id,
        title="Audit & Conflict Document FY 2023-24",
        document_type="STATUTORY_REPORT",
        original_filename="audit.pdf",
        file_path="/app/storage/audit.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="hash_audit",
        status="PROCESSED"
    )
    db_session.add(doc)
    db_session.commit()

    # 1. Valid verified field
    ef_valid = ExtractedField(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        organization_id=org_a.id,
        field_name="drilling_metreage",
        raw_value="1500.0 m",
        numeric_value=1500.0,
        unit="m",
        page_number=1,
        source_text="Exploration Borehole Group A drilled 1500.0 m in FY 2023-24",
        metadata_json={"entity_name": "Block X", "reporting_period": "2023-24"},
        verification_status="VERIFIED"
    )

    # 2. Rejected field (should be excluded)
    ef_rejected = ExtractedField(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        organization_id=org_a.id,
        field_name="drilling_metreage",
        raw_value="99999.0 m",
        numeric_value=99999.0,
        unit="m",
        page_number=2,
        source_text="Faulty sensor reading 99999.0 m in FY 2023-24",
        metadata_json={"entity_name": "Block Y", "reporting_period": "2023-24"},
        verification_status="REJECTED"
    )

    # 3. Conflicting field in an unresolved ReconciliationGroup
    ef_conflict = ExtractedField(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        organization_id=org_a.id,
        field_name="drilling_metreage",
        raw_value="2500.0 m",
        numeric_value=2500.0,
        unit="m",
        page_number=3,
        source_text="Contested drilling reading 2500.0 m in FY 2023-24",
        metadata_json={"entity_name": "Block Z", "reporting_period": "2023-24"},
        verification_status="UNVERIFIED"
    )
    db_session.add_all([ef_valid, ef_rejected, ef_conflict])
    db_session.commit()

    recon_group = ReconciliationGroup(
        id=str(uuid.uuid4()),
        organization_id=org_a.id,
        entity_name="Block Z",
        metric_name="drilling_metreage",
        reporting_period="2023-24",
        conflict_status="CONFLICT",
        resolution_status="UNRESOLVED"
    )
    db_session.add(recon_group)
    db_session.commit()

    recon_cand = ReconciliationCandidate(
        id=str(uuid.uuid4()),
        group_id=recon_group.id,
        document_id=doc.id,
        field_id=ef_conflict.id,
        value="2500.0 m",
        numeric_value=2500.0,
        unit="m"
    )
    db_session.add(recon_cand)
    db_session.commit()

    intent = AggregationIntent(
        is_aggregation=True,
        operation="SUM",
        metric_label="drilling metreage",
        canonical_fields=["drilling_metreage"],
        target_period="2023-24",
        scope_description="FY 2023-24"
    )
    res = structured_lookup_service.execute_aggregation(db_session, intent, allowed_org_ids=[org_a.id])

    assert res is not None
    # REJECTED (99999.0) and CONFLICT (2500.0) must be excluded; only ef_valid (1500.0) included
    assert res.calculated_value == 1500.0
    assert res.conflict_warning is not None
    assert "Cross-document discrepancy detected" in res.conflict_warning


def test_qa_pipeline_end_to_end_aggregation(db_session: Session, test_env: dict):
    """
    Test end-to-end grounded QA pipeline with multi-document aggregation.
    """
    user = test_env["user"]
    org_a = test_env["org_a"]

    # Ensure test documents and fields exist
    count = db_session.query(ExtractedField).filter(
        ExtractedField.organization_id == org_a.id,
        ExtractedField.field_name == "production_quantity"
    ).count()
    if count < 3:
        doc1 = Document(
            id=str(uuid.uuid4()),
            organization_id=org_a.id,
            title="Gevra OC Production Review FY 2023-24",
            document_type="PRODUCTION_REPORT",
            original_filename="gevra.pdf",
            file_path="/app/storage/gevra.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            sha256_hash="hash1",
            status="PROCESSED"
        )
        doc2 = Document(
            id=str(uuid.uuid4()),
            organization_id=org_a.id,
            title="Kusmunda OC Monthly Summary FY 2023-24",
            document_type="PRODUCTION_REPORT",
            original_filename="kusmunda.pdf",
            file_path="/app/storage/kusmunda.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            sha256_hash="hash2",
            status="PROCESSED"
        )
        doc3 = Document(
            id=str(uuid.uuid4()),
            organization_id=org_a.id,
            title="Dipka OC Annual Return FY 2023-24",
            document_type="PRODUCTION_REPORT",
            original_filename="dipka.pdf",
            file_path="/app/storage/dipka.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            sha256_hash="hash3",
            status="PROCESSED"
        )
        db_session.add_all([doc1, doc2, doc3])
        db_session.commit()

        ef1 = ExtractedField(
            id=str(uuid.uuid4()),
            document_id=doc1.id,
            organization_id=org_a.id,
            field_name="production_quantity",
            raw_value="52.5 MT",
            numeric_value=52.5,
            unit="MT",
            page_number=3,
            source_text="Gevra OC produced 52.5 MT in FY 2023-24",
            metadata_json={"entity_name": "Gevra", "reporting_period": "2023-24"},
            verification_status="VERIFIED"
        )
        ef2 = ExtractedField(
            id=str(uuid.uuid4()),
            document_id=doc2.id,
            organization_id=org_a.id,
            field_name="production_quantity",
            raw_value="43.0 MT",
            numeric_value=43.0,
            unit="MT",
            page_number=5,
            source_text="Kusmunda OC achieved 43.0 MT in FY 2023-24",
            metadata_json={"entity_name": "Kusmunda", "reporting_period": "2023-24"},
            verification_status="VERIFIED"
        )
        ef3 = ExtractedField(
            id=str(uuid.uuid4()),
            document_id=doc3.id,
            organization_id=org_a.id,
            field_name="production_quantity",
            raw_value="35.5 MT",
            numeric_value=35.5,
            unit="MT",
            page_number=2,
            source_text="Dipka OC total output 35.5 MT in FY 2023-24",
            metadata_json={"entity_name": "Dipka", "reporting_period": "2023-24"},
            verification_status="UNVERIFIED"
        )
        db_session.add_all([ef1, ef2, ef3])
        db_session.commit()

    from app.services.llm import LLMProvider, LLMResponse, ProviderHealth, ProviderModelInfo, set_llm_provider

    class MockAggLLMProvider(LLMProvider):
        def generate(self, prompt: str, system_prompt=None, temperature=0.1, max_tokens=1024, **kwargs) -> LLMResponse:
            return LLMResponse(
                content="Total raw coal production in FY 2023-24 across 3 mines was 131.0 MT [1] [2] [3].",
                model_name="mock-agg-llm",
                provider="mock",
                latency_ms=10.0
            )

        def structured_generate(self, prompt: str, schema, system_prompt=None, **kwargs):
            return {}

        def health(self) -> ProviderHealth:
            return ProviderHealth(
                is_healthy=True,
                provider="mock",
                model_name="mock-agg-llm",
                endpoint="http://localhost:11434"
            )

        def model_info(self) -> ProviderModelInfo:
            return ProviderModelInfo(
                provider="mock",
                model_name="mock-agg-llm",
                is_local=True
            )

    set_llm_provider(MockAggLLMProvider())

    try:
        qa_response = qa_service.answer_query(
            db=db_session,
            query="What is the total raw coal production in FY 2023-24?",
            current_user=user,
            allowed_org_ids=[org_a.id]
        )

        assert qa_response is not None
        assert qa_response.get("verification_status") in ("SUPPORTED", "PARTIALLY_SUPPORTED")
        assert qa_response.get("aggregation_result") is not None
        assert qa_response["aggregation_result"]["record_count"] >= 3
        assert qa_response["aggregation_result"]["calculated_value"] == 131.0

        # Ensure answer text mentions formula or calculation
        answer_text = qa_response.get("answer", "")
        assert "131.0" in answer_text or "131" in answer_text
        assert len(qa_response["citations"]) >= 3
    finally:
        set_llm_provider(None)


def test_zero_matching_records_refusal(db_session: Session, test_env: dict):
    """
    Verify that an aggregation query targeting non-existent data produces a clean, honest refusal.
    """
    user = test_env["user"]
    org_a = test_env["org_a"]

    qa_response = qa_service.answer_query(
        db=db_session,
        query="What was the total coal dispatch from NonExistentArea in 2011?",
        current_user=user,
        allowed_org_ids=[org_a.id]
    )

    assert qa_response["verification_status"] == "REFUSED"
    assert "No verified structured records found" in qa_response["answer"] or "Insufficient verified evidence" in qa_response["answer"]
