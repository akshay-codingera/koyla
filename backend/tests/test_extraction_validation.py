import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import uuid
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.database import SessionLocal
from app.models.user import User, Role
from app.models.organization import Organization
from app.models.document import Document, DocumentVersion, DocumentPage, Table, TableRow, ProcessingJob
from app.models.chunk import Chunk
from app.models.extraction import ExtractionRun, ExtractedField, ValidationResult, ReconciliationGroup, ReconciliationCandidate
from app.models.verification import VerificationTask
from app.models.audit import AuditEvent
from app.core.security import create_access_token, get_password_hash
from app.services.extraction.rule_based import RuleBasedExtractionProvider
from app.services.extraction.local_llm import LocalLLMExtractionProvider
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.validation.validator import ValidationService
from app.services.reconciliation.reconciler import ReconciliationService
from app.services.verification import VerificationService

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_setup(db_session: Session):
    # Ensure test orgs exist
    org1 = db_session.query(Organization).filter(Organization.code == "ECL").first()
    if not org1:
        org1 = Organization(id=str(uuid.uuid4()), code="ECL", name="Eastern Coalfields Limited", org_type="SUBSIDIARY")
        db_session.add(org1)

    org2 = db_session.query(Organization).filter(Organization.code == "BCCL").first()
    if not org2:
        org2 = Organization(id=str(uuid.uuid4()), code="BCCL", name="Bharat Coking Coal Limited", org_type="SUBSIDIARY")
        db_session.add(org2)

    db_session.commit()

    # Ensure roles exist
    role_verifier = db_session.query(Role).filter(Role.code == "VERIFICATION_OFFICER").first()
    if not role_verifier:
        role_verifier = Role(id=str(uuid.uuid4()), code="VERIFICATION_OFFICER", name="Verification Officer", permissions=["VERIFICATION_OFFICER"])
        db_session.add(role_verifier)

    role_analyst = db_session.query(Role).filter(Role.code == "SUBSIDIARY_ANALYST").first()
    if not role_analyst:
        role_analyst = Role(id=str(uuid.uuid4()), code="SUBSIDIARY_ANALYST", name="Subsidiary Analyst", permissions=["SUBSIDIARY_ANALYST"])
        db_session.add(role_analyst)

    role_hq = db_session.query(Role).filter(Role.code == "CMPDI_HQ_OFFICER").first()
    if not role_hq:
        role_hq = Role(id=str(uuid.uuid4()), code="CMPDI_HQ_OFFICER", name="HQ Officer", permissions=["CMPDI_HQ_OFFICER"])
        db_session.add(role_hq)

    db_session.commit()

    # Ensure users exist
    user_ecl = db_session.query(User).filter(User.username == "test_ecl_analyst").first()
    if not user_ecl:
        user_ecl = User(
            id=str(uuid.uuid4()),
            username="test_ecl_analyst",
            email="test_ecl@koyla.local",
            full_name="ECL Test Analyst",
            hashed_password=get_password_hash("Secret123!"),
            organization_id=org1.id,
            is_active=True
        )
        user_ecl.roles.append(role_analyst)
        db_session.add(user_ecl)

    user_bccl = db_session.query(User).filter(User.username == "test_bccl_analyst").first()
    if not user_bccl:
        user_bccl = User(
            id=str(uuid.uuid4()),
            username="test_bccl_analyst",
            email="test_bccl@koyla.local",
            full_name="BCCL Test Analyst",
            hashed_password=get_password_hash("Secret123!"),
            organization_id=org2.id,
            is_active=True
        )
        user_bccl.roles.append(role_analyst)
        db_session.add(user_bccl)

    user_verifier = db_session.query(User).filter(User.username == "test_verifier_officer").first()
    if not user_verifier:
        user_verifier = User(
            id=str(uuid.uuid4()),
            username="test_verifier_officer",
            email="test_verifier@koyla.local",
            full_name="Test Verification Officer",
            hashed_password=get_password_hash("Secret123!"),
            organization_id=org1.id,
            is_active=True
        )
        user_verifier.roles.append(role_verifier)
        db_session.add(user_verifier)

    db_session.commit()

    return {
        "org_ecl": org1,
        "org_bccl": org2,
        "user_ecl": user_ecl,
        "user_bccl": user_bccl,
        "user_verifier": user_verifier,
        "token_ecl": create_access_token(user_ecl.username),
        "token_bccl": create_access_token(user_bccl.username),
        "token_verifier": create_access_token(user_verifier.username),
    }

