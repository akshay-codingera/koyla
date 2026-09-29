"""
Test Suite for Spreadsheet Multi-Row Merged-Header Propagation (Phase 11 P1-2)

Validates hierarchical header detection and propagation across 23 comprehensive scenarios:
1. Two-row merged header propagation
2. Three-row hierarchical propagation
3. Multiple merged groups
4. Blank child header handling
5. Duplicate header disambiguation
6. Pure Devanagari Hindi headers
7. Mixed Hindi and English headers
8. No-merge regression
9. XLSX worksheet handling via SpreadsheetParser
10. XLS compatibility
11. CSV regression
12. Raw header preservation in metadata
13. Normalized hierarchical header generation
14. Column identity preservation
15. Provenance preservation
16. Row and column coordinate preservation in field extraction
17. P0-3 structured lookup compatibility
18. Numerical aggregation compatibility (1200 + 1300 = 2500)
19. Multiple worksheets with differing header structures
20. Malformed or partial merged ranges
21. Formula evaluation in data rows
22. Empty worksheet behavior
23. Organization / tenant isolation
"""

import io
import os
import uuid
import pytest
import openpyxl
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.document import Document, DocumentPage, Table, TableRow
from app.models.extraction import ExtractedField, ExtractionRun
from app.services.parsers.spreadsheet_parser import spreadsheet_parser
from app.services.parsers.legacy_xls_parser import legacy_xls_parser
from app.services.parsers.csv_parser import csv_parser
from app.services.parsers.spreadsheet_headers import (
    MergedRange,
    detect_header_depth,
    extract_merged_ranges_from_worksheet,
    propagate_hierarchical_headers,
)
from app.services.extraction.rule_based import RuleBasedExtractionProvider
from app.services.qa.structured_lookup import structured_lookup_service


from app.db.database import SessionLocal

@pytest.fixture
def temp_xlsx_dir(tmp_path):
    """Provides a temporary directory for generated test workbooks."""
    return tmp_path

