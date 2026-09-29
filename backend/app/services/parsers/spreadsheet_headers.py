"""
Spreadsheet Hierarchical Header Propagation Service (Phase 11 P1-2)

Provides deterministic multi-row merged-header detection and propagation
for spreadsheet parsing (openpyxl XLSX, with graceful fallback for legacy formats).

Key Capabilities:
1. Merged cell range extraction:
   - Direct extraction from openpyxl Worksheet.merged_cells
   - High-speed XML extraction directly from .xlsx zip package for read_only streams
2. Deterministic header depth heuristic:
   - Evaluates horizontal and vertical merged cell boundaries in top rows
   - Distinguishes header descriptor text rows from numeric/record data rows
3. Multi-row hierarchical header propagation:
   - Propagates parent merged cell values across all child column spans
   - Supports 2, 3, or more header rows
   - Collapses consecutive duplicate labels from vertical merges (e.g. A1:A2 = "Mine")
   - Omits empty/blank levels without manufacturing placeholders (no "Production | None")
   - Preserves source language verbatim (Devanagari Hindi, English, mixed)
   - Disambiguates duplicate final column headers to preserve positional identity
"""

import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("app.services.parsers.spreadsheet_headers")


@dataclass
class MergedRange:
    """Represents a 1-indexed inclusive merged cell boundary."""
    min_row: int
    min_col: int
    max_row: int
    max_col: int
    value: Any = None

    def __str__(self) -> str:
        return f"R{self.min_row}C{self.min_col}:R{self.max_row}C{self.max_col}"


def col2idx(col_str: str) -> int:
    """Converts Excel column string (e.g. 'A', 'Z', 'AA') to 1-indexed int."""
    idx = 0
    for char in col_str.upper():
        if 'A' <= char <= 'Z':
            idx = idx * 26 + (ord(char) - ord('A') + 1)
    return max(1, idx)


def parse_cell_ref(ref: str) -> Tuple[int, int, int, int]:
    """
    Parses Excel cell reference string (e.g. 'B1:C1' or 'A1:A2' or 'B1')
    into 1-indexed (min_row, min_col, max_row, max_col).
    """
    parts = ref.split(":")
    m1 = re.match(r"^([A-Za-z]+)([0-9]+)$", parts[0].strip())
    if not m1:
        return 1, 1, 1, 1
    c1, r1 = col2idx(m1.group(1)), int(m1.group(2))

    if len(parts) > 1:
        m2 = re.match(r"^([A-Za-z]+)([0-9]+)$", parts[1].strip())
        if m2:
            c2, r2 = col2idx(m2.group(1)), int(m2.group(2))
        else:
            c2, r2 = c1, r1
    else:
        c2, r2 = c1, r1

    return min(r1, r2), min(c1, c2), max(r1, r2), max(c1, c2)


def extract_merged_ranges_from_worksheet(
    ws: Any,
    file_path: Optional[str] = None,
    sheet_name: Optional[str] = None,
    sheet_idx: Optional[int] = None
) -> List[MergedRange]:
    """
    Extracts all merged cell ranges from a worksheet.
    Tries openpyxl ws.merged_cells first; falls back to rapid zip inspection
    if in read_only streaming mode.
    """
    ranges: List[MergedRange] = []

    # 1. Try standard openpyxl worksheet.merged_cells
    merged_cells = getattr(ws, "merged_cells", None)
    if merged_cells is not None and hasattr(merged_cells, "ranges") and merged_cells.ranges:
        for r in merged_cells.ranges:
            ranges.append(MergedRange(
                min_row=r.min_row,
                min_col=r.min_col,
                max_row=r.max_row,
                max_col=r.max_col
            ))
        return ranges

    # 2. In read_only mode, openpyxl does not populate merged_cells.
    # Extract directly from zip XML without loading entire DOM.
    if file_path and Path(file_path).exists() and str(file_path).lower().endswith(".xlsx"):
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                target_xml = None
                if sheet_name:
                    if "xl/workbook.xml" in zf.namelist():
                        wb_xml = zf.read("xl/workbook.xml")
                        wb_root = ET.fromstring(wb_xml)
                        sheets = [e for e in wb_root.iter() if e.tag.endswith("sheet")]
                        for idx, s in enumerate(sheets, start=1):
                            if s.attrib.get("name") == sheet_name:
                                candidate = f"xl/worksheets/sheet{idx}.xml"
                                if candidate in zf.namelist():
                                    target_xml = candidate
                                break

                if not target_xml and sheet_idx is not None:
                    candidate = f"xl/worksheets/sheet{sheet_idx}.xml"
                    if candidate in zf.namelist():
                        target_xml = candidate

                if target_xml and target_xml in zf.namelist():
                    s_xml = zf.read(target_xml)
                    s_root = ET.fromstring(s_xml)
                    for elem in s_root.iter():
                        if elem.tag.endswith("mergeCell"):
                            ref = elem.attrib.get("ref")
                            if ref:
                                r1, c1, r2, c2 = parse_cell_ref(ref)
                                ranges.append(MergedRange(
                                    min_row=r1,
                                    min_col=c1,
                                    max_row=r2,
                                    max_col=c2
                                ))
        except Exception as e:
            logger.debug(f"Failed to read merged ranges from zip for {sheet_name}: {e}")

    return ranges


