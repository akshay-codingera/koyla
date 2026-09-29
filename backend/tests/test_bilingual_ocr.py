import os
import sys
import uuid
import tempfile
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageFont

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.document import Document, ProcessingJob, DocumentPage
from app.models.chunk import Chunk
from app.models.organization import Organization
from app.services.parsers.ocr_parser import OCRParser, ocr_parser
from app.services.ingestion import process_document
from app.services.retrieval.keyword_search import keyword_search_engine


def get_hindi_font(size=32):
    font_paths = [
        "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
        "/usr/share/fonts/truetype/lohit-deva/Lohit-Devanagari.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def create_bilingual_test_image(text_en="Central Mine Planning and Design Institute", text_hi="कोल इंडिया लिमिटेड भूवैज्ञानिक रिपोर्ट"):
    img = Image.new("RGB", (900, 250), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = get_hindi_font(32)
    draw.text((25, 30), text_en, fill=(0, 0, 0), font=font)
    draw.text((25, 110), text_hi, fill=(0, 0, 0), font=font)
    return img


def test_1_default_ocr_languages_config():
    """Verify configured/default OCR languages is eng+hin with eng fallback."""
    assert hasattr(settings, "OCR_LANGUAGES")
    assert "eng" in settings.OCR_LANGUAGES
    assert "hin" in settings.OCR_LANGUAGES
    assert settings.OCR_LANGUAGES == "eng+hin"
    assert settings.OCR_FALLBACK_LANGUAGE == "eng"


def test_2_resolve_ocr_languages_both_available():
    """Verify when both English and Hindi are installed, eng+hin is selected without fallback."""
    parser = OCRParser()
    with patch.object(parser, "get_available_languages", return_value=["eng", "hin", "osd"]):
        selected, is_fallback = parser.resolve_ocr_languages("eng+hin")
        assert selected == "eng+hin"
        assert is_fallback is False


def test_3_resolve_ocr_languages_hindi_unavailable_fallback():
    """Verify when Hindi is missing, system gracefully falls back to eng without crashing."""
    parser = OCRParser()
    with patch.object(parser, "get_available_languages", return_value=["eng", "osd"]):
        selected, is_fallback = parser.resolve_ocr_languages("eng+hin")
        assert selected == "eng"
        assert is_fallback is True


def test_4_resolve_ocr_languages_english_unavailable_error():
    """Verify when English is missing from Tesseract, system raises a clear configuration error."""
    parser = OCRParser()
    with patch.object(parser, "get_available_languages", return_value=["hin", "osd"]):
        with pytest.raises(RuntimeError, match="English.*unavailable"):
            parser.resolve_ocr_languages("eng+hin")


def test_5_existing_english_ocr_regression():
    """Verify existing English OCR regression test passes with existing fixture."""
    fixture_path = "demo_data/scanned_borehole_log.png"
    if os.path.exists(fixture_path):
        parsed = ocr_parser.parse(fixture_path)
        assert parsed.total_pages == 1
        page1 = parsed.pages[0]
        assert page1.ocr_applied is True
        assert page1.width == 600
        assert page1.height == 300
        assert page1.metadata.get("ocr_engine") == "tesseract"


def test_6_bilingual_image_ocr_fixture():
    """Verify OCR extracts both English and Hindi text from a bilingual fixture."""
    img = create_bilingual_test_image(
        text_en="Central Mine Planning and Design Institute",
        text_hi="कोल इंडिया लिमिटेड भूवैज्ञानिक रिपोर्ट"
    )
    text, conf, success = ocr_parser.ocr_image(img)
    assert success is True
    assert conf > 0.4
    
    # Assert English extracted
    assert "Planning" in text or "Design" in text or "Central" in text or "Institute" in text
    
    # Assert Hindi Devanagari extracted
    has_hindi = any("\u0900" <= ch <= "\u097F" for ch in text)
    assert has_hindi, f"Expected Hindi Devanagari characters in extracted text, got: {text}"
    assert "कोल" in text or "इंडिया" in text or "रिपोर्ट" in text or "भूवैज्ञानिक" in text


def test_7_mixed_language_document_parse():
    """Verify mixed-language document passes through OCR parser and populates metadata."""
    img = create_bilingual_test_image(
        text_en="Bilingual Exploration Summary",
        text_hi="खनन एवं भूवैज्ञानिक अन्वेषण"
    )
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img.save(tmp.name)
        tmp_path = tmp.name

    try:
        parsed = ocr_parser.parse(tmp_path)
        assert parsed.total_pages == 1
        page = parsed.pages[0]
        assert page.ocr_applied is True
        assert page.metadata.get("ocr_language") in ["eng+hin", "eng"]
        assert "Bilingual" in page.text or "Exploration" in page.text
        has_hindi = any("\u0900" <= ch <= "\u097F" for ch in page.text)
        assert has_hindi, f"Expected Hindi Devanagari in page text, got: {page.text}"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_8_bilingual_ocr_downstream_ingestion():
    """Verify bilingual OCR text flows through end-to-end document ingestion into chunks."""
    img = create_bilingual_test_image(
        text_en="CMPDI Regional Institute Bilaspur SECL",
        text_hi="गेवरा ओपनकास्ट खदान कोयला उत्पादन"
    )
    
    os.makedirs("storage/documents/test_bilingual", exist_ok=True)
    file_path = f"storage/documents/test_bilingual/bilingual_{uuid.uuid4().hex[:6]}.png"
    img.save(file_path)

    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        doc = Document(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            title="Bilingual Gevra Mine Report",
            document_type="GEOLOGICAL_REPORT",
            original_filename="bilingual_gevra.png",
            file_path=file_path,
            mime_type="image/png",
            file_size_bytes=os.path.getsize(file_path),
            sha256_hash="bilingual_hash_" + uuid.uuid4().hex[:8],
            status="QUEUED"
        )
        db.add(doc)

        job = ProcessingJob(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            job_type="INGESTION",
            status="QUEUED",
        )
        db.add(job)
        db.commit()

        # Run ingestion pipeline
        process_document(doc.id, job.id, raise_on_error=True)

        db.refresh(doc)
        db.refresh(job)

        assert job.status == "COMPLETED"
        assert doc.status in ["COMPLETED", "PROCESSED"]

        # Verify page extracted
        pages = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).all()
        assert len(pages) == 1
        page_text = pages[0].extracted_text
        assert "CMPDI" in page_text or "Regional" in page_text or "Bilaspur" in page_text
        assert any("\u0900" <= ch <= "\u097F" for ch in page_text)

        # Verify chunks created
        chunks = db.query(Chunk).filter(Chunk.document_id == doc.id).all()
        assert len(chunks) >= 1
        chunk_content = " ".join([c.content for c in chunks])
        assert any("\u0900" <= ch <= "\u097F" for ch in chunk_content)
    finally:
        db.close()
        if os.path.exists(file_path):
            os.remove(file_path)


def test_9_bilingual_searchability_lexical_retrieval():
    """Verify Hindi OCR text stored in chunks is searchable via lexical retrieval."""
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        doc = Document(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            title="SECL Devanagari Search Test",
            document_type="GEOLOGICAL_REPORT",
            original_filename="secl_search_hi.png",
            file_path="storage/secl_search_hi.png",
            mime_type="image/png",
            file_size_bytes=100,
            sha256_hash="hi_search_hash_" + uuid.uuid4().hex[:8],
            status="PROCESSED"
        )
        db.add(doc)
        db.commit()

        chunk = Chunk(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            chunk_index=1,
            page_number=1,
            chunk_type="TEXT",
            content="गेवरा खदान में कोयला प्रेषण लक्ष्य से अधिक हुआ। CMPDI exploration summary."
        )
        db.add(chunk)
        db.commit()

        # Query using Hindi keyword
        results = keyword_search_engine.search(
            db=db,
            query="कोयला प्रेषण",
            allowed_org_ids=[org.id],
            top_k=20
        )
        retrieved_ids = [r["chunk_id"] for r in results]
        assert chunk.id in retrieved_ids
    finally:
        db.close()


def test_10_ocr_fallback_simulation_on_image():
    """Verify when Hindi is simulated as missing, ocr_image gracefully falls back to eng without raising error."""
    img = create_bilingual_test_image()
    parser = OCRParser()
    with patch.object(parser, "get_available_languages", return_value=["eng", "osd"]):
        text, conf, success = parser.ocr_image(img, lang="eng+hin")
        assert success is True
        assert len(text) > 0
        # English is recognized
        assert "Planning" in text or "Design" in text or "Central" in text or "Institute" in text