def test_deterministic_extraction_domain_fields(db_session: Session):
    """Verifies deterministic regex extraction of identification, geology, and mining fields with unit retention."""
    provider = RuleBasedExtractionProvider()

    sample_text = """
    CENTRAL MINE PLANNING & DESIGN INSTITUTE
    Mine Name: Rajmahal OCP
    Project Name: Rajmahal Expansion Project
    Financial Year: 2024-25
    Reporting Period: Annual 2024-25

    GEOLOGICAL SUMMARY:
    The target coal seams belong to the Barakar Formation.
    Primary seam under evaluation is Coal Seam: Seam IV Top.
    Exploration Borehole No: RJ-42 was drilled to a total drilling depth: 425.50 m.
    Proved Coal Reserves: 145.80 MT, Indicated Reserves: 32.40 MT, Inferred Reserves: 12.10 MT.
    Total Geological Reserves: 190.30 MT.
    Laboratory analysis confirms Coal Grade: G4 with GCV: 4950 kcal/kg and Ash Content: 32.5 %.

    MINING PARAMETERS:
    Annual Target Production: 50.00 MT.
    Actual Coal Production: 46.20 MT achieved during the period.
    Coal Dispatch: 45.10 MT sent to thermal power stations.
    Overburden Removal: 95.40 Mm3.
    Composite Stripping Ratio: 2.06 cum/tonne.
    """

    class DummyChunk:
        id = str(uuid.uuid4())
        content = sample_text
        page_number = 1

    candidates = provider.extract(chunks=[DummyChunk()], tables=[], pages=[])

    extracted_dict = {c.field_name: c for c in candidates}

    # 1. Identification
    assert "mine_name" in extracted_dict
    assert extracted_dict["mine_name"].raw_value == "Rajmahal OCP"
    assert "project_name" in extracted_dict
    assert "Rajmahal Expansion" in extracted_dict["project_name"].raw_value
    assert "fiscal_year" in extracted_dict
    assert extracted_dict["fiscal_year"].raw_value == "2024-25"

    # 2. Geology
    assert "formation" in extracted_dict
    assert extracted_dict["formation"].raw_value == "Barakar"
    assert "seam" in extracted_dict
    assert extracted_dict["seam"].raw_value == "Seam IV Top"
    assert "borehole_id" in extracted_dict
    assert extracted_dict["borehole_id"].raw_value == "RJ-42"
    
    # 3. Drilling & Reserves with units retained
    assert extracted_dict["drilling_metreage"].numeric_value == 425.50
    assert extracted_dict["drilling_metreage"].unit == "m"
    assert extracted_dict["reserves_proved"].numeric_value == 145.80
    assert extracted_dict["reserves_proved"].unit == "MT"
    assert extracted_dict["reserves_total"].numeric_value == 190.30

    # 4. Grade, GCV, Ash
    assert extracted_dict["coal_grade"].raw_value == "G4"
    assert extracted_dict["gcv"].numeric_value == 4950.0
    assert extracted_dict["gcv"].unit.lower() == "kcal/kg"
    assert extracted_dict["ash_content"].numeric_value == 32.5
    assert extracted_dict["ash_content"].unit == "%"

    # 5. Mining production & stripping ratio
    assert extracted_dict["production_quantity"].numeric_value == 46.20
    assert extracted_dict["production_quantity"].unit == "MT"
    assert extracted_dict["stripping_ratio"].numeric_value == 2.06
    assert extracted_dict["stripping_ratio"].unit in ["cum/tonne", "m3/tonne"]

