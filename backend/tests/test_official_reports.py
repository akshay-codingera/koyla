"""
Unit and Integration Tests for Phase 7: Official Prescribed Report Formats & Report Studio
Tests statutory schema integrity, deterministic analytics, reserve deduction hierarchy,
mandatory 2025 Just Transition 25% escrow rule, conditional plates, QP review,
compliance validation, native DOCX generation, and audit trail logging.
"""
import os
import pytest
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, engine, Base
from app.models.organization import Organization
from app.models.user import User, Role, UserRole
from app.models.report import (
    ReportFormat,
    Report,
    ReportFieldMapping,
    ReportTable,
    ReportPlate,
    ReportAnnexure,
    ReportCertification,
    ReportComplianceIssue,
    ReportVersion,
)
from app.models.audit import AuditEvent
from app.services.reports.format_registry import FormatRegistry
from app.services.reports.schema_audit import audit_schema
from app.services.reports.analytics import ReportAnalyticsEngine
from app.services.reports.report_generator import ReportGeneratorService
from app.services.reports.compliance import ReportComplianceValidator
from app.services.reports.review_service import ReportReviewService
from app.services.reports.docx_renderer import ReportDocxRenderer
from app.services.reports.narrative import OFFICIAL_UNAVAILABLE_NOTICE


@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def test_org(db: Session):
    org = db.query(Organization).filter(Organization.code == "ECL_TEST_RPT").first()
    if not org:
        org = Organization(name="Eastern Coalfields Limited Test", code="ECL_TEST_RPT", org_type="SUBSIDIARY")
        db.add(org)
        db.commit()
        db.refresh(org)
    return org


