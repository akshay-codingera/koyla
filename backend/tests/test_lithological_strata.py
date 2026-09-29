"""
Phase 11 P1-1: Normalized Lithological Strata Sequence Model - Test Suite

Tests:
    1.  Model creation & attribute persistence
    2.  Organization isolation & tenancy
    3.  Valid depth interval validation
    4.  Invalid negative depth validation (ValueError)
    5.  Invalid depth_to < depth_from validation (ValueError)
    6.  Deterministic thickness calculation when omitted
    7.  Thickness discrepancy detection (stated vs calculated)
    8.  Strata sequence ordering & continuity validation
    9.  Lithology canonical normalization
    10. Unknown lithology preservation
    11. Hindi / Devanagari bilingual lithology normalization
    12. Exact provenance preservation (document, page, table, row, text)
    13. Extraction from text / OCR fixture
    14. Extraction from structured table fixture
    15. API retrieval: ordered strata sequence
    16. API summary: analytical metrics (depth, coal thickness, seams)
    17. API cross-organization access rejection (RBAC enforcement)
    18. Grounded QA query integration with citations
"""
import os
import sys
import uuid
import pytest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.database import SessionLocal
from app.core.security import create_access_token
from app.models.organization import Organization
from app.models.user import User, Role
from app.models.document import Document, DocumentPage, Table, TableRow
from app.models.geology import BoreholeStratum

