import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.organization import Organization
from app.models.document import Document, DocumentPage, Table, TableRow, ProcessingJob
from app.models.chunk import Chunk
from app.models.audit import AuditEvent
from app.services.storage import storage_service, ALLOWED_EXTENSIONS
from app.services.parsers.pdf_parser import pdf_parser
from app.services.parsers.docx_parser import docx_parser
from app.services.parsers.spreadsheet_parser import spreadsheet_parser
from app.services.parsers.ocr_parser import ocr_parser
from app.services.parsers.base import ParsedDocument, ParsedPage, ParsedTable
from app.services.chunking import chunking_service

client = TestClient(app)

def get_token(username="hq_officer", password="Admin123!"):
    res = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_storage_service_validation():
    # Allowed
    assert storage_service.validate_file("report.pdf") == "application/pdf"
    assert storage_service.validate_file("summary.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert storage_service.validate_file("data.xlsx") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert storage_service.validate_file("legacy.xls") == "application/vnd.ms-excel"
    assert storage_service.validate_file("scan.jpg") == "image/jpeg"
    assert storage_service.validate_file("diagram.png") == "image/png"
    
    # Unsupported
    with pytest.raises(Exception) as excinfo:
        storage_service.validate_file("archive.zip")
    assert "Unsupported file format" in str(excinfo.value)

def test_storage_service_sha256():
    test_bytes = b"CMPDI Central Mine Planning & Design Institute Limited"
    path, sha, size = storage_service.save_bytes(test_bytes, "test_hash.txt", "test_org", "test_doc")
    import hashlib
    expected_sha = hashlib.sha256(test_bytes).hexdigest()
    assert sha == expected_sha
    assert size == len(test_bytes)
    assert os.path.exists(path)

def test_pdf_parser():
    parsed = pdf_parser.parse("demo_data/geological_summary_bccl.pdf")
    assert parsed.total_pages >= 1
    page1 = parsed.pages[0]
    assert "BHARAT COKING COAL LIMITED" in page1.text
    assert page1.ocr_applied is False
    assert page1.confidence == 1.0
    assert len(parsed.tables) >= 1
    table = parsed.tables[0]
    assert "Seam Name" in table.headers or "Column_1" in table.headers

def test_docx_parser():
    parsed = docx_parser.parse("demo_data/mine_safety_inspection_ecl.docx")
    assert parsed.total_pages >= 1
    assert "EASTERN COALFIELDS LIMITED" in parsed.pages[0].text
    assert len(parsed.tables) >= 1
    table = parsed.tables[0]
    assert "Inspection Area" in table.headers
    assert len(table.rows) >= 4

def test_spreadsheet_parser():
    parsed = spreadsheet_parser.parse("demo_data/monthly_coal_production_ccl.xlsx")
    assert parsed.total_pages >= 1
    assert len(parsed.tables) >= 1
    table = parsed.tables[0]
    assert "Month" in table.headers
    assert "Actual_MT" in table.headers
    assert len(table.rows) >= 6

def test_ocr_parser():
    parsed = ocr_parser.parse("demo_data/scanned_borehole_log.png")
    assert parsed.total_pages == 1
    page1 = parsed.pages[0]
    assert page1.ocr_applied is True
    assert page1.width == 600
    assert page1.height == 300

def test_chunking_service_table_preservation():
    table = ParsedTable(
        page_number=1,
        table_index=1,
        caption="Coal Quality Test",
        headers=["Seam", "Ash %", "Moisture %"],
        rows=[["Seam I", "18.5", "2.1"], ["Seam II", "22.4", "1.9"]]
    )
    page = ParsedPage(
        page_number=1,
        text="Section 1: Chemical Analysis\n\nSamples analyzed at CMPDI Central Lab.",
        tables=[table]
    )
    doc = ParsedDocument(pages=[page], total_pages=1, tables=[table])
    
    chunks = chunking_service.chunk_document(doc, "doc_test_123")
    assert len(chunks) == 2
    text_chunk = chunks[0]
    assert text_chunk.chunk_type == "TEXT"
    assert "Section 1: Chemical Analysis" in text_chunk.content
    
    table_chunk = chunks[1]
    assert table_chunk.chunk_type == "TABLE"
    assert "Seam | Ash % | Moisture %" in table_chunk.content
    assert "Seam I | 18.5 | 2.1" in table_chunk.content

def test_document_upload_and_pipeline():
    token = get_token("hq_officer", "Admin123!")
    db = SessionLocal()
    bccl_org = db.query(Organization).filter(Organization.code == "BCCL").first()
    db.close()
    assert bccl_org is not None
    
    with open("demo_data/geological_summary_bccl.pdf", "rb") as f:
        response = client.post(
            "/api/v1/documents/upload?sync=true",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "organization_id": bccl_org.id,
                "title": "BCCL Geological Exploration Report 2024",
                "document_type": "GEOLOGICAL_REPORT",
                "source_tier": "TIER_A"
            },
            files={"file": ("geological_summary_bccl.pdf", f, "application/pdf")}
        )
    assert response.status_code == 201
    data = response.json()
    doc_id = data["id"]
    assert data["source_tier"] == "TIER_A"
    assert data["sha256_hash"] is not None
    
    # Check document detail
    detail_res = client.get(f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail_res.status_code == 200
    doc_data = detail_res.json()
    assert doc_data["status"] == "COMPLETED"
    assert doc_data["page_count"] >= 1
    assert doc_data["table_count"] >= 1
    assert doc_data["chunk_count"] >= 1
    
    # Check pages endpoint
    pages_res = client.get(f"/api/v1/documents/{doc_id}/pages", headers={"Authorization": f"Bearer {token}"})
    assert pages_res.status_code == 200
    pages = pages_res.json()
    assert len(pages) >= 1
    assert "BHARAT COKING COAL LIMITED" in pages[0]["extracted_text"]
    
    # Check tables endpoint
    tables_res = client.get(f"/api/v1/documents/{doc_id}/tables", headers={"Authorization": f"Bearer {token}"})
    assert tables_res.status_code == 200
    tables = tables_res.json()
    assert len(tables) >= 1
    
    # Check chunks endpoint
    chunks_res = client.get(f"/api/v1/documents/{doc_id}/chunks", headers={"Authorization": f"Bearer {token}"})
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    assert len(chunks) >= 1
    assert any(c["chunk_type"] == "TABLE" for c in chunks)

def test_unsupported_file_upload_rejected():
    token = get_token("hq_officer", "Admin123!")
    db = SessionLocal()
    org = db.query(Organization).first()
    db.close()
    
    with open("demo_data/unsupported_archive.zip", "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            data={"organization_id": org.id},
            files={"file": ("unsupported_archive.zip", f, "application/zip")}
        )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

def test_org_scoped_document_security():
    # Login as ri1_analyst (assigned to RI-1)
    ri1_token = get_token("ri1_analyst", "Password123!")
    
    db = SessionLocal()
    # Find BCCL organization (not RI-1)
    bccl_org = db.query(Organization).filter(Organization.code == "BCCL").first()
    db.close()
    
    # Attempt to upload to BCCL as RI-1 analyst
    with open("demo_data/monthly_coal_production_ccl.xlsx", "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {ri1_token}"},
            data={"organization_id": bccl_org.id},
            files={"file": ("monthly_coal_production_ccl.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]
