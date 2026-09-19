import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.core.temporal import validate_fiscal_year_syntax
from app.db.database import SessionLocal
from app.services.qa.grounding_checker import grounding_checker, STANDARD_REFUSAL_TEXT
from app.services.qa.arithmetic_engine import arithmetic_engine
from app.services.qa.structured_lookup import StructuredFact, StructuredLookupService
from app.models.document import Document
from app.models.extraction import ExtractedField, ReconciliationGroup, ReconciliationCandidate
from app.models.user import User
from app.models.organization import Organization


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_setup(db_session: Session):
    org = db_session.query(Organization).filter(Organization.code == "ECL").first()
    if not org:
        org = Organization(id=str(uuid.uuid4()), code="ECL", name="Eastern Coalfields Limited", org_type="SUBSIDIARY")
        db_session.add(org)
        db_session.commit()
    user = db_session.query(User).filter(User.username == "ecl_analyst").first()
    if not user:
        user = User(id=str(uuid.uuid4()), username="ecl_analyst", email="analyst@ecl.gov.in", hashed_password="pwd", organization_id=org.id)
        db_session.add(user)
        db_session.commit()
    return {"org_ecl": org, "user_ecl": user}



# ==============================================================================
# CASE A: Supported Factual Statement
# ==============================================================================
def test_case_a_supported_factual_statement():
    """Verifies that an answer containing only evidence-grounded facts receives SUPPORTED status."""
    evidence = [
        "ECL reported total coal production of 42.5 MT for FY2023-24 at Rajmahal Open Cast Project."
    ]
    facts = [
        {"entity_name": "Rajmahal", "metric_name": "coal_production", "raw_value": "42.5 MT", "numeric_value": 42.5}
    ]
    answer = "Based on the evidence, ECL reported total coal production of 42.5 MT for FY2023-24 at Rajmahal [1]."
    chunks = [{"source_text": evidence[0]}]

    report = grounding_checker.check(
        answer_text=answer,
        evidence_texts=evidence,
        structured_facts=facts,
        calculations=[],
        top_retrieval_score=0.85,
        retrieved_chunks=chunks
    )

    assert report.is_grounded is True
    assert report.verification_status == "SUPPORTED"
    assert report.supported_claims >= 1
    assert len(report.unsupported_claims) == 0
    assert report.confidence_score >= 0.85
    assert report.has_speculative_inference is False


# ==============================================================================
# CASE B: Supported Number + Unsupported Speculative Inference
# ==============================================================================
def test_case_b_supported_number_with_unsupported_inference():
    """
    Verifies that when an LLM produces a supported number followed by an unsupported
    speculative extrapolation (e.g. demand/depletion), the speculation is flagged
    and the answer is either demoted to PARTIALLY_SUPPORTED or cleanly refined.
    """
    evidence = [
        "ECL reported total coal production of 42.5 MT for FY2023-24."
    ]
    facts = [
        {"entity_name": "ECL", "metric_name": "coal_production", "raw_value": "42.5", "numeric_value": 42.5}
    ]
    # This matches the exact failure mode identified in the audit
    answer = (
        "Based on the given evidence, the geological coal reserve or production reported by ECL is approximately 42.5 tons per month. "
        "This indicates that the ECL has sufficient coal resources to meet its current demand without any significant depletion over time."
    )
    chunks = [{"source_text": evidence[0]}]

    report = grounding_checker.check(
        answer_text=answer,
        evidence_texts=evidence,
        structured_facts=facts,
        calculations=[],
        top_retrieval_score=0.85,
        retrieved_chunks=chunks
    )

    # 1. Speculative inference is caught
    assert report.has_speculative_inference is True
    assert report.verification_status == "PARTIALLY_SUPPORTED"
    assert report.confidence_score < 0.80  # Calibrated downward due to ungrounded sentence
    assert any("speculative inference" in u.lower() for u in report.unsupported_claims)

    # 2. Refined answer retains only the evidence-backed sentence
    assert report.refined_answer is not None
    assert "42.5" in report.refined_answer
    assert "sufficient coal resources" not in report.refined_answer
    assert "depletion" not in report.refined_answer

    # 3. Checking the refined answer certifies it as fully SUPPORTED
    refined_report = grounding_checker.check(
        answer_text=report.refined_answer,
        evidence_texts=evidence,
        structured_facts=facts,
        calculations=[],
        top_retrieval_score=0.85,
        retrieved_chunks=chunks
    )
    assert refined_report.is_grounded is True
    assert refined_report.verification_status == "SUPPORTED"