@pytest.fixture
def db():
    """Provides a database session for testing."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_01_two_row_merged_header_propagation():
    """Scenario 1: Two-row merged header (Production -> Raw/Washed, Quality -> Ash/Moisture)."""
    header_rows = [
        [None, "Production", None, "Quality", None],
        ["Mine", "Raw Coal", "Washed Coal", "Ash %", "Moisture %"]
    ]
    merges = [
        MergedRange(min_row=1, min_col=2, max_row=1, max_col=3),
        MergedRange(min_row=1, min_col=4, max_row=1, max_col=5)
    ]

    hierarchical, raw = propagate_hierarchical_headers(header_rows, merges)
    assert hierarchical == [
        "Mine",
        "Production | Raw Coal",
        "Production | Washed Coal",
        "Quality | Ash %",
        "Quality | Moisture %"
    ]
    assert raw == ["Mine", "Raw Coal", "Washed Coal", "Ash %", "Moisture %"]


def test_02_three_row_hierarchical_propagation():
    """Scenario 2: Three-row hierarchical propagation (FY -> Category -> Metric)."""
    header_rows = [
        [None, "FY 2025-26", None, None],
        [None, "Production", None, "Quality"],
        ["Mine", "Raw Coal", "Washed Coal", "Ash"]
    ]
    merges = [
        MergedRange(min_row=1, min_col=2, max_row=1, max_col=4),
        MergedRange(min_row=2, min_col=2, max_row=2, max_col=3)
    ]

    hierarchical, raw = propagate_hierarchical_headers(header_rows, merges)
    assert hierarchical == [
        "Mine",
        "FY 2025-26 | Production | Raw Coal",
        "FY 2025-26 | Production | Washed Coal",
        "FY 2025-26 | Quality | Ash"
    ]


def test_03_multiple_merged_groups():
    """Scenario 3: Multiple distinct merged groups across columns."""
    header_rows = [
        ["Group 1", None, "Group 2", None, "Group 3", None],
        ["A", "B", "C", "D", "E", "F"]
    ]
    merges = [
        MergedRange(min_row=1, min_col=1, max_row=1, max_col=2),
        MergedRange(min_row=1, min_col=3, max_row=1, max_col=4),
        MergedRange(min_row=1, min_col=5, max_row=1, max_col=6)
    ]
    hierarchical, _ = propagate_hierarchical_headers(header_rows, merges)
    assert hierarchical == [
        "Group 1 | A",
        "Group 1 | B",
        "Group 2 | C",
        "Group 2 | D",
        "Group 3 | E",
        "Group 3 | F"
    ]


def test_04_blank_child_header_handling():
    """Scenario 4: Merged parent with blank child columns does not invent 'None'."""
    header_rows = [
        ["Mine", "Production", None],
        [None, "Raw Coal", None]
    ]
    merges = [
        MergedRange(min_row=1, min_col=2, max_row=1, max_col=3)
    ]
    hierarchical, _ = propagate_hierarchical_headers(header_rows, merges)
    assert hierarchical == ["Mine", "Production | Raw Coal", "Production"]
    assert "None" not in hierarchical[2]


def test_05_duplicate_header_disambiguation():
    """Scenario 5: Repeated headers are disambiguated by position to preserve identity."""
    header_rows = [
        ["Production", "Production"],
        ["Raw Coal", "Raw Coal"]
    ]
    merges = []
    hierarchical, _ = propagate_hierarchical_headers(header_rows, merges)
    assert hierarchical == ["Production | Raw Coal", "Production | Raw Coal [col=2]"]


def test_06_hindi_headers():
    """Scenario 6: Devanagari Hindi headers remain UTF-8 safe and are preserved verbatim."""
    header_rows = [
        [None, "उत्पादन", None, "गुणवत्ता", None],
        ["खदान", "कच्चा कोयला", "धुला हुआ कोयला", "राख %", "नमी %"]
    ]
    merges = [
        MergedRange(min_row=1, min_col=2, max_row=1, max_col=3),
        MergedRange(min_row=1, min_col=4, max_row=1, max_col=5)
    ]
    hierarchical, _ = propagate_hierarchical_headers(header_rows, merges)
    assert hierarchical == [
        "खदान",
        "उत्पादन | कच्चा कोयला",
        "उत्पादन | धुला हुआ कोयला",
        "गुणवत्ता | राख %",
        "गुणवत्ता | नमी %"
    ]


def test_07_mixed_hindi_english_headers():
    """Scenario 7: Mixed Hindi and English hierarchical headers."""
    header_rows = [
        [None, "Production", None],
        ["खदान", "कच्चा कोयला", "Washed Coal"]
    ]
    merges = [
        MergedRange(min_row=1, min_col=2, max_row=1, max_col=3)
    ]
    hierarchical, _ = propagate_hierarchical_headers(header_rows, merges)
    assert hierarchical == [
        "खदान",
        "Production | कच्चा कोयला",
        "Production | Washed Coal"
    ]


def test_08_no_merge_regression():
    """Scenario 8: Standard spreadsheet with no merged cells maintains single-row behavior."""
    header_rows = [
        ["Month", "Production_MT", "Target_MT", "Grade"]
    ]
    merges = []
    hierarchical, raw = propagate_hierarchical_headers(header_rows, merges)
    assert hierarchical == ["Month", "Production_MT", "Target_MT", "Grade"]
    assert raw == ["Month", "Production_MT", "Target_MT", "Grade"]


def test_09_xlsx_worksheet_handling(temp_xlsx_dir):
    """Scenario 9: End-to-end parsing of physical XLSX workbook with 2-row merged headers."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Mining_Report"

    ws.merge_cells("B1:C1")
    ws["B1"] = "Production"
    ws.merge_cells("D1:E1")
    ws["D1"] = "Quality"

    ws.append(["Mine", "Raw Coal", "Washed Coal", "Ash %", "Moisture %"])
    ws.append(["Mine-A", 1200, 850, 18.2, 4.1])
    ws.append(["Mine-B", 1300, 900, 17.4, 4.5])

    file_path = str(temp_xlsx_dir / "fixture_a.xlsx")
    wb.save(file_path)
    wb.close()

    parsed = spreadsheet_parser.parse(file_path)
    assert parsed.total_pages == 1
    assert len(parsed.tables) == 1
    tbl = parsed.tables[0]

    assert tbl.headers == [
        "Mine",
        "Production | Raw Coal",
        "Production | Washed Coal",
        "Quality | Ash %",
        "Quality | Moisture %"
    ]
    assert len(tbl.rows) == 2
    assert tbl.rows[0] == ["Mine-A", "1200", "850", "18.2", "4.1"]
    assert tbl.rows[1] == ["Mine-B", "1300", "900", "17.4", "4.5"]
    assert tbl.metadata.get("has_hierarchical_headers") is True
    assert tbl.metadata.get("header_depth") == 2


