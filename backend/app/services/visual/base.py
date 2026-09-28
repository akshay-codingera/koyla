from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List

# Approved visual taxonomy — Phase 9 & Phase 7 standard
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


class ClassificationReviewStatus(str, Enum):
    """
    Review state for visual classifications.
    High confidence classifications are automatically accepted.
    Low/medium confidence or UNKNOWN classifications require human verification.
    """
    ACCEPTED = "ACCEPTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"
    VERIFIED = "VERIFIED"
    CORRECTED = "CORRECTED"


@dataclass
class VisualClassificationResult:
    """
    Standardized, provider-agnostic visual classification output.
    Captures prediction, calibrated confidence, audit signals, and human review requirements.
    """
    predicted_class: str
    confidence: float
    classifier_name: str
    classifier_version: str
    review_status: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    visual_asset_ref: Optional[str] = None

    def __post_init__(self):
        # Enforce taxonomy integrity: unknown types safely default to UNKNOWN
        if self.predicted_class not in VISUAL_TYPES:
            self.predicted_class = "UNKNOWN"
            self.review_status = ClassificationReviewStatus.REVIEW_REQUIRED.value

        # Clamp confidence to valid probability interval [0.0, 1.0]
        try:
            self.confidence = max(0.0, min(1.0, float(self.confidence)))
        except (ValueError, TypeError):
            self.confidence = 0.0

        # UNKNOWN classifications always require review
        if self.predicted_class == "UNKNOWN":
            self.review_status = ClassificationReviewStatus.REVIEW_REQUIRED.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predicted_class": self.predicted_class,
            "confidence": round(self.confidence, 4),
            "classifier_name": self.classifier_name,
            "classifier_version": self.classifier_version,
            "review_status": self.review_status,
            "evidence": self.evidence,
            "visual_asset_ref": self.visual_asset_ref,
        }


class VisualClassifier(ABC):
    """
    Abstract Visual Classifier Contract.
    Decouples visual element classification from detection and storage pipelines.
    Enables pluggable heuristic and future domain-specific computer vision classifiers.
    """
    classifier_name: str = "base"
    classifier_version: str = "1.0.0"
    is_available: bool = True

    @abstractmethod
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
        Classifies a visual asset based on available multi-modal signals:
        OCR text, caption, figure number, spatial layout, and image characteristics.
        """
        pass

    def health(self) -> Dict[str, Any]:
        """
        Returns structured health and operational status for the classifier.
        """
        return {
            "classifier_name": self.classifier_name,
            "classifier_version": self.classifier_version,
            "is_available": self.is_available,
            "status": "UP" if self.is_available else "UNAVAILABLE",
        }
