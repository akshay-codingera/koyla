from sqlalchemy import Column, String, Text, ForeignKey, DateTime, JSON
from app.models.base import UUIDMixin
from app.db.database import Base

class VerificationTask(UUIDMixin, Base):
    __tablename__ = "verification_tasks"
    
    task_type = Column(String(50), nullable=False)  # 'LOW_CONFIDENCE_OCR', 'LOW_CONFIDENCE_EXTRACTION', 'VALIDATION_ERROR', 'EXTRACTION_CONFLICT', 'REPORT_APPROVAL', 'SUSPICIOUS_METRIC', 'AMBIGUOUS_TABLE_CONTINUATION'
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    target_id = Column(String(36), nullable=True)
    field_id = Column(String(36), ForeignKey("extracted_fields.id", ondelete="CASCADE"), nullable=True)
    reconciliation_group_id = Column(String(36), ForeignKey("reconciliation_groups.id", ondelete="CASCADE"), nullable=True)
    assigned_to = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="PENDING", nullable=False)  # 'PENDING', 'APPROVED', 'CORRECTED', 'REJECTED', 'DEFERRED'
    action_taken = Column(String(50), nullable=True)                # 'APPROVE', 'CORRECT', 'REJECT', 'DEFER'
    corrected_value = Column(Text, nullable=True)
    evidence_context = Column(JSON, nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
