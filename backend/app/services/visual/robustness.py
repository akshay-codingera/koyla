import io
import math
import logging
from typing import Optional, Dict, Any
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure PIL decompression bomb ceiling to protect against memory exhaustion attacks
try:
    max_pixels = getattr(settings, "VISUAL_MAX_IMAGE_PIXELS", 50_000_000)
    Image.MAX_IMAGE_PIXELS = max_pixels
except Exception:
    Image.MAX_IMAGE_PIXELS = 50_000_000


def clamp_confidence(conf: Any) -> float:
    """
    Safely clamps confidence scores strictly to the probability domain [0.0, 1.0].
    Handles NaNs, infinities, and invalid string inputs.
    """
    try:
        val = float(conf)
        if math.isnan(val) or math.isinf(val):
            return 0.0
        return max(0.0, min(1.0, val))
    except (ValueError, TypeError):
        return 0.0


def validate_bbox(
    bbox: Optional[Dict[str, Any]],
    page_width: Optional[float] = None,
    page_height: Optional[float] = None,
) -> Optional[Dict[str, float]]:
    """
    Validates and normalizes bounding box coordinates.
    Protects against negative, inverted, infinite, or malformed coordinates.
    """
    if not bbox or not isinstance(bbox, dict):
        return None

    try:
        x0 = float(bbox.get("x0", 0.0))
        y0 = float(bbox.get("y0", 0.0))
        x1 = float(bbox.get("x1", 0.0))
        y1 = float(bbox.get("y1", 0.0))
    except (ValueError, TypeError):
        logger.warning(f"Invalid non-numeric coordinates in bbox: {bbox}")
        return None

    for val in (x0, y0, x1, y1):
        if math.isnan(val) or math.isinf(val):
            return None

    # Fix inverted coordinates if necessary
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0

    # Ensure non-negative coordinates
    x0 = max(0.0, x0)
    y0 = max(0.0, y0)
    x1 = max(x0, x1)
    y1 = max(y0, y1)

    # Clamp to page bounds if provided
    if page_width and page_width > 0:
        x0 = min(x0, page_width)
        x1 = min(x1, page_width)
    if page_height and page_height > 0:
        y0 = min(y0, page_height)
        y1 = min(y1, page_height)

    return {
        "x0": round(x0, 2),
        "y0": round(y0, 2),
        "x1": round(x1, 2),
        "y1": round(y1, 2),
    }


def safe_inspect_image_bytes(image_bytes: Optional[bytes]) -> Dict[str, Any]:
    """
    Inspects image bytes safely without throwing unhandled exceptions.
    Detects corrupt headers, zero-byte buffers, and decompression threats.
    """
    if not image_bytes or len(image_bytes) == 0:
        return {
            "valid": False,
            "width": 0,
            "height": 0,
            "format": "NONE",
            "size_bytes": 0,
            "error": "Empty or missing image bytes"
        }

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()

        # Reopen after verify (verify closes stream in PIL)
        with Image.open(io.BytesIO(image_bytes)) as img:
            w, h = img.size
            fmt = str(img.format or "UNKNOWN")
            return {
                "valid": True,
                "width": w,
                "height": h,
                "format": fmt,
                "size_bytes": len(image_bytes),
                "error": None
            }
    except Image.DecompressionBombError as dbe:
        logger.warning(f"Decompression bomb blocked in visual processor: {dbe}")
        return {
            "valid": False,
            "width": 0,
            "height": 0,
            "format": "DECOMPRESSION_BOMB",
            "size_bytes": len(image_bytes),
            "error": "Image exceeds maximum allowed decompression pixel limit"
        }
    except Exception as e:
        logger.warning(f"Corrupt or unsupported image bytes: {e}")
        return {
            "valid": False,
            "width": 0,
            "height": 0,
            "format": "CORRUPT",
            "size_bytes": len(image_bytes),
            "error": f"Image parsing error: {str(e)}"
        }
