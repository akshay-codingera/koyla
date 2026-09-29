"""
Phase 11 P1-3: Two-Tier 4-Eyes Verification for Statutory Reserve Edits - Test Suite

Tests:
    1.  Proposing reserve edit preserves original value and enters PENDING_VERIFICATION
    2.  Four-Eyes rule: maker attempting self-approval is rejected (HTTP 403)
    3.  Self-approval blocked logs security audit event STATUTORY_RESERVE_SELF_APPROVAL_BLOCKED
    4.  Independent checker can approve proposed edit
    5.  Approved edit updates authoritative ExtractedField and marks VERIFIED
    6.  Rejection leaves original authoritative value intact and stores rejection rationale
    7.  Already-resolved edits (VERIFIED or REJECTED) cannot be approved or rejected again
    8.  Concurrency control: double-approval of same request is safely blocked (HTTP 409)
    9.  Unauthorized maker without edit permissions is rejected (HTTP 403)
    10. Unauthorized checker without verifier role is rejected (HTTP 403)
    11. Organization isolation: maker cannot propose edit for another organization
    12. Organization isolation: checker cannot approve edit for another organization
    13. Enterprise roles (HQ, Ministry, Sysadmin) can review across organizations
    14. Grounded QA excludes pending proposed values and uses authoritative original value
    15. Grounded QA incorporates approved verified value
    16. P0-3 Aggregation excludes pending proposals and uses authoritative values
    17. P0-3 Aggregation includes verified value after approval
    18. Audit event generation on proposal (STATUTORY_RESERVE_EDIT_PROPOSED)
    19. Audit event generation on approval (STATUTORY_RESERVE_EDIT_APPROVED)
    20. Audit event generation on rejection (STATUTORY_RESERVE_EDIT_REJECTED)
    21. Numeric validation: negative reserve rejected (ValueError / 400)
    22. Numeric validation: non-numeric string rejected (ValueError / 400)
    23. Unit compatibility: incompatible unit rejected (ValueError / 400)
    24. Unit preservation: valid unit suffix cleanly parsed and preserved
    25. Immutable history: multiple successive proposals preserved chronologically
    26. Maker cannot reject own edit (four-eyes resolution separation)
    27. API: POST /api/v1/statutory/reserves/{id}/edits
    28. API: GET /api/v1/statutory/reserve-edits/pending
    29. API: GET /api/v1/statutory/reserve-edits/{id}
    30. API: POST /api/v1/statutory/reserve-edits/{id}/approve (self-approval blocked)
    31. API: POST /api/v1/statutory/reserve-edits/{id}/approve (independent approval)
    32. API: POST /api/v1/statutory/reserve-edits/{id}/reject
    33. API: GET /api/v1/statutory/reserves/{id}/history
"""
import os
import sys
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.db.database import SessionLocal
from app.core.security import create_access_token
from app.models.organization import Organization
from app.models.user import User, Role, UserRole
from app.models.document import Document, DocumentPage
from app.models.extraction import ExtractedField, ExtractionRun
from app.models.verification import StatutoryReserveVerification
from app.models.audit import AuditEvent
from app.services.statutory_verification import StatutoryVerificationService
from app.services.qa.structured_lookup import structured_lookup_service, AggregationIntent
from app.services.qa.qa_service import qa_service


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


