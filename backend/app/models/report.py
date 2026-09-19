"""
Report Models for Statutory Government Formats
Encapsulates prescribed official templates, report instances, field mappings with provenance,
tables, conditional plates, statutory annexures, certifications, and compliance issues.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, ForeignKey, DateTime, BigInteger, Text, Float, JSON
)
from sqlalchemy.orm import relationship
from app.models.base import UUIDMixin
from app.db.database import Base


class ReportFormat(UUIDMixin, Base):
    """Registered Authoritative Government Report Format."""
    __tablename__ = "report_formats"

    report_type = Column(String(100), nullable=False, unique=True, index=True)
    issuing_authority = Column(String(255), nullable=False)
    document_title = Column(String(500), nullable=False)
    om_number = Column(String(100), nullable=False)
    om_date = Column(String(50), nullable=False)
    guideline_year = Column(Integer, nullable=False)
    effective_status = Column(String(50), nullable=False, default="ACTIVE_STATUTORY")
    official_source_url = Column(String(500), nullable=True)
    source_document_hash = Column(String(64), nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    superseded_by = Column(String(36), ForeignKey("report_formats.id"), nullable=True)
    format_tier = Column(String(50), nullable=False, default="STATUTORY")
    schema_json = Column(JSON, nullable=False)


class Report(UUIDMixin, Base):
    """Main Report Submission Instance."""
    __tablename__ = "reports"

    format_id = Column(String(36), ForeignKey("report_formats.id"), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    mine_name = Column(String(255), nullable=False)
    block_name = Column(String(255), nullable=False)
    report_title = Column(String(500), nullable=False)
    base_date = Column(String(50), nullable=False) # e.g. "2026-03"
    
    # Readiness state machine
    status = Column(String(50), nullable=False, default="DRAFT", index=True)
    # Allowed statuses:
    # DRAFT, DATA_INCOMPLETE, REVIEW_REQUIRED, FORMAT_COMPLIANT,
    # VERIFIED, READY_FOR_AUTHORIZED_REVIEW, READY_FOR_AUTHORIZED_SUBMISSION

    compliance_status = Column(String(50), nullable=False, default="PARTIALLY_COMPLIANT")
    # Allowed: COMPLIANT, PARTIALLY_COMPLIANT, NON_COMPLIANT

    docx_file_path = Column(String(500), nullable=True)
    docx_file_size_bytes = Column(BigInteger, nullable=True)
    sha256_hash = Column(String(64), nullable=True)
    version_number = Column(Integer, default=1, nullable=False)
    
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    field_mappings = relationship("ReportFieldMapping", backref="report", cascade="all, delete-orphan")
    tables = relationship("ReportTable", backref="report", cascade="all, delete-orphan")
    annexures = relationship("ReportAnnexure", backref="report", cascade="all, delete-orphan")
    plates = relationship("ReportPlate", backref="report", cascade="all, delete-orphan")
    certifications = relationship("ReportCertification", backref="report", cascade="all, delete-orphan")
    compliance_issues = relationship("ReportComplianceIssue", backref="report", cascade="all, delete-orphan")
    versions = relationship("ReportVersion", backref="report", cascade="all, delete-orphan")


class ReportFieldMapping(UUIDMixin, Base):
    """Exact field mapping with provenance, calculations, and QP review."""
    __tablename__ = "report_field_mappings"

    report_id = Column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    internal_id = Column(String(100), nullable=False, index=True)
    official_id = Column(String(50), nullable=True) # e.g. "1.1.1", None for front matter
    exact_official_label = Column(String(500), nullable=False)
    chapter = Column(String(100), nullable=True)
    section = Column(String(100), nullable=True)
    
    # Availability status
    field_status = Column(String(50), nullable=False, default="AVAILABLE_FROM_KOYLADB")
    # Allowed: AVAILABLE_FROM_KOYLADB, DERIVABLE_FROM_KOYLADB, EXTRACTABLE_FROM_SOURCE,
    # REQUIRES_HUMAN_INPUT, REQUIRES_EXTERNAL_ATTACHMENT, NOT_YET_SUPPORTED, NOT_APPLICABLE

    generated_value = Column(Text, nullable=True)
    normalized_value = Column(Text, nullable=True)
    numeric_value = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)

    # Provenance
    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    source_chunk_id = Column(String(36), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True)
    source_page = Column(Integer, nullable=True)
    extracted_field_id = Column(String(36), ForeignKey("extracted_fields.id", ondelete="SET NULL"), nullable=True)
    confidence = Column(Float, default=1.0)
    
    # Deterministic Lineage & Grounding
    calculation_lineage = Column(JSON, nullable=True)
    grounding_evidence = Column(JSON, nullable=True)

    # Human / QP Review Action
    reviewer_action = Column(String(50), nullable=True, default="PENDING")
    # Allowed: PENDING, ACCEPTED, CORRECTED, FLAGGED
    original_generated_value = Column(Text, nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)


class ReportTable(UUIDMixin, Base):
    """Prescribed structured tables."""
    __tablename__ = "report_tables"

    report_id = Column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    internal_id = Column(String(50), nullable=False)
    official_id = Column(String(50), nullable=False) # e.g. "Table 1.1"
    exact_official_label = Column(String(500), nullable=False)
    chapter = Column(String(100), nullable=True)
    columns_schema = Column(JSON, nullable=False)
    rows_data = Column(JSON, nullable=False, default=list)
    row_count = Column(Integer, default=0, nullable=False)
    is_complete = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)


class ReportAnnexure(UUIDMixin, Base):
    """Prescribed statutory & conditional annexures."""
    __tablename__ = "report_annexures"

    report_id = Column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    internal_id = Column(String(50), nullable=False)
    official_reference = Column(String(50), nullable=False) # e.g. "Annexure 1"
    title = Column(String(500), nullable=False)
    requirement_type = Column(String(50), nullable=False, default="MANDATORY")
    # Allowed: MANDATORY, CONDITIONAL, OPTIONAL, OTHER_DOCUMENT_IF_ANY, NOT_APPLICABLE
    applicability = Column(String(255), nullable=True)
    attachment_status = Column(String(50), nullable=False, default="MISSING")
    # Allowed: ATTACHED_AND_VERIFIED, MISSING, NOT_APPLICABLE, PENDING_ATTACHMENT
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    file_path = Column(String(500), nullable=True)
    page_count = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)


class ReportPlate(UUIDMixin, Base):
    """Prescribed technical plans / plates / drawings with method conditionality."""
    __tablename__ = "report_plates"

    report_id = Column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    internal_id = Column(String(50), nullable=False)
    plate_id = Column(String(50), nullable=False) # e.g. "Plate 1", "Plate 6A"
    official_title = Column(String(500), nullable=False)
    sequence = Column(Integer, nullable=False)
    applicability = Column(String(255), nullable=True)
    scale_requirement = Column(String(50), nullable=False)
    required_for_oc = Column(Boolean, default=True)
    required_for_ug = Column(Boolean, default=True)
    attachment_status = Column(String(50), nullable=False, default="SOURCE_REQUIRED")
    # Allowed: MANDATORY, CONDITIONAL, NOT_APPLICABLE, SOURCE_REQUIRED,
    # HUMAN_GIS_INPUT_REQUIRED, VERIFIED_ATTACHMENT, REVIEW_REQUIRED
    verification_status = Column(String(50), default="UNVERIFIED")
    display_notice = Column(String(255), default="NOT GENERATED — SOURCE DATA REQUIRED")
    attached_file_path = Column(String(500), nullable=True)


class ReportCertification(UUIDMixin, Base):
    """Prescribed statutory certifications & undertakings."""
    __tablename__ = "report_certifications"

    report_id = Column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    internal_id = Column(String(50), nullable=False)
    official_purpose = Column(String(500), nullable=False)
    signatory_role = Column(String(50), nullable=False)
    # Allowed: prepared_by, certified_by, verified_by, board_authorized_by, other_authorized_signatory
    undertaking_text = Column(Text, nullable=False)
    signatory_name = Column(String(200), nullable=True)
    signatory_designation = Column(String(200), nullable=True)
    registration_or_accreditation_number = Column(String(100), nullable=True)
    audit_state = Column(String(50), nullable=False, default="SYSTEM_GENERATED")
    # Allowed: SYSTEM_GENERATED, HUMAN_VERIFIED, AUTHORIZED_SIGNED, AUTHORITY_APPROVED
    signed_at = Column(DateTime, nullable=True)
    authority_approval_reference = Column(String(200), nullable=True)


class ReportComplianceIssue(UUIDMixin, Base):
    """Detailed compliance issues detected during validation."""
    __tablename__ = "report_compliance_issues"

    report_id = Column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    severity = Column(String(20), nullable=False) # CRITICAL, WARNING, INFO
    issue_type = Column(String(50), nullable=False)
    target_node_id = Column(String(100), nullable=True)
    target_official_id = Column(String(50), nullable=True)
    description = Column(Text, nullable=False)
    statutory_reference = Column(String(255), nullable=True)
    resolution_hint = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)


class ReportVersion(UUIDMixin, Base):
    """Immutable version history for frozen reports."""
    __tablename__ = "report_versions"

    report_id = Column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)
    docx_file_path = Column(String(500), nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    change_summary = Column(Text, nullable=True)
    snapshot_json = Column(JSON, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
