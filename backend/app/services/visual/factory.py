from typing import Optional
from app.core.config import settings
from app.services.visual.base import VisualClassifier
from app.services.visual.heuristic_classifier import HeuristicVisualClassifier
from app.services.visual.domain_cv_classifier import DomainCVClassifier

_heuristic_singleton: Optional[HeuristicVisualClassifier] = None
_domain_cv_singleton: Optional[DomainCVClassifier] = None


def get_visual_classifier(name: Optional[str] = None) -> VisualClassifier:
    """
    Factory function for resolving the active VisualClassifier.
    Enforces configuration-driven selection and fails fast on unsupported options.
    """
    global _heuristic_singleton, _domain_cv_singleton

    classifier_choice = (
        name.lower().strip()
        if name
        else getattr(settings, "VISUAL_CLASSIFIER", "heuristic").lower().strip()
    )

    if classifier_choice == "heuristic":
        if _heuristic_singleton is None:
            _heuristic_singleton = HeuristicVisualClassifier()
        return _heuristic_singleton
    elif classifier_choice == "domain_cv":
        if _domain_cv_singleton is None:
            _domain_cv_singleton = DomainCVClassifier()
        return _domain_cv_singleton
    else:
        raise ValueError(
            f"Invalid VISUAL_CLASSIFIER '{classifier_choice}'. "
            f"Supported visual classifiers: 'heuristic', 'domain_cv'."
        )
