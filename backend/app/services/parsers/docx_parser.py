from pathlib import Path
from typing import List
import docx
from app.services.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParsedTable

class DOCXParser(BaseParser):
    def can_handle(self, mime_type: str, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext == ".docx" or "wordprocessingml" in mime_type

    def parse(self, file_path: str) -> ParsedDocument:
        doc = docx.Document(file_path)
        all_tables: List[ParsedTable] = []
        
        # Extract tables first
        for t_idx, table in enumerate(doc.tables):
            if not table.rows:
                continue
            
            headers = [cell.text.strip() or f"Col_{i+1}" for i, cell in enumerate(table.rows[0].cells)]
            rows = []
            for r in table.rows[1:]:
                rows.append([cell.text.strip() for cell in r.cells])
                
            parsed_table = ParsedTable(
                page_number=1,
                table_index=t_idx + 1,
                caption=f"DOCX Table {t_idx + 1}",
                headers=headers,
                rows=rows,
                metadata={"row_count": len(rows), "col_count": len(headers)}
            )
            all_tables.append(parsed_table)

        # Extract embedded images if present
        all_visuals = []
        try:
            from PIL import Image as PILImage
            import io
            from app.services.parsers.base import ParsedVisual
            img_idx = 0
            for rel_id, part in doc.part.related_parts.items():
                if getattr(part, "content_type", "").startswith("image/"):
                    img_idx += 1
                    blob = part.blob
                    try:
                        pil_img = PILImage.open(io.BytesIO(blob))
                        w, h = pil_img.size
                        all_visuals.append(
                            ParsedVisual(
                                page_number=1,
                                bbox={"x0": 0.0, "y0": 0.0, "x1": float(w), "y1": float(h)},
                                image_bytes=blob,
                                width_px=w,
                                height_px=h,
                                visual_type="OTHER",
                                classification_confidence=0.5,
                                classification_method="docx_embedded_extraction",
                                extraction_method="docx_embedded",
                                figure_number=f"DOCX Figure {img_idx}",
                                caption=f"DOCX Embedded Image {img_idx}",
                                metadata={"rel_id": rel_id, "content_type": part.content_type}
                            )
                        )
                    except Exception:
                        pass
        except Exception:
            pass
            
        # Group paragraphs into logical pages/sections
        text_lines = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            if p.style.name.startswith("Heading"):
                text_lines.append(f"\n## {text}\n")
            else:
                text_lines.append(text)
                
        full_text = "\n".join(text_lines)
        
        # Split text into logical pages if large (roughly 3000 chars per virtual page)
        page_chunks = []
        if len(full_text) > 3000:
            lines = full_text.split("\n")
            curr_chunk = []
            curr_len = 0
            for line in lines:
                curr_chunk.append(line)
                curr_len += len(line)
                if curr_len > 2500 and line.startswith("##"):
                    page_chunks.append("\n".join(curr_chunk))
                    curr_chunk = []
                    curr_len = 0
            if curr_chunk:
                page_chunks.append("\n".join(curr_chunk))
        else:
            page_chunks = [full_text]
            
        pages: List[ParsedPage] = []
        for p_idx, page_content in enumerate(page_chunks):
            page_num = p_idx + 1
            # Associate tables with page 1 (or corresponding virtual page)
            page_tables = all_tables if page_num == 1 else []
            page_visuals = all_visuals if page_num == 1 else []
            pages.append(
                ParsedPage(
                    page_number=page_num,
                    text=page_content,
                    ocr_applied=False,
                    confidence=1.0,
                    tables=page_tables,
                    visuals=page_visuals,
                    metadata={"virtual_page": True}
                )
            )
            
        return ParsedDocument(
            pages=pages,
            total_pages=len(pages),
            tables=all_tables,
            metadata={
                "format": "DOCX",
                "paragraph_count": len(doc.paragraphs),
                "table_count": len(all_tables)
            },
            ocr_applied=False
        )

docx_parser = DOCXParser()