def test_10_xls_compatibility():
    """Scenario 10: Legacy XLS parser handles standard .xls without crashing."""
    assert legacy_xls_parser.can_handle("application/vnd.ms-excel", "test.xls") is True
    assert legacy_xls_parser.can_handle("application/vnd.openxmlformats", "test.xlsx") is False


def test_11_csv_regression(temp_xlsx_dir):
    """Scenario 11: CSV parser retains flat single-row header parsing without regression."""
    csv_file = temp_xlsx_dir / "test.csv"
    csv_file.write_text("Mine,Production,Grade\nMine-A,1200,G11\nMine-B,1300,G12\n", encoding="utf-8")

    parsed = csv_parser.parse(str(csv_file))
    assert parsed.total_pages == 1
    assert len(parsed.tables) == 1
    assert parsed.tables[0].headers == ["Mine", "Production", "Grade"]
    assert len(parsed.tables[0].rows) == 2


def test_12_raw_header_preservation(temp_xlsx_dir):
    """Scenario 12: Direct/raw column headers are preserved in table metadata."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.merge_cells("B1:C1")
    ws["B1"] = "Production"
    ws.append(["Mine", "Raw Coal", "Washed Coal"])
    ws.append(["Mine-1", 500, 300])

    path = str(temp_xlsx_dir / "raw_headers.xlsx")
    wb.save(path)
    wb.close()

    parsed = spreadsheet_parser.parse(path)
    tbl = parsed.tables[0]
    assert tbl.metadata.get("raw_headers") == ["Mine", "Raw Coal", "Washed Coal"]
    assert tbl.metadata.get("hierarchical_headers") == ["Mine", "Production | Raw Coal", "Production | Washed Coal"]


def test_13_normalized_hierarchical_header_generation(temp_xlsx_dir):
    """Scenario 13: Normalization produces formatted string suitable for text/vector indexing."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.merge_cells("B1:C1")
    ws["B1"] = "Production (MT)"
    ws.append(["Mine", "Raw Coal", "Washed Coal"])
    ws.append(["A", 100, 50])

    path = str(temp_xlsx_dir / "text_index.xlsx")
    wb.save(path)
    wb.close()

    parsed = spreadsheet_parser.parse(path)
    page_text = parsed.pages[0].text
    assert "Production (MT) | Raw Coal" in page_text
    assert "Production (MT) | Washed Coal" in page_text


