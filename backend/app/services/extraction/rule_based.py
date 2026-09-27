import re
from typing import List, Dict, Any, Optional, Tuple
from app.services.extraction.base import BaseExtractionProvider, FieldCandidate

class RuleBasedExtractionProvider(BaseExtractionProvider):
    """
    Deterministic rule-based extractor for geological, mining, and reporting domain fields.
    Extracts high-precision structured data from both text chunks and preserved tables
    while strictly guaranteeing physical source page provenance.
    """

    # Domain field regex patterns for unstructured text
    TEXT_PATTERNS = [
        # Identification
        {
            "field": "mine_name",
            "category": "IDENTIFICATION",
            "type": "STRING",
            "pattern": r"(?:Mine(?:\s+Name)?|Colliery|OCP|Mine\s+Block)\s*[:\-]?\s*([A-Za-z0-9\s\-]+?)(?=\n|,|\.|\;|\(|\)|$)",
            "unit": None,
            "confidence": 0.90,
        },
        {
            "field": "project_name",
            "category": "IDENTIFICATION",
            "type": "STRING",
            "pattern": r"(?:Project(?:\s+Name)?|Block(?:\s+Name)?)\s*[:\-]?\s*([A-Za-z0-9\s\-]+?Project|[A-Za-z0-9\s\-]+?Block|[A-Za-z0-9\s\-]+?Expansion)(?=\n|,|\.|\;|\(|\)|$)",
            "unit": None,
            "confidence": 0.88,
        },
        {
            "field": "fiscal_year",
            "category": "IDENTIFICATION",
            "type": "STRING",
            "pattern": r"(?:FY|Financial\s+Year)\s*[:\-]?\s*([0-9]{4}[-\/][0-9]{2,4})",
            "unit": None,
            "confidence": 0.95,
        },
        {
            "field": "reporting_period",
            "category": "IDENTIFICATION",
            "type": "STRING",
            "pattern": r"(?:Reporting\s+Period|For\s+the\s+period(?:\s+ending)?|Period)\s*[:\-]?\s*([A-Za-z0-9\s\-\/\.]+?)(?=\n|\.|\;|\(|$)",
            "unit": None,
            "confidence": 0.85,
        },
        # Geology / Exploration
        {
            "field": "formation",
            "category": "GEOLOGY",
            "type": "STRING",
            "pattern": r"\b(Barakar|Raniganj|Karharbari|Talchir|Damuda)(?:\s+Formation)?\b",
            "unit": None,
            "confidence": 0.92,
        },
        {
            "field": "seam",
            "category": "GEOLOGY",
            "type": "STRING",
            "pattern": r"(?:Coal\s+Seam|Seam(?:\s+Name)?)\s*[:\-]?\s*([A-Za-z0-9\-\s]+?)(?=\n|,|\.|\;|\(|$)",
            "unit": None,
            "confidence": 0.90,
        },
        {
            "field": "borehole_id",
            "category": "GEOLOGY",
            "type": "STRING",
            "pattern": r"(?:Borehole(?:\s+No\.?|\s+ID)?)\s*[:\-]?\s*([A-Z0-9\-\/]+)",
            "unit": None,
            "confidence": 0.95,
        },
        {
            "field": "drilling_metreage",
            "category": "GEOLOGY",
            "type": "NUMBER",
            "pattern": r"(?:Drilling\s+Metreage|Drilling\s+Meterage|Drilling\s+Depth|Borehole\s+Depth|Total\s+Metreage)\s*[:\-]?\s*([0-9\.,]+)\s*(m|metres|meters)",
            "unit_group": 2,
            "val_group": 1,
            "confidence": 0.92,
        },
        {
            "field": "reserves_proved",
            "category": "GEOLOGY",
            "type": "NUMBER",
            "pattern": r"(?:Proved\s+(?:Coal\s+)?Reserves?|Proved\s+Resource)\s*[:\-]?\s*([0-9\.,]+)\s*(MT|Million\s+Tonnes?|Tonnes?|tonnes?)",
            "unit_group": 2,
            "val_group": 1,
            "confidence": 0.92,
        },
        {
            "field": "reserves_indicated",
            "category": "GEOLOGY",
            "type": "NUMBER",
            "pattern": r"(?:Indicated\s+(?:Coal\s+)?Reserves?|Indicated\s+Resource)\s*[:\-]?\s*([0-9\.,]+)\s*(MT|Million\s+Tonnes?|Tonnes?|tonnes?)",
            "unit_group": 2,
            "val_group": 1,
            "confidence": 0.92,
        },
        {
            "field": "reserves_inferred",
            "category": "GEOLOGY",
            "type": "NUMBER",
            "pattern": r"(?:Inferred\s+(?:Coal\s+)?Reserves?|Inferred\s+Resource)\s*[:\-]?\s*([0-9\.,]+)\s*(MT|Million\s+Tonnes?|Tonnes?|tonnes?)",
            "unit_group": 2,
            "val_group": 1,
            "confidence": 0.92,
        },
        {
            "field": "reserves_total",
            "category": "GEOLOGY",
            "type": "NUMBER",
            "pattern": r"(?:Total\s+(?:Geological\s+)?Reserves?|Total\s+Coal\s+Resource)\s*[:\-]?\s*([0-9\.,]+)\s*(MT|Million\s+Tonnes?|Tonnes?|tonnes?)",
            "unit_group": 2,
            "val_group": 1,
            "confidence": 0.90,
        },
        {
            "field": "coal_grade",
            "category": "GEOLOGY",
            "type": "STRING",
            "pattern": r"(?:Coal\s+Grade|Grade)\s*[:\-]?\s*([A-G][0-9]{1,2}|W-[I-IV]+|Steel-[I-II]+|Non-coking\s+Grade\s+[A-G][0-9]{1,2})",
            "unit": None,
            "confidence": 0.92,
        },
        {
            "field": "gcv",
            "category": "GEOLOGY",
            "type": "NUMBER",
            "pattern": r"(?:GCV|Gross\s+Calorific\s+Value)\s*[:\-]?\s*([0-9\.,]+)\s*(kcal\/kg|Kcal\/Kg)",
            "unit_group": 2,
            "val_group": 1,
            "confidence": 0.92,
        },
        {
            "field": "ash_content",
            "category": "GEOLOGY",
            "type": "NUMBER",
            "pattern": r"(?:Ash\s+Content|Ash\s*%|Ash)\s*[:\-]?\s*([0-9\.,]+)\s*(%|percent)",
            "unit_group": 2,
            "val_group": 1,
            "confidence": 0.92,
        },
        # Mining / Production
        {
            "field": "production_quantity",
            "category": "MINING",
            "type": "NUMBER",
            "pattern": r"(?:Coal\s+Production|Actual\s+Production|Production\s+Achieved|Production)\s*[:\-]?\s*([0-9\.,]+)\s*(MT|Million\s+Tonnes?|Tonnes?|tonnes?|LT|Lakh\s+Tonnes?)",
            "unit_group": 2,
            "val_group": 1,
            "confidence": 0.92,
        },
        {
            "field": "target_quantity",
            "category": "MINING",
            "type": "NUMBER",
            "pattern": r"(?:Production\s+Target|Target\s+Production|Annual\s+Target|Target)\s*[:\-]?\s*([0-9\.,]+)\s*(MT|Million\s+Tonnes?|Tonnes?|tonnes?)",
            "unit_group": 2,
            "val_group": 1,
            "confidence": 0.90,
        },
        {
            "field": "dispatch_quantity",
            "category": "MINING",
            "type": "NUMBER",
            "pattern": r"(?:Coal\s+Dispatch|Dispatch|Offtake)\s*[:\-]?\s*([0-9\.,]+)\s*(MT|Million\s+Tonnes?|Tonnes?|tonnes?)",
            "unit_group": 2,
            "val_group": 1,
            "confidence": 0.90,
        },
        {
            "field": "stripping_ratio",
            "category": "MINING",
            "type": "NUMBER",
            "pattern": r"(?:Stripping\s+Ratio(?:\s*\(OB:Coal\))?|Composite\s+Stripping\s+Ratio)\s*[:\-]?\s*([0-9\.,]+)\s*(cum\/tonne|cum\/t|m3\/tonne|m3\/t|:1)?",
            "unit_group": 2,
            "val_group": 1,
            "default_unit": "m3/tonne",
            "confidence": 0.90,
        },
        {
            "field": "overburden_removal",
            "category": "MINING",
            "type": "NUMBER",
            "pattern": r"(?:Overburden\s+Removal|OB\s+Removal|Overburden)\s*[:\-]?\s*([0-9\.,]+)\s*(Mm3|Million\s+m3|m3|lakh\s+m3|cum)",
            "unit_group": 2,
            "val_group": 1,
            "confidence": 0.90,
        },
    ]

    # Table column mapping keywords to domain fields
    TABLE_HEADER_RULES = [
        {"field": "production_quantity", "category": "MINING", "type": "NUMBER", "unit": "MT", "keywords": ["production", "actual prod", "coal prod"]},
        {"field": "target_quantity", "category": "MINING", "type": "NUMBER", "unit": "MT", "keywords": ["target", "prod target", "planned prod"]},
        {"field": "dispatch_quantity", "category": "MINING", "type": "NUMBER", "unit": "MT", "keywords": ["dispatch", "offtake"]},
        {"field": "stripping_ratio", "category": "MINING", "type": "NUMBER", "unit": "m3/tonne", "keywords": ["stripping ratio", "sr (ob:coal)", "s.r."]},
        {"field": "overburden_removal", "category": "MINING", "type": "NUMBER", "unit": "Mm3", "keywords": ["overburden", "ob removal", "ob (mm3)"]},
        {"field": "reserves_proved", "category": "GEOLOGY", "type": "NUMBER", "unit": "MT", "keywords": ["proved reserve", "proved (mt)", "proved coal"]},
        {"field": "reserves_indicated", "category": "GEOLOGY", "type": "NUMBER", "unit": "MT", "keywords": ["indicated reserve", "indicated (mt)"]},
        {"field": "reserves_inferred", "category": "GEOLOGY", "type": "NUMBER", "unit": "MT", "keywords": ["inferred reserve", "inferred (mt)"]},
        {"field": "reserves_total", "category": "GEOLOGY", "type": "NUMBER", "unit": "MT", "keywords": ["total reserve", "total (mt)", "gross reserve"]},
        {"field": "drilling_metreage", "category": "GEOLOGY", "type": "NUMBER", "unit": "m", "keywords": ["drilling depth", "metreage", "meterage", "depth (m)"]},
        {"field": "coal_grade", "category": "GEOLOGY", "type": "STRING", "unit": None, "keywords": ["grade", "coal grade"]},
        {"field": "gcv", "category": "GEOLOGY", "type": "NUMBER", "unit": "kcal/kg", "keywords": ["gcv", "gross calorific value"]},
        {"field": "ash_content", "category": "GEOLOGY", "type": "NUMBER", "unit": "%", "keywords": ["ash %", "ash content", "ash percent"]},
        {"field": "seam", "category": "GEOLOGY", "type": "STRING", "unit": None, "keywords": ["seam", "seam name"]},
        {"field": "borehole_id", "category": "GEOLOGY", "type": "STRING", "unit": None, "keywords": ["borehole", "bh no", "bh id", "borehole no"]},
    ]

    def extract(
        self,
        chunks: List[Any],
        tables: List[Any],
        pages: List[Any]
    ) -> List[FieldCandidate]:
        candidates: List[FieldCandidate] = []
        
        # 1. Extract from text chunks
        for chunk in chunks:
            chunk_text = getattr(chunk, "content", "")
            chunk_page = getattr(chunk, "page_number", None)
            chunk_id = getattr(chunk, "id", None)
            
            for pat in self.TEXT_PATTERNS:
                regex = pat["pattern"]
                matches = list(re.finditer(regex, chunk_text, re.IGNORECASE))
                for match in matches:
                    if pat.get("val_group"):
                        raw_val = match.group(pat["val_group"]).strip()
                        raw_unit = match.group(pat["unit_group"]).strip() if pat.get("unit_group") and match.group(pat["unit_group"]) else pat.get("default_unit")
                    else:
                        raw_val = match.group(1).strip()
                        raw_unit = pat.get("unit")
                        
                    normalized_val, numeric_val = self._parse_value(raw_val, pat["type"])
                    
                    # Context snippet
                    start = max(0, match.start() - 40)
                    end = min(len(chunk_text), match.end() + 40)
                    snippet = chunk_text[start:end].replace("\n", " ").strip()
                    
                    score = pat["confidence"]
                    level = "HIGH" if score >= 0.85 else ("MEDIUM" if score >= 0.60 else "LOW")
                    
                    candidate = FieldCandidate(
                        field_name=pat["field"],
                        field_category=pat["category"],
                        data_type=pat["type"],
                        raw_value=raw_val,
                        normalized_value=str(normalized_val) if normalized_val is not None else None,
                        numeric_value=numeric_val,
                        unit=raw_unit,
                        page_number=chunk_page,
                        chunk_id=chunk_id,
                        source_text=f"...{snippet}...",
                        extraction_method="RULE_BASED",
                        confidence_score=score,
                        confidence_level=level,
                        metadata={"pattern": regex}
                    )
                    candidates.append(candidate)

        # 2. Extract from structured tables (preserving exact physical row page provenance)
        for table in tables:
            headers = getattr(table, "headers", [])
            rows = getattr(table, "table_rows", [])
            table_page = getattr(table, "page_number", 1)
            table_id = getattr(table, "id", None)
            
            if not headers or not rows:
                continue

            # Identify entity column (e.g. Mine, Seam, Borehole)
            entity_col_idx = None
            entity_col_name = None
            for idx, h in enumerate(headers):
                h_clean = str(h).strip().lower()
                if any(kw in h_clean for kw in ["mine", "project", "seam", "borehole", "block", "unit"]):
                    entity_col_idx = idx
                    entity_col_name = str(h).strip()
                    break

            # Map column indices to domain metrics
            col_mappings: List[Tuple[int, Dict[str, Any]]] = []
            for idx, h in enumerate(headers):
                h_clean = str(h).strip().lower()
                for rule in self.TABLE_HEADER_RULES:
                    if any(kw in h_clean for kw in rule["keywords"]):
                        # Extract unit from header if present e.g. "Production (MT)" or "Depth (m)"
                        detected_unit = rule.get("unit")
                        unit_match = re.search(r"\((.*?)\)", str(h))
                        if unit_match:
                            detected_unit = unit_match.group(1).strip()
                        
                        col_mappings.append((idx, {**rule, "detected_unit": detected_unit}))
                        break

            # Extract cell values from each row
            for row in rows:
                cells = getattr(row, "cells", [])
                # Crucial provenance rule: preserve exact physical row source page!
                row_page = getattr(row, "source_page", None) or table_page
                row_id = getattr(row, "id", None)
                
                if not cells or len(cells) != len(headers):
                    continue

                entity_name = str(cells[entity_col_idx]).strip() if entity_col_idx is not None and entity_col_idx < len(cells) else None

                for col_idx, rule in col_mappings:
                    if col_idx >= len(cells):
                        continue
                    cell_val = str(cells[col_idx]).strip()
                    if not cell_val or cell_val.lower() in ["nil", "na", "n/a", "-", "--", "none"]:
                        continue

                    normalized_val, numeric_val = self._parse_value(cell_val, rule["type"])
                    if normalized_val is None:
                        continue

                    # High confidence for clean table extraction
                    score = 0.95 if numeric_val is not None or rule["type"] == "STRING" else 0.75
                    level = "HIGH" if score >= 0.85 else "MEDIUM"
                    
                    # Format-aware coordinate provenance
                    tbl_meta = getattr(table, "metadata_json", {}) or {}
                    field_meta = {
                        "header": headers[col_idx],
                        "entity_name": entity_name,
                        "entity_col": entity_col_name,
                        "logical_table_id": getattr(table, "logical_table_id", None)
                    }
                    if tbl_meta.get("sheet_name"):
                        sheet = tbl_meta["sheet_name"]
                        col_letter = chr(ord('A') + min(col_idx, 25))
                        row_num = (getattr(row, "row_index", 1) or 1) + 1
                        field_meta["sheet_name"] = sheet
                        field_meta["cell_coordinate"] = f"{col_letter}{row_num}"
                        field_meta["provenance_display"] = f"Sheet: '{sheet}', Cell: '{col_letter}{row_num}'"
                    elif tbl_meta.get("format") == "CSV":
                        r_idx = getattr(row, "row_index", 1) or 1
                        field_meta["csv_row"] = r_idx
                        field_meta["csv_col"] = headers[col_idx]
                        field_meta["provenance_display"] = f"Row {r_idx}, Col '{headers[col_idx]}'"
                    
                    row_snippet = " | ".join(str(c) for c in cells)

                    candidate = FieldCandidate(
                        field_name=rule["field"],
                        field_category=rule["category"],
                        data_type=rule["type"],
                        raw_value=cell_val,
                        normalized_value=str(normalized_val) if normalized_val is not None else None,
                        numeric_value=numeric_val,
                        unit=rule.get("detected_unit"),
                        page_number=row_page,  # Guaranteed exact physical source page
                        table_id=table_id,
                        row_id=row_id,
                        source_text=f"Table Row: [{row_snippet}]",
                        extraction_method="RULE_BASED",
                        confidence_score=score,
                        confidence_level=level,
                        metadata=field_meta
                    )
                    candidates.append(candidate)

        return candidates

    def _parse_value(self, raw_str: str, data_type: str) -> Tuple[Optional[Any], Optional[float]]:
        """Parses and normalizes raw string values according to declared data type."""
        if not raw_str:
            return None, None
            
        clean_str = raw_str.strip()
        if data_type == "NUMBER":
            # Remove commas and non-numeric chars except dot and minus
            num_clean = re.sub(r"[^\d\.\-]", "", clean_str)
            try:
                val = float(num_clean)
                return val, val
            except (ValueError, TypeError):
                return None, None
        elif data_type == "DATE":
            return clean_str, None
        else: # STRING
            return clean_str, None