def is_data_row(row: List[Any]) -> bool:
    """
    Determines if a row is primarily data rather than header text.
    Data rows typically have numeric values (floats, ints, currency, percentages)
    or standard date patterns in multiple columns.
    """
    if not row or not any(c is not None and str(c).strip() for c in row):
        return False
    non_empty = [c for c in row if c is not None and str(c).strip()]
    if not non_empty:
        return False

    numeric_count = 0
    for cell in non_empty:
        s = str(cell).strip()
        cleaned = re.sub(r'^[₹$€£\s]+', '', s).replace(',', '').rstrip('%')
        try:
            float(cleaned)
            numeric_count += 1
        except ValueError:
            pass

    # If 40% or more of non-empty cells are numeric, this is a data row
    return (numeric_count / len(non_empty)) >= 0.40


def detect_header_depth(
    sample_rows: List[List[Any]],
    merged_ranges: List[MergedRange],
    max_search_depth: int = 6
) -> int:
    """
    Determines how many rows form the header block.
    Heuristic:
    1. If merged ranges exist in the top rows, header depth must cover at least the span
       of the horizontal merged header cells plus subsequent label rows before data begins.
    2. Header rows terminate when the first data row is encountered.
    3. If no merged cells exist in the top rows, defaults to 1.
    """
    if not sample_rows:
        return 1

    # Filter to merged ranges that touch the header region (rows 1..max_search_depth)
    header_merges = [
        r for r in merged_ranges
        if r.min_row <= max_search_depth and (r.max_col > r.min_col or r.max_row > r.min_row)
    ]

    if not header_merges:
        # Standard single-row header
        return 1

    max_merged_row = max((r.max_row for r in header_merges), default=1)

    # Find the first data row
    first_data_row_idx = None
    for idx, r in enumerate(sample_rows[:max_search_depth + 2]):
        row_num = idx + 1
        if is_data_row(r):
            first_data_row_idx = row_num
            break

    if first_data_row_idx is not None:
        depth = max(1, first_data_row_idx - 1)
        return min(depth, max_search_depth)

    return max(1, min(max_merged_row, max_search_depth))


def propagate_hierarchical_headers(
    header_rows: List[List[Any]],
    merged_ranges: List[MergedRange],
    separator: str = " | "
) -> Tuple[List[str], List[str]]:
    """
    Propagates parent merged-header values across child columns and generates
    normalized hierarchical headers.

    Returns:
        (hierarchical_headers, raw_headers)
    """
    if not header_rows:
        return [], []

    depth = len(header_rows)
    num_cols = max((len(r) for r in header_rows), default=0)
    if num_cols == 0:
        return [], []

    # 1. Build 2D grid of header cells [row_idx][col_idx]
    grid: List[List[Any]] = [
        [header_rows[r][c] if c < len(header_rows[r]) else None for c in range(num_cols)]
        for r in range(depth)
    ]

    # 2. Propagate merged ranges to fill unpopulated cells within the range
    for m in merged_ranges:
        if m.min_row <= depth:
            # Top-left cell value (1-indexed to 0-indexed)
            r_top = m.min_row - 1
            c_left = m.min_col - 1
            val = grid[r_top][c_left] if (r_top < depth and c_left < num_cols) else None

            if val is not None and str(val).strip():
                r_end = min(m.max_row, depth)
                c_end = min(m.max_col, num_cols)
                for r_idx in range(m.min_row - 1, r_end):
                    for c_idx in range(m.min_col - 1, c_end):
                        cur = grid[r_idx][c_idx]
                        if cur is None or not str(cur).strip():
                            grid[r_idx][c_idx] = val

    # 3. Assemble hierarchical headers for each column
    hierarchical_headers: List[str] = []
    raw_headers: List[str] = []
    seen_headers: Dict[str, int] = {}

    for c in range(num_cols):
        parts: List[str] = []
        for r in range(depth):
            val = str(grid[r][c]).strip() if grid[r][c] is not None else ""
            # Omit empty parts and collapse consecutive identical labels
            if val and (not parts or parts[-1] != val):
                parts.append(val)

        if parts:
            col_hdr = separator.join(parts)
        else:
            col_hdr = f"Col_{c + 1}"

        # Raw header represents the bottom-most / direct column label
        bottom_val = (
            str(header_rows[-1][c]).strip()
            if (c < len(header_rows[-1]) and header_rows[-1][c] is not None)
            else ""
        )
        raw_hdr = bottom_val if bottom_val else col_hdr
        raw_headers.append(raw_hdr)

        # Disambiguate duplicate final headers to preserve column identity
        if col_hdr in seen_headers:
            seen_headers[col_hdr] += 1
            disambiguated = f"{col_hdr} [col={c + 1}]"
        else:
            seen_headers[col_hdr] = 1
            disambiguated = col_hdr

        hierarchical_headers.append(disambiguated)

    return hierarchical_headers, raw_headers