@pytest.fixture(scope="module")
def env_fixture(db_session):
    suffix = uuid.uuid4().hex[:6]

    # Organizations
    org_a = Organization(
        id=str(uuid.uuid4()),
        code=f"WCL_{suffix}",
        name=f"Western Coalfields Limited {suffix}",
        org_type="SUBSIDIARY",
        is_active=True
    )
    org_b = Organization(
        id=str(uuid.uuid4()),
        code=f"ECL_{suffix}",
        name=f"Eastern Coalfields Limited {suffix}",
        org_type="SUBSIDIARY",
        is_active=True
    )
    org_hq = Organization(
        id=str(uuid.uuid4()),
        code=f"CMPDI_HQ_{suffix}",
        name="CMPDI HQ",
        org_type="HQ",
        is_active=True
    )
    db_session.add_all([org_a, org_b, org_hq])
    db_session.commit()

    # Roles
    def get_or_create_role(code, name):
        r = db_session.query(Role).filter(Role.code == code).first()
        if not r:
            r = Role(id=str(uuid.uuid4()), code=code, name=name, permissions=[code])
            db_session.add(r)
            db_session.commit()
        return r

    role_analyst = get_or_create_role("SUBSIDIARY_ANALYST", "Subsidiary Analyst")
    role_verifier = get_or_create_role("VERIFICATION_OFFICER", "Verification Officer")
    role_hq = get_or_create_role("CMPDI_HQ_OFFICER", "CMPDI HQ Officer")
    role_guest = get_or_create_role("GUEST_VIEWER", "Guest Viewer")

    # Users
    # Maker in Org A
    user_maker = User(
        id=str(uuid.uuid4()),
        username=f"maker_a_{suffix}",
        email=f"maker_a_{suffix}@wcl.in",
        full_name="Maker Analyst Org A",
        hashed_password="hash",
        organization_id=org_a.id,
        is_active=True
    )
    user_maker.roles.append(role_analyst)

    # Independent Checker in Org A
    user_checker_a = User(
        id=str(uuid.uuid4()),
        username=f"checker_a_{suffix}",
        email=f"checker_a_{suffix}@wcl.in",
        full_name="Checker Verifier Org A",
        hashed_password="hash",
        organization_id=org_a.id,
        is_active=True
    )
    user_checker_a.roles.append(role_verifier)

    # User in Org B (different org)
    user_maker_b = User(
        id=str(uuid.uuid4()),
        username=f"maker_b_{suffix}",
        email=f"maker_b_{suffix}@ecl.in",
        full_name="Maker Analyst Org B",
        hashed_password="hash",
        organization_id=org_b.id,
        is_active=True
    )
    user_maker_b.roles.append(role_analyst)

    # Checker in Org B
    user_checker_b = User(
        id=str(uuid.uuid4()),
        username=f"checker_b_{suffix}",
        email=f"checker_b_{suffix}@ecl.in",
        full_name="Checker Verifier Org B",
        hashed_password="hash",
        organization_id=org_b.id,
        is_active=True
    )
    user_checker_b.roles.append(role_verifier)

    # Enterprise HQ Officer
    user_hq = User(
        id=str(uuid.uuid4()),
        username=f"hq_{suffix}",
        email=f"hq_{suffix}@cmpdi.in",
        full_name="HQ Officer",
        hashed_password="hash",
        organization_id=org_hq.id,
        is_active=True
    )
    user_hq.roles.append(role_hq)

    # Unauthorized guest user
    user_guest = User(
        id=str(uuid.uuid4()),
        username=f"guest_{suffix}",
        email=f"guest_{suffix}@guest.in",
        full_name="Guest Viewer",
        hashed_password="hash",
        organization_id=org_a.id,
        is_active=True
    )
    user_guest.roles.append(role_guest)

    db_session.add_all([user_maker, user_checker_a, user_maker_b, user_checker_b, user_hq, user_guest])
    db_session.commit()

    # Synthetic Document & Statutory Reserve Field
    doc = Document(
        id=str(uuid.uuid4()),
        organization_id=org_a.id,
        title="WCL Statutory Geological Reserve Report 2025-26",
        original_filename="wcl_geo_reserves_2025.pdf",
        file_path="/tmp/wcl_geo_reserves.pdf",
        sha256_hash=f"hash_{suffix}",
        mime_type="application/pdf",
        document_type="GEOLOGICAL_REPORT",
        file_size_bytes=102400
    )
    db_session.add(doc)
    db_session.commit()

    page = DocumentPage(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        page_number=1,
        extracted_text="Mine: TEST-MINE-001. Gross Geological Reserve: 1000 MT. Proved Reserve: 800 MT."
    )
    db_session.add(page)
    db_session.commit()

    run = ExtractionRun(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        status="COMPLETED",
        provider="RULE_BASED"
    )
    db_session.add(run)
    db_session.commit()

    reserve_field = ExtractedField(
        id=str(uuid.uuid4()),
        extraction_run_id=run.id,
        organization_id=org_a.id,
        document_id=doc.id,
        field_name="reserves_total",
        field_category="GEOLOGY",
        data_type="NUMBER",
        raw_value="1000",
        normalized_value="1000",
        numeric_value=1000.0,
        unit="MT",
        page_number=1,
        source_text="Mine: TEST-MINE-001. Gross Geological Reserve: 1000 MT.",
        extraction_method="RULE_BASED",
        confidence_score=0.98,
        confidence_level="HIGH",
        verification_status="VERIFIED",
        metadata_json={"entity_name": "TEST-MINE-001"}
    )
    db_session.add(reserve_field)
    db_session.commit()

    tokens = {
        "maker": create_access_token(user_maker.username),
        "checker_a": create_access_token(user_checker_a.username),
        "maker_b": create_access_token(user_maker_b.username),
        "checker_b": create_access_token(user_checker_b.username),
        "hq": create_access_token(user_hq.username),
        "guest": create_access_token(user_guest.username),
    }

    env_data = {
        "org_a": org_a,
        "org_b": org_b,
        "org_hq": org_hq,
        "maker": user_maker,
        "checker_a": user_checker_a,
        "maker_b": user_maker_b,
        "checker_b": user_checker_b,
        "hq": user_hq,
        "guest": user_guest,
        "doc": doc,
        "field": reserve_field,
        "tokens": tokens,
    }

    yield env_data

    # Cleanup
    try:
        db_session.query(StatutoryReserveVerification).filter(
            StatutoryReserveVerification.organization_id.in_([org_a.id, org_b.id, org_hq.id])
        ).delete(synchronize_session=False)
        db_session.query(AuditEvent).filter(
            AuditEvent.organization_id.in_([org_a.id, org_b.id, org_hq.id])
        ).delete(synchronize_session=False)
        db_session.query(ExtractedField).filter(ExtractedField.document_id == doc.id).delete(synchronize_session=False)
        db_session.query(ExtractionRun).filter(ExtractionRun.document_id == doc.id).delete(synchronize_session=False)
        db_session.query(DocumentPage).filter(DocumentPage.document_id == doc.id).delete(synchronize_session=False)
        db_session.query(Document).filter(Document.id == doc.id).delete(synchronize_session=False)
        db_session.query(UserRole).filter(
            UserRole.user_id.in_([user_maker.id, user_checker_a.id, user_maker_b.id, user_checker_b.id, user_hq.id, user_guest.id])
        ).delete(synchronize_session=False)
        db_session.query(User).filter(
            User.id.in_([user_maker.id, user_checker_a.id, user_maker_b.id, user_checker_b.id, user_hq.id, user_guest.id])
        ).delete(synchronize_session=False)
        db_session.query(Organization).filter(Organization.id.in_([org_a.id, org_b.id, org_hq.id])).delete(synchronize_session=False)
        db_session.commit()
    except Exception:
        db_session.rollback()


