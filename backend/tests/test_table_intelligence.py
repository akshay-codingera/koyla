import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import uuid
from app.services.parsers.base import ParsedTable, ParsedDocument, ParsedPage
from app.services.table_intelligence import table_intelligence_service
from app.services.chunking import ChunkingService
from app.models.organization import Organization
from app.models.document import Document, ProcessingJob, Table, TableRow
from app.models.verification import VerificationTask
from app.db.database import SessionLocal
from app.services.ingestion import process_document
from app.services.parsers.base import BaseParser

# 1. Single-page table
def test_single_page_table():
    table = ParsedTable(
        page_number=1,
        table_index=0,
        caption="Table 1: Seam Reserves",
        headers=["Seam", "Thickness (m)", "Ash %"],
        rows=[
            ["Seam I", "4.2", "18.5"],
            ["Seam II", "3.8", "21.0"],
            ["Seam III", "2.1", "16.4"],
        ]
    )
    result = table_intelligence_service.detect_continuations([table])
    
    assert len(result) == 1
    t = result[0]
    assert t.is_continuation is False
    assert t.continuation_status == "STANDALONE"
    assert t.part_number == 1
    assert t.total_parts == 1
    assert t.logical_table_id is not None
    assert t.row_pages == [1, 1, 1]

# 2. Two-page table continuation
def test_two_page_table_continuation():
    table1 = ParsedTable(
        page_number=1,
        table_index=0,
        caption="Coal Quality by Borehole",
        headers=["Borehole ID", "Depth (m)", "Ash %", "Moisture %"],
        rows=[
            ["BH-01", "102.5", "18.2", "2.4"],
            ["BH-02", "115.0", "19.5", "2.1"],
            ["BH-03", "128.4", "17.9", "2.6"],
        ]
    )
    table2 = ParsedTable(
        page_number=2,
        table_index=0,
        caption="Coal Quality by Borehole (contd.)",
        headers=["Borehole ID", "Depth (m)", "Ash %", "Moisture %"],
        rows=[
            ["BH-04", "142.1", "20.1", "2.0"],
            ["BH-05", "155.8", "21.4", "1.9"],
        ]
    )
    
    result = table_intelligence_service.detect_continuations([table1, table2])
    
    assert len(result) == 2
    part1, part2 = result[0], result[1]
    
    assert part1.logical_table_id == part2.logical_table_id
    assert part1.is_continuation is False
    assert part1.part_number == 1
    assert part1.total_parts == 2
    
    assert part2.is_continuation is True
    assert part2.continuation_status == "AUTO_MERGED"
    assert part2.part_number == 2
    assert part2.total_parts == 2
    assert part2.continuation_confidence >= 0.70
    assert part1.row_pages == [1, 1, 1]
    assert part2.row_pages == [2, 2]

# 3. Multi-page continuous table (3+ pages)
def test_multipage_continuous_table_three_plus_pages():
    p1 = ParsedTable(
        page_number=1,
        table_index=0,
        caption="Monthly Production Log",
        headers=["Month", "Target (MT)", "Actual (MT)"],
        rows=[["Apr", "1.2", "1.1"], ["May", "1.3", "1.3"]]
    )
    p2 = ParsedTable(
        page_number=2,
        table_index=0,
        caption="Monthly Production Log (Continued)",
        headers=["Month", "Target (MT)", "Actual (MT)"],
        rows=[["Jun", "1.2", "1.2"], ["Jul", "1.4", "1.3"]]
    )
    p3 = ParsedTable(
        page_number=3,
        table_index=0,
        caption="Monthly Production Log (cont.)",
        headers=["Month", "Target (MT)", "Actual (MT)"],
        rows=[["Aug", "1.5", "1.4"], ["Sep", "1.5", "1.6"]]
    )
    
    result = table_intelligence_service.detect_continuations([p1, p2, p3])
    
    assert len(result) == 3
    assert result[0].logical_table_id == result[1].logical_table_id == result[2].logical_table_id
    assert [r.part_number for r in result] == [1, 2, 3]
    assert [r.total_parts for r in result] == [3, 3, 3]
    assert result[0].is_continuation is False
    assert result[1].is_continuation is True
    assert result[2].is_continuation is True

