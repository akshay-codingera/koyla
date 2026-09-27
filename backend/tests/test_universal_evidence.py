import os
import io
import uuid
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from PIL import Image

from app.main import app
from app.db.database import SessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.models.document import Document, DocumentPage, Table, TableRow
from app.models.visual import VisualAsset
from app.models.extraction import ExtractedField
from app.models.evidence import DocumentRelationship
from app.services.storage import storage_service
from app.services.parsers.csv_parser import csv_parser
from app.services.parsers.legacy_xls_parser import legacy_xls_parser
from app.services.parsers.txt_parser import txt_parser
from app.services.parsers.ocr_parser import ocr_parser
from app.services.parsers.docx_parser import docx_parser
from app.services.relationships import relationship_discovery_service
from app.services.qa.qa_service import QAService

client = TestClient(app)

def get_token(username="admin", password="password"):
    res = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    if res.status_code == 200:
        return res.json()["access_token"]
    # Fallback to HQ Officer
    res = client.post("/api/v1/auth/login", data={"username": "hq_officer", "password": "Admin123!"})
    if res.status_code == 200:
        return res.json()["access_token"]
    return None

class TestMultiformatParsers:
    def test_csv_parser_with_sniffing(self):
        """Tests CSV auto-sniffer on comma, tab, and semicolon delimiters."""
        csv_content = "Mine_Name,Target_MT,Actual_MT,Variance_MT\nGevra OC,50.0,52.5,+2.5\nDipka OC,35.0,34.2,-0.8\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            assert csv_parser.can_handle("text/csv", temp_path)
            doc = csv_parser.parse(temp_path)
            assert doc.total_pages == 1
            assert len(doc.tables) == 1
            tbl = doc.tables[0]
            assert tbl.headers == ["Mine_Name", "Target_MT", "Actual_MT", "Variance_MT"]
            assert len(tbl.rows) == 2
            assert tbl.rows[0][0] == "Gevra OC"
            assert tbl.metadata["delimiter"] == ","
        finally:
            os.remove(temp_path)

    def test_csv_parser_semicolon_sniffer(self):
        """Tests CSV auto-sniffer with semicolon delimiter."""
        csv_content = "Block;Depth_m;Seam;Grade\nBlock A;120.5;Seam I;G4\nBlock B;210.0;Seam II;G5\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            doc = csv_parser.parse(temp_path)
            assert len(doc.tables) == 1
            tbl = doc.tables[0]
            assert tbl.headers == ["Block", "Depth_m", "Seam", "Grade"]
            assert tbl.metadata["delimiter"] == ";"
            assert len(tbl.rows) == 2
        finally:
            os.remove(temp_path)

    def test_txt_parser_virtual_pagination(self):
        """Tests plain text parser with encoding fallback and section pagination."""
        short_txt = "# Geological Exploration Brief\n\nDrilling operations confirmed Barakar formation across North Block.\n"
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(short_txt)
            temp_path = f.name

        try:
            assert txt_parser.can_handle("text/plain", temp_path)
            doc = txt_parser.parse(temp_path)
            assert doc.total_pages == 1
            assert "Barakar formation" in doc.pages[0].text
        finally:
            os.remove(temp_path)

    def test_direct_image_visual_evidence(self):
        """Tests that direct image parsing creates a ParsedVisual classified into the 14-class taxonomy."""
        img = Image.new("RGB", (300, 200), color=(200, 100, 50))
        with tempfile.NamedTemporaryFile(suffix="_geological_section_map.png", delete=False) as f:
            img.save(f, format="PNG")
            temp_path = f.name

        try:
            assert ocr_parser.can_handle("image/png", temp_path)
            doc = ocr_parser.parse(temp_path)
            assert doc.total_pages == 1
            page = doc.pages[0]
            assert len(page.visuals) == 1
            vis = page.visuals[0]
            assert vis.width_px == 300
            assert vis.height_px == 200
            assert vis.visual_type in ["GEOLOGICAL_SECTION", "MAP", "UNKNOWN"]
            assert vis.extraction_method == "direct_upload"
        finally:
            os.remove(temp_path)

    def test_storage_accepts_universal_formats(self):
        """Verifies StorageService allows .csv, .txt, .xlsx, .xls, .pdf, .jpg, .png."""
        for ext in [".csv", ".txt", ".xlsx", ".xls", ".pdf", ".jpg", ".png"]:
            mime = storage_service.validate_file(f"test_file{ext}")
            assert mime is not None

