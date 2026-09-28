import io
import math
import os
import sys
import pytest
from PIL import Image
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import Settings
from app.models.visual import VisualAsset, VISUAL_TYPES
from app.models.verification import VerificationTask
from app.services.verification import VerificationService
from app.services.visual.base import (
    VisualClassifier,
    VisualClassificationResult,
    ClassificationReviewStatus,
)
from app.services.visual.heuristic_classifier import HeuristicVisualClassifier
from app.services.visual.domain_cv_classifier import DomainCVClassifier
from app.services.visual.factory import get_visual_classifier
from app.services.visual.robustness import (
    clamp_confidence,
    validate_bbox,
    safe_inspect_image_bytes,
)


# -----------------------------------------------------------------------------
# 1. Taxonomy & Base Contract Tests
# -----------------------------------------------------------------------------

def test_visual_taxonomy_exact_14_classes():
    """Approved visual taxonomy must contain exactly the 14 approved classes."""
    expected_classes = [
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
    assert len(VISUAL_TYPES) == 14
    for cls_name in expected_classes:
        assert cls_name in VISUAL_TYPES, f"Missing class in taxonomy: {cls_name}"


def test_visual_classification_result_validation():
    """Result validates taxonomy and clamps confidence."""
    # Valid high confidence
    res = VisualClassificationResult(
        predicted_class="MINE_PLAN",
        confidence=0.85,
        classifier_name="test_clf",
        classifier_version="1.0",
        review_status=ClassificationReviewStatus.ACCEPTED.value,
    )
    assert res.predicted_class == "MINE_PLAN"
    assert res.confidence == 0.85
    assert res.review_status == "ACCEPTED"

    # Out-of-taxonomy class falls back to UNKNOWN and forces REVIEW_REQUIRED
    res_invalid = VisualClassificationResult(
        predicted_class="SATELLITE_HYPERSPECTRAL_MAP",
        confidence=0.99,
        classifier_name="test_clf",
        classifier_version="1.0",
        review_status="ACCEPTED",
    )
    assert res_invalid.predicted_class == "UNKNOWN"
    assert res_invalid.review_status == "REVIEW_REQUIRED"

    # Confidence clamping
    res_clamp_high = VisualClassificationResult(
        predicted_class="MAP",
        confidence=1.45,
        classifier_name="test_clf",
        classifier_version="1.0",
        review_status="ACCEPTED",
    )
    assert res_clamp_high.confidence == 1.0

    res_clamp_low = VisualClassificationResult(
        predicted_class="MAP",
        confidence=-0.5,
        classifier_name="test_clf",
        classifier_version="1.0",
        review_status="ACCEPTED",
    )
    assert res_clamp_low.confidence == 0.0

    # Serialization
    d = res.to_dict()
    assert d["predicted_class"] == "MINE_PLAN"
    assert d["confidence"] == 0.85
    assert d["review_status"] == "ACCEPTED"
    assert "evidence" in d


# -----------------------------------------------------------------------------
# 2. Deterministic Heuristic Classifier Tests
# -----------------------------------------------------------------------------

def test_heuristic_classifier_high_confidence_acceptance():
    """Clear domain patterns yield high confidence and ACCEPTED status."""
    clf = HeuristicVisualClassifier()

    # Borehole Log
    res = clf.classify(
        caption="Figure 4: Borehole Log BH-204 lithological sequence",
        ocr_text="Drilling depth 150m, coal seam VI encountered at 45m depth",
    )
    assert res.predicted_class == "BOREHOLE_LOG"
    assert res.confidence >= 0.70
    assert res.review_status == ClassificationReviewStatus.ACCEPTED.value
    assert "detected_figure_number" in res.evidence
    assert res.evidence["detected_figure_number"] == "Figure 4"

    # Geological Map
    res_map = clf.classify(
        caption="Map 1: Geological Map of North Karanpura Coalfield",
        ocr_text="Scale 1:50000, Barakar formation outcrop boundary",
    )
    assert res_map.predicted_class == "MAP"
    assert res_map.confidence >= 0.70
    assert res_map.review_status == ClassificationReviewStatus.ACCEPTED.value


def test_heuristic_classifier_low_confidence_review_required():
    """Weak or ambiguous signals result in REVIEW_REQUIRED."""
    clf = HeuristicVisualClassifier()

    # Only generic "chart" mention
    res = clf.classify(caption="A chart showing values")
    assert res.predicted_class == "CHART"
    assert res.confidence < 0.70
    assert res.review_status == ClassificationReviewStatus.REVIEW_REQUIRED.value

    # Only generic "plot" mention
    res_plot = clf.classify(caption="Plot of samples")
    assert res_plot.predicted_class == "PLOT"
    assert res_plot.confidence < 0.70
    assert res_plot.review_status == ClassificationReviewStatus.REVIEW_REQUIRED.value


def test_heuristic_classifier_unknown_fallback():
    """Irrelevant page text with no visual keywords safely defaults to UNKNOWN."""
    clf = HeuristicVisualClassifier()
    res = clf.classify(
        page_text="The committee discussed financial statements and administrative directives in the meeting room."
    )
    assert res.predicted_class == "UNKNOWN"
    assert res.confidence == 0.0
    assert res.review_status == ClassificationReviewStatus.REVIEW_REQUIRED.value
    assert "No deterministic domain keywords" in res.evidence.get("reason", "")


def test_heuristic_spatial_layout_signals():
    """Spatial bounding box calculations provide aspect ratio evidence."""
    clf = HeuristicVisualClassifier()
    bbox = {"x0": 50.0, "y0": 100.0, "x1": 450.0, "y1": 300.0}
    res = clf.classify(caption="Plate II: Geological cross-section A-B", bbox=bbox)

    assert "spatial_signals" in res.evidence
    spatial = res.evidence["spatial_signals"]
    assert spatial["width"] == 400.0
    assert spatial["height"] == 200.0
    assert spatial["aspect_ratio"] == 2.0


def test_heuristic_custom_thresholds():
    """Classifier respects custom high/low thresholds."""
    # Stricter threshold of 0.90
    clf_strict = HeuristicVisualClassifier(high_confidence_threshold=0.90)
    res = clf_strict.classify(caption="Figure 1: Mine Plan layout")
    assert res.predicted_class == "MINE_PLAN"
    if res.confidence < 0.90:
        assert res.review_status == ClassificationReviewStatus.REVIEW_REQUIRED.value


# -----------------------------------------------------------------------------
# 3. Domain CV Classifier (Extension Point) Tests
# -----------------------------------------------------------------------------

def test_domain_cv_unconfigured_status():
    """Unconfigured DomainCVClassifier reports NOT_CONFIGURED and is_available=False."""
    cv_clf = DomainCVClassifier(model_path=None)
    assert not cv_clf.is_available

    health = cv_clf.health()
    assert health["status"] == "NOT_CONFIGURED"
    assert health["is_available"] is False
    assert "Future domain CV classifier" in health["message"]


def test_domain_cv_unavailable_when_weights_file_missing():
    """Reports UNAVAILABLE when model_path points to non-existent file."""
    cv_clf = DomainCVClassifier(model_path="/opt/models/non_existent_weights.onnx")
    assert not cv_clf.is_available

    health = cv_clf.health()
    assert health["status"] == "UNAVAILABLE"
    assert health["is_available"] is False


def test_domain_cv_configured_status(tmp_path):
    """Reports CONFIGURED when model weights file actually exists on disk."""
    fake_weights = tmp_path / "mining_geology_v1.onnx"
    fake_weights.write_bytes(b"MODEL_WEIGHTS_HEADER")

    cv_clf = DomainCVClassifier(model_path=str(fake_weights))
    assert cv_clf.is_available

    health = cv_clf.health()
    assert health["status"] == "CONFIGURED"
    assert health["is_available"] is True


def test_domain_cv_classify_fails_fast_when_unconfigured():
    """DomainCVClassifier refuses to classify when weights are missing."""
    cv_clf = DomainCVClassifier(model_path=None)
    with pytest.raises(RuntimeError) as exc_info:
        cv_clf.classify(caption="Some caption")
    assert "No trained model weights are provisioned" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 4. Factory & Configuration Tests
# -----------------------------------------------------------------------------

def test_visual_classifier_factory():
    """Factory correctly instantiates heuristic and domain_cv classifiers."""
    clf_h = get_visual_classifier("heuristic")
    assert isinstance(clf_h, HeuristicVisualClassifier)

    clf_cv = get_visual_classifier("domain_cv")
    assert isinstance(clf_cv, DomainCVClassifier)

    # Invalid classifier name raises ValueError
    with pytest.raises(ValueError) as exc:
        get_visual_classifier("yolo_v8_vision")
    assert "Invalid VISUAL_CLASSIFIER" in str(exc.value)


def test_security_validation_visual_classifier():
    """Settings security validation accepts only allowed classifiers."""
    s = Settings(
        SECRET_KEY="test-secret-key-at-least-32-chars-long",
        ENVIRONMENT="development",
        CORS_ORIGINS=["http://localhost:3000"],
        VISUAL_CLASSIFIER="heuristic",
    )
    s.validate_security()

    s_cv = Settings(
        SECRET_KEY="test-secret-key-at-least-32-chars-long",
        ENVIRONMENT="development",
        CORS_ORIGINS=["http://localhost:3000"],
        VISUAL_CLASSIFIER="domain_cv",
    )
    s_cv.validate_security()

    s_bad = Settings(
        SECRET_KEY="test-secret-key-at-least-32-chars-long",
        ENVIRONMENT="development",
        CORS_ORIGINS=["http://localhost:3000"],
        VISUAL_CLASSIFIER="external_openai_vision",
    )
    with pytest.raises(ValueError) as exc:
        s_bad.validate_security()
    assert "Invalid VISUAL_CLASSIFIER" in str(exc.value)


# -----------------------------------------------------------------------------
# 5. Robustness & Bounding Box Tests
# -----------------------------------------------------------------------------

def test_clamp_confidence():
    """Test confidence clamping across normal and edge case inputs."""
    assert clamp_confidence(0.75) == 0.75
    assert clamp_confidence(1.5) == 1.0
    assert clamp_confidence(-0.5) == 0.0
    assert clamp_confidence(float("nan")) == 0.0
    assert clamp_confidence(float("inf")) == 0.0
    assert clamp_confidence("invalid_str") == 0.0
    assert clamp_confidence(None) == 0.0


def test_validate_bbox():
    """Bounding box coordinates are normalized, cleaned, and inverted axes swapped."""
    # Standard valid bbox
    valid = validate_bbox({"x0": 10.5, "y0": 20.5, "x1": 100.5, "y1": 200.5})
    assert valid == {"x0": 10.5, "y0": 20.5, "x1": 100.5, "y1": 200.5}

    # Inverted coordinates: x0 > x1, y0 > y1
    inverted = validate_bbox({"x0": 150.0, "y0": 250.0, "x1": 50.0, "y1": 100.0})
    assert inverted == {"x0": 50.0, "y0": 100.0, "x1": 150.0, "y1": 250.0}

    # Negative coordinates clamped to 0.0
    negative = validate_bbox({"x0": -30.0, "y0": -15.0, "x1": 80.0, "y1": 90.0})
    assert negative == {"x0": 0.0, "y0": 0.0, "x1": 80.0, "y1": 90.0}

    # Page bound clamping
    out_of_bounds = validate_bbox(
        {"x0": 10.0, "y0": 20.0, "x1": 800.0, "y1": 1200.0},
        page_width=595.0,
        page_height=842.0,
    )
    assert out_of_bounds == {"x0": 10.0, "y0": 20.0, "x1": 595.0, "y1": 842.0}

    # Invalid non-numeric or NaN coordinates return None
    assert validate_bbox({"x0": "bad", "y0": 10.0, "x1": 20.0, "y1": 30.0}) is None
    assert validate_bbox({"x0": float("nan"), "y0": 10.0, "x1": 20.0, "y1": 30.0}) is None
    assert validate_bbox(None) is None


def test_safe_inspect_image_bytes():
    """Image byte inspection handles valid, empty, and corrupt inputs safely."""
    # Valid PNG bytes
    img = Image.new("RGB", (64, 48), color="green")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    valid_bytes = buf.getvalue()

    info = safe_inspect_image_bytes(valid_bytes)
    assert info["valid"] is True
    assert info["width"] == 64
    assert info["height"] == 48
    assert info["format"] == "PNG"
    assert info["error"] is None

    # Empty bytes
    empty_info = safe_inspect_image_bytes(b"")
    assert empty_info["valid"] is False
    assert empty_info["format"] == "NONE"

    # Corrupt bytes
    corrupt_info = safe_inspect_image_bytes(b"\x00\x01\x02\x03\x04corrupt_header_bytes")
    assert corrupt_info["valid"] is False
    assert corrupt_info["format"] == "CORRUPT"
    assert "Image parsing error" in corrupt_info["error"]


# -----------------------------------------------------------------------------
# 6. Human Verification Workflow Integration Tests
# -----------------------------------------------------------------------------

def test_verification_workflow_visual_review_approve():
    """APPROVE action on VISUAL_REVIEW task transitions VisualAsset to VERIFIED."""
    db = MagicMock()
    user_id = "test-user-id"

    mock_visual = MagicMock()
    mock_visual.id = "vis-001"
    mock_visual.visual_type = "MINE_PLAN"
    mock_visual.verification_status = "PENDING"
    mock_visual.classification_confidence = 0.65
    mock_visual.metadata_json = {}

    mock_task = MagicMock()
    mock_task.id = "task-001"
    mock_task.task_type = "VISUAL_REVIEW"
    mock_task.target_id = "vis-001"
    mock_task.field_id = None
    mock_task.reconciliation_group_id = None
    mock_task.organization_id = "CIL_HQ"

    db.query.return_value.filter.return_value.first.side_effect = [
        mock_task,    # db.query(VerificationTask)
        mock_visual,  # db.query(VisualAsset)
    ]

    with patch("app.services.verification.log_audit_event") as mock_audit:
        result = VerificationService.process_action(
            db=db,
            task_id="task-001",
            action="APPROVE",
            user_id=user_id,
            review_notes="Approved as correct mine plan.",
        )
        assert mock_visual.verification_status == "VERIFIED"
        assert mock_task.status == "APPROVED"
        mock_audit.assert_called_once()


def test_verification_workflow_visual_review_correct():
    """CORRECT action updates visual_type and preserves original classification in metadata."""
    db = MagicMock()
    user_id = "reviewer-uuid"

    mock_visual = MagicMock()
    mock_visual.id = "vis-002"
    mock_visual.visual_type = "UNKNOWN"
    mock_visual.verification_status = "PENDING"
    mock_visual.classification_confidence = 0.0
    mock_visual.metadata_json = {"detected_figure": "Fig 3"}

    mock_task = MagicMock()
    mock_task.id = "task-002"
    mock_task.task_type = "VISUAL_REVIEW"
    mock_task.target_id = "vis-002"
    mock_task.field_id = None
    mock_task.reconciliation_group_id = None
    mock_task.organization_id = "CMPDI_RI1"

    db.query.return_value.filter.return_value.first.side_effect = [
        mock_task,
        mock_visual,
    ]

    with patch("app.services.verification.log_audit_event"):
        VerificationService.process_action(
            db=db,
            task_id="task-002",
            action="CORRECT",
            user_id=user_id,
            corrected_value="GEOLOGICAL_SECTION",
            review_notes="Identified as geological cross section through seam III.",
        )

        assert mock_visual.visual_type == "GEOLOGICAL_SECTION"
        assert mock_visual.verification_status == "CORRECTED"
        assert mock_visual.metadata_json["original_classification"] == "UNKNOWN"
        assert mock_visual.metadata_json["original_confidence"] == 0.0
        assert mock_visual.metadata_json["corrected_by"] == user_id


def test_verification_workflow_visual_review_correct_invalid_taxonomy():
    """CORRECT action fails if corrected_value is not in the 14-class taxonomy."""
    db = MagicMock()
    mock_visual = MagicMock()
    mock_visual.id = "vis-003"
    mock_visual.visual_type = "UNKNOWN"

    mock_task = MagicMock()
    mock_task.id = "task-003"
    mock_task.task_type = "VISUAL_REVIEW"
    mock_task.target_id = "vis-003"
    mock_task.field_id = None
    mock_task.reconciliation_group_id = None

    db.query.return_value.filter.return_value.first.side_effect = [
        mock_task,
        mock_visual,
    ]

    with pytest.raises(ValueError) as exc:
        VerificationService.process_action(
            db=db,
            task_id="task-003",
            action="CORRECT",
            user_id="u1",
            corrected_value="INVALID_NON_EXISTENT_TYPE",
        )
    assert "Invalid visual type" in str(exc.value)
