from datetime import datetime
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, JSON, Float
from sqlalchemy.orm import relationship
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


class StatutoryReserveVerification(UUIDMixin, Base):
    __tablename__ = "statutory_reserve_verifications"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    reserve_record_id = Column(String(36), ForeignKey("extracted_fields.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    entity_name = Column(String(255), nullable=True)

    # Values & Provenance
    original_value = Column(Text, nullable=False)
    original_numeric_value = Column(Float, nullable=True)
    proposed_value = Column(Text, nullable=False)
    proposed_numeric_value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)

    # State Machine: 'PENDING_VERIFICATION', 'VERIFIED', 'REJECTED'
    status = Column(String(50), nullable=False, default="PENDING_VERIFICATION", index=True)

    # Maker tracking
    maker_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    maker_comment = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)

    # Checker / Verifier tracking
    verifier_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    verifier_comment = Column(Text, nullable=True)

    # Lifecycle Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    metadata_json = Column(JSON, nullable=True)

    # Relationships
    organization = relationship("Organization")
    reserve_record = relationship("ExtractedField")
    maker = relationship("User", foreign_keys=[maker_user_id])
    verifier = relationship("User", foreign_keys=[verifier_user_id])

