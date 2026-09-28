from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, BigInteger, Text, Float, JSON
from sqlalchemy.orm import relationship
from app.models.base import UUIDMixin
from app.db.database import Base

class Document(UUIDMixin, Base):
    __tablename__ = "documents"
    organization_id = Column(String(36), ForeignKey("organizations.id"))
    title = Column(String(255), nullable=False)
    document_type = Column(String(100), nullable=False)
    source_tier = Column(String(20), default="TIER_B")
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    status = Column(String(50), default="QUEUED")
    is_demo_data = Column(Boolean, default=False)
    created_by = Column(String(36), ForeignKey("users.id"))
    updated_at = Column(DateTime)
    
class DocumentVersion(UUIDMixin, Base):
    __tablename__ = "document_versions"
    document_id = Column(String(36), ForeignKey("documents.id"))
    version_number = Column(Integer, nullable=False)
    supersedes_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    file_path = Column(String(500), nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    change_summary = Column(String(1000))
    
class ProcessingJob(UUIDMixin, Base):
    __tablename__ = "processing_jobs"
    document_id = Column(String(36), ForeignKey("documents.id"))
    job_type = Column(String(50))
    status = Column(String(50), default="QUEUED")
    progress_pct = Column(Integer, default=0)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

class DocumentPage(UUIDMixin, Base):
    __tablename__ = "document_pages"
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    extracted_text = Column(Text, nullable=True)
    ocr_applied = Column(Boolean, default=False)
    confidence_score = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)

class Table(UUIDMixin, Base):
    __tablename__ = "tables"
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    table_index = Column(Integer, nullable=False)
    caption = Column(String(500), nullable=True)
    headers = Column(JSON, nullable=False)
    row_count = Column(Integer, nullable=False, default=0)
    col_count = Column(Integer, nullable=False, default=0)
    
    # Logical table continuation fields
    logical_table_id = Column(String(36), index=True, nullable=True)
    is_continuation = Column(Boolean, default=False)
    continuation_of_id = Column(String(36), ForeignKey("tables.id"), nullable=True)
    part_number = Column(Integer, default=1)
    total_parts = Column(Integer, default=1)
    has_repeated_headers = Column(Boolean, default=False)
    continuation_confidence = Column(Float, default=1.0)
    continuation_status = Column(String(50), default="STANDALONE")  # 'STANDALONE', 'AUTO_MERGED', 'REVIEW_REQUIRED'
    
    metadata_json = Column(JSON, nullable=True)
    table_rows = relationship("TableRow", backref="table", cascade="all, delete-orphan", order_by="TableRow.row_index")

class TableRow(UUIDMixin, Base):
    __tablename__ = "table_rows"
    table_id = Column(String(36), ForeignKey("tables.id", ondelete="CASCADE"), nullable=False)
    row_index = Column(Integer, nullable=False)
    logical_row_index = Column(Integer, nullable=True)
    source_page = Column(Integer, nullable=True)
    cells = Column(JSON, nullable=False)
    metadata_json = Column(JSON, nullable=True)

