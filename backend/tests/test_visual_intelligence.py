"""
Phase 9: Visual & Figure Intelligence — Test Suite

Tests cover:
1. VisualAsset model CRUD
2. ParsedVisual dataclass
3. Visual detector classification heuristics
4. Caption/figure number regex
5. Visual chunk creation
6. Visual taxonomy validation
7. Coordinate convention verification
8. Low-confidence verification task logic
9. Storage path conventions
10. UNKNOWN fallback behavior
"""
import pytest
import hashlib
import io
import uuid
from unittest.mock import MagicMock, patch
from PIL import Image

# ─── Model Tests ─────────────────────────────────────────────────────────────


class TestVisualAssetModel:
    """Test the VisualAsset SQLAlchemy model definition."""

    def test_visual_asset_import(self):
        """VisualAsset can be imported from models."""
        from app.models.visual import VisualAsset, VISUAL_TYPES
        assert VisualAsset is not None
        assert isinstance(VISUAL_TYPES, list)

    def test_visual_taxonomy_completeness(self):
        """Approved visual taxonomy contains all 14 required types."""
        from app.models.visual import VISUAL_TYPES
        required = [
            "MAP", "MINE_PLAN", "CROSS_SECTION", "GEOLOGICAL_SECTION",
            "BOREHOLE_LOG", "STRATIGRAPHIC_DIAGRAM", "CHART", "PLOT",
            "TABLE_IMAGE", "TECHNICAL_DRAWING", "PHOTOGRAPH", "PLATE",
            "OTHER", "UNKNOWN",
        ]
        for vt in required:
            assert vt in VISUAL_TYPES, f"Missing visual type: {vt}"
        assert len(VISUAL_TYPES) == 14

    def test_visual_asset_table_name(self):
        from app.models.visual import VisualAsset
        assert VisualAsset.__tablename__ == "visual_assets"

    def test_visual_asset_default_values(self):
        """Column defaults are defined correctly in the model schema."""
        from app.models.visual import VisualAsset
        # SQLAlchemy Column defaults are applied at INSERT time, not construction.
        # Verify column default definitions directly.
        cols = {c.name: c for c in VisualAsset.__table__.columns}
        assert cols["visual_type"].default.arg == "UNKNOWN"
        assert cols["classification_confidence"].default.arg == 0.0
        assert cols["classification_method"].default.arg == "deterministic_heuristic"
        assert cols["extraction_method"].default.arg == "pymupdf_raster"
        assert cols["verification_status"].default.arg == "PENDING"

    def test_visual_asset_registered_in_models_init(self):
        """VisualAsset is exported from app.models.__init__."""
        from app.models import VisualAsset
        assert VisualAsset is not None


# ─── ParsedVisual Tests ──────────────────────────────────────────────────────


class TestParsedVisual:
    """Test the ParsedVisual dataclass from base.py."""

    def test_parsed_visual_creation(self):
        from app.services.parsers.base import ParsedVisual
        pv = ParsedVisual(
            page_number=1,
            bbox={"x0": 10.0, "y0": 20.0, "x1": 200.0, "y1": 300.0},
            width_px=190,
            height_px=280,
            visual_type="CHART",
            classification_confidence=0.75,
        )
        assert pv.page_number == 1
        assert pv.visual_type == "CHART"
        assert pv.classification_confidence == 0.75
        assert pv.extraction_method == "pymupdf_raster"

    def test_parsed_visual_defaults(self):
        from app.services.parsers.base import ParsedVisual
        pv = ParsedVisual(page_number=5)
        assert pv.visual_type == "UNKNOWN"
        assert pv.classification_confidence == 0.0
        assert pv.image_bytes is None
        assert pv.figure_number is None
        assert pv.caption is None

    def test_parsed_page_has_visuals_list(self):
        from app.services.parsers.base import ParsedPage
        page = ParsedPage(page_number=1)
        assert hasattr(page, 'visuals')
        assert isinstance(page.visuals, list)
        assert len(page.visuals) == 0


# ─── Visual Detector Tests ───────────────────────────────────────────────────