# ==============================================================================
# CASE C: Wrong-Organization Citation Filtering
# ==============================================================================
def test_case_c_wrong_organization_citation_filtering():
    """
    Verifies that when a query specifically targets ECL, documents from BCCL
    that do not mention ECL are prevented from contaminating citations.
    """
    raw_results = [
        {"title": "ECL Annual Safety Audit 2023-24", "source_text": "ECL achieved 42.5 MT."},
        {"title": "BCCL Geological Exploration Report 2024", "source_text": "Moonidih colliery drilled Seam-III."}
    ]
    query = "What is the coal production reported for ECL?"

    # Simulating organization consistency filter
    import re
    target_sub = "ECL"
    consistent_results = []
    for r in raw_results:
        r_text = r.get("source_text", "").upper()
        r_title = r.get("title", "").upper()
        if target_sub in r_text or target_sub in r_title:
            consistent_results.append(r)
        else:
            is_conflicting = any(
                s in r_title for s in ["BCCL", "CCL", "WCL", "SECL", "MCL", "NCL"]
                if s != target_sub
            )
            if not is_conflicting:
                consistent_results.append(r)

    assert len(consistent_results) == 1
    assert consistent_results[0]["title"] == "ECL Annual Safety Audit 2023-24"
    assert "BCCL" not in consistent_results[0]["title"]


# ==============================================================================
# CASE D: Wrong-Document Citation Binding
# ==============================================================================
def test_case_d_wrong_document_citation_binding():
    """Verifies that citation-to-claim binding detects citations that do not support the attached assertion."""
    evidence = [
        "ECL achieved 42.5 MT production in FY2023-24."
    ]
    chunks = [
        {"source_text": "BCCL Moonidih colliery conducted drilling on Seam-IV."} # Chunk 1 does not have 42.5 MT
    ]
    answer = "ECL achieved 42.5 MT production [1]."

    report = grounding_checker.check(
        answer_text=answer,
        evidence_texts=evidence,
        structured_facts=[],
        calculations=[],
        top_retrieval_score=0.85,
        retrieved_chunks=chunks
    )

    assert report.citation_binding_valid is False
    assert len(report.mismatched_citations) >= 1
    assert "[1]" in report.mismatched_citations[0]


# ==============================================================================
# CASE E: Unsupported Historical Question
# ==============================================================================
def test_case_e_unsupported_historical_question():
    """Verifies that an unsupported historical question produces explicit refusal."""
    evidence = [
        "ECL Rajmahal production records for FY2022-23 and FY2023-24."
    ]
    # System returns refusal when question asks about 1947
    refusal_answer = STANDARD_REFUSAL_TEXT
    report = grounding_checker.check(
        answer_text=refusal_answer,
        evidence_texts=evidence,
        structured_facts=[],
        calculations=[],
        top_retrieval_score=0.01
    )

    assert report.is_refusal is True
    assert report.verification_status == "REFUSED"
    assert report.confidence_score == 0.0


# ==============================================================================
# CASE F: Invalid Financial Year / Temporal Validation
# ==============================================================================
def test_case_f_temporal_financial_year_validation():
    """
    Verifies that malformed financial years (e.g. 2025-61) are strictly rejected,
    while legitimate fiscal years (FY2023-24, 2024-25) are validated.
    """
    # 1. Invalid rollover: 2025-61 (expected 2025-26)
    valid_bad, err_bad = validate_fiscal_year_syntax("2025-61")
    assert valid_bad is False
    assert "Invalid financial year rollover" in err_bad

    # 2. Random hex test periods
    valid_hex, _ = validate_fiscal_year_syntax("2025-ba")
    assert valid_hex is False

    # 3. Valid formats
    valid_1, norm_1 = validate_fiscal_year_syntax("FY2023-24")
    assert valid_1 is True
    assert norm_1 == "FY2023-24"

    valid_2, norm_2 = validate_fiscal_year_syntax("2024-25")
    assert valid_2 is True
    assert norm_2 == "FY2024-25"

    valid_3, norm_3 = validate_fiscal_year_syntax("FY 2022-2023")
    assert valid_3 is True
    assert norm_3 == "FY2022-23"

    valid_4, norm_4 = validate_fiscal_year_syntax("Q2 FY2023-24")
    assert valid_4 is True