class TestUniversalEvidenceAPI:
    def test_evidence_summary_endpoint(self):
        token = get_token()
        res = client.get("/api/v1/evidence/summary", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert "total_documents" in data
        assert "text_evidence_count" in data
        assert "table_evidence_count" in data
        assert "structured_values_count" in data
        assert "visual_assets_count" in data
        assert "needs_review_count" in data
        assert "relationships_count" in data

    def test_evidence_items_endpoint(self):
        token = get_token()
        res = client.get("/api/v1/evidence/items?limit=10", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_evidence_batch_upload_api(self):
        token = get_token()
        db = SessionLocal()
        org = db.query(Organization).first()
        db.close()
        assert org is not None

        csv_content = b"Mine_Name,Coal_Production_MT\nGevra OC,52.5\nKusmunda OC,41.2\n"
        txt_content = b"Geological Report on Barakar Formation in SECL region.\n"

        files = [
            ("files", ("monthly_prod.csv", csv_content, "text/csv")),
            ("files", ("geology_notes.txt", txt_content, "text/plain"))
        ]

        res = client.post(
            "/api/v1/evidence/upload?sync=true",
            headers={"Authorization": f"Bearer {token}"},
            data={"organization_id": org.id, "source_tier": "TIER_A"},
            files=files
        )
        assert res.status_code == 201
        data = res.json()
        assert data["total_files"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["detected_format"] in ["CSV", "TXT"]

class TestRelationshipDiscovery:
    def test_relationship_discovery_same_mine(self):
        db = SessionLocal()
        org = db.query(Organization).first()
        user = db.query(User).first()

        doc1 = Document(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            title="Gevra Monthly Review 2024",
            document_type="PRODUCTION_REPORT",
            source_tier="TIER_A",
            original_filename="gevra_monthly_2024.xlsx",
            file_path="storage/test/gevra_monthly_2024.xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size_bytes=1024,
            sha256_hash=uuid.uuid4().hex,
            status="COMPLETED",
            created_by=user.id
        )
        doc2 = Document(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            title="Gevra Geological Model Plan",
            document_type="GEOLOGICAL_REPORT",
            source_tier="TIER_A",
            original_filename="gevra_geological_model.pdf",
            file_path="storage/test/gevra_geological_model.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            sha256_hash=uuid.uuid4().hex,
            status="COMPLETED",
            created_by=user.id
        )
        db.add_all([doc1, doc2])
        db.commit()

        # Add matching mine field to both
        f1 = ExtractedField(
            organization_id=org.id,
            document_id=doc1.id,
            field_name="mine_name",
            field_category="IDENTIFICATION",
            data_type="STRING",
            raw_value="Gevra OC",
            normalized_value="Gevra OC",
            validation_status="PASS"
        )
        f2 = ExtractedField(
            organization_id=org.id,
            document_id=doc2.id,
            field_name="mine_name",
            field_category="IDENTIFICATION",
            data_type="STRING",
            raw_value="Gevra OC",
            normalized_value="Gevra OC",
            validation_status="PASS"
        )
        db.add_all([f1, f2])
        db.commit()

        try:
            rels = relationship_discovery_service.discover_relationships(db, doc2.id, org.id)
            assert len(rels) >= 1
            rel_types = [r.relationship_type for r in rels]
            assert "SAME_MINE_OR_BLOCK" in rel_types
        finally:
            db.query(DocumentRelationship).filter(DocumentRelationship.source_document_id == doc2.id).delete()
            db.query(ExtractedField).filter(ExtractedField.document_id.in_([doc1.id, doc2.id])).delete()
            db.query(Document).filter(Document.id.in_([doc1.id, doc2.id])).delete()
            db.commit()
            db.close()

class TestEvidenceReviewAPI:
    def test_review_extracted_value_approve_and_correct(self):
        token = get_token()
        db = SessionLocal()
        org = db.query(Organization).first()
        user = db.query(User).first()

        doc = Document(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            title="Review Test Document",
            document_type="PRODUCTION_REPORT",
            source_tier="TIER_B",
            original_filename="review_test.csv",
            file_path="storage/test/review_test.csv",
            mime_type="text/csv",
            file_size_bytes=1024,
            sha256_hash=uuid.uuid4().hex,
            status="COMPLETED",
            created_by=user.id
        )
        db.add(doc)
        db.commit()

        field = ExtractedField(
            organization_id=org.id,
            document_id=doc.id,
            field_name="coal_production",
            field_category="MINING",
            data_type="NUMBER",
            raw_value="48.5",
            normalized_value="48.5",
            numeric_value=48.5,
            unit="MT",
            verification_status="UNVERIFIED",
            validation_status="WARNING"
        )
        db.add(field)
        db.commit()

        try:
            # 1. Approve
            res = client.post(
                f"/api/v1/evidence/val_{field.id}/review",
                headers={"Authorization": f"Bearer {token}"},
                json={"action": "APPROVE", "notes": "Verified against physical dispatch slip"}
            )
            assert res.status_code == 200
            assert res.json()["verification_status"] == "VERIFIED"

            # 2. Correct
            res2 = client.post(
                f"/api/v1/evidence/val_{field.id}/review",
                headers={"Authorization": f"Bearer {token}"},
                json={"action": "CORRECT", "corrected_value": "49.2", "notes": "Adjusted per final calibration"}
            )
            assert res2.status_code == 200
            assert res2.json()["verification_status"] == "CORRECTED"
        finally:
            db.query(ExtractedField).filter(ExtractedField.id == field.id).delete()
            db.query(Document).filter(Document.id == doc.id).delete()
            db.commit()
            db.close()
