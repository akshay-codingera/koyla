from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, Text, Float, JSON
from app.models.base import UUIDMixin
from app.db.database import Base

class ExtractionRun(UUIDMixin, Base):
    __tablename__ = "extraction_runs"
    
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    provider = Column(String(50), nullable=False, default="RULE_BASED")  # 'RULE_BASED', 'LOCAL_LLM', 'HYBRID'
    status = Column(String(50), nullable=False, default="PENDING")       # 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'MODEL_UNAVAILABLE'
    fields_extracted_count = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)


class ExtractedField(UUIDMixin, Base):
    __tablename__ = "extracted_fields"
    
    extraction_run_id = Column(String(36), ForeignKey("extraction_runs.id", ondelete="CASCADE"), nullable=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    
    # Field identification & categorization
    field_name = Column(String(100), nullable=False, index=True)
    field_category = Column(String(50), nullable=False, default="GENERAL") # 'IDENTIFICATION', 'GEOLOGY', 'MINING', 'FINANCIAL'
    data_type = Column(String(20), nullable=False, default="STRING")        # 'STRING', 'NUMBER', 'DATE'
    
    # Values & units
    raw_value = Column(Text, nullable=False)
    normalized_value = Column(Text, nullable=True)      # Stored as formatted string
    numeric_value = Column(Float, nullable=True)         # Floating point value if numeric
    unit = Column(String(50), nullable=True)            # 'MT', 'tonnes', 'm', 'kcal/kg', '%', 'cum/tonne', etc.
    
    # Exact provenance tracking
    page_number = Column(Integer, nullable=True)        # Exact physical source page
    table_id = Column(String(36), ForeignKey("tables.id", ondelete="SET NULL"), nullable=True)
    row_id = Column(String(36), ForeignKey("table_rows.id", ondelete="SET NULL"), nullable=True)
    chunk_id = Column(String(36), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True)
    source_text = Column(Text, nullable=True)           # Exact surrounding text or cell snippet
    
    # Confidence and status separation
    extraction_method = Column(String(50), nullable=False, default="RULE_BASED") # 'RULE_BASED', 'LOCAL_LLM'
    confidence_score = Column(Float, nullable=False, default=1.0)                 # 0.0 - 1.0
    confidence_level = Column(String(20), nullable=False, default="HIGH")        # 'HIGH', 'MEDIUM', 'LOW'
    
    validation_status = Column(String(20), nullable=False, default="PASS")       # 'PASS', 'WARNING', 'ERROR'
    reconciliation_status = Column(String(20), nullable=False, default="STANDALONE") # 'STANDALONE', 'MATCHED', 'CONFLICT', 'RESOLVED'
    verification_status = Column(String(20), nullable=False, default="UNVERIFIED")   # 'UNVERIFIED', 'VERIFIED', 'CORRECTED', 'REJECTED'
    
    # Human verification tracking
    is_corrected = Column(Boolean, default=False, nullable=False)
    corrected_value = Column(Text, nullable=True)
    corrected_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    corrected_at = Column(DateTime, nullable=True)
    
    metadata_json = Column(JSON, nullable=True)


class ValidationResult(UUIDMixin, Base):
    __tablename__ = "validation_results"
    
    field_id = Column(String(36), ForeignKey("extracted_fields.id", ondelete="CASCADE"), nullable=False)
    rule_name = Column(String(100), nullable=False)
    rule_category = Column(String(50), nullable=False) # 'TYPE', 'RANGE', 'UNIT', 'CONSISTENCY', 'REQUIRED'
    status = Column(String(20), nullable=False)        # 'PASS', 'WARNING', 'ERROR'
    severity = Column(String(20), nullable=False)      # 'INFO', 'WARNING', 'CRITICAL'
    message = Column(Text, nullable=False)
    observed_value = Column(Text, nullable=True)
    expected_constraint = Column(Text, nullable=True)


class ReconciliationGroup(UUIDMixin, Base):
    __tablename__ = "reconciliation_groups"
    
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    entity_name = Column(String(255), nullable=False)     # e.g., Mine name, Project name, or Seam name
    metric_name = Column(String(100), nullable=False)     # e.g., 'production_quantity'
    reporting_period = Column(String(100), nullable=False)# e.g., '2024-25'
    conflict_status = Column(String(50), nullable=False, default="MATCHED") # 'MATCHED', 'CONFLICT'
    resolution_status = Column(String(50), nullable=False, default="UNRESOLVED") # 'UNRESOLVED', 'RESOLVED', 'DEFERRED'
    resolved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)


class ReconciliationCandidate(UUIDMixin, Base):
    __tablename__ = "reconciliation_candidates"
    
    group_id = Column(String(36), ForeignKey("reconciliation_groups.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    field_id = Column(String(36), ForeignKey("extracted_fields.id", ondelete="CASCADE"), nullable=False)
    value = Column(Text, nullable=False)
    numeric_value = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    confidence_score = Column(Float, nullable=False, default=1.0)