# ==============================================================================
# CASE G: Cross-Document Conflict Verification
# ==============================================================================
def test_case_g_cross_document_conflict_handling(db_session: Session, test_setup):
    """Verifies that conflicting values across documents trigger CONFLICT_REQUIRES_REVIEW and preserve both sources."""
    org = test_setup["org_ecl"]
    user = test_setup["user_ecl"]

    doc_a = Document(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        title="Conflict Report Alpha",
        document_type="PRODUCTION_REPORT",
        original_filename="alpha.pdf",
        file_path="storage/alpha.pdf",
        mime_type="application/pdf",
        file_size_bytes=400,
        sha256_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        status="PROCESSED",
        created_by=user.id
    )
    doc_b = Document(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        title="Conflict Report Beta",
        document_type="PRODUCTION_REPORT",
        original_filename="beta.pdf",
        file_path="storage/beta.pdf",
        mime_type="application/pdf",
        file_size_bytes=400,
        sha256_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        status="PROCESSED",
        created_by=user.id
    )
    db_session.add_all([doc_a, doc_b])
    db_session.commit()

    test_entity = "Mine Adversarial Omega"
    test_fy = "FY2023-24"

    rg = ReconciliationGroup(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        entity_name=test_entity,
        metric_name="coal_production",
        reporting_period=test_fy,
        conflict_status="CONFLICT",
        resolution_status="UNRESOLVED"
    )
    db_session.add(rg)
    db_session.flush()

    field_a = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc_a.id,
        field_name="coal_production",
        raw_value="50.0 MT",
        numeric_value=50.0,
        unit="MT",
    )
    field_b = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc_b.id,
        field_name="coal_production",
        raw_value="55.0 MT",
        numeric_value=55.0,
        unit="MT",
    )
    db_session.add_all([field_a, field_b])
    db_session.commit()

    cand_a = ReconciliationCandidate(
        id=str(uuid.uuid4()),
        group_id=rg.id,
        document_id=doc_a.id,
        field_id=field_a.id,
        value="50.0",
        numeric_value=50.0,
        unit="MT",
        confidence_score=1.0
    )
    cand_b = ReconciliationCandidate(
        id=str(uuid.uuid4()),
        group_id=rg.id,
        document_id=doc_b.id,
        field_id=field_b.id,
        value="55.0",
        numeric_value=55.0,
        unit="MT",
        confidence_score=1.0
    )
    db_session.add_all([cand_a, cand_b])
    db_session.commit()

    service = StructuredLookupService()
    res = service.lookup(
        db=db_session,
        query=f"What is the coal production for {test_entity} in {test_fy}?",
        allowed_org_ids=[org.id]
    )

    assert res.conflict_warning is not None
    assert res.conflict_warning.conflict_detected is True
    assert res.conflict_warning.status == "CONFLICT_REQUIRES_REVIEW"
    assert len(res.conflict_warning.candidates) == 2
    # Ensure both candidate values are preserved
    vals = [c["numeric_value"] for c in res.conflict_warning.candidates]
    assert 50.0 in vals
    assert 55.0 in vals


# ==============================================================================
# CASE H: Deterministic Arithmetic Calculation (Zero LLM Math)
# ==============================================================================
def test_case_h_deterministic_arithmetic_calculation():
    """Verifies that mathematical comparisons (YoY) execute strictly via Python code."""
    records = [
        {"entity_name": "Gevra OC", "metric_name": "coal_production", "reporting_period": "FY2022-23", "numeric_value": 46.7, "unit": "MT", "document_id": "doc1", "page_number": 2},
        {"entity_name": "Gevra OC", "metric_name": "coal_production", "reporting_period": "FY2023-24", "numeric_value": 52.5, "unit": "MT", "document_id": "doc2", "page_number": 4},
    ]
    query = "What is the year over year production change from FY2022-23 to FY2023-24 for Gevra OC?"

    calculations = arithmetic_engine.detect_and_execute_calculations(query, records)
    assert len(calculations) >= 1
    calc = calculations[0]
    assert calc.operation == "YOY_COMPARISON"
    assert calc.absolute_change == 5.8
    assert calc.percentage_change == 12.42
    assert "increased by +5.8 MT (+12.42%)" in calc.natural_language_summary
    assert calc.verified is True


# ==============================================================================
# CASE I: Multi-Page Table Value Provenance Preservation
# ==============================================================================
def test_case_i_multipage_table_provenance():
    """Verifies that table values spanning across physical pages preserve exact page provenance."""
    fact = StructuredFact(
        field_id="field-table-part2",
        document_id="doc-exploration-01",
        document_title="Detailed Exploration Block VIII",
        page_number=14,
        entity_name="Seam VI",
        metric_name="proved_reserves",
        raw_value="12.4 MT",
        numeric_value=12.4,
        unit="MT",
        reporting_period="FY2023-24",
        table_id="tab-continuation-01",
        source_text="Seam VI | Proved: 12.4 MT | Indicated: 4.2 MT [Table Continuation Page 14]"
    )

    evidence = [fact.source_text]
    answer = "Seam VI has proved reserves of 12.4 MT reported on page 14 [1]."
    chunks = [{"source_text": evidence[0], "page_number": 14, "title": fact.document_title}]

    report = grounding_checker.check(
        answer_text=answer,
        evidence_texts=evidence,
        structured_facts=[fact.dict()],
        calculations=[],
        top_retrieval_score=0.90,
        retrieved_chunks=chunks
    )

    assert report.is_grounded is True
    assert report.verification_status == "SUPPORTED"
    assert report.supported_claims >= 1


# ==============================================================================
# CASE J: Off-Topic Question Refusal
# ==============================================================================
def test_case_j_off_topic_question_refusal():
    """Verifies that an off-topic query without topical overlap is refused immediately."""
    evidence = [
        "BCCL Moonidih colliery coal seam exploration records."
    ]
    answer = STANDARD_REFUSAL_TEXT

    report = grounding_checker.check(
        answer_text=answer,
        evidence_texts=evidence,
        structured_facts=[],
        calculations=[],
        top_retrieval_score=0.00
    )

    assert report.is_refusal is True
    assert report.verification_status == "REFUSED"
    assert report.confidence_score == 0.0
    assert len(report.unsupported_claims) == 0