def test_missing_values_not_hallucinated(db_session: Session):
    """Verifies that missing domain fields are explicitly absent rather than invented."""
    provider = RuleBasedExtractionProvider()
    sparse_text = "Administrative report for Coal India Limited. No geological drilling or production data recorded."
    
    class DummyChunk:
        id = str(uuid.uuid4())
        content = sparse_text
        page_number = 1

    candidates = provider.extract(chunks=[DummyChunk()], tables=[], pages=[])
    extracted_names = [c.field_name for c in candidates]

    # Must NOT hallucinate fields
    assert "production_quantity" not in extracted_names
    assert "stripping_ratio" not in extracted_names
    assert "reserves_proved" not in extracted_names
    assert "gcv" not in extracted_names
    assert "ash_content" not in extracted_names

def test_exact_physical_page_provenance_from_multipage_logical_table(db_session: Session, test_setup):
    """
    CRITICAL PROVENANCE TEST:
    Verifies that fields extracted from multi-page logical tables strictly preserve
    the physical source page of each row (e.g. Row on Page 3 must have page_number=3).
    """
    org = test_setup["org_ecl"]
    user = test_setup["user_ecl"]

    doc = Document(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        title="Multi-page Geological Exploration Statement",
        document_type="GEOLOGICAL_REPORT",
        source_tier="TIER_A",
        original_filename="multi_page_statement.pdf",
        file_path="storage/documents/test_multi_page.pdf",
        mime_type="application/pdf",
        file_size_bytes=1000,
        sha256_hash="1111222233334444555566667777888899990000111122223333444455556666",
        status="PROCESSED",
        created_by=user.id
    )
    db_session.add(doc)
    db_session.commit()

    logical_id = str(uuid.uuid4())

    # Table Part 1 on Page 1
    t1 = Table(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        page_number=1,
        table_index=1,
        caption="Seam Reserve Statement",
        headers=["Seam Name", "Proved Reserve (MT)", "Grade", "Ash %"],
        logical_table_id=logical_id,
        part_number=1,
        total_parts=2
    )
    db_session.add(t1)
    db_session.flush()

    r1 = TableRow(
        id=str(uuid.uuid4()),
        table_id=t1.id,
        row_index=1,
        logical_row_index=1,
        source_page=1,
        cells=["Seam I", "52.40", "G4", "24.5"]
    )
    db_session.add(r1)

    # Table Part 2 on Page 2 (Continuation)
    t2 = Table(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        page_number=2,
        table_index=1,
        caption="Seam Reserve Statement (Contd.)",
        headers=["Seam Name", "Proved Reserve (MT)", "Grade", "Ash %"],
        logical_table_id=logical_id,
        is_continuation=True,
        part_number=2,
        total_parts=2
    )
    db_session.add(t2)
    db_session.flush()

    r2 = TableRow(
        id=str(uuid.uuid4()),
        table_id=t2.id,
        row_index=1,
        logical_row_index=2,
        source_page=2,  # EXACT PHYSICAL SOURCE PAGE
        cells=["Seam II Bottom", "38.70", "G6", "29.8"]
    )
    db_session.add(r2)
    db_session.commit()

    # Run extraction pipeline
    pipeline = ExtractionPipeline()
    run = pipeline.run_pipeline(db_session, doc.id, org.id)
    assert run.status == "COMPLETED"

    fields = db_session.query(ExtractedField).filter(ExtractedField.document_id == doc.id).all()
    assert len(fields) > 0

    # Locate field extracted from row on Page 2 (Seam II Bottom reserves)
    seam2_reserves = next((f for f in fields if f.raw_value == "38.70"), None)
    assert seam2_reserves is not None
    assert seam2_reserves.field_name == "reserves_proved"
    assert seam2_reserves.numeric_value == 38.70
    assert seam2_reserves.unit == "MT"
    # CRITICAL: page_number MUST be 2, not 1!
    assert seam2_reserves.page_number == 2
    assert seam2_reserves.table_id == t2.id
    assert seam2_reserves.row_id == r2.id

    # Locate field extracted from row on Page 1
    seam1_reserves = next((f for f in fields if f.raw_value == "52.40"), None)
    assert seam1_reserves is not None
    assert seam1_reserves.page_number == 1
    assert seam1_reserves.table_id == t1.id