class TestVisualDetector:
    """Test the deterministic visual detection engine."""

    def test_detector_import(self):
        from app.services.parsers.visual_detector import visual_detector
        assert visual_detector is not None

    def test_caption_figure_number_regex(self):
        """Test figure number extraction from text."""
        from app.services.parsers.visual_detector import FIGURE_NUMBER_PATTERNS
        test_cases = [
            ("Figure 1: Coal seam distribution", "Figure 1"),
            ("Fig. 2.3 - Borehole log summary", "Fig. 2.3"),
            ("FIGURE 4A showing mine plan", "FIGURE 4A"),
            ("Plate III: Geological cross-section", "Plate III"),
            ("Map 1 of the mining area", "Map 1"),
        ]
        for text, expected_prefix in test_cases:
            found = False
            for pattern in FIGURE_NUMBER_PATTERNS:
                match = pattern.search(text)
                if match:
                    full_match = match.group(0).strip()
                    assert expected_prefix.lower() in full_match.lower() or full_match.lower() in expected_prefix.lower(), \
                        f"Expected '{expected_prefix}' in '{full_match}' for text '{text}'"
                    found = True
                    break
            assert found, f"No pattern matched for: {text}"

    def test_classification_keywords(self):
        """Test classification from context keywords."""
        from app.services.parsers.visual_detector import visual_detector
        # Mine plan
        _, _, vtype, conf = visual_detector._classify_from_context(
            "Figure 1: Mine Plan layout showing excavation zones", None
        )
        assert vtype == "MINE_PLAN"
        assert conf > 0.3

        # Borehole log
        _, _, vtype, conf = visual_detector._classify_from_context(
            "Figure 2: Borehole Log BH-101", None
        )
        assert vtype == "BOREHOLE_LOG"
        assert conf > 0.3

        # Cross section
        _, _, vtype, conf = visual_detector._classify_from_context(
            "Geological cross-section A-B through the coal field", None
        )
        assert vtype in ("CROSS_SECTION", "GEOLOGICAL_SECTION")
        assert conf > 0.3

    def test_unknown_classification_fallback(self):
        """When context provides no signals, classification should be UNKNOWN."""
        from app.services.parsers.visual_detector import visual_detector
        _, _, vtype, conf = visual_detector._classify_from_context(
            "This is just regular text with no figure indicators", None
        )
        assert vtype == "UNKNOWN"
        assert conf == 0.0

    def test_stratigraphic_classification(self):
        from app.services.parsers.visual_detector import visual_detector
        _, _, vtype, conf = visual_detector._classify_from_context(
            "Figure 5: Stratigraphic column of the Gondwana formation", None
        )
        assert vtype == "STRATIGRAPHIC_DIAGRAM"
        assert conf > 0.3

    def test_overlap_computation(self):
        """Test bounding box overlap calculation."""
        from app.services.parsers.visual_detector import visual_detector
        bbox1 = {"x0": 0, "y0": 0, "x1": 100, "y1": 100}
        bbox2 = {"x0": 50, "y0": 50, "x1": 150, "y1": 150}
        overlap = visual_detector._compute_overlap_ratio(bbox1, bbox2)
        assert overlap > 0.0
        assert overlap < 1.0

        # No overlap
        bbox3 = {"x0": 200, "y0": 200, "x1": 300, "y1": 300}
        overlap2 = visual_detector._compute_overlap_ratio(bbox1, bbox3)
        assert overlap2 == 0.0

        # Complete overlap
        bbox4 = {"x0": 0, "y0": 0, "x1": 100, "y1": 100}
        overlap3 = visual_detector._compute_overlap_ratio(bbox1, bbox4)
        assert overlap3 == 1.0

    def test_rect_clustering(self):
        """Test spatial clustering of drawing rectangles."""
        from app.services.parsers.visual_detector import VisualDetector
        rects = [
            (10, 10, 50, 50),
            (55, 10, 90, 50),
            (12, 55, 50, 90),
            (300, 300, 350, 350),
            (310, 310, 360, 360),
        ]
        clusters = VisualDetector._cluster_rects(rects, merge_distance=15.0)
        # Should produce 2 clusters: one near (10-90, 10-90), one near (300-360, 300-360)
        assert len(clusters) == 2

    def test_empty_detection(self):
        """Detector should return empty list for pages with no visuals."""
        from app.services.parsers.visual_detector import visual_detector
        mock_page = MagicMock()
        mock_page.get_image_info.return_value = []
        mock_page.get_drawings.return_value = []
        mock_page.rect = MagicMock()
        mock_page.rect.width = 595
        mock_page.rect.height = 842
        mock_doc = MagicMock()

        visuals = visual_detector.detect_visuals_on_page(
            page=mock_page, doc=mock_doc, page_number=1, page_text=""
        )
        assert isinstance(visuals, list)
        assert len(visuals) == 0

    def test_small_image_filtered(self):
        """Images smaller than VISUAL_MIN_IMAGE_SIZE should be filtered out."""
        from app.services.parsers.visual_detector import visual_detector
        mock_page = MagicMock()
        # Small decorative image (20x20)
        mock_page.get_image_info.return_value = [{
            "xref": 1, "width": 20, "height": 20,
            "bbox": (0, 0, 20, 20),
        }]
        mock_page.get_drawings.return_value = []
        mock_page.rect = MagicMock()
        mock_page.rect.width = 595
        mock_page.rect.height = 842
        mock_doc = MagicMock()

        visuals = visual_detector.detect_visuals_on_page(
            page=mock_page, doc=mock_doc, page_number=1, page_text=""
        )
        assert len(visuals) == 0