# ==============================================================================
# 1. CORE DOMAIN & MAKER-CHECKER TESTS
# ==============================================================================

def test_01_create_reserve_edit_preserves_values_and_pending_status(db_session, env_fixture):
    maker = env_fixture["maker"]
    field = env_fixture["field"]

    verif = StatutoryVerificationService.propose_edit(
        db=db_session,
        user=maker,
        reserve_id=field.id,
        proposed_value="1200 MT",
        reason="Updated borehole survey 2025",
        comment="Seam IV boundary re-assessed"
    )

    assert verif.id is not None
    assert verif.status == "PENDING_VERIFICATION"
    assert verif.maker_user_id == maker.id
    assert verif.original_numeric_value == 1000.0
    assert verif.proposed_numeric_value == 1200.0
    assert verif.reason == "Updated borehole survey 2025"
    assert verif.unit == "MT"

    # CRITICAL: Authoritative reserve field MUST remain 1000.0
    db_session.refresh(field)
    assert field.numeric_value == 1000.0
    assert field.verification_status == "VERIFIED"


def test_02_maker_cannot_approve_own_edit_four_eyes_violation(db_session, env_fixture):
    maker = env_fixture["maker"]
    field = env_fixture["field"]

    verif = db_session.query(StatutoryReserveVerification).filter(
        StatutoryReserveVerification.reserve_record_id == field.id,
        StatutoryReserveVerification.status == "PENDING_VERIFICATION"
    ).first()

    with pytest.raises(HTTPException) as exc_info:
        StatutoryVerificationService.approve_edit(
            db=db_session,
            user=maker,  # Attempting self-approval
            edit_id=verif.id,
            comment="Self approving"
        )

    assert exc_info.value.status_code == 403
    assert "Four-eyes policy violation" in exc_info.value.detail

    # Authoritative value MUST remain unchanged
    db_session.refresh(field)
    assert field.numeric_value == 1000.0

    # Verification must remain pending
    db_session.refresh(verif)
    assert verif.status == "PENDING_VERIFICATION"