# 4. Repeated-header continuation across pages
def test_repeated_header_continuation_across_pages():
    table1 = ParsedTable(
        page_number=1,
        table_index=0,
        caption="Geological Seam Intersections",
        headers=["Seam", "Thickness", "Grade"],
        rows=[
            ["Seam A", "3.2m", "G4"],
            ["Seam B", "4.1m", "G5"],
        ]
    )
    # Parser extracted repeated header as rows[0] on page 2
    table2 = ParsedTable(
        page_number=2,
        table_index=0,
        caption=None,
        headers=["Seam", "Thickness", "Grade"],
        rows=[
            ["Seam", "Thickness", "Grade"],  # Repeated header row!
            ["Seam C", "2.8m", "G3"],
            ["Seam D", "5.0m", "G4"],
        ]
    )
    
    result = table_intelligence_service.detect_continuations([table1, table2])
    
    part1, part2 = result[0], result[1]
    assert part1.logical_table_id == part2.logical_table_id
    assert part2.has_repeated_headers is True
    assert part2.is_continuation is True
    # Verify row 0 repeated header was stripped so rows are not duplicated
    assert len(part2.rows) == 2
    assert part2.rows[0] == ["Seam C", "2.8m", "G3"]
    assert part2.rows[1] == ["Seam D", "5.0m", "G4"]

# 5. Multiple separate tables on the same page
def test_multiple_separate_tables_on_same_page():
    t1 = ParsedTable(
        page_number=1,
        table_index=0,
        caption="Table 1: Seam Thickness",
        headers=["Seam", "Thickness"],
        rows=[["I", "2.5"], ["II", "3.0"]]
    )
    t2 = ParsedTable(
        page_number=1,
        table_index=1,
        caption="Table 2: Heavy Machinery",
        headers=["Equipment", "Units"],
        rows=[["Shovel 10m3", "4"], ["Dumper 100T", "18"]]
    )
    
    result = table_intelligence_service.detect_continuations([t1, t2])
    
    assert len(result) == 2
    assert result[0].logical_table_id != result[1].logical_table_id
    assert result[0].is_continuation is False
    assert result[1].is_continuation is False
    assert result[0].part_number == 1 and result[0].total_parts == 1
    assert result[1].part_number == 1 and result[1].total_parts == 1

# 6. Different tables on adjacent pages
def test_different_tables_on_adjacent_pages():
    # Case 6A: Ending safeguard (Table 1 ends with Total)
    t1 = ParsedTable(
        page_number=1,
        table_index=0,
        caption="Block A Reserves",
        headers=["Block", "Proved", "Indicated", "Total"],
        rows=[
            ["Sector 1", "12.5", "5.0", "17.5"],
            ["Grand Total", "12.5", "5.0", "17.5"],  # Total row marks end of table!
        ]
    )
    t2 = ParsedTable(
        page_number=2,
        table_index=0,
        caption="Block B Reserves",
        headers=["Block", "Proved", "Indicated", "Total"],
        rows=[
            ["Sector 2", "8.0", "3.5", "11.5"],
        ]
    )
    
    result = table_intelligence_service.detect_continuations([t1, t2])
    assert result[0].logical_table_id != result[1].logical_table_id
    assert result[1].is_continuation is False

    # Case 6B: Explicit distinct table numbers "Table 1" vs "Table 2"
    t3 = ParsedTable(
        page_number=1,
        table_index=0,
        caption="Table 1: Chemical Composition",
        headers=["Sample", "Carbon %", "Sulfur %"],
        rows=[["S-1", "65.4", "0.45"]]
    )
    t4 = ParsedTable(
        page_number=2,
        table_index=0,
        caption="Table 2: Petrographic Analysis",
        headers=["Sample", "Vitrinite %", "Inertinite %"],
        rows=[["S-1", "72.1", "21.4"]]
    )
    result2 = table_intelligence_service.detect_continuations([t3, t4])
    assert result2[0].logical_table_id != result2[1].logical_table_id
    assert result2[1].is_continuation is False