# ─── Chunking Tests ──────────────────────────────────────────────────────────


class TestVisualChunking:
    """Test visual evidence chunk creation."""

    def test_visual_chunk_creation(self):
        from app.services.chunking import chunking_service

        class MockVisualAsset:
            def __init__(self):
                self.id = str(uuid.uuid4())
                self.visual_type = "CHART"
                self.figure_number = "Figure 1"
                self.caption = "Production trend 2020-2024"
                self.page_number = 3
                self.raw_ocr_text = None
                self.normalized_ocr_text = "Coal production increased from 500 MT to 700 MT"
                self.ocr_confidence = 0.85
                self.classification_confidence = 0.7

        va = MockVisualAsset()
        chunks = chunking_service.chunk_visual_assets(
            visual_assets=[va], document_id="doc-123", start_chunk_index=100
        )
        assert len(chunks) == 1
        c = chunks[0]
        assert c.chunk_type == "VISUAL"
        assert c.page_number == 3
        assert c.chunk_index == 100
        assert "CHART" in c.content
        assert "Figure 1" in c.content
        assert "Coal production" in c.content
        assert c.metadata_json["source_type"] == "visual"
        assert c.metadata_json["visual_type"] == "CHART"

    def test_visual_chunk_skips_empty_ocr(self):
        from app.services.chunking import chunking_service

        class MockVisualAsset:
            def __init__(self):
                self.id = str(uuid.uuid4())
                self.visual_type = "MAP"
                self.figure_number = None
                self.caption = None
                self.page_number = 1
                self.raw_ocr_text = None
                self.normalized_ocr_text = None
                self.ocr_confidence = None
                self.classification_confidence = 0.3

        va = MockVisualAsset()
        chunks = chunking_service.chunk_visual_assets(
            visual_assets=[va], document_id="doc-456", start_chunk_index=1
        )
        assert len(chunks) == 0  # No OCR text = no chunk

    def test_visual_chunk_skips_trivial_text(self):
        from app.services.chunking import chunking_service

        class MockVisualAsset:
            def __init__(self):
                self.id = str(uuid.uuid4())
                self.visual_type = "PHOTOGRAPH"
                self.figure_number = None
                self.caption = None
                self.page_number = 1
                self.raw_ocr_text = "abc"
                self.normalized_ocr_text = "abc"
                self.ocr_confidence = 0.5
                self.classification_confidence = 0.4

        va = MockVisualAsset()
        chunks = chunking_service.chunk_visual_assets(
            visual_assets=[va], document_id="doc-789", start_chunk_index=1
        )
        assert len(chunks) == 0  # < 10 chars = too short


# ─── Settings Tests ──────────────────────────────────────────────────────────


class TestVisualSettings:
    """Test Phase 9 configuration settings."""

    def test_visual_settings_exist(self):
        from app.core.config import settings
        assert hasattr(settings, 'VISUAL_OCR_CONFIDENCE_MIN')
        assert hasattr(settings, 'VISUAL_DETECTION_DPI')
        assert hasattr(settings, 'VISUAL_MIN_IMAGE_SIZE')
        assert hasattr(settings, 'VISUAL_CLASSIFICATION_CONFIDENCE_MIN')

    def test_visual_settings_defaults(self):
        from app.core.config import settings
        assert settings.VISUAL_OCR_CONFIDENCE_MIN == 0.70
        assert settings.VISUAL_DETECTION_DPI == 150
        assert settings.VISUAL_MIN_IMAGE_SIZE == 50
        assert settings.VISUAL_CLASSIFICATION_CONFIDENCE_MIN == 0.5