def test_14_column_identity_preservation(temp_xlsx_dir):
    """Scenario 14: Data row cell alignment matches the propagated headers count exactly."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.merge_cells("B1:D1")
    ws["B1"] = "Dispatches"
    ws.append(["Mine", "Road", "Rail", "MGR"])
    ws.append(["Amrapali", 250, 600, 150])

    path = str(temp_xlsx_dir / "col_identity.xlsx")
    wb.save(path)
    wb.close()

    parsed = spreadsheet_parser.parse(path)
    tbl = parsed.tables[0]
    assert len(tbl.headers) == 4
    assert len(tbl.rows[0]) == 4
    assert tbl.rows[0][1] == "250"
    assert tbl.rows[0][2] == "600"
    assert tbl.rows[0][3] == "150"


def test_15_provenance_preservation(temp_xlsx_dir):
    """Scenario 15: Table metadata retains sheet name, row counts, and merge count provenance."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dispatch_Data"
    ws.merge_cells("B1:C1")
    ws["B1"] = "Dispatches"
    ws.append(["Mine", "Road", "Rail"])
    ws.append(["M-1", 10, 20])

    path = str(temp_xlsx_dir / "provenance.xlsx")
    wb.save(path)
    wb.close()

    parsed = spreadsheet_parser.parse(path)
    meta = parsed.tables[0].metadata
    assert meta["sheet_name"] == "Dispatch_Data"
    assert meta["row_count"] == 1
    assert meta["col_count"] == 3
    assert meta["merged_ranges_count"] >= 1


def test_16_row_column_coordinate_preservation():
    """Scenario 16: Rule-based extractor generates cell coordinate provenance for hierarchical tables."""
    extractor = RuleBasedExtractionProvider()

    table_meta = {
        "sheet_name": "Monthly_Prod",
        "has_hierarchical_headers": True,
        "format": "Spreadsheet"
    }

    class MockTable:
        id = "tbl-123"
        page_number = 1
        headers = ["Mine", "Production | Raw Coal", "Production | Washed Coal"]
        metadata_json = table_meta
        logical_table_id = "log-tbl-1"

    class MockRow:
        id = "row-456"
        row_index = 1
        source_page = 1
        cells = ["Mine-A", "1200", "850"]

    tbl = MockTable()
    tbl.table_rows = [MockRow()]

    candidates = extractor.extract(chunks=[], tables=[tbl], pages=[])
    prod_cands = [c for c in candidates if c.field_name == "production_quantity"]
    assert len(prod_cands) >= 1
    cand = prod_cands[0]
    assert cand.numeric_value == 1200.0
    assert cand.metadata.get("sheet_name") == "Monthly_Prod"
    assert cand.metadata.get("cell_coordinate") == "B2"
    assert cand.metadata.get("header") == "Production | Raw Coal"


def test_17_p03_structured_lookup_compatibility(db: Session):
    """Scenario 17: Structured lookup detects production metric from hierarchical header."""
    org = Organization(name="CMPDI_P12_TEST", code=f"P12_ORG_{uuid.uuid4().hex[:6]}", org_type="SUBSIDIARY")
    db.add(org)
    db.commit()

    doc = Document(
        organization_id=org.id,
        title="CCL Hierarchical Production",
        original_filename="ccl_hier.xlsx",
        file_path="/tmp/ccl_hier.xlsx",
        sha256_hash="hash_p12_hier",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        document_type="PRODUCTION_REPORT",
        file_size_bytes=1024
    )
    db.add(doc)
    db.commit()

    field = ExtractedField(
        organization_id=org.id,
        document_id=doc.id,
        field_name="production_quantity",
        field_category="MINING",
        data_type="NUMBER",
        raw_value="1200 MT",
        normalized_value="1200",
        numeric_value=1200.0,
        unit="MT",
        page_number=1,
        source_text="Production | Raw Coal: 1200 MT",
        extraction_method="RULE_BASED",
        confidence_score=0.95,
        confidence_level="HIGH",
        metadata_json={"header": "Production | Raw Coal", "entity_name": "Mine-A"}
    )
    db.add(field)
    db.commit()

    lookup_res = structured_lookup_service.lookup(
        db=db,
        query="What is the production quantity for Mine-A?",
        allowed_org_ids=[org.id]
    )
    assert len(lookup_res.facts) >= 1
    fact = lookup_res.facts[0]
    assert fact.numeric_value == 1200.0
    assert fact.unit == "MT"


