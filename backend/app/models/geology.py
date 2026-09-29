from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    ForeignKey,
    DateTime,
    Text,
    Float,
    JSON,
    Index,
)
from app.models.base import UUIDMixin
from app.db.database import Base


class BoreholeStratum(UUIDMixin, Base):
    """
    Normalized relational representation of an ordered lithological stratum
    extracted from borehole logs or geological exploration documents.
    """
    __tablename__ = "borehole_strata"

    organization_id = Column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    borehole_id = Column(String(100), nullable=False, index=True)
    stratum_order = Column(Integer, nullable=False)

    # Depth & thickness metrics (meters)
    depth_from_m = Column(Float, nullable=False)
    depth_to_m = Column(Float, nullable=False)
    thickness_m = Column(Float, nullable=False)
    stated_thickness_m = Column(Float, nullable=True)

    # Lithology and Coal Seam
    lithology_type = Column(String(100), nullable=False, index=True)
    raw_lithology = Column(String(255), nullable=True)
    seam_name = Column(String(100), nullable=True, index=True)

    # Exact provenance back to source document components
    page_number = Column(Integer, nullable=True)
    chunk_id = Column(
        String(36),
        ForeignKey("chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    table_id = Column(
        String(36),
        ForeignKey("tables.id", ondelete="SET NULL"),
        nullable=True,
    )
    row_id = Column(
        String(36),
        ForeignKey("table_rows.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_text = Column(Text, nullable=True)
    extraction_method = Column(String(50), nullable=False, default="RULE_BASED")
    confidence_score = Column(Float, nullable=False, default=1.0)

    # Discrepancy & Verification
    has_thickness_discrepancy = Column(Boolean, default=False, nullable=False)
    discrepancy_details = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    __table_args__ = (
        Index(
            "ix_borehole_strata_org_bh_order",
            "organization_id",
            "borehole_id",
            "stratum_order",
        ),
    )