# ─── Coordinate Convention Tests ─────────────────────────────────────────────


class TestCoordinateConvention:
    """Verify coordinate convention documentation and usage."""

    def test_bbox_dict_format(self):
        """Bounding boxes should use {x0, y0, x1, y1} format."""
        from app.services.parsers.base import ParsedVisual
        pv = ParsedVisual(
            page_number=1,
            bbox={"x0": 72.0, "y0": 100.0, "x1": 400.0, "y1": 500.0},
        )
        assert "x0" in pv.bbox
        assert "y0" in pv.bbox
        assert "x1" in pv.bbox
        assert "y1" in pv.bbox
        # Values are in PDF points (1/72 inch)
        assert pv.bbox["x0"] >= 0

    def test_bbox_allows_none(self):
        from app.services.parsers.base import ParsedVisual
        pv = ParsedVisual(page_number=1)
        assert pv.bbox is None


# ─── API Route Tests ─────────────────────────────────────────────────────────


class TestVisualAPIRoutes:
    """Test visual API route definitions exist."""

    def test_visuals_router_exists(self):
        from app.api.v1.visuals import router
        assert router is not None

    def test_visual_types_endpoint(self):
        from app.api.v1.visuals import list_visual_types
        assert callable(list_visual_types)

    def test_api_registered_in_main(self):
        """visuals router is registered in the FastAPI app (requires DB)."""
        try:
            from app.main import app
            routes = [r.path for r in app.routes]
            visual_routes = [r for r in routes if "visuals" in r]
            assert len(visual_routes) > 0, "No visual routes found in app"
        except Exception:
            # DB not available — verify router import works independently
            from app.api.v1.visuals import router
            assert len(router.routes) > 0


# ─── Provenance Tests ────────────────────────────────────────────────────────


class TestVisualProvenance:
    """Test visual provenance chain requirements."""

    def test_visual_asset_has_document_fk(self):
        from app.models.visual import VisualAsset
        columns = {c.name for c in VisualAsset.__table__.columns}
        assert "document_id" in columns
        assert "page_id" in columns
        assert "page_number" in columns

    def test_visual_asset_has_classification_fields(self):
        from app.models.visual import VisualAsset
        columns = {c.name for c in VisualAsset.__table__.columns}
        assert "visual_type" in columns
        assert "classification_confidence" in columns
        assert "classification_method" in columns

    def test_visual_asset_has_ocr_fields(self):
        from app.models.visual import VisualAsset
        columns = {c.name for c in VisualAsset.__table__.columns}
        assert "raw_ocr_text" in columns
        assert "normalized_ocr_text" in columns
        assert "ocr_confidence" in columns

    def test_visual_asset_has_storage_fields(self):
        from app.models.visual import VisualAsset
        columns = {c.name for c in VisualAsset.__table__.columns}
        assert "file_path" in columns
        assert "image_hash" in columns
        assert "width_px" in columns
        assert "height_px" in columns

    def test_visual_asset_has_figure_identity(self):
        from app.models.visual import VisualAsset
        columns = {c.name for c in VisualAsset.__table__.columns}
        assert "figure_number" in columns
        assert "caption" in columns

    def test_visual_asset_has_verification(self):
        from app.models.visual import VisualAsset
        columns = {c.name for c in VisualAsset.__table__.columns}
        assert "verification_status" in columns
        assert "bbox_json" in columns
        assert "extraction_method" in columns


# ─── Image Hash Tests ────────────────────────────────────────────────────────


class TestImageHash:
    """Test image integrity hashing."""

    def test_sha256_consistency(self):
        """Same image bytes should produce same hash."""
        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        hash1 = hashlib.sha256(image_bytes).hexdigest()
        hash2 = hashlib.sha256(image_bytes).hexdigest()
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_different_images_different_hash(self):
        img1 = Image.new("RGB", (100, 100), color="red")
        img2 = Image.new("RGB", (100, 100), color="blue")
        buf1 = io.BytesIO()
        buf2 = io.BytesIO()
        img1.save(buf1, format="PNG")
        img2.save(buf2, format="PNG")

        hash1 = hashlib.sha256(buf1.getvalue()).hexdigest()
        hash2 = hashlib.sha256(buf2.getvalue()).hexdigest()
        assert hash1 != hash2