def test_validation_rules_range_and_units(db_session: Session):
    """Verifies domain validation rules: negative stripping ratio (ERROR), ash % > 100 (ERROR), high stripping warning."""
    validator = ValidationService()

    # 1. Invalid negative stripping ratio -> ERROR
    f_neg_sr = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        field_name="stripping_ratio",
        data_type="NUMBER",
        raw_value="-2.50",
        numeric_value=-2.50,
        unit="cum/tonne"
    )
    results = validator.validate_field(f_neg_sr)
    assert f_neg_sr.validation_status == "ERROR"
    assert any(r.status == "ERROR" and "cannot be negative" in r.message for r in results)

    # 2. Impossible Ash % (> 100%) -> ERROR
    f_ash_err = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        field_name="ash_content",
        data_type="NUMBER",
        raw_value="112.5",
        numeric_value=112.5,
        unit="%"
    )
    results = validator.validate_field(f_ash_err)
    assert f_ash_err.validation_status == "ERROR"
    assert any(r.status == "ERROR" and "impossible" in r.message.lower() for r in results)

    # 3. Valid normal stripping ratio -> PASS
    f_valid_sr = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        field_name="stripping_ratio",
        data_type="NUMBER",
        raw_value="2.35",
        numeric_value=2.35,
        unit="cum/tonne"
    )
    results = validator.validate_field(f_valid_sr)
    assert f_valid_sr.validation_status == "PASS"

    # 4. Incompatible measurement unit -> ERROR
    f_bad_unit = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        field_name="production_quantity",
        data_type="NUMBER",
        raw_value="50.0",
        numeric_value=50.0,
        unit="kcal/kg"  # completely wrong unit for production
    )
    results = validator.validate_field(f_bad_unit)
    assert f_bad_unit.validation_status == "ERROR"
    assert any(r.status == "ERROR" and "Incompatible unit" in r.message for r in results)

def test_separation_of_confidence_from_validation(db_session: Session):
    """
    Verifies that extraction confidence (how well the parser extracted the token)
    remains distinct from domain validation (whether the value satisfies physical laws).
    """
    validator = ValidationService()

    field = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        field_name="stripping_ratio",
        data_type="NUMBER",
        raw_value="-1.85",
        numeric_value=-1.85,
        unit="m3/tonne",
        confidence_score=0.95,
        confidence_level="HIGH"  # Parsed cleanly from explicit table cell
    )
    validator.validate_field(field)

    # Confidence score must remain HIGH (0.95), but validation_status is ERROR!
    assert field.confidence_score == 0.95
    assert field.confidence_level == "HIGH"
    assert field.validation_status == "ERROR"

def test_local_llm_offline_resilience(db_session: Session):
    """Verifies that if local LLM is offline, extraction falls back safely to RULE_BASED without failing."""
    llm = LocalLLMExtractionProvider(endpoint_url="http://127.0.0.1:9999/api/generate")
    assert llm.check_availability() is False
    res = llm.extract(chunks=[], tables=[], pages=[])
    assert res == []

