import re
from typing import Tuple, Optional

# Canonical lithology vocabulary mapping
LITHOLOGY_CANONICAL_MAP = {
    # Coal and Carbonaceous facies
    "carbonaceous shale": "Shale",
    "carb shale": "Shale",
    "carb. shale": "Shale",
    "coaly shale": "Shale",
    "shaly coal": "Coal",
    "shaley coal": "Coal",
    "coal": "Coal",
    # Sandstone facies
    "coarse grained sandstone": "Sandstone",
    "coarse sandstone": "Sandstone",
    "fine grained sandstone": "Sandstone",
    "fine-grained sandstone": "Sandstone",
    "fine sandstone": "Sandstone",
    "medium grained sandstone": "Sandstone",
    "medium sandstone": "Sandstone",
    "ferruginous sandstone": "Sandstone",
    "gritty sandstone": "Sandstone",
    "sandstone": "Sandstone",
    "sand stone": "Sandstone",
    # Shale & Mudstone facies
    "sandy shale": "Shale",
    "shale": "Shale",
    "siltstone": "Siltstone",
    "silt stone": "Siltstone",
    "clay": "Clay",
    "fireclay": "Fireclay",
    "mudstone": "Mudstone",
    # Top soil & Overburden
    "top soil": "Top Soil",
    "topsoil": "Top Soil",
    "soil": "Top Soil",
    "alluvium": "Alluvium",
    "overburden": "Overburden",
    # Devanagari Hindi mappings
    "कोयला": "Coal",
    "शेल": "Shale",
    "बलुआ पत्थर": "Sandstone",
    "सैंडस्टोन": "Sandstone",
    "सिल्टस्टोन": "Siltstone",
    "गाद पत्थर": "Siltstone",
    "गाद": "Siltstone",
    "मिट्टी": "Top Soil",
    "टॉप सॉइल": "Top Soil",
    "ओवरबर्डन": "Overburden",
    "क्ले": "Clay",
    "जलोढ़": "Alluvium",
}

SEAM_PATTERN = re.compile(
    r"(?:(?:Seam|सीम)\s*[-_:]?\s*([A-Za-z0-9IVXLCDM\u0966-\u096F]+)|\b([A-Za-z0-9IVXLCDM\u0966-\u096F]+)\s*(?:Seam|सीम))",
    re.IGNORECASE,
)


def extract_seam_and_lithology(raw_text: str) -> Tuple[Optional[str], str]:
    """
    Extracts seam name if embedded in the raw lithology text and returns
    (detected_seam_name, cleaned_raw_lithology).
    Example: 'Coal (Seam III Bottom)' -> ('Seam III Bottom', 'Coal')
             'कोयला (सीम II)' -> ('सीम II', 'कोयला')
    """
    if not raw_text:
        return None, ""

    cleaned = raw_text.strip()
    seam_name = None

    # Check for parenthesized seam first e.g. (Seam III) or (सीम II)
    paren_match = re.search(r"\(\s*((?:Seam|सीम)\s*[-_:]?\s*[A-Za-z0-9IVXLCDM\u0966-\u096F\s]+)\)", cleaned, re.IGNORECASE)
    if paren_match:
        seam_name = paren_match.group(1).strip()
        cleaned = cleaned.replace(paren_match.group(0), "").strip()
    else:
        match = SEAM_PATTERN.search(cleaned)
        if match:
            seam_id = match.group(1) or match.group(2)
            prefix = "सीम" if "सीम" in match.group(0) else "Seam"
            seam_name = f"{prefix} {seam_id.strip()}"
            cleaned = SEAM_PATTERN.sub("", cleaned).strip()

    # Clean punctuation and brackets
    cleaned = re.sub(r"[\s\-_:,\(\)]+$", "", cleaned).strip()
    cleaned = re.sub(r"^[\s\-_:,\(\)]+", "", cleaned).strip()

    return seam_name, cleaned


def normalize_lithology_full(raw_lithology: str) -> Tuple[str, str, Optional[str]]:
    """
    Deterministically normalizes lithology terminology.
    Returns: (normalized_lithology, cleaned_raw_lithology, extracted_seam_name)
    """
    if not raw_lithology:
        return "Unknown", "", None

    extracted_seam, cleaned_raw = extract_seam_and_lithology(raw_lithology)
    lookup_key = re.sub(r"\s+", " ", cleaned_raw.lower().strip())

    if lookup_key in LITHOLOGY_CANONICAL_MAP:
        normalized = LITHOLOGY_CANONICAL_MAP[lookup_key]
    else:
        # Check longest matching key first to avoid subword collisions (e.g. coal inside carb shale)
        matched = None
        for key, canonical in sorted(LITHOLOGY_CANONICAL_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if lookup_key == key or re.search(rf"\b{re.escape(key)}\b", lookup_key):
                matched = canonical
                break
        if matched:
            normalized = matched
        else:
            # Preserve original description without forcing into an incorrect category
            normalized = cleaned_raw.strip() if cleaned_raw else "Unknown"

    return normalized, cleaned_raw, extracted_seam


def normalize_lithology(raw_lithology: str) -> str:
    """
    Convenience function returning the normalized lithology category as a string.
    """
    normalized, _, _ = normalize_lithology_full(raw_lithology)
    return normalized
