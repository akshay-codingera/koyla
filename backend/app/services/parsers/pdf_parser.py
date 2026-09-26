import io
from pathlib import Path
from typing import List
import pymupdf
from PIL import Image
from app.services.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParsedTable
from app.services.parsers.ocr_parser import ocr_parser
from app.services.parsers.visual_detector import visual_detector

class PDFParser(BaseParser):
    def can_handle(self, mime_type: str, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext == ".pdf" or mime_type in ["application/pdf", "application/x-pdf"]

    def parse(self, file_path: str) -> ParsedDocument:
        doc = pymupdf.open(file_path)
        pages: List[ParsedPage] = []
        all_tables: List[ParsedTable] = []
        doc_ocr_applied = False
        
        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_num = page_idx + 1
                native_text = page.get_text("text").strip()
                rect = page.rect
                width = int(rect.width)
                height = int(rect.height)
                
                # Extract tables using native PyMuPDF table finder
                page_tables: List[ParsedTable] = []
                try:
                    tabs = page.find_tables()
                    for t_idx, tab in enumerate(tabs):
                        extracted = tab.extract()
                        if not extracted or len(extracted) < 1:
                            continue
                        
                        raw_headers = extracted[0]
                        headers = [str(h or f"Column_{i+1}").strip() for i, h in enumerate(raw_headers)]
                        rows = []
                        for r in extracted[1:]:
                            rows.append([str(c if c is not None else "").strip() for c in r])
                            
                        parsed_table = ParsedTable(
                            page_number=page_num,
                            table_index=t_idx + 1,
                            caption=f"Table {t_idx + 1} (Page {page_num})",
                            headers=headers,
                            rows=rows,
                            metadata={"row_count": len(rows), "col_count": len(headers)}
                        )
                        page_tables.append(parsed_table)
                        all_tables.append(parsed_table)
                except Exception as e:
                    # PyMuPDF table extraction fallback
                    page_tables = []
                
                # Determine if OCR is required:
                # Digital PDF with native text does NOT need OCR.
                # Scanned page (empty or minimal text) triggers local OCR.
                if len(native_text) < 30:
                    # Check if page has images or is scanned
                    pix = page.get_pixmap(dpi=150)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    ocr_text, conf, success = ocr_parser.ocr_image(img)
                    
                    if len(ocr_text) > len(native_text):
                        text = ocr_text
                        ocr_applied = True
                        confidence = conf
                        doc_ocr_applied = True
                    else:
                        text = native_text
                        ocr_applied = False
                        confidence = 0.95
                else:
                    text = native_text
                    ocr_applied = False
                    confidence = 1.0  # Clean digital native text
                
                # Phase 9: Visual detection on this page
                try:
                    page_visuals = visual_detector.detect_visuals_on_page(
                        page=page, doc=doc, page_number=page_num, page_text=text
                    )
                except Exception:
                    page_visuals = []

                parsed_page = ParsedPage(
                    page_number=page_num,
                    text=text,
                    ocr_applied=ocr_applied,
                    confidence=confidence,
                    width=width,
                    height=height,
                    tables=page_tables,
                    visuals=page_visuals,
                    metadata={"char_count": len(text)}
                )
                pages.append(parsed_page)
                
            return ParsedDocument(
                pages=pages,
                total_pages=len(pages),
                tables=all_tables,
                metadata={
                    "format": "PDF",
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "page_count": len(pages)
                },
                ocr_applied=doc_ocr_applied
            )
        finally:
            doc.close()

pdf_parser = PDFParser()
