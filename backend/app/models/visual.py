"""
Phase 9: Visual & Figure Intelligence — VisualAsset Model

Single normalized table covering: visual asset storage, extracted evidence,
provenance chain (organization → document → page → visual → bbox), and
verification state.

Coordinate Convention:
    bbox_json stores PyMuPDF unrotated page coordinates {x0, y0, x1, y1}
    where origin is top-left, units are PDF points (1/72 inch).
    Frontend must scale from PDF points to display pixels using the page's
    rendered dimensions.
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import UUIDMixin
from app.db.database import Base


# Approved visual taxonomy — Phase 9 design specification
VISUAL_TYPES = [
    "MAP",
    "MINE_PLAN",
    "CROSS_SECTION",
    "GEOLOGICAL_SECTION",
    "BOREHOLE_LOG",
    "STRATIGRAPHIC_DIAGRAM",
    "CHART",
    "PLOT",
    "TABLE_IMAGE",
    "TECHNICAL_DRAWING",
    "PHOTOGRAPH",
    "PLATE",
    "OTHER",
    "UNKNOWN",
]


class VisualAsset(UUIDMixin, Base):
    """
    Represents a detected visual element (figure, chart, map, photograph, etc.)
    extracted from a document page during ingestion.

    Provenance chain: Organization → Document → Page → VisualAsset → bbox region

    Detection limitations (documented per Phase 9 specification):
    - Embedded raster image detection does not equal complete visual understanding
    - Vector graphics require separate handling and may produce false positives
    - Composite figures may require grouping that is imperfect
    - OCR can be noisy, especially on geological diagrams
    - Classification may be UNKNOWN — this is the correct safe output
    - Visual interpretation is not equivalent to expert geological interpretation
    - ocr_confidence threshold is a configurable operational threshold,
      NOT a guarantee of semantic accuracy
    """
    __tablename__ = "visual_assets"
    __table_args__ = (
        Index("idx_visual_document_id", "document_id"),
        Index("idx_visual_page_id", "page_id"),
        Index("idx_visual_type", "visual_type"),
        Index("idx_visual_verification", "verification_status"),
    )

    # --- Provenance ---
    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_id = Column(
        String(36),
        ForeignKey("document_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number = Column(Integer, nullable=False)  # denormalized for query efficiency

    # --- Classification ---
    visual_type = Column(String(30), nullable=False, default="UNKNOWN")
    classification_confidence = Column(Float, nullable=False, default=0.0)
    classification_method = Column(String(50), nullable=False, default="deterministic_heuristic")

    # --- Spatial / Bounding Box ---
    # PyMuPDF unrotated page coordinates: {x0, y0, x1, y1} in PDF points
    bbox_json = Column(JSON, nullable=True)

    # --- Storage ---
    file_path = Column(String(500), nullable=False)  # relative to STORAGE_DIR
    image_hash = Column(String(64), nullable=False)   # SHA-256 of extracted image bytes
    width_px = Column(Integer, nullable=True)
    height_px = Column(Integer, nullable=True)
    extraction_method = Column(String(50), nullable=False, default="pymupdf_raster")
    # "pymupdf_raster", "pymupdf_vector", "composite"

    # --- Figure Identity ---
    figure_number = Column(String(50), nullable=True)   # "Figure 1", "Plate II", etc.
    caption = Column(Text, nullable=True)

    # --- OCR Evidence ---
    raw_ocr_text = Column(Text, nullable=True)
    normalized_ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)

    # --- Verification ---
    verification_status = Column(
        String(30), nullable=False, default="PENDING"
    )  # PENDING, VERIFIED, REVIEW_REQUIRED, REJECTED

    # --- Extension ---
    metadata_json = Column(JSON, nullable=True)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow)