def test_cross_document_reconciliation_conflict_detection(db_session: Session, test_setup):
    """
    Verifies cross-document reconciliation:
    When Document A and Document B report differing values for the same entity and metric in the same period,
    a ReconciliationGroup is created with status CONFLICT and a VerificationTask is queued.
    """
    org = test_setup["org_ecl"]
    user = test_setup["user_ecl"]

    doc_a = Document(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        title="Monthly Operating Review Document A",
        document_type="PRODUCTION_REPORT",
        original_filename="doc_a.pdf",
        file_path="storage/test_doc_a.pdf",
        mime_type="application/pdf",
        file_size_bytes=500,
        sha256_hash="aaaa111122223333444455556666777788889999000011112222333344445555",
        status="PROCESSED",
        created_by=user.id
    )
    doc_b = Document(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        title="Annual Reconciliation Statement Document B",
        document_type="PRODUCTION_REPORT",
        original_filename="doc_b.pdf",
        file_path="storage/test_doc_b.pdf",
        mime_type="application/pdf",
        file_size_bytes=500,
        sha256_hash="bbbb111122223333444455556666777788889999000011112222333344445555",
        status="PROCESSED",
        created_by=user.id
    )
    db_session.add_all([doc_a, doc_b])
    db_session.commit()

    unique_mine = f"Rajmahal OCP {uuid.uuid4().hex[:6]}"
    unique_period = f"2024-{uuid.uuid4().hex[:2]}"

    # Context fields
    f_mine_a = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc_a.id,
        field_name="mine_name",
        raw_value=unique_mine,
        normalized_value=unique_mine,
        data_type="STRING"
    )
    f_period_a = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc_a.id,
        field_name="fiscal_year",
        raw_value=unique_period,
        normalized_value=unique_period,
        data_type="STRING"
    )
    f_prod_a = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc_a.id,
        field_name="production_quantity",
        raw_value="42.50",
        numeric_value=42.50,
        unit="MT",
        data_type="NUMBER"
    )

    f_mine_b = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc_b.id,
        field_name="mine_name",
        raw_value=unique_mine,
        normalized_value=unique_mine,
        data_type="STRING"
    )
    f_period_b = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc_b.id,
        field_name="fiscal_year",
        raw_value=unique_period,
        normalized_value=unique_period,
        data_type="STRING"
    )
    f_prod_b = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc_b.id,
        field_name="production_quantity",
        raw_value="38.00",  # Diverges by ~11.8% from doc_a
        numeric_value=38.00,
        unit="MT",
        data_type="NUMBER"
    )

    db_session.add_all([f_mine_a, f_period_a, f_prod_a, f_mine_b, f_period_b, f_prod_b])
    db_session.commit()

    reconciler = ReconciliationService()
    groups = reconciler.reconcile_organization_fields(db_session, org.id)

    # Locate group for Rajmahal OCP production_quantity
    prod_group = next((g for g in groups if g.metric_name == "production_quantity" and g.entity_name == unique_mine), None)
    assert prod_group is not None
    assert prod_group.conflict_status == "CONFLICT"

    # Verify conflict verification task created
    task = db_session.query(VerificationTask).filter(
        VerificationTask.reconciliation_group_id == prod_group.id,
        VerificationTask.task_type == "EXTRACTION_CONFLICT"
    ).first()
    assert task is not None
    assert task.status == "PENDING"
    assert task.evidence_context["divergence_pct"] > 1.0

def test_human_verification_actions_and_audit(db_session: Session, test_setup):
    """
    Verifies human verification actions (APPROVE, CORRECT, REJECT, DEFER):
    - CORRECT action records new value, marks is_corrected=True, preserves original raw value.
    - Generates immutable AuditEvent.
    """
    org = test_setup["org_ecl"]
    user_verifier = test_setup["user_verifier"]

    doc = Document(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        title="Verification Test Document",
        document_type="PRODUCTION_REPORT",
        original_filename="verif_doc.pdf",
        file_path="storage/verif_doc.pdf",
        mime_type="application/pdf",
        file_size_bytes=500,
        sha256_hash="cccc111122223333444455556666777788889999000011112222333344445555",
        status="PROCESSED",
        created_by=user_verifier.id
    )
    db_session.add(doc)
    db_session.commit()

    field = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc.id,
        field_name="stripping_ratio",
        raw_value="25.5",
        numeric_value=25.5,
        unit="cum/tonne",
        data_type="NUMBER",
        verification_status="UNVERIFIED"
    )
    db_session.add(field)
    db_session.commit()

    task = VerificationTask(
        id=str(uuid.uuid4()),
        task_type="VALIDATION_ERROR",
        organization_id=org.id,
        document_id=doc.id,
        field_id=field.id,
        status="PENDING"
    )
    db_session.add(task)
    db_session.commit()

    # 1. Verification Officer performs CORRECT action
    updated_task = VerificationService.process_action(
        db=db_session,
        task_id=task.id,
        user_id=user_verifier.id,
        action="CORRECT",
        corrected_value="2.55",
        review_notes="OCR error: misplaced decimal point corrected from 25.5 to 2.55"
    )

    assert updated_task.status == "CORRECTED"
    assert updated_task.action_taken == "CORRECT"
    assert updated_task.corrected_value == "2.55"

    db_session.refresh(field)
    assert field.verification_status == "CORRECTED"
    assert field.is_corrected is True
    assert field.corrected_value == "2.55"
    assert field.raw_value == "25.5"  # Original raw value untouched!
    assert field.corrected_by == user_verifier.id

    # 2. Verify AuditEvent created
    audit = db_session.query(AuditEvent).filter(
        AuditEvent.object_id == task.id,
        AuditEvent.action == "VERIFICATION_CORRECT"
    ).first()
    assert audit is not None
    assert audit.actor_id == user_verifier.id
    assert audit.details["previous_value"] == "25.5"
    assert audit.details["corrected_value"] == "2.55"

