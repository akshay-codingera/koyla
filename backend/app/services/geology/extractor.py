import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.services.geology.normalizer import normalize_lithology_full
from app.services.geology.validator import validate_stratum_metrics

logger = logging.getLogger(__name__)

# Borehole ID detection patterns
BOREHOLE_ID_PATTERNS = [
    re.compile(r"\b(BH-TEST-[0-9]+)\b", re.IGNORECASE),
    re.compile(r"\b(BH[-_\s]*[0-9]+[A-Za-z0-9\-_\/]*)\b", re.IGNORECASE),
    re.compile(r"(?:Borehole(?:\s+No\.?|\s+ID|\s+Log|\s+Number)?|बोरहोल(?:\s+संख्या|\s+आईडी|\s+लॉग)?)\s*[:\-#]?\s*([A-Za-z0-9\-_\/]+)", re.IGNORECASE),
]

# Strata interval line pattern
# Matches lines like:
# "1. 0.0 - 2.5 m Top Soil"
# "0.0–2.5 m — Top Soil"
# "2.5 to 8.0 m Sandstone"
# "12.5 - 15.0 m Coal Seam IV"
# "0.0 - 2.5 मी. मिट्टी"
STRATA_LINE_PATTERN = re.compile(
    r"^\s*(?:(?:Stratum|Layer|संस्तर)\s+)?(?:(?P<order>\d+)[\.\:\)]\s*)?"
    r"(?P<from>\d+(?:\.\d+)?)\s*(?:-|–|—|\bto\b|\bसे\b)\s*"
    r"(?P<to>\d+(?:\.\d+)?)\s*(?:m|metres|meters|मी\.?|मीटर)?\s*"
    r"(?:\(\s*(?P<stated_thick>\d+(?:\.\d+)?)\s*(?:m|metres|meters|मी\.?|मीटर)?\)\s*)?"
    r"(?:[:\-—–|]\s*)?"
    r"(?P<lithology>[A-Za-z\u0900-\u097F0-9\s\(\)\/\.,_-]+?)"
    r"(?:\s*[:\-—–|]?\s*(?P<seam>(?:Seam|सीम)\s*[-_:]?\s*[A-Za-z0-9IVXLCDM\u0966-\u096F]+|[A-Za-z0-9IVXLCDM\u0966-\u096F]+\s*(?:Seam|सीम)))?"
    r"\s*$",
    re.IGNORECASE | re.UNICODE,
)


def extract_borehole_id_from_text(text: str) -> Optional[str]:
    """Scans text for explicit borehole identifiers."""
    if not text:
        return None
    for pattern in BOREHOLE_ID_PATTERNS:
        match = pattern.search(text)
        if match:
            bh_id = match.group(1).strip()
            if bh_id.lower() in ["log", "no", "id", "number", "संख्या", "लॉग"]:
                continue
            # Normalize internal spaces e.g. "BH 01" -> "BH-01"
            bh_id = re.sub(r"\s+", "-", bh_id)
            return bh_id
    return None