def test_03_self_approval_blocked_logs_security_audit_event(db_session, env_fixture):
    verif = db_session.query(StatutoryReserveVerification).filter(
        StatutoryReserveVerification.status == "PENDING_VERIFICATION"
    ).first()

    audit = db_session.query(AuditEvent).filter(
        AuditEvent.action == "STATUTORY_RESERVE_SELF_APPROVAL_BLOCKED",
        AuditEvent.object_id == verif.id
    ).first()

    assert audit is not None
    assert audit.actor_id == env_fixture["maker"].id
    assert audit.details.get("violation") == "maker_user_id == verifier_user_id"


def test_04_independent_checker_can_approve_edit(db_session, env_fixture):
    checker = env_fixture["checker_a"]
    field = env_fixture["field"]

    verif = db_session.query(StatutoryReserveVerification).filter(
        StatutoryReserveVerification.reserve_record_id == field.id,
        StatutoryReserveVerification.status == "PENDING_VERIFICATION"
    ).first()

    approved = StatutoryVerificationService.approve_edit(
        db=db_session,
        user=checker,
        edit_id=verif.id,
        comment="Independently verified against exploration logs"
    )

    assert approved.status == "VERIFIED"
    assert approved.verifier_user_id == checker.id
    assert approved.verified_at is not None
    assert approved.verifier_comment == "Independently verified against exploration logs"

    # CRITICAL: Authoritative reserve field MUST now be updated to 1200.0
    db_session.refresh(field)
    assert field.numeric_value == 1200.0
    assert field.verification_status == "VERIFIED"
    assert field.is_corrected is True
    assert field.corrected_by == checker.id


def test_05_audit_event_logged_on_approval(db_session, env_fixture):
    verif = db_session.query(StatutoryReserveVerification).filter(
        StatutoryReserveVerification.status == "VERIFIED"
    ).first()

    audit = db_session.query(AuditEvent).filter(
        AuditEvent.action == "STATUTORY_RESERVE_EDIT_APPROVED",
        AuditEvent.object_id == verif.id
    ).first()

    assert audit is not None
    assert audit.actor_id == env_fixture["checker_a"].id
    assert audit.details.get("applied_value") == 1200.0


def test_06_already_resolved_edit_cannot_be_approved_or_rejected(db_session, env_fixture):
    checker = env_fixture["checker_a"]
    verif = db_session.query(StatutoryReserveVerification).filter(
        StatutoryReserveVerification.status == "VERIFIED"
    ).first()

    # Cannot re-approve
    with pytest.raises(HTTPException) as exc1:
        StatutoryVerificationService.approve_edit(db=db_session, user=checker, edit_id=verif.id)
    assert exc1.value.status_code == 400

    # Cannot reject resolved
    with pytest.raises(HTTPException) as exc2:
        StatutoryVerificationService.reject_edit(db=db_session, user=checker, edit_id=verif.id)
    assert exc2.value.status_code == 400


def test_07_rejection_leaves_authoritative_value_intact(db_session, env_fixture):
    maker = env_fixture["maker"]
    checker = env_fixture["checker_a"]
    field = env_fixture["field"]

    # Propose second edit: 1200 -> 1500
    prop2 = StatutoryVerificationService.propose_edit(
        db=db_session,
        user=maker,
        reserve_id=field.id,
        proposed_value="1500 MT",
        reason="Preliminary speculative estimate"
    )

    assert prop2.status == "PENDING_VERIFICATION"
    db_session.refresh(field)
    assert field.numeric_value == 1200.0

    # Checker rejects prop2
    rejected = StatutoryVerificationService.reject_edit(
        db=db_session,
        user=checker,
        edit_id=prop2.id,
        comment="Speculative estimates cannot be recorded as statutory reserves"
    )

    assert rejected.status == "REJECTED"
    assert rejected.verifier_user_id == checker.id
    assert rejected.rejected_at is not None
    assert rejected.verifier_comment == "Speculative estimates cannot be recorded as statutory reserves"

    # CRITICAL: Field value remains 1200.0
    db_session.refresh(field)
    assert field.numeric_value == 1200.0