# 7. A new table beginning after a previous table
def test_new_table_beginning_after_previous_table():
    # Sequence:
    # Page 1: Seam Quality Part 1
    # Page 2: Seam Quality Part 2 (continuation)
    # Page 2: HEMM Fleet (different table on same page)
    t1 = ParsedTable(
        page_number=1,
        table_index=0,
        caption="Seam Quality Data",
        headers=["Seam", "GCV (kcal/kg)", "Ash %"],
        rows=[["Seam I", "4500", "22.5"]]
    )
    t2 = ParsedTable(
        page_number=2,
        table_index=0,
        caption="Seam Quality Data (contd.)",
        headers=["Seam", "GCV (kcal/kg)", "Ash %"],
        rows=[["Seam II", "4200", "26.0"]]
    )
    t3 = ParsedTable(
        page_number=2,
        table_index=1,
        caption="Table 3: HEMM Fleet",
        headers=["Model", "Count"],
        rows=[["CAT 777D", "12"]]
    )
    
    result = table_intelligence_service.detect_continuations([t1, t2, t3])
    
    assert len(result) == 3
    # t1 and t2 share logical table
    assert result[0].logical_table_id == result[1].logical_table_id
    assert result[1].is_continuation is True
    assert result[0].total_parts == 2
    assert result[1].total_parts == 2
    
    # t3 is standalone on Page 2
    assert result[2].logical_table_id != result[0].logical_table_id
    assert result[2].is_continuation is False
    assert result[2].part_number == 1 and result[2].total_parts == 1

# 8. Large logical tables split into processing chunks
def test_large_logical_table_split_into_chunks():
    # Create a 2-page logical table with 30 total rows
    t1 = ParsedTable(
        page_number=1,
        table_index=0,
        caption="Detailed Borehole Collar Survey",
        headers=["Borehole", "Easting", "Northing", "Elevation"],
        rows=[[f"BH-{i:03d}", f"{650000+i}", f"{2600000+i}", f"{250+i}"] for i in range(1, 16)],
        row_pages=[1] * 15
    )
    t2 = ParsedTable(
        page_number=2,
        table_index=0,
        caption="Detailed Borehole Collar Survey (contd.)",
        headers=["Borehole", "Easting", "Northing", "Elevation"],
        rows=[[f"BH-{i:03d}", f"{650000+i}", f"{2600000+i}", f"{250+i}"] for i in range(16, 31)],
        row_pages=[2] * 15
    )
    
    tables = table_intelligence_service.detect_continuations([t1, t2])
    
    doc = ParsedDocument(
        pages=[
            ParsedPage(page_number=1, text="", tables=[tables[0]]),
            ParsedPage(page_number=2, text="", tables=[tables[1]])
        ],
        total_pages=2,
        tables=tables
    )
    
    # Chunk with max 12 rows per chunk -> 30 rows = 3 chunks
    chunker = ChunkingService(max_table_rows_per_chunk=12)
    chunks = chunker.chunk_document(doc, "doc-large-tbl-123")
    
    table_chunks = [c for c in chunks if c.chunk_type == "TABLE"]
    assert len(table_chunks) == 3
    
    # Every chunk must preserve master headers and provenance tags
    for c in table_chunks:
        assert "Headers: Borehole | Easting | Northing | Elevation" in c.content
        assert c.metadata_json["logical_table_id"] == tables[0].logical_table_id
        assert c.metadata_json["total_parts"] == 3
        
    # Chunk 1 (rows 1-12) should have Page 1 provenance
    assert "[P.1] BH-001 | 650001" in table_chunks[0].content
    assert table_chunks[0].metadata_json["part"] == 1
    
    # Chunk 3 (rows 25-30) should have Page 2 provenance
    assert "[P.2] BH-030 | 650030" in table_chunks[2].content
    assert table_chunks[2].metadata_json["part"] == 3

# 9. Ambiguous continuation flags REVIEW_REQUIRED
def test_ambiguous_continuation_review_required():
    # Consecutive pages, identical column headers, but NO continuation caption cues or repeated row 0
    # Evaluates to score 0.55 (W_BASE 0.15 + W_HDR_IDENTICAL 0.20 + W_CTX_TOP 0.10 + W_ALIGN 0.10)
    # Must NOT auto-merge; must be marked REVIEW_REQUIRED with persisted signals
    t1 = ParsedTable(
        page_number=1,
        table_index=0,
        caption=None,
        headers=["Sample ID", "Depth (m)", "Density (g/cc)"],
        rows=[["S1", "10", "1.4"]]
    )
    t2 = ParsedTable(
        page_number=2,
        table_index=0,
        caption=None,
        headers=["Sample ID", "Depth (m)", "Density (g/cc)"],
        rows=[["S2", "20", "1.8"]]
    )
    
    result = table_intelligence_service.detect_continuations([t1, t2])
    assert len(result) == 2
    # Must NOT be auto-merged silently!
    assert result[0].logical_table_id != result[1].logical_table_id
    assert result[1].is_continuation is False
    assert result[1].continuation_status == "REVIEW_REQUIRED"
    assert 0.35 <= result[1].continuation_confidence < 0.70
    assert "continuation_signals" in result[1].metadata
    assert result[1].metadata["continuation_signals"]["hard_gate_passed"] is True

