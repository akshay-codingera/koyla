import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def validate_stratum_metrics(
    depth_from_m: float,
    depth_to_m: float,
    stated_thickness_m: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Validates depth interval and computes thickness with deterministic discrepancy detection.
    Raises ValueError on invalid physics (negative depth or depth_to < depth_from).
    """
    if depth_from_m is None or depth_to_m is None:
        raise ValueError("depth_from_m and depth_to_m must not be None.")

    depth_from = float(depth_from_m)
    depth_to = float(depth_to_m)

    if depth_from < 0:
        raise ValueError(
            f"Invalid depth interval: depth_from_m cannot be negative (observed: {depth_from})"
        )

    if depth_to < depth_from:
        raise ValueError(
            f"Invalid depth interval: depth_to_m ({depth_to}) cannot be less than depth_from_m ({depth_from}). "
            f"depth_to_m must be greater than or equal to depth_from_m."
        )

    calculated_thickness = round(depth_to - depth_from, 3)

    has_discrepancy = False
    discrepancy_details = None

    if stated_thickness_m is not None:
        stated = float(stated_thickness_m)
        if stated < 0:
            raise ValueError(
                f"Invalid thickness: stated_thickness_m cannot be negative (observed: {stated})"
            )
        variance = round(stated - calculated_thickness, 3)
        diff_abs = round(abs(variance), 3)
        if diff_abs > 0.01:
            has_discrepancy = True
            discrepancy_details = {
                "stated_thickness_m": stated,
                "calculated_thickness_m": calculated_thickness,
                "variance_m": variance,
                "difference_m": diff_abs,
                "reason": (
                    f"Discrepancy detected: Stated thickness ({stated}m) differs from calculated "
                    f"depth interval ({calculated_thickness}m) by {variance}m."
                ),
                "warning": (
                    f"Stated thickness ({stated}m) differs from calculated "
                    f"depth interval ({calculated_thickness}m) by {variance}m."
                ),
            }
            logger.warning(
                f"Lithological stratum thickness discrepancy detected: {discrepancy_details['warning']}"
            )

    return {
        "depth_from_m": depth_from,
        "depth_to_m": depth_to,
        "thickness_m": calculated_thickness,
        "stated_thickness_m": float(stated_thickness_m) if stated_thickness_m is not None else None,
        "has_thickness_discrepancy": has_discrepancy,
        "discrepancy_details": discrepancy_details,
    }


def validate_strata_sequence(strata: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates the vertical sequence of extracted strata for a borehole.
    Checks that stratum_order increases with depth and flags overlapping or inverted intervals.
    """
    if not strata:
        return {"valid": True, "strata_count": 0, "anomalies": []}

    sorted_strata = sorted(strata, key=lambda s: s.get("stratum_order", 0))
    anomalies = []

    for i in range(1, len(sorted_strata)):
        prev = sorted_strata[i - 1]
        curr = sorted_strata[i]

        prev_to = prev.get("depth_to_m", 0.0)
        curr_from = curr.get("depth_from_m", 0.0)

        # Inverted depth sequence check
        if curr_from < prev.get("depth_from_m", 0.0):
            anomalies.append({
                "type": "INVERTED_DEPTH",
                "stratum_order": curr.get("stratum_order"),
                "message": (
                    f"Stratum {curr.get('stratum_order')} depth_from ({curr_from}m) is shallower "
                    f"than preceding stratum {prev.get('stratum_order')} ({prev.get('depth_from_m')}m)."
                ),
            })
        # Overlapping interval check
        elif curr_from < prev_to - 0.01:
            anomalies.append({
                "type": "OVERLAPPING_INTERVAL",
                "stratum_order": curr.get("stratum_order"),
                "message": (
                    f"Stratum {curr.get('stratum_order')} begins at {curr_from}m, "
                    f"overlapping preceding stratum ending at {prev_to}m."
                ),
            })
        # Depth gap check
        elif curr_from > prev_to + 0.05:
            anomalies.append({
                "type": "DEPTH_GAP",
                "stratum_order": curr.get("stratum_order"),
                "message": (
                    f"Depth gap detected: Stratum {curr.get('stratum_order')} begins at {curr_from}m, "
                    f"leaving a gap from preceding stratum ending at {prev_to}m."
                ),
            })

    is_valid = len(anomalies) == 0
    return {
        "valid": is_valid,
        "is_valid": is_valid,
        "strata_count": len(sorted_strata),
        "anomalies": anomalies,
        "issues": anomalies,
    }