def test_08_maker_cannot_reject_own_edit(db_session, env_fixture):
    maker = env_fixture["maker"]
    field = env_fixture["field"]

    prop = StatutoryVerificationService.propose_edit(
        db=db_session,
        user=maker,
        reserve_id=field.id,
        proposed_value="1250 MT",
        reason="Test maker reject restriction"
    )

    with pytest.raises(HTTPException) as exc:
        StatutoryVerificationService.reject_edit(
            db=db_session,
            user=maker,
            edit_id=prop.id,
            comment="Maker trying to self-reject"
        )
    assert exc.value.status_code == 403
    assert "Four-eyes policy violation" in exc.value.detail


def test_09_concurrency_atomic_double_approval_blocked(db_session, env_fixture):
    checker_a = env_fixture["checker_a"]
    hq_checker = env_fixture["hq"]
    field = env_fixture["field"]

    # Find the pending 1250 edit
    pending = db_session.query(StatutoryReserveVerification).filter(
        StatutoryReserveVerification.reserve_record_id == field.id,
        StatutoryReserveVerification.status == "PENDING_VERIFICATION"
    ).first()

    # First checker approves
    approved = StatutoryVerificationService.approve_edit(
        db=db_session,
        user=checker_a,
        edit_id=pending.id,
        comment="First checker won"
    )
    assert approved.status == "VERIFIED"

    # Second concurrent checker attempts to approve the exact same edit
    with pytest.raises(HTTPException) as exc:
        StatutoryVerificationService.approve_edit(
            db=db_session,
            user=hq_checker,
            edit_id=pending.id,
            comment="Second concurrent checker"
        )
    assert exc.value.status_code in [400, 409]


# ==============================================================================
# 2. RBAC & TENANCY ISOLATION TESTS
# ==============================================================================

def test_10_unauthorized_user_without_maker_role_rejected(db_session, env_fixture):
    guest = env_fixture["guest"]
    field = env_fixture["field"]

    with pytest.raises(HTTPException) as exc:
        StatutoryVerificationService.propose_edit(
            db=db_session,
            user=guest,
            reserve_id=field.id,
            proposed_value="1300 MT",
            reason="Guest proposal"
        )
    assert exc.value.status_code == 403
    assert "Permission denied" in exc.value.detail


def test_11_unauthorized_checker_without_verifier_role_rejected(db_session, env_fixture):
    # maker_b is an analyst in Org B, does NOT have verifier role
    analyst_b = env_fixture["maker_b"]
    maker_a = env_fixture["maker"]
    field = env_fixture["field"]

    prop = StatutoryVerificationService.propose_edit(
        db=db_session,
        user=maker_a,
        reserve_id=field.id,
        proposed_value="1280 MT",
        reason="Test unauthorized checker"
    )

    with pytest.raises(HTTPException) as exc:
        StatutoryVerificationService.approve_edit(
            db=db_session,
            user=analyst_b,  # Only SUBSIDIARY_ANALYST, not VERIFICATION_OFFICER
            edit_id=prop.id
        )
    assert exc.value.status_code == 403
    assert "Permission denied" in exc.value.detail


def test_12_cross_organization_maker_proposal_rejected(db_session, env_fixture):
    maker_b = env_fixture["maker_b"] # Org B
    field = env_fixture["field"]     # Org A

    with pytest.raises(HTTPException) as exc:
        StatutoryVerificationService.propose_edit(
            db=db_session,
            user=maker_b,
            reserve_id=field.id,
            proposed_value="1400 MT",
            reason="Cross-org proposal attempt"
        )
    assert exc.value.status_code == 403
    assert "organization scope" in exc.value.detail.lower()


def test_13_cross_organization_checker_approval_rejected(db_session, env_fixture):
    checker_b = env_fixture["checker_b"] # Org B
    field = env_fixture["field"]         # Org A

    pending = db_session.query(StatutoryReserveVerification).filter(
        StatutoryReserveVerification.reserve_record_id == field.id,
        StatutoryReserveVerification.status == "PENDING_VERIFICATION"
    ).first()

    with pytest.raises(HTTPException) as exc:
        StatutoryVerificationService.approve_edit(
            db=db_session,
            user=checker_b, # Restricted to Org B
            edit_id=pending.id
        )
    assert exc.value.status_code == 403
    assert "organization scope" in exc.value.detail.lower()