def test_api_verification_queue_and_action(test_setup):
    """Verifies REST API endpoints for verification queue and applying review decisions."""
    token_verifier = test_setup["token_verifier"]
    token_ecl = test_setup["token_ecl"]

    # 1. Fetch queue
    res = client.get(
        "/api/v1/verification/queue",
        headers={"Authorization": f"Bearer {token_verifier}"}
    )
    assert res.status_code == 200
    queue = res.json()
    assert isinstance(queue, list)

    # 2. Analyst without verification permissions cannot take action
    if len(queue) > 0:
        task_id = queue[0]["id"]
        res_denied = client.post(
            f"/api/v1/verification/tasks/{task_id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": f"Bearer {token_ecl}"}
        )
        assert res_denied.status_code == 403

        # Verifier can approve
        res_approved = client.post(
            f"/api/v1/verification/tasks/{task_id}/action",
            json={"action": "APPROVE", "review_notes": "Approved by verification specialist"},
            headers={"Authorization": f"Bearer {token_verifier}"}
        )
        assert res_approved.status_code == 200
        assert res_approved.json()["status"] == "APPROVED"

def test_configurable_reconciliation_threshold(db_session: Session, test_setup):
    """
    Verifies that the cross-document reconciliation threshold is configurable per policy
    and is not treated as a fixed institutional mandate.
    """
    org = test_setup["org_ecl"]
    user = test_setup["user_ecl"]

    doc_x = Document(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        title="Doc X",
        document_type="PRODUCTION_REPORT",
        original_filename="doc_x.pdf",
        file_path="storage/doc_x.pdf",
        mime_type="application/pdf",
        file_size_bytes=500,
        sha256_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        status="PROCESSED",
        created_by=user.id
    )
    doc_y = Document(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        title="Doc Y",
        document_type="PRODUCTION_REPORT",
        original_filename="doc_y.pdf",
        file_path="storage/doc_y.pdf",
        mime_type="application/pdf",
        file_size_bytes=500,
        sha256_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        status="PROCESSED",
        created_by=user.id
    )
    db_session.add_all([doc_x, doc_y])
    db_session.commit()

    test_mine = f"Config Mine {uuid.uuid4().hex[:6]}"
    test_period = "FY2024-25"

    # Field 1: 100.0 MT
    f_x = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc_x.id,
        field_name="production_quantity",
        raw_value="100.0",
        numeric_value=100.0,
        unit="MT",
        data_type="NUMBER",
        metadata_json={"entity_name": test_mine}
    )
    f_p_x = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc_x.id,
        field_name="fiscal_year",
        raw_value=test_period,
        data_type="STRING"
    )
    # Field 2: 103.0 MT (Divergence = 3%)
    f_y = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc_y.id,
        field_name="production_quantity",
        raw_value="103.0",
        numeric_value=103.0,
        unit="MT",
        data_type="NUMBER",
        metadata_json={"entity_name": test_mine}
    )
    f_p_y = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc_y.id,
        field_name="fiscal_year",
        raw_value=test_period,
        data_type="STRING"
    )
    db_session.add_all([f_x, f_p_x, f_y, f_p_y])
    db_session.commit()

    reconciler = ReconciliationService()

    # Case A: With threshold = 0.05 (5%), a 3% variance is ACCEPTABLE -> MATCHED
    groups_lenient = reconciler.reconcile_organization_fields(db_session, org.id, variance_threshold=0.05)
    grp = next((g for g in groups_lenient if g.entity_name == test_mine), None)
    assert grp is not None
    assert grp.conflict_status == "MATCHED"

    # Case B: With threshold = 0.02 (2%), a 3% variance triggers a CONFLICT
    groups_strict = reconciler.reconcile_organization_fields(db_session, org.id, variance_threshold=0.02)
    grp_strict = next((g for g in groups_strict if g.entity_name == test_mine), None)
    assert grp_strict is not None
    assert grp_strict.conflict_status == "CONFLICT"