# 10. Database persistence and API verification of continuous table
def test_database_table_continuation_persistence():
    db = SessionLocal()
    org = db.query(Organization).first()
    assert org is not None
    
    doc = Document(
        organization_id=org.id,
        title="Test Continuous Table Ingestion",
        document_type="GEOLOGICAL_REPORT",
        source_tier="TIER_A",
        original_filename="test_tables.pdf",
        file_path="demo_data/geological_summary_bccl.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash=uuid.uuid4().hex,
        status="QUEUED"
    )
    db.add(doc)
    db.commit()
    
    job = ProcessingJob(
        document_id=doc.id,
        job_type="INGESTION",
        status="QUEUED"
    )
    db.add(job)
    db.commit()
    
    # Build two-part continuous table
    p1 = ParsedTable(
        page_number=1,
        table_index=0,
        caption="Borehole Assay Ledger",
        headers=["BH", "Lithology", "Recovery %"],
        rows=[["BH-10", "Sandstone", "95%"], ["BH-11", "Shale", "90%"]]
    )
    p2 = ParsedTable(
        page_number=2,
        table_index=0,
        caption="Borehole Assay Ledger (contd.)",
        headers=["BH", "Lithology", "Recovery %"],
        rows=[["BH-12", "Coal Seam I", "98%"], ["BH-13", "Carbonaceous Shale", "88%"]]
    )
    
    # Mock parser for this test
    class MockTableParser(BaseParser):
        def can_handle(self, mime_type, filename): return True
        def parse(self, file_path):
            return ParsedDocument(
                pages=[
                    ParsedPage(page_number=1, text="Page 1 text", tables=[p1]),
                    ParsedPage(page_number=2, text="Page 2 text", tables=[p2])
                ],
                total_pages=2,
                tables=[p1, p2]
            )
            
    from unittest.mock import patch
    with patch("app.services.ingestion.get_parser_for_file", return_value=MockTableParser()):
        process_document(doc.id, job.id)
        
    db.refresh(doc)
    assert doc.status == "COMPLETED"
    
    # Query tables in database
    db_tables = db.query(Table).filter(Table.document_id == doc.id).order_by(Table.page_number.asc()).all()
    assert len(db_tables) == 2
    t_part1, t_part2 = db_tables[0], db_tables[1]
    
    assert t_part1.logical_table_id == t_part2.logical_table_id
    assert t_part1.part_number == 1
    assert t_part2.part_number == 2
    assert t_part1.total_parts == 2
    assert t_part2.total_parts == 2
    assert t_part2.is_continuation is True
    assert t_part2.continuation_of_id == t_part1.id
    assert t_part2.continuation_status == "AUTO_MERGED"
    
    # Check rows in database
    rows_p1 = db.query(TableRow).filter(TableRow.table_id == t_part1.id).order_by(TableRow.row_index.asc()).all()
    rows_p2 = db.query(TableRow).filter(TableRow.table_id == t_part2.id).order_by(TableRow.row_index.asc()).all()
    
    assert len(rows_p1) == 2
    assert len(rows_p2) == 2
    
    # Check logical row indexing continuity (1, 2, 3, 4)
    assert [r.logical_row_index for r in rows_p1] == [1, 2]
    assert [r.logical_row_index for r in rows_p2] == [3, 4]
    
    # Check physical source page provenance
    assert [r.source_page for r in rows_p1] == [1, 1]
    assert [r.source_page for r in rows_p2] == [2, 2]
    
    db.close()