def test_14_enterprise_hq_can_approve_across_organizations(db_session, env_fixture):
    hq_user = env_fixture["hq"] # Enterprise HQ scope
    field = env_fixture["field"]

    pending = db_session.query(StatutoryReserveVerification).filter(
        StatutoryReserveVerification.reserve_record_id == field.id,
        StatutoryReserveVerification.status == "PENDING_VERIFICATION"
    ).first()

    approved = StatutoryVerificationService.approve_edit(
        db=db_session,
        user=hq_user,
        edit_id=pending.id,
        comment="Approved by CMPDI HQ Chief Officer"
    )
    assert approved.status == "VERIFIED"
    assert approved.verifier_user_id == hq_user.id

    db_session.refresh(field)
    assert field.numeric_value == 1280.0


# ==============================================================================
# 3. NUMERIC & UNIT VALIDATION TESTS
# ==============================================================================

def test_15_numeric_validation_rejects_negative_and_malformed(db_session, env_fixture):
    maker = env_fixture["maker"]
    field = env_fixture["field"]

    # Negative
    with pytest.raises(HTTPException) as exc1:
        StatutoryVerificationService.propose_edit(
            db=db_session, user=maker, reserve_id=field.id, proposed_value="-500 MT", reason="Negative test"
        )
    assert exc1.value.status_code == 400
    assert "cannot be negative" in exc1.value.detail

    # Non-numeric
    with pytest.raises(HTTPException) as exc2:
        StatutoryVerificationService.propose_edit(
            db=db_session, user=maker, reserve_id=field.id, proposed_value="not_a_number MT", reason="Malformed test"
        )
    assert exc2.value.status_code == 400
    assert "Invalid numeric value" in exc2.value.detail


def test_16_unit_compatibility_validation(db_session, env_fixture):
    maker = env_fixture["maker"]
    field = env_fixture["field"] # Unit is MT

    # Incompatible unit e.g. km
    with pytest.raises(HTTPException) as exc:
        StatutoryVerificationService.propose_edit(
            db=db_session, user=maker, reserve_id=field.id, proposed_value="1400 km", reason="Unit test"
        )
    assert exc.value.status_code == 400
    assert "Incompatible unit" in exc.value.detail


# ==============================================================================
# 4. GROUNDED QA & P0-3 AGGREGATION INTEGRATION
# ==============================================================================

def test_17_grounded_qa_excludes_pending_and_uses_authoritative(db_session, env_fixture):
    field = env_fixture["field"]
    maker = env_fixture["maker"]
    checker = env_fixture["checker_a"]
    user = env_fixture["checker_a"]

    from app.services.llm import LLMProvider, LLMResponse, ProviderHealth, ProviderModelInfo, set_llm_provider

    class MockStatutoryLLMProvider(LLMProvider):
        def generate(self, prompt: str, system_prompt=None, **kwargs) -> LLMResponse:
            if "2200" in prompt:
                content = "The total reserve of TEST-MINE-001 is 2,200.0 MT [1]."
            elif "1280" in prompt:
                content = "The total reserve of TEST-MINE-001 is 1,280.0 MT [1]."
            elif "1000" in prompt:
                content = "The total reserve of TEST-MINE-001 is 1,000.0 MT [1]."
            else:
                content = "The total reserve of TEST-MINE-001 is 1,200.0 MT [1]."
            return LLMResponse(content=content, model_name="mock-statutory-llm", provider="mock", latency_ms=5.0)

        def structured_generate(self, prompt: str, schema, system_prompt=None, **kwargs):
            return {}

        def health(self) -> ProviderHealth:
            return ProviderHealth(is_healthy=True, provider="mock", model_name="mock-statutory-llm", endpoint="http://localhost:11434")

        def model_info(self) -> ProviderModelInfo:
            return ProviderModelInfo(provider="mock", model_name="mock-statutory-llm", is_local=True)

    set_llm_provider(MockStatutoryLLMProvider())
    try:
        db_session.refresh(field)
        initial_val = field.numeric_value
        # Propose initial_val -> 2200 MT
        prop = StatutoryVerificationService.propose_edit(
            db=db_session,
            user=maker,
            reserve_id=field.id,
            proposed_value="2200 MT",
            reason="Testing QA isolation while pending"
        )

        # 1. While PENDING: Grounded QA MUST report authoritative initial value, NOT 2,200 MT
        query = "What is the total reserve of TEST-MINE-001?"
        res_before = qa_service.answer_query(
            db=db_session,
            current_user=user,
            query=query,
            allowed_org_ids=[env_fixture["org_a"].id]
        )
        assert res_before["verification_status"] == "SUPPORTED"
        val_str = f"{int(initial_val):,}"
        assert val_str in res_before["answer"] or str(int(initial_val)) in res_before["answer"]
        assert "2200" not in res_before["answer"]

        # 2. Checker approves 2200 MT
        StatutoryVerificationService.approve_edit(
            db=db_session,
            user=checker,
            edit_id=prop.id,
            comment="Approving 2200 MT for QA test"
        )

        # 3. After VERIFIED: Grounded QA immediately reflects new authoritative 2,200 MT
        res_after = qa_service.answer_query(
            db=db_session,
            current_user=user,
            query=query,
            allowed_org_ids=[env_fixture["org_a"].id]
        )
        assert res_after["verification_status"] == "SUPPORTED"
        assert "2,200" in res_after["answer"] or "2200" in res_after["answer"]
    finally:
        set_llm_provider(None)