@pytest.fixture(scope="module")
def test_user(db: Session, test_org: Organization):
    user = db.query(User).filter(User.username == "qp_officer_test").first()
    if not user:
        user = User(
            username="qp_officer_test",
            email="qp@ecl.test.in",
            full_name="Shri R. K. Sharma (QP)",
            hashed_password="hashed_test_pass",
            organization_id=test_org.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def test_01_schema_audit_integrity_and_inventory_counts():
    """Verify Appendix-I machine-readable schema integrity and automated inventory counts."""
    report = audit_schema()
    assert report["status"] == "PASS", f"Schema audit failed: {report.get('errors')}"
    assert report["total_nodes"] == 244
    assert report["total_actionable_requirements"] == 217

    counts = report["counts"]
    assert counts["front_matter_requirements"] == 14
    assert counts["checklist_requirements"] == 12
    assert counts["total_chapter_parameters"] == 156
    assert counts["chapter_fields_parameters"] == 133
    assert counts["prescribed_tables"] == 23
    assert counts["plans_plates_drawings"] == 23
    assert counts["annexure_supporting_documents"] == 8
    assert counts["certification_signature_requirements"] == 4
    assert counts["mandatory_items"] == 154
    assert counts["conditional_items"] == 62
    assert counts["items_requiring_human_input"] == 54
    assert counts["items_requiring_external_attachments"] == 31
    assert len(report["errors"]) == 0


def test_02_official_format_registration_and_source_record(db: Session):
    """Verify format seeded in DB with full Authoritative Source Record."""
    fmt = FormatRegistry.seed_default_statutory_format(db)
    assert fmt is not None
    assert fmt.report_type == "MINING_PLAN_AND_CLOSURE_PLAN_2025"
    assert "Coal Controller Organisation" in fmt.issuing_authority
    assert fmt.om_number == "F.No. CPAM-34011/28/2019-CPAM [E-343762]"
    assert fmt.om_date == "2025-01-31"
    assert fmt.guideline_year == 2025
    assert fmt.effective_status == "ACTIVE_STATUTORY"
    assert fmt.format_tier == "STATUTORY"
    assert fmt.source_document_hash is not None


def test_03_no_invented_official_ids(db: Session):
    """Ensure no synthetic official IDs (like CP.1 or IDX.1) exist in the schema."""
    fmt = FormatRegistry.get_format(db, "MINING_PLAN_AND_CLOSURE_PLAN_2025")
    nodes = fmt.schema_json.get("nodes", [])

    for n in nodes:
        ntype = n.get("node_type")
        oid = n.get("official_id")
        if ntype in ("FRONT_MATTER", "CERTIFICATION"):
            assert oid is None, f"Node '{n.get('internal_id')}' must not have an invented official_id (found '{oid}')"
        elif ntype == "CHECKLIST" and n.get("parent_id") is not None:
            assert oid is None, f"Checklist item '{n.get('internal_id')}' must not have invented official_id"


def test_04_deterministic_reserve_deduction_lineage():
    """Verify 7-step reserve deduction hierarchy and mathematical lineage."""
    lineage = ReportAnalyticsEngine.calculate_reserves_lineage(
        proved_mt=200.0,
        indicated_mt=50.0,
        inferred_mt=10.0,
        geological_deduction_pct=10.0,
        blocked_reserves_mt=25.0,
        mining_loss_pct=5.0,
        prior_depleted_mt=10.0,
    )

    outputs = lineage["outputs"]
    assert outputs["gross_geological_mt"] == 260.0 # 200 + 50 + 10
    assert outputs["geological_deduction_mt"] == 26.0 # 10% of 260
    assert outputs["net_geological_mt"] == 234.0 # 260 - 26
    assert outputs["blocked_reserves_mt"] == 25.0
    assert outputs["minable_mt"] == 209.0 # 234 - 25
    assert outputs["mining_loss_mt"] == 10.45 # 5% of 209
    assert outputs["extractable_mt"] == 198.55 # 209 - 10.45
    assert outputs["balance_mt"] == 188.55 # 198.55 - 10
    assert len(lineage["steps"]) == 7


def test_05_stripping_ratio_and_lom_calculations():
    """Verify stripping ratio and Life of Mine deterministic formulas."""
    sr_res = ReportAnalyticsEngine.calculate_stripping_ratio_lineage(
        ob_volume_mcum=180.0,
        coal_tonnage_mt=45.0,
    )
    assert sr_res["result"] == 4.0 # 180 / 45
    assert sr_res["unit"] == "cum/tonne"

    lom_res = ReportAnalyticsEngine.calculate_lom_lineage(
        extractable_mt=150.0,
        rated_capacity_mtpa=6.0,
    )
    assert lom_res["result"] == 25.0 # 150 / 6
    assert lom_res["unit"] == "Years"


def test_06_statutory_closure_and_transformation_rules():
    """
    Verify statutory separation of:
    - Base Mine Closure Escrow per Section 3.5.1
    - Rule A: Community Development & Livelihood Projects (5-yearly escrow head per Section 3.5.5(ii)).
    - Rule B: Just Transformation Corpus (final closure head per Section 3.5.5(iv)).
    """
    # 1. Base closure escrow calculation
    escrow = ReportAnalyticsEngine.calculate_mine_closure_escrow_lineage(
        project_area_ha=1000.0,
        is_opencast=True,
        base_rate_lakh_ha=9.0,
        wpi_factor=1.35,
        mine_life_years=25,
    )
    assert escrow["escalated_rate_lakh_ha"] == 12.15
    assert escrow["total_closure_cost_lakh"] == 12150.0
    assert escrow["annual_escrow_deposit_lakh"] == 486.0
    assert escrow["annual_compounded_deposit_lakh"] == 510.3

    # 2. Rule A: Community Development 25% minimum five-yearly deposit
    five_yearly_deposit = 486.0 * 5.0 # 2430.0 Lakh INR
    rule_a_res = ReportAnalyticsEngine.calculate_community_development_escrow(
        five_yearly_escrow_deposit_lakh=five_yearly_deposit,
        activity_claims_lakh={"vocational_training": 200.0, "healthcare_infra": 200.0, "drinking_water": 200.0}
    )
    assert rule_a_res["min_earmarked_lakh"] == 607.5 # 25% of 2430.0
    assert rule_a_res["min_earmarked_pct"] == 25.0
    assert rule_a_res["single_activity_cap_lakh"] == 202.5 # 1/3 of 607.5
    assert rule_a_res["has_cap_violations"] is False

    # 3. Rule B: Just Transformation Corpus 10% of balance deposited amount
    rule_b_res = ReportAnalyticsEngine.calculate_just_transformation_corpus(
        final_closure_balance_deposited_lakh=1215.0, # e.g. balance at final closure
    )
    assert rule_b_res["just_transformation_corpus_lakh"] == 121.5 # 10% of 1215.0
    assert rule_b_res["reimbursable_90_pct_balance_lakh"] == 1093.5 # 90%
    assert rule_b_res["just_transformation_corpus_pct"] == 10.0


def test_07_report_generation_end_to_end(db: Session, test_org: Organization, test_user: User):
    """Verify end-to-end report generation with full statutory components."""
    report = ReportGeneratorService.generate_report(
        db=db,
        format_id="MINING_PLAN_AND_CLOSURE_PLAN_2025",
        organization_id=test_org.id,
        mine_name="Amritnagar Colliery Test",
        block_name="Raniganj Deep Coal Block",
        base_date="2026-03",
        user_id=test_user.id,
    )

    assert report.id is not None
    assert report.status in ("DRAFT", "DATA_INCOMPLETE", "REVIEW_REQUIRED", "FORMAT_COMPLIANT")
    assert report.version_number == 1

    # Verify field mappings count
    mappings = db.query(ReportFieldMapping).filter(ReportFieldMapping.report_id == report.id).all()
    assert len(mappings) >= 140 # 133 chapter fields + 14 front matter

    # Verify prescribed tables count
    tables = db.query(ReportTable).filter(ReportTable.report_id == report.id).all()
    assert len(tables) == 23 # Exactly 23 prescribed tables

    # Verify technical plates count and conditionality
    plates = db.query(ReportPlate).filter(ReportPlate.report_id == report.id).all()
    assert len(plates) == 23 # Exactly 23 technical plates Plate I to Plate XXIII
    plt_oc = next((p for p in plates if p.plate_id == "Plate XIII"), None)
    plt_ug = next((p for p in plates if p.plate_id == "Plate XV"), None)
    assert plt_oc is not None and plt_oc.required_for_oc is True and plt_oc.required_for_ug is False
    assert plt_ug is not None and plt_ug.required_for_ug is True and plt_ug.required_for_oc is False
    assert all(p.attachment_status == "SOURCE_REQUIRED" for p in plates)
    assert all(p.display_notice == "NOT GENERATED — SOURCE DATA REQUIRED" for p in plates)

    # Verify statutory annexures count
    annexures = db.query(ReportAnnexure).filter(ReportAnnexure.report_id == report.id).all()
    assert len(annexures) == 8 # Exactly 8 prescribed statutory annexures

    # Verify certifications count
    certs = db.query(ReportCertification).filter(ReportCertification.report_id == report.id).all()
    assert len(certs) == 4 # Exactly 4 statutory execution instruments
    assert all(c.audit_state == "SYSTEM_GENERATED" for c in certs)


def test_08_compliance_validation_and_readiness_states(db: Session, test_org: Organization, test_user: User):
    """Verify deterministic compliance validator and issue generation."""
    report = (
        db.query(Report)
        .filter(Report.organization_id == test_org.id)
        .order_by(Report.created_at.desc())
        .first()
    )
    assert report is not None

    res = ReportComplianceValidator.validate_report(db, report)
    assert "compliance_status" in res
    assert "readiness_state" in res
    assert res["total_issues"] > 0 # Expect warnings for pending QP review & source plates
    assert report.status == res["readiness_state"]


def test_09_human_qp_review_and_value_preservation(db: Session, test_org: Organization, test_user: User):
    """Verify QP review, value correction, and original value preservation."""
    report = (
        db.query(Report)
        .filter(Report.organization_id == test_org.id)
        .order_by(Report.created_at.desc())
        .first()
    )
    mapping = db.query(ReportFieldMapping).filter(ReportFieldMapping.report_id == report.id).first()
    original_val = mapping.generated_value

    corrected_val = "Corrected by Qualified Person R. K. Sharma"
    updated_mapping = ReportReviewService.review_field(
        db=db,
        report_id=report.id,
        mapping_id=mapping.id,
        action="CORRECTED",
        corrected_value=corrected_val,
        notes="Verified from original borehole logs",
        user_id=test_user.id,
    )

    assert updated_mapping.reviewer_action == "CORRECTED"
    assert updated_mapping.generated_value == corrected_val
    assert updated_mapping.original_generated_value == original_val
    assert updated_mapping.reviewed_by == test_user.id


def test_10_statutory_certification_signing(db: Session, test_org: Organization, test_user: User):
    """Verify execution certification signing transitions state to AUTHORIZED_SIGNED."""
    report = (
        db.query(Report)
        .filter(Report.organization_id == test_org.id)
        .order_by(Report.created_at.desc())
        .first()
    )
    cert = db.query(ReportCertification).filter(ReportCertification.report_id == report.id).first()

    signed_cert = ReportReviewService.sign_certification(
        db=db,
        report_id=report.id,
        certification_id=cert.id,
        signatory_name="Shri R. K. Sharma",
        signatory_designation="Qualified Person (Rule 22C MCR 1960)",
        reg_number="QP/CMPDI/2021/042",
        user_id=test_user.id,
    )

    assert signed_cert.audit_state == "AUTHORIZED_SIGNED"
    assert signed_cert.signatory_name == "Shri R. K. Sharma"
    assert signed_cert.signed_at is not None


def test_11_native_docx_physical_generation_and_hash(db: Session, test_org: Organization):
    """Verify real physical DOCX generation with python-docx, layout, and SHA-256 hash."""
    report = (
        db.query(Report)
        .filter(Report.organization_id == test_org.id)
        .order_by(Report.created_at.desc())
        .first()
    )

    file_path, file_size, sha256_hash = ReportDocxRenderer.render_report_docx(report)
    assert os.path.exists(file_path), f"DOCX file was not generated at: {file_path}"
    assert file_size > 5000, f"DOCX file suspiciously small: {file_size} bytes"
    assert len(sha256_hash) == 64

    # Verify DOCX structure can be reopened
    from docx import Document
    reopened = Document(file_path)
    assert len(reopened.paragraphs) > 50
    assert len(reopened.tables) >= 25 # Cover table, TOC, Checklist, 23 Prescribed tables, Plates, Annexures, Certifications


def test_12_immutable_version_freezing(db: Session, test_org: Organization, test_user: User):
    """Verify version freezing creates immutable snapshot and increments version number."""
    report = (
        db.query(Report)
        .filter(Report.organization_id == test_org.id)
        .order_by(Report.created_at.desc())
        .first()
    )
    initial_vnum = report.version_number

    version = ReportReviewService.freeze_version(
        db=db,
        report_id=report.id,
        docx_file_path=report.docx_file_path or "test.docx",
        sha256_hash=report.sha256_hash or "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        change_summary="Frozen official statutory draft for audit review",
        user_id=test_user.id,
    )

    assert version.version_number == initial_vnum
    assert version.snapshot_json is not None
    assert len(version.snapshot_json["fields"]) > 0
    assert report.version_number == initial_vnum + 1


def test_13_audit_trail_logging(db: Session, test_org: Organization):
    """Verify immutable AuditEvent entries are created for all report actions."""
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.organization_id == test_org.id)
        .filter(AuditEvent.object_type.in_(["REPORT", "REPORT_FIELD_MAPPING", "REPORT_CERTIFICATION", "REPORT_VERSION"]))
        .all()
    )
    assert len(events) >= 3
    actions = [e.action for e in events]
    assert any("REPORT_GENERATE" in a for a in actions)
    assert any("REPORT_FIELD" in a for a in actions)
    assert any("REPORT_CERTIFICATION" in a for a in actions)