# 11. No-header continuation works
def test_no_header_continuation():
    t1 = ParsedTable(
        page_number=1,
        table_index=0,
        caption="Heavy Earth Moving Machinery (HEMM) Deployment",
        headers=["Equipment Type", "Model", "Capacity", "Operational Count"],
        rows=[
            ["Dump Truck", "CAT 777D", "100 Ton", "14"],
            ["Hydraulic Shovel", "Komatsu PC2000", "12 Cu.M", "3"]
        ]
    )
    # Headless continuation on Page 2 (no headers extracted, top of page, continuation caption)
    t2 = ParsedTable(
        page_number=2,
        table_index=0,
        caption="HEMM Deployment (contd.)",
        headers=[],  # Headless!
        rows=[
            ["Wheel Loader", "CAT 988H", "6.4 Cu.M", "5"],
            ["Dozer", "BEML BD355", "410 HP", "6"]
        ]
    )
    
    result = table_intelligence_service.detect_continuations([t1, t2])
    assert len(result) == 2
    assert result[0].logical_table_id == result[1].logical_table_id
    assert result[1].is_continuation is True
    assert result[1].continuation_status == "AUTO_MERGED"
    # Headers must be inherited from predecessor
    assert result[1].headers == t1.headers
    assert result[0].total_parts == 2
    assert result[1].total_parts == 2

# 12. Identical headers alone must NEVER cause two separate tables to merge
def test_identical_header_separate_tables_remain_separate():
    # Identical headers on adjacent pages, but distinct non-continuation captions
    t1 = ParsedTable(
        page_number=1,
        table_index=0,
        caption="Procurement Summary: Mechanical Spares",
        headers=["Item Code", "Description", "Quantity", "Unit Rate (INR)"],
        rows=[["M-101", "Bearing Assembly", "50", "12500"]]
    )
    t2 = ParsedTable(
        page_number=2,
        table_index=0,
        caption="Procurement Summary: Electrical Spares",
        headers=["Item Code", "Description", "Quantity", "Unit Rate (INR)"],
        rows=[["E-201", "Transformer Coil", "4", "450000"]]
    )
    
    result = table_intelligence_service.detect_continuations([t1, t2])
    assert len(result) == 2
    # Distinct captions without continuation cues must NOT merge
    assert result[0].logical_table_id != result[1].logical_table_id
    assert result[1].is_continuation is False
    assert result[1].continuation_status == "STANDALONE"

# 13. Physical and Logical views both work via API
def test_physical_and_logical_api_views():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token
    from datetime import timedelta
    
    client = TestClient(app)
    db = SessionLocal()
    org = db.query(Organization).first()
    
    doc = Document(
        organization_id=org.id,
        title="Test API View Slices",
        document_type="PRODUCTION_REPORT",
        source_tier="TIER_A",
        original_filename="api_views_test.pdf",
        file_path="demo_data/geological_summary_bccl.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
        sha256_hash=uuid.uuid4().hex,
        status="COMPLETED"
    )
    db.add(doc)
    db.commit()
    
    log_id = str(uuid.uuid4())
    # Physical Table Slice 1
    t1 = Table(
        document_id=doc.id,
        page_number=1,
        table_index=0,
        caption="Quarterly Coal Despatch",
        headers=["Sector", "Target (MT)", "Actual (MT)"],
        row_count=2,
        col_count=3,
        logical_table_id=log_id,
        is_continuation=False,
        part_number=1,
        total_parts=2,
        continuation_status="AUTO_MERGED"
    )
    db.add(t1)
    db.flush()
    
    db.add(TableRow(table_id=t1.id, row_index=1, logical_row_index=1, source_page=1, cells=["Power", "10.0", "9.8"]))
    db.add(TableRow(table_id=t1.id, row_index=2, logical_row_index=2, source_page=1, cells=["Steel", "4.0", "3.9"]))
    
    # Physical Table Slice 2
    t2 = Table(
        document_id=doc.id,
        page_number=2,
        table_index=0,
        caption="Quarterly Coal Despatch (contd.)",
        headers=["Sector", "Target (MT)", "Actual (MT)"],
        row_count=1,
        col_count=3,
        logical_table_id=log_id,
        is_continuation=True,
        continuation_of_id=t1.id,
        part_number=2,
        total_parts=2,
        continuation_status="AUTO_MERGED"
    )
    db.add(t2)
    db.flush()
    
    db.add(TableRow(table_id=t2.id, row_index=1, logical_row_index=3, source_page=2, cells=["Cement", "2.5", "2.6"]))
    db.commit()
    
    # Token for HQ officer
    token = create_access_token(subject="hq_officer", expires_delta=timedelta(minutes=60))
    
    # 1. Physical View
    res_phys = client.get(f"/api/v1/documents/{doc.id}/tables?view=physical", headers={"Authorization": f"Bearer {token}"})
    assert res_phys.status_code == 200
    phys_data = res_phys.json()
    assert len(phys_data) == 2
    assert phys_data[0]["page_number"] == 1 and phys_data[0]["row_count"] == 2
    assert phys_data[1]["page_number"] == 2 and phys_data[1]["row_count"] == 1
    
    # 2. Logical View
    res_log = client.get(f"/api/v1/documents/{doc.id}/tables?view=logical", headers={"Authorization": f"Bearer {token}"})
    assert res_log.status_code == 200
    log_data = res_log.json()
    assert len(log_data) == 1
    log_tbl = log_data[0]
    assert log_tbl["logical_table_id"] == log_id
    assert log_tbl["total_parts"] == 2
    assert log_tbl["row_count"] == 3
    assert log_tbl["spanned_pages"] == [1, 2]
    assert len(log_tbl["physical_slices"]) == 2
    # Verify row provenance in logical view
    assert log_tbl["row_details"][0]["source_page"] == 1
    assert log_tbl["row_details"][2]["source_page"] == 2
    assert [r["logical_row_index"] for r in log_tbl["row_details"]] == [1, 2, 3]
    
    db.close()