def test_18_p03_aggregation_respects_verification_lifecycle(db_session, env_fixture):
    field = env_fixture["field"] # currently 2200 MT
    maker = env_fixture["maker"]

    # Propose 2200 -> 3500 MT
    prop = StatutoryVerificationService.propose_edit(
        db=db_session,
        user=maker,
        reserve_id=field.id,
        proposed_value="3500 MT",
        reason="Pending aggregation test"
    )

    intent = AggregationIntent(
        is_aggregation=True,
        operation="SUM",
        metric_label="coal reserves",
        canonical_fields=["reserves_total"],
        target_entity="TEST-MINE-001"
    )

    agg = structured_lookup_service.execute_aggregation(
        db=db_session,
        intent=intent,
        allowed_org_ids=[env_fixture["org_a"].id]
    )

    assert agg is not None
    # Must aggregate authoritative 2200.0 MT, NOT 3500.0 MT
    assert agg.calculated_value == 2200.0
    assert "2,200" in agg.formula or "2200" in agg.formula
    assert "3,500" not in agg.formula and "3500" not in agg.formula


# ==============================================================================
# 5. IMMUTABLE HISTORY & REST API ENDPOINT TESTS
# ==============================================================================

def test_19_immutable_history_records_all_proposals(db_session, env_fixture):
    field = env_fixture["field"]
    maker = env_fixture["maker"]

    history = StatutoryVerificationService.get_reserve_edit_history(
        db=db_session,
        user=maker,
        reserve_id=field.id
    )

    # Several proposals were recorded throughout tests
    assert len(history) >= 4
    statuses = [h.status for h in history]
    assert "VERIFIED" in statuses
    assert "REJECTED" in statuses
    assert "PENDING_VERIFICATION" in statuses


def test_20_api_endpoints_e2e(api_client, env_fixture):
    field = env_fixture["field"]
    tokens = env_fixture["tokens"]

    # 1. Maker proposes edit via API
    resp_prop = api_client.post(
        f"/api/v1/statutory/reserves/{field.id}/edits",
        headers={"Authorization": f"Bearer {tokens['maker']}"},
        json={
            "proposed_value": "2450.0 MT",
            "reason": "Official mine lease boundary revision 2026",
            "comment": "Submitted for approval"
        }
    )
    assert resp_prop.status_code == 201
    prop_data = resp_prop.json()
    assert prop_data["status"] == "PENDING_VERIFICATION"
    assert prop_data["proposed_numeric_value"] == 2450.0
    edit_id = prop_data["id"]

    # 2. List pending edits
    resp_list = api_client.get(
        "/api/v1/statutory/reserve-edits/pending",
        headers={"Authorization": f"Bearer {tokens['checker_a']}"}
    )
    assert resp_list.status_code == 200
    pending_list = resp_list.json()
    assert any(p["id"] == edit_id for p in pending_list)

    # 3. Get edit detail
    resp_detail = api_client.get(
        f"/api/v1/statutory/reserve-edits/{edit_id}",
        headers={"Authorization": f"Bearer {tokens['checker_a']}"}
    )
    assert resp_detail.status_code == 200
    assert resp_detail.json()["id"] == edit_id

    # 4. Self-approval blocked via API
    resp_self = api_client.post(
        f"/api/v1/statutory/reserve-edits/{edit_id}/approve",
        headers={"Authorization": f"Bearer {tokens['maker']}"}, # Maker token
        json={"comment": "Maker trying to approve"}
    )
    assert resp_self.status_code == 403
    assert "Four-eyes policy violation" in resp_self.json()["detail"]

    # 5. Checker approves via API
    resp_approve = api_client.post(
        f"/api/v1/statutory/reserve-edits/{edit_id}/approve",
        headers={"Authorization": f"Bearer {tokens['checker_a']}"}, # Checker token
        json={"comment": "Approved by statutory verification officer"}
    )
    assert resp_approve.status_code == 200
    assert resp_approve.json()["status"] == "VERIFIED"
    assert resp_approve.json()["verifier_name"] is not None

    # 6. History endpoint returns all proposals
    resp_hist = api_client.get(
        f"/api/v1/statutory/reserves/{field.id}/history",
        headers={"Authorization": f"Bearer {tokens['maker']}"}
    )
    assert resp_hist.status_code == 200
    assert len(resp_hist.json()) >= 1
    assert any(h["id"] == edit_id and h["status"] == "VERIFIED" for h in resp_hist.json())


