"""
Phase 9: Visual & Figure Intelligence — Deterministic Visual Detector

Implements a 3-layer detection strategy for PDF pages:

Layer A — Displayed raster images (PyMuPDF get_image_info / extract_image)
Layer B — Vector graphics regions (PyMuPDF get_drawings)
Layer C — Caption/label context (regex on surrounding page text)

Detection limitations (documented per Phase 9 specification):
- Embedded raster image detection does not equal complete visual understanding
- Vector graphics require separate handling and may produce false positives
- Composite figures may require grouping that is imperfect
- OCR can be noisy, especially on geological diagrams
- Classification may be UNKNOWN — this is the correct safe output
- Visual interpretation is not equivalent to expert geological interpretation

Coordinate convention:
    All bounding boxes use PyMuPDF unrotated page coordinates
    {x0, y0, x1, y1} where origin is top-left, units are PDF points (1/72 inch).
"""
import io
import re
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image

from app.services.parsers.base import ParsedVisual
from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Caption / Figure Number Patterns ────────────────────────────────────────

# Matches: "Figure 1", "Fig. 2", "FIGURE 3.1", "Plate I", "Plate II",
#           "Map 1", "Cross-Section A-A'", etc.
FIGURE_NUMBER_PATTERNS = [
    re.compile(r"(?:Figure|Fig\.?)\s*(\d+(?:\.\d+)?[a-zA-Z]?)", re.IGNORECASE),
    re.compile(r"(?:Plate)\s+([IVXLCDM]+|\d+)", re.IGNORECASE),
    re.compile(r"(?:Map)\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"(?:Chart)\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"(?:Diagram)\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"(?:Drawing)\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"(?:Photo(?:graph)?)\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
]

# Caption line pattern — text immediately following a figure identifier
CAPTION_PATTERN = re.compile(
    r"(?:(?:Figure|Fig\.?|Plate|Map|Chart|Diagram|Drawing|Photo(?:graph)?)\s*"
    r"(?:\d+(?:\.\d+)?[a-zA-Z]?|[IVXLCDM]+))\s*[:\.\-–—]?\s*(.+)",
    re.IGNORECASE,
)

# ─── Classification Keywords ─────────────────────────────────────────────────

# Maps keyword patterns to visual_type and a base confidence contribution.
# Multiple matches increase confidence (capped at 1.0).
CLASSIFICATION_RULES: List[Tuple[re.Pattern, str, float]] = [
    (re.compile(r"\bmine\s*plan\b", re.I), "MINE_PLAN", 0.7),
    (re.compile(r"\bmine\s*layout\b", re.I), "MINE_PLAN", 0.6),
    (re.compile(r"\bcross[- ]?section\b", re.I), "CROSS_SECTION", 0.7),
    (re.compile(r"\bsection\s+[A-Z][-–—][A-Z]['']?\b", re.I), "CROSS_SECTION", 0.65),
    (re.compile(r"\bgeological\s+section\b", re.I), "GEOLOGICAL_SECTION", 0.7),
    (re.compile(r"\blitho\s*log\b", re.I), "GEOLOGICAL_SECTION", 0.6),
    (re.compile(r"\bborehole\s*log\b", re.I), "BOREHOLE_LOG", 0.75),
    (re.compile(r"\bbore\s*hole\b", re.I), "BOREHOLE_LOG", 0.5),
    (re.compile(r"\bdrill\s*(?:ing)?\s*log\b", re.I), "BOREHOLE_LOG", 0.6),
    (re.compile(r"\bstratigraph", re.I), "STRATIGRAPHIC_DIAGRAM", 0.7),
    (re.compile(r"\bcolumnar\s+section\b", re.I), "STRATIGRAPHIC_DIAGRAM", 0.6),
    (re.compile(r"\bmap\b", re.I), "MAP", 0.5),
    (re.compile(r"\bgeological\s+map\b", re.I), "MAP", 0.8),
    (re.compile(r"\btopograph", re.I), "MAP", 0.6),
    (re.compile(r"\bchart\b", re.I), "CHART", 0.4),
    (re.compile(r"\bbar\s*(?:chart|graph)\b", re.I), "CHART", 0.65),
    (re.compile(r"\bpie\s*chart\b", re.I), "CHART", 0.7),
    (re.compile(r"\bhistogram\b", re.I), "CHART", 0.65),
    (re.compile(r"\bplot\b", re.I), "PLOT", 0.4),
    (re.compile(r"\bscatter\s*plot\b", re.I), "PLOT", 0.7),
    (re.compile(r"\bgraph\b", re.I), "PLOT", 0.35),
    (re.compile(r"\btable\b", re.I), "TABLE_IMAGE", 0.3),
    (re.compile(r"\btechnical\s+drawing\b", re.I), "TECHNICAL_DRAWING", 0.7),
    (re.compile(r"\bblueprint\b", re.I), "TECHNICAL_DRAWING", 0.6),
    (re.compile(r"\bschematic\b", re.I), "TECHNICAL_DRAWING", 0.5),
    (re.compile(r"\bphotograph\b", re.I), "PHOTOGRAPH", 0.7),
    (re.compile(r"\bphoto\b", re.I), "PHOTOGRAPH", 0.5),
    (re.compile(r"\bplate\b", re.I), "PLATE", 0.5),
]


class VisualDetector:
    """
    Deterministic visual detection engine for PDF pages.
    Uses PyMuPDF raster image info, vector drawings, and caption context.
    Does NOT use neural vision models.
    """

    def __init__(self):
        self.min_size = settings.VISUAL_MIN_IMAGE_SIZE
        self.dpi = settings.VISUAL_DETECTION_DPI

    def detect_visuals_on_page(
        self,
        page,          # pymupdf.Page object
        doc,           # pymupdf.Document object
        page_number: int,
        page_text: str = "",
    ) -> List[ParsedVisual]:
        """
        Run all detection layers on a single PDF page.
        Returns list of ParsedVisual objects ready for persistence.
        """
        visuals: List[ParsedVisual] = []

        # --- Layer A: Raster images ---
        raster_visuals = self._detect_raster_images(page, doc, page_number)
        visuals.extend(raster_visuals)

        # --- Layer B: Vector graphics regions ---
        vector_visuals = self._detect_vector_regions(page, page_number)
        visuals.extend(vector_visuals)

        # --- Deduplication: merge overlapping regions ---
        visuals = self._merge_overlapping(visuals, page)

        # --- Layer C: Caption/context classification ---
        for v in visuals:
            fig_num, caption, vtype, conf = self._classify_from_context(
                page_text, v.bbox
            )
            if fig_num and not v.figure_number:
                v.figure_number = fig_num
            if caption and not v.caption:
                v.caption = caption
            # Upgrade classification if context provides stronger signal
            if conf > v.classification_confidence:
                v.visual_type = vtype
                v.classification_confidence = conf

        return visuals

    # ─── Layer A: Raster Image Detection ─────────────────────────────────

    def _detect_raster_images(
        self, page, doc, page_number: int
    ) -> List[ParsedVisual]:
        """Extract displayed raster images from a PDF page using get_image_info."""
        visuals = []
        try:
            image_infos = page.get_image_info(xrefs=True)
        except Exception as e:
            logger.warning(f"get_image_info failed on page {page_number}: {e}")
            return visuals

        seen_xrefs = set()
        for info in image_infos:
            xref = info.get("xref", 0)
            if xref <= 0 or xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            # Image dimensions from the info dict
            img_width = info.get("width", 0)
            img_height = info.get("height", 0)

            # Skip tiny decorative images
            if img_width < self.min_size or img_height < self.min_size:
                continue

            # Bounding box on page (transform matrix gives display rect)
            bbox = info.get("bbox", None)
            if bbox:
                bbox_dict = {
                    "x0": round(bbox[0], 2),
                    "y0": round(bbox[1], 2),
                    "x1": round(bbox[2], 2),
                    "y1": round(bbox[3], 2),
                }
                # Skip if display area is too small
                display_w = abs(bbox_dict["x1"] - bbox_dict["x0"])
                display_h = abs(bbox_dict["y1"] - bbox_dict["y0"])
                if display_w < self.min_size or display_h < self.min_size:
                    continue
            else:
                bbox_dict = None

            # Extract image bytes
            try:
                img_data = doc.extract_image(xref)
                if not img_data or not img_data.get("image"):
                    continue
                image_bytes = img_data["image"]
                ext = img_data.get("ext", "png")
                # Convert to PNG for consistent storage
                if ext.lower() not in ("png", "jpg", "jpeg"):
                    try:
                        pil_img = Image.open(io.BytesIO(image_bytes))
                        buf = io.BytesIO()
                        pil_img.save(buf, format="PNG")
                        image_bytes = buf.getvalue()
                    except Exception:
                        pass  # Use original bytes
            except Exception as e:
                logger.warning(f"extract_image failed for xref {xref} on page {page_number}: {e}")
                continue

            visual = ParsedVisual(
                page_number=page_number,
                bbox=bbox_dict,
                image_bytes=image_bytes,
                width_px=img_width,
                height_px=img_height,
                visual_type="UNKNOWN",
                classification_confidence=0.0,
                extraction_method="pymupdf_raster",
                metadata={"xref": xref, "ext": ext},
            )
            visuals.append(visual)

        return visuals

    # ─── Layer B: Vector Graphics Detection ──────────────────────────────

    def _detect_vector_regions(
        self, page, page_number: int
    ) -> List[ParsedVisual]:
        """
        Detect regions with dense vector graphics (drawings) that may
        represent charts, technical drawings, maps, cross-sections, etc.

        Groups nearby drawing objects into candidate regions rather than
        creating one VisualAsset per tiny drawing object.
        """
        visuals = []
        try:
            drawings = page.get_drawings()
        except Exception as e:
            logger.warning(f"get_drawings failed on page {page_number}: {e}")
            return visuals

        if not drawings or len(drawings) < 5:
            # Too few drawing commands — unlikely to be a meaningful figure
            return visuals

        # Collect bounding rects of all drawing paths
        rects = []
        for d in drawings:
            r = d.get("rect")
            if r:
                x0, y0, x1, y1 = r
                w = abs(x1 - x0)
                h = abs(y1 - y0)
                if w > 5 and h > 5:  # skip tiny marks
                    rects.append((x0, y0, x1, y1))

        if len(rects) < 5:
            return visuals

        # Group spatially close rects into clusters
        clusters = self._cluster_rects(rects, merge_distance=15.0)

        page_rect = page.rect
        page_area = page_rect.width * page_rect.height

        for cluster_bbox, count in clusters:
            x0, y0, x1, y1 = cluster_bbox
            cluster_w = x1 - x0
            cluster_h = y1 - y0
            cluster_area = cluster_w * cluster_h

            # Skip if cluster is too small (< 3% of page) or too large (> 95%)
            if cluster_area < page_area * 0.03:
                continue
            if cluster_area > page_area * 0.95:
                continue
            # Skip if too few drawing elements in cluster
            if count < 5:
                continue

            bbox_dict = {
                "x0": round(x0, 2),
                "y0": round(y0, 2),
                "x1": round(x1, 2),
                "y1": round(y1, 2),
            }

            # Render the region as a pixmap for storage
            try:
                clip_rect = __import__("pymupdf").Rect(x0, y0, x1, y1)
                pix = page.get_pixmap(dpi=self.dpi, clip=clip_rect)
                image_bytes = pix.tobytes("png")
                w_px = pix.width
                h_px = pix.height
            except Exception as e:
                logger.warning(f"Pixmap rendering failed for vector region on page {page_number}: {e}")
                continue

            visual = ParsedVisual(
                page_number=page_number,
                bbox=bbox_dict,
                image_bytes=image_bytes,
                width_px=w_px,
                height_px=h_px,
                visual_type="UNKNOWN",
                classification_confidence=0.0,
                extraction_method="pymupdf_vector",
                metadata={"drawing_count": count},
            )
            visuals.append(visual)

        return visuals

    # ─── Rect Clustering ─────────────────────────────────────────────────

    @staticmethod
    def _cluster_rects(
        rects: List[Tuple[float, float, float, float]],
        merge_distance: float = 15.0,
    ) -> List[Tuple[Tuple[float, float, float, float], int]]:
        """
        Merge nearby rectangles into clusters.
        Returns list of (merged_bbox, element_count).
        """
        if not rects:
            return []

        # Sort by y0, then x0
        sorted_rects = sorted(rects, key=lambda r: (r[1], r[0]))

        clusters: List[List[Tuple[float, float, float, float]]] = []
        for rect in sorted_rects:
            merged = False
            for cluster in clusters:
                # Check if rect overlaps/is close to any rect in cluster
                cx0 = min(r[0] for r in cluster)
                cy0 = min(r[1] for r in cluster)
                cx1 = max(r[2] for r in cluster)
                cy1 = max(r[3] for r in cluster)

                # Expand cluster bbox by merge_distance
                if (rect[0] <= cx1 + merge_distance and
                    rect[2] >= cx0 - merge_distance and
                    rect[1] <= cy1 + merge_distance and
                    rect[3] >= cy0 - merge_distance):
                    cluster.append(rect)
                    merged = True
                    break

            if not merged:
                clusters.append([rect])

        result = []
        for cluster in clusters:
            merged_bbox = (
                min(r[0] for r in cluster),
                min(r[1] for r in cluster),
                max(r[2] for r in cluster),
                max(r[3] for r in cluster),
            )
            result.append((merged_bbox, len(cluster)))

        return result

    # ─── Overlap Merging ─────────────────────────────────────────────────

    def _merge_overlapping(
        self, visuals: List[ParsedVisual], page
    ) -> List[ParsedVisual]:
        """
        Merge visuals whose bounding boxes significantly overlap.
        Prefers raster over vector when merging.
        """
        if len(visuals) <= 1:
            return visuals

        merged: List[ParsedVisual] = []
        used = [False] * len(visuals)

        for i, v1 in enumerate(visuals):
            if used[i]:
                continue
            current = v1
            for j, v2 in enumerate(visuals):
                if i == j or used[j]:
                    continue
                if current.bbox and v2.bbox:
                    overlap = self._compute_overlap_ratio(current.bbox, v2.bbox)
                    if overlap > 0.5:
                        # Prefer raster over vector
                        if v2.extraction_method == "pymupdf_raster" and current.extraction_method != "pymupdf_raster":
                            current = v2
                        used[j] = True
            merged.append(current)
            used[i] = True

        return merged

    @staticmethod
    def _compute_overlap_ratio(
        bbox1: Dict[str, float], bbox2: Dict[str, float]
    ) -> float:
        """Compute intersection-over-minimum-area ratio."""
        x0 = max(bbox1["x0"], bbox2["x0"])
        y0 = max(bbox1["y0"], bbox2["y0"])
        x1 = min(bbox1["x1"], bbox2["x1"])
        y1 = min(bbox1["y1"], bbox2["y1"])

        if x1 <= x0 or y1 <= y0:
            return 0.0

        intersection = (x1 - x0) * (y1 - y0)
        area1 = (bbox1["x1"] - bbox1["x0"]) * (bbox1["y1"] - bbox1["y0"])
        area2 = (bbox2["x1"] - bbox2["x0"]) * (bbox2["y1"] - bbox2["y0"])
        min_area = min(area1, area2)

        if min_area <= 0:
            return 0.0
        return intersection / min_area

    # ─── Layer C: Caption / Context Classification ───────────────────────

    def _classify_from_context(
        self,
        page_text: str,
        bbox: Optional[Dict[str, float]],
    ) -> Tuple[Optional[str], Optional[str], str, float]:
        """
        Use page text to find figure numbers, captions, and classify visuals.

        Returns: (figure_number, caption, visual_type, confidence)
        """
        if not page_text:
            return None, None, "UNKNOWN", 0.0

        figure_number = None
        caption = None
        best_type = "UNKNOWN"
        best_conf = 0.0

        # Search for figure/plate numbers
        for pattern in FIGURE_NUMBER_PATTERNS:
            match = pattern.search(page_text)
            if match:
                # Reconstruct the full figure label
                full_match = match.group(0).strip()
                figure_number = full_match
                break

        # Search for caption text
        cap_match = CAPTION_PATTERN.search(page_text)
        if cap_match:
            raw_caption = cap_match.group(1).strip()
            # Limit caption to first sentence or 200 chars
            if ". " in raw_caption:
                raw_caption = raw_caption[: raw_caption.index(". ") + 1]
            caption = raw_caption[:200]

        # Apply classification rules
        context_text = (caption or "") + " " + (figure_number or "")
        # Also check a window of page text for classification
        search_text = context_text + " " + page_text[:1000]

        type_scores: Dict[str, float] = {}
        for pattern, vtype, base_conf in CLASSIFICATION_RULES:
            if pattern.search(search_text):
                current = type_scores.get(vtype, 0.0)
                type_scores[vtype] = min(1.0, current + base_conf * 0.5)

        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            best_conf = type_scores[best_type]

        return figure_number, caption, best_type, best_conf


# Module-level singleton
visual_detector = VisualDetector()
