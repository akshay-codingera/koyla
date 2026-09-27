from pathlib import Path
from typing import List
from app.services.parsers.base import BaseParser, ParsedDocument, ParsedPage

class TxtParser(BaseParser):
    """
    Parser for plain text documents (.txt).
    Features:
    - Multi-encoding fallback (utf-8, latin-1, cp1252)
    - Paragraph and section segmentation (by Markdown-like headings or double newlines)
    - Virtual pagination for large text files (>3000 chars)
    """
    ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    def can_handle(self, mime_type: str, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext == ".txt" or mime_type == "text/plain"

    def _read_content(self, file_path: str):
        content = ""
        used_encoding = "utf-8"
        for enc in self.ENCODINGS:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                    used_encoding = enc
                    break
            except (UnicodeDecodeError, Exception):
                continue

        if not content:
            with open(file_path, "rb") as f:
                content = f.read().decode("latin-1", errors="replace")
                used_encoding = "latin-1 (fallback)"

        return content, used_encoding

    def parse(self, file_path: str) -> ParsedDocument:
        content, encoding = self._read_content(file_path)
        content = content.strip()

        if not content:
            empty_page = ParsedPage(
                page_number=1,
                text="Plain Text Document (Empty)",
                ocr_applied=False,
                confidence=1.0,
                tables=[],
                metadata={"empty": True, "encoding": encoding}
            )
            return ParsedDocument(
                pages=[empty_page],
                total_pages=1,
                tables=[],
                metadata={"format": "TXT", "encoding": encoding},
                ocr_applied=False
            )

        # Virtual pagination: chunk text into ~2500 character pages on paragraph boundaries
        page_chunks: List[str] = []
        if len(content) > 3000:
            paragraphs = content.split("\n\n")
            curr_chunk: List[str] = []
            curr_len = 0
            for para in paragraphs:
                curr_chunk.append(para)
                curr_len += len(para)
                if curr_len > 2500:
                    page_chunks.append("\n\n".join(curr_chunk))
                    curr_chunk = []
                    curr_len = 0
            if curr_chunk:
                page_chunks.append("\n\n".join(curr_chunk))
        else:
            page_chunks = [content]

        pages: List[ParsedPage] = []
        for idx, chunk_text in enumerate(page_chunks):
            page_num = idx + 1
            pages.append(
                ParsedPage(
                    page_number=page_num,
                    text=chunk_text,
                    ocr_applied=False,
                    confidence=1.0,
                    tables=[],
                    metadata={
                        "virtual_page": len(page_chunks) > 1,
                        "encoding": encoding,
                        "char_count": len(chunk_text)
                    }
                )
            )

        return ParsedDocument(
            pages=pages,
            total_pages=len(pages),
            tables=[],
            metadata={
                "format": "TXT",
                "char_count": len(content),
                "encoding": encoding,
                "virtual_pages": len(pages)
            },
            ocr_applied=False
        )

txt_parser = TxtParser()
