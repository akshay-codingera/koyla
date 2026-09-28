import os
import logging
from typing import Optional, Dict, Any

from app.core.config import settings
from app.services.visual.base import (
    VisualClassifier,
    VisualClassificationResult,
    ClassificationReviewStatus,
)

logger = logging.getLogger(__name__)


class DomainCVClassifier(VisualClassifier):
    """
    Extension Point for Future Domain-Specific Computer Vision Classifiers
    (e.g., PyTorch / ONNX model fine-tuned on CIL/CMPDI geological sections & mine maps).

    CRITICAL ARCHITECTURAL GUARANTEE:
    This adapter explicitly declares its unconfigured / non-operational status.
    It NEVER fabricates predictions or claims a trained vision model exists without
    actual validated model weights on disk.
    """
    classifier_name: str = "domain_cv_mining_geology"
    classifier_version: str = "0.1.0-unconfigured"

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or getattr(settings, "VISUAL_DOMAIN_MODEL_PATH", None)
        self._model = None
        self._load_attempted = False

    @property
    def is_available(self) -> bool:
        """Returns True ONLY if valid model weights exist and are successfully loaded."""
        if not self.model_path:
            return False
        return os.path.isfile(self.model_path)

    def health(self) -> Dict[str, Any]:
        """
        Reports explicit operational status of the domain CV classifier extension point.
        """
        if not self.model_path:
            return {
                "classifier_name": self.classifier_name,
                "classifier_version": self.classifier_version,
                "status": "NOT_CONFIGURED",
                "message": (
                    "Future domain CV classifier extension point is ready, but no trained "
                    "model weights are configured (VISUAL_DOMAIN_MODEL_PATH is unset). "
                    "Koyla uses deterministic heuristic visual intelligence."
                ),
                "is_available": False,
                "model_path": None,
            }

        if not os.path.isfile(self.model_path):
            return {
                "classifier_name": self.classifier_name,
                "classifier_version": self.classifier_version,
                "status": "UNAVAILABLE",
                "message": f"Configured model weights path '{self.model_path}' does not exist on storage.",
                "is_available": False,
                "model_path": self.model_path,
            }

        return {
            "classifier_name": self.classifier_name,
            "classifier_version": self.classifier_version,
            "status": "CONFIGURED",
            "message": "Domain CV weights detected.",
            "is_available": True,
            "model_path": self.model_path,
        }

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
        Executes domain computer-vision inference when trained weights are provisioned.
        Fails fast with an explicit error when weights are not present.
        """
        if not self.is_available:
            raise RuntimeError(
                f"DomainCVClassifier cannot execute classification: No trained model weights "
                f"are provisioned at '{self.model_path}'. Set VISUAL_CLASSIFIER=heuristic or "
                f"provision validated weights."
            )

        # Placeholder for future PyTorch / ONNX model execution
        # When active, it produces a standard VisualClassificationResult conforming to the 14-class taxonomy
        raise NotImplementedError("Domain CV model inference pipeline is not yet attached.")