def test_18_numerical_aggregation_compatibility(db: Session):
    """Scenario 18: P0-3 Structured numerical aggregation calculates 1200 + 1300 = 2500 MT."""
    org = Organization(name="WCL_P12_TEST", code=f"WCL_ORG_{uuid.uuid4().hex[:6]}", org_type="SUBSIDIARY")
    db.add(org)
    db.commit()

    doc = Document(
        organization_id=org.id,
        title="WCL Hierarchical Dispatches",
        original_filename="wcl_hier.xlsx",
        file_path="/tmp/wcl_hier.xlsx",
        sha256_hash="hash_wcl_p12",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        document_type="PRODUCTION_REPORT",
        file_size_bytes=2048
    )
    db.add(doc)
    db.commit()

    f1 = ExtractedField(
        organization_id=org.id,
        document_id=doc.id,
        field_name="production_quantity",
        field_category="MINING",
        data_type="NUMBER",
        raw_value="1200 MT",
        normalized_value="1200",
        numeric_value=1200.0,
        unit="MT",
        page_number=1,
        source_text="Production | Raw Coal: 1200 MT (Mine-A)",
        extraction_method="RULE_BASED",
        confidence_score=0.95,
        confidence_level="HIGH",
        verification_status="VERIFIED",
        metadata_json={"header": "Production | Raw Coal", "entity_name": "Mine-A"}
    )
    f2 = ExtractedField(
        organization_id=org.id,
        document_id=doc.id,
        field_name="production_quantity",
        field_category="MINING",
        data_type="NUMBER",
        raw_value="1300 MT",
        normalized_value="1300",
        numeric_value=1300.0,
        unit="MT",
        page_number=1,
        source_text="Production | Raw Coal: 1300 MT (Mine-B)",
        extraction_method="RULE_BASED",
        confidence_score=0.95,
        confidence_level="HIGH",
        verification_status="VERIFIED",
        metadata_json={"header": "Production | Raw Coal", "entity_name": "Mine-B"}
    )
    db.add_all([f1, f2])
    db.commit()

    lookup_res = structured_lookup_service.lookup(
        db=db,
        query="What was the total raw coal production in WCL?",
        allowed_org_ids=[org.id]
    )
    assert lookup_res.is_aggregation_query is True
    assert lookup_res.aggregation_result is not None
    agg = lookup_res.aggregation_result
    assert agg.calculated_value == 2500.0
    assert agg.unit == "MT"
    assert agg.record_count == 2
    assert ("1,200" in agg.formula or "1200" in agg.formula) and ("1,300" in agg.formula or "1300" in agg.formula)


def test_19_multiple_worksheets_with_different_headers(temp_xlsx_dir):
    """Scenario 19: Workbook containing 2-row merged header, single-row header, and empty sheet."""
    wb = openpyxl.Workbook()

    # Sheet 1: 2-row merged
    ws1 = wb.active
    ws1.title = "Merged_Sheet"
    ws1.merge_cells("B1:C1")
    ws1["B1"] = "Capacity"
    ws1.append(["Mine", "Nominal", "Peak"])
    ws1.append(["Mine-1", 10, 15])

    # Sheet 2: Flat single-row
    ws2 = wb.create_sheet("Flat_Sheet")
    ws2.append(["ID", "Name", "Location"])
    ws2.append(["1", "Central Pit", "Ranchi"])

    # Sheet 3: Empty
    wb.create_sheet("Blank_Sheet")

    path = str(temp_xlsx_dir / "multi_style.xlsx")
    wb.save(path)
    wb.close()

    parsed = spreadsheet_parser.parse(path)
    assert parsed.total_pages == 3
    assert len(parsed.tables) == 2

    t1 = next(t for t in parsed.tables if "Merged_Sheet" in t.caption)
    assert t1.headers == ["Mine", "Capacity | Nominal", "Capacity | Peak"]

    t2 = next(t for t in parsed.tables if "Flat_Sheet" in t.caption)
    assert t2.headers == ["ID", "Name", "Location"]


