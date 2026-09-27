from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, JSON, Index
from app.models.base import UUIDMixin
from app.db.database import Base

class DocumentRelationship(UUIDMixin, Base):
    """
    Represents an auto-discovered or verified relationship between two documents.
    Deterministic relationship discovery based on:
    - SAME_ORGANIZATION: documents belong to same subsidiary/RI
    - SAME_MINE_OR_BLOCK: matching extracted mine/block entity
    - SAME_PERIOD: matching fiscal year or operational period
    - SAME_METRIC: matching numerical metric tracked across reports
    - DOCUMENT_FAMILY: matching document series or naming taxonomy
    - CROSS_MODAL_EVIDENCE: visual asset (map/section) corroborates text/table evidence
    - SUPERSEDES: explicit version or revision lineage
    """
    __tablename__ = "document_relationships"
    __table_args__ = (
        Index("idx_doc_rel_source", "source_document_id"),
        Index("idx_doc_rel_target", "target_document_id"),
        Index("idx_doc_rel_type", "relationship_type"),
    )

    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    target_document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(50), nullable=False)  # SAME_MINE_OR_BLOCK, SAME_PERIOD, SAME_METRIC, DOCUMENT_FAMILY, SUPERSEDES, CROSS_MODAL_EVIDENCE
    confidence = Column(Float, nullable=False, default=1.0)
    matching_criteria = Column(JSON, nullable=True)  # e.g. {"field": "mine_name", "matched_value": "Gevra OC", "rule": "exact_match"}
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