from app.services.geology.normalizer import (
    normalize_lithology,
    extract_seam_and_lithology,
    LITHOLOGY_CANONICAL_MAP,
)
from app.services.geology.validator import (
    validate_stratum_metrics,
    validate_strata_sequence,
)
from app.services.geology.extractor import (
    extract_strata_from_text_lines,
    extract_strata_from_table,
    extract_borehole_id_from_text,
)
from app.services.geology.strata_service import strata_service
from app.services.qa.structured_lookup import structured_lookup_service
from app.services.qa.qa_service import qa_service

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def strata_fixture(db: Session):
    """
    Sets up isolated test organizations, users, and geological document.
    """
    # Pre-cleanup
    existing_orgs = db.query(Organization).filter(
        Organization.code.in_(["CMPDI_GEOL_TEST", "ECL_GEOL_TEST", "BCCL_GEOL_TEST"])
    ).all()
    for o in existing_orgs:
        db.query(BoreholeStratum).filter(BoreholeStratum.organization_id == o.id).delete(synchronize_session=False)
        db.query(TableRow).filter(
            TableRow.table_id.in_(db.query(Table.id).join(Document).filter(Document.organization_id == o.id))
        ).delete(synchronize_session=False)
        db.query(Table).filter(
            Table.document_id.in_(db.query(Document.id).filter(Document.organization_id == o.id))
        ).delete(synchronize_session=False)
        db.query(DocumentPage).filter(
            DocumentPage.document_id.in_(db.query(Document.id).filter(Document.organization_id == o.id))
        ).delete(synchronize_session=False)
        db.query(Document).filter(Document.organization_id == o.id).delete(synchronize_session=False)
        
        user_ids = [u[0] for u in db.query(User.id).filter(User.organization_id == o.id).all()]
        if user_ids:
            from app.models.user import UserRole
            db.query(UserRole).filter(UserRole.user_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.delete(o)
    db.commit()

    # 1. Create Orgs
    org_cmpdi = Organization(
        id=str(uuid.uuid4()),
        code="CMPDI_GEOL_TEST",
        name="CMPDI Geological Exploration Division",
        org_type="CENTRAL",
        is_active=True,
    )
    org_ecl = Organization(
        id=str(uuid.uuid4()),
        code="ECL_GEOL_TEST",
        name="Eastern Coalfields Limited Geological Wing",
        org_type="SUBSIDIARY",
        is_active=True,
    )
    org_bccl = Organization(
        id=str(uuid.uuid4()),
        code="BCCL_GEOL_TEST",
        name="Bharat Coking Coal Limited Exploration Wing",
        org_type="SUBSIDIARY",
        is_active=True,
    )
    db.add_all([org_cmpdi, org_ecl, org_bccl])
    db.commit()

    # 2. Roles
    r_hq = db.query(Role).filter(Role.code == "CMPDI_HQ_OFFICER").first()
    r_sub = db.query(Role).filter(Role.code == "SUBSIDIARY_ANALYST").first()

    # 3. Create Users
    user_hq = User(
        id=str(uuid.uuid4()),
        username="hq_geologist_test",
        email="hq_geol@cmpdi.co.in",
        full_name="HQ Exploration Officer",
        hashed_password="hashed_pw_dummy",
        organization_id=org_cmpdi.id,
        is_active=True,
    )
    if r_hq:
        user_hq.roles.append(r_hq)

    user_ecl = User(
        id=str(uuid.uuid4()),
        username="ecl_geologist_test",
        email="geol@ecl.gov.in",
        full_name="ECL Subsidiary Geologist",
        hashed_password="hashed_pw_dummy",
        organization_id=org_ecl.id,
        is_active=True,
    )
    if r_sub:
        user_ecl.roles.append(r_sub)

    user_bccl = User(
        id=str(uuid.uuid4()),
        username="bccl_geologist_test",
        email="geol@bccl.gov.in",
        full_name="BCCL Subsidiary Geologist",
        hashed_password="hashed_pw_dummy",
        organization_id=org_bccl.id,
        is_active=True,
    )
    if r_sub:
        user_bccl.roles.append(r_sub)

    db.add_all([user_hq, user_ecl, user_bccl])
    db.commit()

    # 4. Create Documents
    doc_ecl = Document(
        id=str(uuid.uuid4()),
        title="Raniganj Basin Borehole BH-01 Exploration Report",
        original_filename="BH-01_Raniganj_Geological_Report.pdf",
        document_type="GEOLOGICAL_REPORT",
        file_path="/app/data/documents/test_ecl_bh01.pdf",
        mime_type="application/pdf",
        file_size_bytes=1048576,
        organization_id=org_ecl.id,
        created_by=user_ecl.id,
        source_tier="TIER_A",
        status="COMPLETED",
        sha256_hash="test_sha256_ecl_geol_001",
    )
    doc_bccl = Document(
        id=str(uuid.uuid4()),
        title="Jharia Basin Borehole BH-BCCL-99 Exploration Report",
        original_filename="BH-BCCL-99_Jharia_Log.pdf",
        document_type="GEOLOGICAL_REPORT",
        file_path="/app/data/documents/test_bccl_bh99.pdf",
        mime_type="application/pdf",
        file_size_bytes=1048576,
        organization_id=org_bccl.id,
        created_by=user_bccl.id,
        source_tier="TIER_A",
        status="COMPLETED",
        sha256_hash="test_sha256_bccl_geol_001",
    )
    db.add_all([doc_ecl, doc_bccl])
    db.commit()

    yield {
        "org_cmpdi": org_cmpdi,
        "org_ecl": org_ecl,
        "org_bccl": org_bccl,
        "user_hq": user_hq,
        "user_ecl": user_ecl,
        "user_bccl": user_bccl,
        "doc_ecl": doc_ecl,
        "doc_bccl": doc_bccl,
    }

    # Teardown
    db.query(BoreholeStratum).filter(
        BoreholeStratum.organization_id.in_([org_cmpdi.id, org_ecl.id, org_bccl.id])
    ).delete(synchronize_session=False)
    db.query(TableRow).filter(
        TableRow.table_id.in_(
            db.query(Table.id).join(Document).filter(
                Document.organization_id.in_([org_cmpdi.id, org_ecl.id, org_bccl.id])
            )
        )
    ).delete(synchronize_session=False)
    db.query(Table).filter(
        Table.document_id.in_(
            db.query(Document.id).filter(
                Document.organization_id.in_([org_cmpdi.id, org_ecl.id, org_bccl.id])
            )
        )
    ).delete(synchronize_session=False)
    db.query(DocumentPage).filter(
        DocumentPage.document_id.in_(
            db.query(Document.id).filter(
                Document.organization_id.in_([org_cmpdi.id, org_ecl.id, org_bccl.id])
            )
        )
    ).delete(synchronize_session=False)
    db.query(Document).filter(
        Document.organization_id.in_([org_cmpdi.id, org_ecl.id, org_bccl.id])
    ).delete(synchronize_session=False)
    user_ids = [user_hq.id, user_ecl.id, user_bccl.id]
    from app.models.user import UserRole
    db.query(UserRole).filter(UserRole.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.query(Organization).filter(
        Organization.id.in_([org_cmpdi.id, org_ecl.id, org_bccl.id])
    ).delete(synchronize_session=False)
    db.commit()


# -------------------------------------------------------------------------
# Test Cases
# -------------------------------------------------------------------------

def test_1_stratum_model_instantiation(db: Session, strata_fixture):
    """Scenario 1: Instantiating and persisting a BoreholeStratum model."""
    doc = strata_fixture["doc_ecl"]
    org = strata_fixture["org_ecl"]

    stratum = BoreholeStratum(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc.id,
        borehole_id="BH-01",
        stratum_order=1,
        depth_from_m=0.0,
        depth_to_m=4.5,
        thickness_m=4.5,
        stated_thickness_m=4.5,
        lithology_type="Top Soil",
        raw_lithology="Alluvial Soil and Weathered Mantle",
        page_number=1,
        source_text="0.0 - 4.5m Alluvial Soil and Weathered Mantle",
        has_thickness_discrepancy=False,
    )
    db.add(stratum)
    db.commit()
    db.refresh(stratum)

    assert stratum.id is not None
    assert stratum.borehole_id == "BH-01"
    assert stratum.depth_from_m == 0.0
    assert stratum.depth_to_m == 4.5
    assert stratum.thickness_m == 4.5
    assert stratum.lithology_type == "Top Soil"


def test_2_organization_isolation(db: Session, strata_fixture):
    """Scenario 2: Organization isolation ensures strata queries are scoped."""
    org_ecl = strata_fixture["org_ecl"]
    org_bccl = strata_fixture["org_bccl"]
    doc_bccl = strata_fixture["doc_bccl"]

    # Add BCCL stratum
    bccl_stratum = BoreholeStratum(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        document_id=doc_bccl.id,
        borehole_id="BH-BCCL-99",
        stratum_order=1,
        depth_from_m=0.0,
        depth_to_m=6.0,
        thickness_m=6.0,
        lithology_type="Sandstone",
    )
    db.add(bccl_stratum)
    db.commit()

    # Query scoped to ECL
    ecl_strata = strata_service.get_strata_by_borehole(
        db, "BH-BCCL-99", allowed_org_ids=[org_ecl.id]
    )
    assert len(ecl_strata) == 0

    # Query scoped to BCCL
    bccl_strata = strata_service.get_strata_by_borehole(
        db, "BH-BCCL-99", allowed_org_ids=[org_bccl.id]
    )
    assert len(bccl_strata) == 1
    assert bccl_strata[0].borehole_id == "BH-BCCL-99"


def test_3_valid_depth_interval():
    """Scenario 3: Valid depths calculate thickness correctly."""
    metrics = validate_stratum_metrics(0.0, 5.5, stated_thickness_m=5.5)
    assert metrics["depth_from_m"] == 0.0
    assert metrics["depth_to_m"] == 5.5
    assert metrics["thickness_m"] == 5.5
    assert metrics["has_thickness_discrepancy"] is False


def test_4_invalid_negative_depth():
    """Scenario 4: Negative depths raise ValueError."""
    with pytest.raises(ValueError, match="cannot be negative"):
        validate_stratum_metrics(-2.5, 10.0)


def test_5_invalid_depth_order():
    """Scenario 5: depth_to < depth_from raises ValueError."""
    with pytest.raises(ValueError, match="must be greater than or equal to"):
        validate_stratum_metrics(20.0, 15.0)


def test_6_thickness_calculation_omitted():
    """Scenario 6: When stated thickness is omitted, calculated interval thickness is used."""
    metrics = validate_stratum_metrics(12.35, 17.85, stated_thickness_m=None)
    assert metrics["thickness_m"] == 5.5
    assert metrics["stated_thickness_m"] is None
    assert metrics["has_thickness_discrepancy"] is False


def test_7_thickness_discrepancy_detection():
    """Scenario 7: Observable discrepancy between stated and calculated thickness is flagged."""
    # Stated 4.0m, but interval 10.0 to 15.5 is 5.5m (difference 1.5m > 0.05m tolerance)
    metrics = validate_stratum_metrics(10.0, 15.5, stated_thickness_m=4.0)
    assert metrics["thickness_m"] == 5.5
    assert metrics["stated_thickness_m"] == 4.0
    assert metrics["has_thickness_discrepancy"] is True
    assert metrics["discrepancy_details"]["difference_m"] == 1.5
    assert "Discrepancy detected" in metrics["discrepancy_details"]["reason"]


def test_8_strata_sequence_ordering_and_continuity():
    """Scenario 8: Sequence continuity validator flags gaps and overlaps."""
    continuous_sequence = [
        {"stratum_order": 1, "depth_from_m": 0.0, "depth_to_m": 5.0, "lithology_type": "Soil"},
        {"stratum_order": 2, "depth_from_m": 5.0, "depth_to_m": 12.0, "lithology_type": "Sandstone"},
        {"stratum_order": 3, "depth_from_m": 12.0, "depth_to_m": 16.5, "lithology_type": "Coal"},
    ]
    res_valid = validate_strata_sequence(continuous_sequence)
    assert res_valid["is_valid"] is True
    assert len(res_valid["issues"]) == 0

    gap_sequence = [
        {"stratum_order": 1, "depth_from_m": 0.0, "depth_to_m": 5.0, "lithology_type": "Soil"},
        # Gap between 5.0 and 8.0m
        {"stratum_order": 2, "depth_from_m": 8.0, "depth_to_m": 15.0, "lithology_type": "Sandstone"},
    ]
    res_gap = validate_strata_sequence(gap_sequence)
    assert res_gap["is_valid"] is False
    assert any("Depth gap detected" in iss["message"] for iss in res_gap["issues"])


def test_9_lithology_normalization_canonical_terms():
    """Scenario 9: Canonical normalization of standard mining terminology."""
    assert normalize_lithology("fine-grained sandstone") == "Sandstone"
    assert normalize_lithology("Carbonaceous Shale with Coal Streaks") == "Shale"
    assert normalize_lithology("Bright Banded Coal") == "Coal"
    assert normalize_lithology("Siltstone and Mudstone") == "Siltstone"
    assert normalize_lithology("Weathered Alluvial Clay") == "Clay"

    seam, lith = extract_seam_and_lithology("Coal (Seam III Bottom)")
    assert seam == "Seam III Bottom"
    assert lith == "Coal"


def test_10_unknown_lithology_preservation():
    """Scenario 10: Unknown lithology strings preserve verbatim text."""
    unknown_lith = "Kimberlitic Breccia with Xenoliths"
    norm = normalize_lithology(unknown_lith)
    assert norm == unknown_lith


def test_11_hindi_devanagari_lithology_normalization():
    """Scenario 11: Bilingual Hindi Devanagari lithology normalization."""
    assert normalize_lithology("कोयला (Coal)") == "Coal"
    assert normalize_lithology("बलुआ पत्थर") == "Sandstone"
    assert normalize_lithology("शेल") == "Shale"
    assert normalize_lithology("मिट्टी") == "Top Soil"
    assert normalize_lithology("गाद पत्थर") == "Siltstone"

    seam_hi, lith_hi = extract_seam_and_lithology("कोयला (सीम II)")
    assert seam_hi == "सीम II"
    assert lith_hi == "कोयला"


def test_12_provenance_preservation(db: Session, strata_fixture):
    """Scenario 12: Provenance fields accurately preserve source references."""
    doc = strata_fixture["doc_ecl"]
    org = strata_fixture["org_ecl"]

    stratum = BoreholeStratum(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc.id,
        borehole_id="BH-01",
        stratum_order=2,
        depth_from_m=4.5,
        depth_to_m=12.0,
        thickness_m=7.5,
        lithology_type="Sandstone",
        page_number=3,
        source_text="Page 3, Row 4: 4.5m - 12.0m Coarse Feldspathic Sandstone",
        extraction_method="TABLE_PARSER",
    )
    db.add(stratum)
    db.commit()
    db.refresh(stratum)

    assert stratum.document_id == doc.id
    assert stratum.page_number == 3
    assert stratum.extraction_method == "TABLE_PARSER"
    assert "Feldspathic Sandstone" in stratum.source_text


def test_13_extraction_from_text_fixture():
    """Scenario 13: Extracting borehole strata from OCR / text fixture."""
    text_content = """
    CENTRAL MINE PLANNING & DESIGN INSTITUTE LIMITED
    Raniganj Coalfield Exploration - Borehole BH-TEST-001
    
    Lithological Sequence Log:
    1. 0.00 - 3.50m (3.50m) Top Soil and Alluvium
    2. 3.50 - 14.80m (11.30m) Grey Medium-Grained Sandstone
    3. 14.80 - 18.20m (3.40m) Coal Seam I
    4. 18.20 - 24.50m (6.30m) Carbonaceous Shale
    5. 24.50 - 31.00m (6.50m) Coal (Seam II)
    """

    bh_id = extract_borehole_id_from_text(text_content)
    assert bh_id == "BH-TEST-001"

    candidates = extract_strata_from_text_lines(
        text_content, default_borehole_id=bh_id, page_number=1, document_id="doc-test-123"
    )
    assert len(candidates) >= 5
    assert candidates[0]["lithology_type"] == "Top Soil"
    assert candidates[1]["lithology_type"] == "Sandstone"
    assert candidates[2]["lithology_type"] == "Coal"
    assert candidates[2]["seam_name"] == "Seam I"
    assert candidates[4]["lithology_type"] == "Coal"
    assert candidates[4]["seam_name"] == "Seam II"


def test_14_extraction_from_table_fixture(db: Session, strata_fixture):
    """Scenario 14: Extracting strata sequence from structured Table & TableRow entities."""
    doc = strata_fixture["doc_ecl"]

    mock_table = Table(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        page_number=2,
        table_index=1,
        caption="Borehole BH-01 Lithological Sequence",
        headers=["Strata No", "Depth From (m)", "Depth To (m)", "Thickness (m)", "Lithology", "Seam Name"],
        row_count=2,
    )
    db.add(mock_table)
    db.flush()

    row1 = TableRow(
        id=str(uuid.uuid4()),
        table_id=mock_table.id,
        row_index=0,
        cells=[
            {"text": "1", "col": 0},
            {"text": "12.0", "col": 1},
            {"text": "18.5", "col": 2},
            {"text": "6.5", "col": 3},
            {"text": "Grey Sandstone", "col": 4},
            {"text": "-", "col": 5},
        ]
    )
    row2 = TableRow(
        id=str(uuid.uuid4()),
        table_id=mock_table.id,
        row_index=1,
        cells=[
            {"text": "2", "col": 0},
            {"text": "18.5", "col": 1},
            {"text": "23.5", "col": 2},
            {"text": "5.0", "col": 3},
            {"text": "Coal", "col": 4},
            {"text": "Seam III", "col": 5},
        ]
    )
    db.add_all([row1, row2])
    db.commit()

    candidates = extract_strata_from_table(mock_table, [row1, row2], doc.id, default_borehole_id="BH-01")
    assert len(candidates) == 2
    assert candidates[0]["lithology_type"] == "Sandstone"
    assert candidates[0]["depth_from_m"] == 12.0
    assert candidates[0]["depth_to_m"] == 18.5
    assert candidates[1]["lithology_type"] == "Coal"
    assert candidates[1]["seam_name"] == "Seam III"


def test_15_api_get_borehole_strata_ordered(db: Session, strata_fixture):
    """Scenario 15: API returns ordered strata sequence for authorized user."""
    doc = strata_fixture["doc_ecl"]
    org = strata_fixture["org_ecl"]
    user = strata_fixture["user_ecl"]

    # Seed 3 sequential strata for BH-01
    db.query(BoreholeStratum).filter(BoreholeStratum.borehole_id == "BH-01").delete(synchronize_session=False)
    s1 = BoreholeStratum(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc.id,
        borehole_id="BH-01",
        stratum_order=1,
        depth_from_m=0.0,
        depth_to_m=4.5,
        thickness_m=4.5,
        lithology_type="Top Soil",
    )
    s2 = BoreholeStratum(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc.id,
        borehole_id="BH-01",
        stratum_order=2,
        depth_from_m=4.5,
        depth_to_m=15.0,
        thickness_m=10.5,
        lithology_type="Sandstone",
    )
    s3 = BoreholeStratum(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        document_id=doc.id,
        borehole_id="BH-01",
        stratum_order=3,
        depth_from_m=15.0,
        depth_to_m=20.5,
        thickness_m=5.5,
        lithology_type="Coal",
        seam_name="Seam I",
    )
    db.add_all([s1, s2, s3])
    db.commit()

    token = create_access_token(user.username)
    res = client.get(
        "/api/v1/geology/boreholes/BH-01/strata",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    assert data[0]["stratum_order"] == 1
    assert data[0]["lithology_type"] == "Top Soil"
    assert data[1]["stratum_order"] == 2
    assert data[1]["lithology_type"] == "Sandstone"
    assert data[2]["stratum_order"] == 3
    assert data[2]["lithology_type"] == "Coal"
    assert data[2]["seam_name"] == "Seam I"


def test_16_api_get_borehole_summary(db: Session, strata_fixture):
    """Scenario 16: API computes analytical summary for borehole."""
    user = strata_fixture["user_ecl"]
    token = create_access_token(user.username)

    res = client.get(
        "/api/v1/geology/boreholes/BH-01/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    summary = res.json()
    assert summary["borehole_id"] == "BH-01"
    assert summary["total_depth_m"] == 20.5
    assert summary["total_coal_thickness_m"] == 5.5
    assert summary["coal_strata_count"] == 1
    assert "Seam I" in summary["seams"]
    assert "Sandstone" in summary["lithology_breakdown"]


def test_17_cross_organization_access_rejection(db: Session, strata_fixture):
    """Scenario 17: User in BCCL cannot access ECL borehole records."""
    user_bccl = strata_fixture["user_bccl"]
    token = create_access_token(user_bccl.username)

    # 1. Scoped query returns empty list for BCCL user accessing ECL borehole
    res_strata = client.get(
        "/api/v1/geology/boreholes/BH-01/strata",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_strata.status_code == 200
    assert len(res_strata.json()) == 0

    # 2. Summary returns 404 for unauthorized borehole
    res_summary = client.get(
        "/api/v1/geology/boreholes/BH-01/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_summary.status_code == 404

    # 3. Direct stratum lookup returns 403 Forbidden
    ecl_stratum = db.query(BoreholeStratum).filter(BoreholeStratum.borehole_id == "BH-01").first()
    res_single = client.get(
        f"/api/v1/geology/strata/{ecl_stratum.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_single.status_code == 403


def test_18_qa_grounded_strata_query(db: Session, strata_fixture):
    """Scenario 18: Grounded QA structured lookup detects borehole strata and cites facts."""
    org = strata_fixture["org_ecl"]
    user = strata_fixture["user_ecl"]

    query = "What are the lithological layers and coal thickness in borehole BH-01?"
    lookup_res = structured_lookup_service.lookup(
        db=db,
        query=query,
        allowed_org_ids=[org.id],
    )

    assert len(lookup_res.facts) >= 3
    # Check that borehole strata facts are present
    bh_facts = [f for f in lookup_res.facts if "BH-01" in (f.entity_name or "")]
    assert len(bh_facts) >= 3

    # Check total coal fact was computed
    coal_fact = next((f for f in lookup_res.facts if f.metric_name == "total_coal_thickness"), None)
    assert coal_fact is not None
    assert coal_fact.numeric_value == 5.5

    # Run QA service query
    qa_res = qa_service.answer_query(
        db=db,
        current_user=user,
        query=query,
        allowed_org_ids=[org.id]
    )

    assert any(
        "BH-01" in (c["excerpt"] if isinstance(c, dict) else c.excerpt) or
        "Coal" in (c["excerpt"] if isinstance(c, dict) else c.excerpt)
        for c in qa_res["citations"]
    )
