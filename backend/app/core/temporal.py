import re
from typing import Tuple, Optional

def validate_fiscal_year_syntax(period: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Strict validator for financial year and reporting period syntax in KOYLA.
    Valid formats:
      - 'FY2023-24', 'FY 2023-24', 'FY2023-2024'
      - '2023-24', '2023-2024'
      - 'Q1 FY2023-24', 'Q2 FY2023-24', etc.
      - 'CY2023', '2023' (calendar year between 1950 and 2100)
    Rejects malformed strings like '2025-61', '2025-ba', 'FY2023-28'.
    Returns: (is_valid: bool, reason_or_normalized: Optional[str])
    """
    if not period or not isinstance(period, str):
        return False, "Period is empty or not a string"

    p = period.strip()

    # 1. FY YYYY-YY or YYYY-YY (e.g. FY2023-24 or 2023-24)
    m = re.match(r'^(?:(?:Q[1-4]|H[1-2])\s+)?(?:FY\s*)?(\d{4})[-/](\d{2})$', p, re.IGNORECASE)
    if m:
        start_year = int(m.group(1))
        end_yy = int(m.group(2))
        expected_yy = (start_year + 1) % 100
        if end_yy != expected_yy:
            return False, f"Invalid financial year rollover: '{p}' (expected {start_year:04d}-{expected_yy:02d}, got {start_year:04d}-{end_yy:02d})"
        if not (1950 <= start_year <= 2100):
            return False, f"Year out of operational range: {start_year}"
        return True, f"FY{start_year}-{expected_yy:02d}"

    # 2. FY YYYY-YYYY or YYYY-YYYY (e.g. FY2023-2024 or 2023-2024)
    m = re.match(r'^(?:(?:Q[1-4]|H[1-2])\s+)?(?:FY\s*)?(\d{4})[-/](\d{4})$', p, re.IGNORECASE)
    if m:
        start_year = int(m.group(1))
        end_year = int(m.group(2))
        if end_year != start_year + 1:
            return False, f"Invalid financial year rollover: '{p}' (expected {start_year}-{start_year+1}, got {start_year}-{end_year})"
        if not (1950 <= start_year <= 2100):
            return False, f"Year out of operational range: {start_year}"
        return True, f"FY{start_year}-{(start_year + 1) % 100:02d}"

    # 3. Calendar Year YYYY or CYYYYY
    m = re.match(r'^(?:CY\s*)?(\d{4})$', p, re.IGNORECASE)
    if m:
        year = int(m.group(1))
        if 1950 <= year <= 2100:
            return True, f"CY{year}"
        return False, f"Calendar year out of operational range: {year}"

    # 4. Standard categorical periods
    if p.lower() in ["lifetime", "cumulative", "current", "historical"]:
        return True, p.capitalize()

    return False, f"Malformed reporting period format: '{p}'"