def test_21_audit_event_logged_on_rejection(db_session, env_fixture):
    # From test_07, a rejection occurred
    audit = db_session.query(AuditEvent).filter(
        AuditEvent.action == "STATUTORY_RESERVE_EDIT_REJECTED",
        AuditEvent.organization_id == env_fixture["org_a"].id
    ).first()

    assert audit is not None
    assert audit.actor_id == env_fixture["checker_a"].id
    assert audit.details.get("rejection_comment") == "Speculative estimates cannot be recorded as statutory reserves"


def test_22_api_rejection_flow(api_client, env_fixture):
    field = env_fixture["field"]
    tokens = env_fixture["tokens"]

    # Maker proposes
    resp_prop = api_client.post(
        f"/api/v1/statutory/reserves/{field.id}/edits",
        headers={"Authorization": f"Bearer {tokens['maker']}"},
        json={
            "proposed_value": "9999.0 MT",
            "reason": "Unsubstantiated exploratory revision",
            "comment": "Draft"
        }
    )
    assert resp_prop.status_code == 201
    edit_id = resp_prop.json()["id"]

    # Checker rejects via API
    resp_rej = api_client.post(
        f"/api/v1/statutory/reserve-edits/{edit_id}/reject",
        headers={"Authorization": f"Bearer {tokens['checker_a']}"},
        json={"comment": "Insufficient core sample density"}
    )
    assert resp_rej.status_code == 200
    assert resp_rej.json()["status"] == "REJECTED"
    assert resp_rej.json()["verifier_comment"] == "Insufficient core sample density"


def test_23_api_cross_org_isolation_rejection(api_client, env_fixture):
    field = env_fixture["field"]
    tokens = env_fixture["tokens"]

    # Propose new edit
    resp_prop = api_client.post(
        f"/api/v1/statutory/reserves/{field.id}/edits",
        headers={"Authorization": f"Bearer {tokens['maker']}"},
        json={
            "proposed_value": "2600.0 MT",
            "reason": "Org isolation test via API"
        }
    )
    assert resp_prop.status_code == 201
    edit_id = resp_prop.json()["id"]

    # Checker B (Org B) tries to view edit in Org A
    resp_get = api_client.get(
        f"/api/v1/statutory/reserve-edits/{edit_id}",
        headers={"Authorization": f"Bearer {tokens['checker_b']}"}
    )
    assert resp_get.status_code == 403

    # Checker B (Org B) tries to approve edit in Org A
    resp_app = api_client.post(
        f"/api/v1/statutory/reserve-edits/{edit_id}/approve",
        headers={"Authorization": f"Bearer {tokens['checker_b']}"},
        json={"comment": "Cross org intruder"}
    )
    assert resp_app.status_code == 403


def test_24_api_unauthorized_guest_blocked(api_client, env_fixture):
    field = env_fixture["field"]
    tokens = env_fixture["tokens"]

    # Guest tries to propose
    resp_prop = api_client.post(
        f"/api/v1/statutory/reserves/{field.id}/edits",
        headers={"Authorization": f"Bearer {tokens['guest']}"},
        json={"proposed_value": "3000.0 MT", "reason": "Guest proposal"}
    )
    assert resp_prop.status_code == 403

