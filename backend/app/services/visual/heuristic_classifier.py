import re
import logging
from typing import Optional, Dict, Any, List, Tuple

from app.core.config import settings
from app.services.visual.base import (
    VisualClassifier,
    VisualClassificationResult,
    ClassificationReviewStatus,
    VISUAL_TYPES,
)
from app.services.visual.robustness import clamp_confidence

logger = logging.getLogger(__name__)

# Caption / Figure Number Extraction Patterns
FIGURE_NUMBER_PATTERNS = [
    re.compile(r"(?:Figure|Fig\.?)\s*(\d+(?:\.\d+)?[a-zA-Z]?)", re.IGNORECASE),
    re.compile(r"(?:Plate)\s+([IVXLCDM]+|\d+)", re.IGNORECASE),
    re.compile(r"(?:Map)\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"(?:Chart)\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"(?:Diagram)\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"(?:Drawing)\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"(?:Photo(?:graph)?)\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
]

CAPTION_PATTERN = re.compile(
    r"(?:(?:Figure|Fig\.?|Plate|Map|Chart|Diagram|Drawing|Photo(?:graph)?)\s*"
    r"(?:\d+(?:\.\d+)?[a-zA-Z]?|[IVXLCDM]+))\s*[:\.\-–—]?\s*(.+)",
    re.IGNORECASE,
)

# Deterministic Classification Rules (Pattern, Target Type, Base Confidence)
CLASSIFICATION_RULES: List[Tuple[re.Pattern, str, float]] = [
    (re.compile(r"\bmine\s*plan\b", re.I), "MINE_PLAN", 0.75),
    (re.compile(r"\bmine\s*layout\b", re.I), "MINE_PLAN", 0.65),
    (re.compile(r"\bquarry\s*layout\b", re.I), "MINE_PLAN", 0.70),
    (re.compile(r"\bcross[- ]?section\b", re.I), "CROSS_SECTION", 0.75),
    (re.compile(r"\bsection\s+[A-Z][-–—][A-Z]['']?\b", re.I), "CROSS_SECTION", 0.70),
    (re.compile(r"\bgeological\s+section\b", re.I), "GEOLOGICAL_SECTION", 0.75),
    (re.compile(r"\blitho\s*log\b", re.I), "GEOLOGICAL_SECTION", 0.65),
    (re.compile(r"\bborehole\s*log\b", re.I), "BOREHOLE_LOG", 0.80),
    (re.compile(r"\bbore\s*hole\b", re.I), "BOREHOLE_LOG", 0.55),
    (re.compile(r"\bdrill\s*(?:ing)?\s*log\b", re.I), "BOREHOLE_LOG", 0.65),
    (re.compile(r"\bstratigraph", re.I), "STRATIGRAPHIC_DIAGRAM", 0.75),
    (re.compile(r"\bcolumnar\s+section\b", re.I), "STRATIGRAPHIC_DIAGRAM", 0.65),
    (re.compile(r"\bgeological\s+map\b", re.I), "MAP", 0.85),
    (re.compile(r"\btopograph", re.I), "MAP", 0.65),
    (re.compile(r"\bindex\s*map\b", re.I), "MAP", 0.75),
    (re.compile(r"\bmap\b", re.I), "MAP", 0.50),
    (re.compile(r"\bbar\s*(?:chart|graph)\b", re.I), "CHART", 0.70),
    (re.compile(r"\bpie\s*chart\b", re.I), "CHART", 0.75),
    (re.compile(r"\bhistogram\b", re.I), "CHART", 0.70),
    (re.compile(r"\bchart\b", re.I), "CHART", 0.45),
    (re.compile(r"\bscatter\s*plot\b", re.I), "PLOT", 0.75),
    (re.compile(r"\bplot\b", re.I), "PLOT", 0.45),
    (re.compile(r"\bgraph\b", re.I), "PLOT", 0.40),
    (re.compile(r"\btable\s*image\b", re.I), "TABLE_IMAGE", 0.70),
    (re.compile(r"\btable\b", re.I), "TABLE_IMAGE", 0.35),
    (re.compile(r"\btechnical\s+drawing\b", re.I), "TECHNICAL_DRAWING", 0.75),
    (re.compile(r"\bblueprint\b", re.I), "TECHNICAL_DRAWING", 0.65),
    (re.compile(r"\bschematic\b", re.I), "TECHNICAL_DRAWING", 0.55),
    (re.compile(r"\bphotograph\b", re.I), "PHOTOGRAPH", 0.75),
    (re.compile(r"\bphoto\b", re.I), "PHOTOGRAPH", 0.55),
    (re.compile(r"\bplate\b", re.I), "PLATE", 0.55),
]


class HeuristicVisualClassifier(VisualClassifier):
    """
    Deterministic rule-based visual classifier for mining & geological figures.
    Evaluates OCR content, caption headers, figure identifiers, and spatial layout signals.
    Applies calibrated confidence thresholds to route ambiguous figures to human verification.
    """
    classifier_name: str = "deterministic_heuristic"
    classifier_version: str = "1.1.0"
    is_available: bool = True

    def __init__(
        self,
        high_confidence_threshold: Optional[float] = None,
        low_confidence_threshold: Optional[float] = None,
    ):
        self.high_threshold = (
            high_confidence_threshold
            if high_confidence_threshold is not None
            else getattr(settings, "VISUAL_HIGH_CONFIDENCE_THRESHOLD", 0.70)
        )
        self.low_threshold = (
            low_confidence_threshold
            if low_confidence_threshold is not None
            else getattr(settings, "VISUAL_LOW_CONFIDENCE_THRESHOLD", 0.40)
        )

    def extract_caption_and_figure(self, text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Extracts figure numbering and caption text deterministically."""
        if not text:
            return None, None

        fig_num = None
        for pattern in FIGURE_NUMBER_PATTERNS:
            match = pattern.search(text)
            if match:
                fig_num = match.group(0).strip()
                break

        caption = None
        cap_match = CAPTION_PATTERN.search(text)
        if cap_match:
            raw_caption = cap_match.group(1).strip()
            if ". " in raw_caption:
                raw_caption = raw_caption[: raw_caption.index(". ") + 1]
            caption = raw_caption[:250]

        return fig_num, caption

    def classify(
        self,
        image_bytes: Optional[bytes] = None,
        caption: Optional[str] = None,
        page_text: Optional[str] = None,
        bbox: Optional[Dict[str, float]] = None,
        ocr_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        visual_asset_ref: Optional[str] = None,
    ) -> VisualClassificationResult:
        """
        Classifies figure based on multi-signal evidence without hallucination.
        """
        evidence: Dict[str, Any] = {
            "matched_rules": [],
            "matched_keywords": [],
            "caption_present": bool(caption),
            "ocr_present": bool(ocr_text),
            "spatial_signals": {},
        }

        # 1. Build composite search corpus from available text signals
        search_parts = []
        if caption:
            search_parts.append(caption)
        if ocr_text:
            search_parts.append(ocr_text[:500])
        if page_text:
            search_parts.append(page_text[:1000])

        combined_text = " ".join(search_parts).strip()

        # 2. Extract figure number if not already supplied
        fig_num, extracted_cap = self.extract_caption_and_figure(combined_text)
        if fig_num:
            evidence["detected_figure_number"] = fig_num
        if extracted_cap and not caption:
            evidence["detected_caption"] = extracted_cap

        # 3. Spatial / layout clues
        if bbox:
            w = abs(bbox.get("x1", 0.0) - bbox.get("x0", 0.0))
            h = abs(bbox.get("y1", 0.0) - bbox.get("y0", 0.0))
            if w > 0 and h > 0:
                aspect_ratio = round(w / h, 2)
                evidence["spatial_signals"] = {
                    "width": round(w, 1),
                    "height": round(h, 1),
                    "aspect_ratio": aspect_ratio,
                }

        # 4. Evaluate classification rules
        type_scores: Dict[str, float] = {}
        for pattern, vtype, base_conf in CLASSIFICATION_RULES:
            match = pattern.search(combined_text)
            if match:
                kw = match.group(0)
                evidence["matched_rules"].append(f"{vtype}:{kw}")
                if kw not in evidence["matched_keywords"]:
                    evidence["matched_keywords"].append(kw)

                # Incremental accumulation with saturation at 1.0
                current = type_scores.get(vtype, 0.0)
                type_scores[vtype] = min(1.0, current + base_conf * 0.6)

        # 5. Determine winning classification and confidence
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            best_conf = clamp_confidence(type_scores[best_type])
        else:
            best_type = "UNKNOWN"
            best_conf = 0.0
            evidence["reason"] = "No deterministic domain keywords or figure identifiers matched."

        # 6. Apply calibrated review workflow
        # High confidence -> ACCEPTED
        # Medium/Low confidence or UNKNOWN -> REVIEW_REQUIRED
        if best_type != "UNKNOWN" and best_conf >= self.high_threshold:
            review_status = ClassificationReviewStatus.ACCEPTED.value
        else:
            review_status = ClassificationReviewStatus.REVIEW_REQUIRED.value

        evidence["score_summary"] = {k: round(v, 4) for k, v in type_scores.items()}
        evidence["thresholds"] = {
            "high": self.high_threshold,
            "low": self.low_threshold,
        }

        return VisualClassificationResult(
            predicted_class=best_type,
            confidence=best_conf,
            classifier_name=self.classifier_name,
            classifier_version=self.classifier_version,
            review_status=review_status,
            evidence=evidence,
            visual_asset_ref=visual_asset_ref,
        )