def extract_strata_from_text_lines(
    text: str,
    default_borehole_id: Optional[str] = None,
    page_number: Optional[int] = None,
    document_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Extracts ordered lithological strata lines from text.
    Handles English and Hindi/Devanagari intervals.
    """
    if not text:
        return []

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    extracted: List[Dict[str, Any]] = []

    # Detect borehole ID if not supplied
    bh_id = default_borehole_id or extract_borehole_id_from_text(text) or "BH-UNKNOWN"

    order_counter = 1

    for line in lines:
        # Check if line contains a new borehole declaration
        found_bh = extract_borehole_id_from_text(line)
        if found_bh and not default_borehole_id:
            bh_id = found_bh
            order_counter = 1
            continue

        match = STRATA_LINE_PATTERN.match(line)
        if not match:
            continue

        from_str = match.group("from")
        to_str = match.group("to")
        raw_litho = match.group("lithology")
        seam_match = match.group("seam")
        explicit_order = match.group("order")
        stated_str = match.group("stated_thick")
        stated_val = float(stated_str) if stated_str else None

        if not from_str or not to_str or not raw_litho:
            continue

        try:
            depth_from = float(from_str)
            depth_to = float(to_str)
            metrics = validate_stratum_metrics(depth_from, depth_to, stated_thickness_m=stated_val)
        except ValueError:
            # Skip invalid numbers or unphysical intervals
            continue

        # Normalize lithology and extract embedded seam name
        normalized_litho, cleaned_raw, inline_seam = normalize_lithology_full(raw_litho)
        final_seam = seam_match or inline_seam

        order_val = int(explicit_order) if explicit_order else order_counter
        order_counter = order_val + 1

        extracted.append({
            "borehole_id": bh_id,
            "stratum_order": order_val,
            "depth_from_m": metrics["depth_from_m"],
            "depth_to_m": metrics["depth_to_m"],
            "thickness_m": metrics["thickness_m"],
            "stated_thickness_m": metrics["stated_thickness_m"],
            "lithology_type": normalized_litho,
            "raw_lithology": cleaned_raw,
            "seam_name": final_seam,
            "page_number": page_number,
            "document_id": document_id,
            "source_text": line,
            "extraction_method": "RULE_BASED_TEXT",
            "confidence_score": 0.95,
            "has_thickness_discrepancy": metrics["has_thickness_discrepancy"],
            "discrepancy_details": metrics["discrepancy_details"],
        })

    return extracted


def extract_strata_from_table(
    table: Any,
    rows: List[Any],
    document_id: str,
    default_borehole_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Extracts lithological strata sequence from structured table rows.
    """
    if not table or not rows or not table.headers:
        return []

    headers = [str(h).lower().strip() for h in table.headers]
    
    # Identify column indices
    from_idx = None
    to_idx = None
    thick_idx = None
    litho_idx = None
    seam_idx = None
    order_idx = None

    for i, h in enumerate(headers):
        if any(kw in h for kw in ["from", "depth from", "गहराई से"]):
            from_idx = i
        elif any(kw in h for kw in ["to", "depth to", "गहराई तक"]):
            to_idx = i
        elif any(kw in h for kw in ["thickness", "thick", "मोटाई"]):
            thick_idx = i
        elif any(kw in h for kw in ["lithology", "strata", "rock", "formation", "संस्तर", "शैल"]):
            litho_idx = i
        elif any(kw in h for kw in ["seam", "coal seam", "सीम"]):
            seam_idx = i
        elif any(kw in h for kw in ["order", "sl", "s.no", "no", "क्रम"]):
            order_idx = i

    if from_idx is None or to_idx is None or litho_idx is None:
        return []

    bh_id = default_borehole_id
    if not bh_id and table.caption:
        bh_id = extract_borehole_id_from_text(table.caption)
    bh_id = bh_id or "BH-TABLE"

    extracted: List[Dict[str, Any]] = []
    order_counter = 1

    for row in rows:
        row_vals = []
        if hasattr(row, "cells") and isinstance(row.cells, list):
            row_vals = [c.get("text", "") if isinstance(c, dict) else str(c) for c in row.cells]
        elif hasattr(row, "row_values"):
            row_vals = row.row_values or []

        if len(row_vals) <= max(from_idx, to_idx, litho_idx):
            continue

        raw_from = str(row_vals[from_idx]).strip()
        raw_to = str(row_vals[to_idx]).strip()
        raw_litho = str(row_vals[litho_idx]).strip()
        raw_thick = str(row_vals[thick_idx]).strip() if thick_idx is not None and len(row_vals) > thick_idx else None
        raw_seam = str(row_vals[seam_idx]).strip() if seam_idx is not None and len(row_vals) > seam_idx else None
        raw_order = str(row_vals[order_idx]).strip() if order_idx is not None and len(row_vals) > order_idx else None

        # Clean numeric depth values
        clean_from = re.sub(r"[^\d\.]", "", raw_from)
        clean_to = re.sub(r"[^\d\.]", "", raw_to)
        clean_thick = re.sub(r"[^\d\.]", "", raw_thick) if raw_thick else None

        if not clean_from or not clean_to:
            continue

        try:
            depth_from = float(clean_from)
            depth_to = float(clean_to)
            stated_thick = float(clean_thick) if clean_thick else None
            metrics = validate_stratum_metrics(depth_from, depth_to, stated_thickness_m=stated_thick)
        except ValueError:
            continue

        normalized_litho, cleaned_raw, inline_seam = normalize_lithology_full(raw_litho)
        final_seam = raw_seam if (raw_seam and raw_seam not in ["-", "—", "N/A"]) else inline_seam

        order_val = int(raw_order) if (raw_order and raw_order.isdigit()) else order_counter
        order_counter = order_val + 1

        extracted.append({
            "borehole_id": bh_id,
            "stratum_order": order_val,
            "depth_from_m": metrics["depth_from_m"],
            "depth_to_m": metrics["depth_to_m"],
            "thickness_m": metrics["thickness_m"],
            "stated_thickness_m": metrics["stated_thickness_m"],
            "lithology_type": normalized_litho,
            "raw_lithology": cleaned_raw,
            "seam_name": final_seam,
            "page_number": table.page_number,
            "document_id": document_id,
            "table_id": table.id if hasattr(table, "id") else None,
            "row_id": row.id if hasattr(row, "id") else None,
            "source_text": " | ".join([str(v) for v in row_vals]),
            "extraction_method": "RULE_BASED_TABLE",
            "confidence_score": 0.98,
            "has_thickness_discrepancy": metrics["has_thickness_discrepancy"],
            "discrepancy_details": metrics["discrepancy_details"],
        })

    return extracted