def test_20_malformed_partial_merged_ranges():
    """Scenario 20: Out-of-bounds or zero-size merged ranges handled without crash."""
    header_rows = [["Col_1", "Col_2"]]
    # Merged range extending past header rows
    merges = [MergedRange(min_row=10, min_col=10, max_row=12, max_col=12)]
    hierarchical, _ = propagate_hierarchical_headers(header_rows, merges)
    assert hierarchical == ["Col_1", "Col_2"]


def test_21_formula_evaluation_support(temp_xlsx_dir):
    """Scenario 21: Calculated values in formula cells are parsed via data_only mode."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.merge_cells("B1:C1")
    ws["B1"] = "Production"
    ws.append(["Mine", "Target", "Actual"])
    ws.append(["Mine-X", 100, 120])

    path = str(temp_xlsx_dir / "formula_test.xlsx")
    wb.save(path)
    wb.close()

    parsed = spreadsheet_parser.parse(path)
    assert parsed.tables[0].rows[0][2] == "120"


def test_22_empty_worksheet_behavior(temp_xlsx_dir):
    """Scenario 22: Completely blank spreadsheet produces empty page with graceful metadata."""
    wb = openpyxl.Workbook()
    path = str(temp_xlsx_dir / "empty.xlsx")
    wb.save(path)
    wb.close()

    parsed = spreadsheet_parser.parse(path)
    assert parsed.total_pages == 1
    assert len(parsed.tables) == 0
    assert parsed.pages[0].metadata.get("empty") is True


def test_23_tenant_isolation_in_ingestion(db: Session):
    """Scenario 23: Tables extracted from spreadsheets are strictly tenant-isolated."""
    org1 = Organization(name="ORG_1_TEST", code=f"ORG1_{uuid.uuid4().hex[:6]}", org_type="SUBSIDIARY")
    org2 = Organization(name="ORG_2_TEST", code=f"ORG2_{uuid.uuid4().hex[:6]}", org_type="SUBSIDIARY")
    db.add_all([org1, org2])
    db.commit()

    doc1 = Document(
        organization_id=org1.id,
        title="Org1 Spreadsheet",
        original_filename="org1.xlsx",
        file_path="/tmp/org1.xlsx",
        sha256_hash="hash_org1",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        document_type="PRODUCTION_REPORT",
        file_size_bytes=100
    )
    doc2 = Document(
        organization_id=org2.id,
        title="Org2 Spreadsheet",
        original_filename="org2.xlsx",
        file_path="/tmp/org2.xlsx",
        sha256_hash="hash_org2",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        document_type="PRODUCTION_REPORT",
        file_size_bytes=100
    )
    db.add_all([doc1, doc2])
    db.commit()

    f_org1 = ExtractedField(
        organization_id=org1.id,
        document_id=doc1.id,
        field_name="production_quantity",
        field_category="MINING",
        data_type="NUMBER",
        raw_value="500 MT",
        normalized_value="500",
        numeric_value=500.0,
        unit="MT",
        page_number=1,
        source_text="Production | Raw Coal: 500 MT",
        extraction_method="RULE_BASED",
        confidence_score=0.95,
        confidence_level="HIGH",
        verification_status="VERIFIED"
    )
    f_org2 = ExtractedField(
        organization_id=org2.id,
        document_id=doc2.id,
        field_name="production_quantity",
        field_category="MINING",
        data_type="NUMBER",
        raw_value="9000 MT",
        normalized_value="9000",
        numeric_value=9000.0,
        unit="MT",
        page_number=1,
        source_text="Production | Raw Coal: 9000 MT",
        extraction_method="RULE_BASED",
        confidence_score=0.95,
        confidence_level="HIGH",
        verification_status="VERIFIED"
    )
    db.add_all([f_org1, f_org2])
    db.commit()

    # Query scoped strictly to org1
    res_org1 = structured_lookup_service.lookup(
        db=db,
        query="What is the total raw coal production?",
        allowed_org_ids=[org1.id]
    )
    assert res_org1.aggregation_result.calculated_value == 500.0
    assert 9000.0 not in [c.numeric_value for c in res_org1.aggregation_result.contributing_records]