# 14. Ambiguous case creates VerificationTask with persisted signal evidence
def test_ambiguous_case_creates_verification_task_with_evidence():
    db = SessionLocal()
    org = db.query(Organization).first()
    
    doc = Document(
        organization_id=org.id,
        title="Test Ambiguous Continuation Task",
        document_type="GEOLOGICAL_REPORT",
        source_tier="TIER_B",
        original_filename="ambiguous_doc.pdf",
        file_path="demo_data/geological_summary_bccl.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash=uuid.uuid4().hex,
        status="QUEUED"
    )
    db.add(doc)
    db.commit()
    
    job = ProcessingJob(
        document_id=doc.id,
        job_type="INGESTION",
        status="QUEUED"
    )
    db.add(job)
    db.commit()
    
    # Candidate tables yielding score in [0.35, 0.70)
    # Identical headers on consecutive pages, but NO continuation cues (caption=None, no repeated row 0)
    p1 = ParsedTable(
        page_number=1,
        table_index=0,
        caption=None,
        headers=["Block", "Drilled Holes", "Total Meterage"],
        rows=[["North Block", "14", "2800m"]]
    )
    p2 = ParsedTable(
        page_number=2,
        table_index=0,
        caption=None,
        headers=["Block", "Drilled Holes", "Total Meterage"],
        rows=[["South Block", "10", "2200m"]]
    )
    
    class MockAmbiguousParser(BaseParser):
        def can_handle(self, mime_type, filename): return True
        def parse(self, file_path):
            return ParsedDocument(
                pages=[
                    ParsedPage(page_number=1, text="Text 1", tables=[p1]),
                    ParsedPage(page_number=2, text="Text 2", tables=[p2])
                ],
                total_pages=2,
                tables=[p1, p2]
            )
            
    from unittest.mock import patch
    with patch("app.services.ingestion.get_parser_for_file", return_value=MockAmbiguousParser()):
        process_document(doc.id, job.id)
        
    db.refresh(doc)
    assert doc.status == "COMPLETED"
    
    # Check VerificationTask was created
    task = db.query(VerificationTask).filter(
        VerificationTask.document_id == doc.id,
        VerificationTask.task_type == "TABLE_CONTINUATION_REVIEW"
    ).first()
    
    assert task is not None
    assert task.status == "PENDING"
    assert "Ambiguous table continuation detected between Page 1 and Page 2" in task.review_notes
    assert "Score" in task.review_notes
    
    # Check Table metadata persisted signals
    tbl2 = db.query(Table).filter(Table.document_id == doc.id, Table.page_number == 2).first()
    assert tbl2 is not None
    assert tbl2.continuation_status == "REVIEW_REQUIRED"
    assert "continuation_signals" in tbl2.metadata_json
    assert tbl2.metadata_json["continuation_signals"]["hard_gate_passed"] is True
    assert "signals" in tbl2.metadata_json["continuation_signals"]
    
    db.close()
