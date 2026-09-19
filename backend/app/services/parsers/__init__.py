from pathlib import Path
from fastapi import HTTPException
from app.services.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParsedTable
from app.services.parsers.pdf_parser import pdf_parser
from app.services.parsers.docx_parser import docx_parser
from app.services.parsers.spreadsheet_parser import spreadsheet_parser
from app.services.parsers.ocr_parser import ocr_parser

PARSERS = [
    pdf_parser,
    docx_parser,
    spreadsheet_parser,
    ocr_parser,
]

def get_parser_for_file(mime_type: str, filename: str) -> BaseParser:
    for parser in PARSERS:
        if parser.can_handle(mime_type, filename):
            return parser
            
    ext = Path(filename).suffix.lower()
    raise HTTPException(
        status_code=400,
        detail=f"No parser available for format '{ext}' (MIME: {mime_type})"
    )

__all__ = [
    "BaseParser",
    "ParsedDocument",
    "ParsedPage",
    "ParsedTable",
    "pdf_parser",
    "docx_parser",
    "spreadsheet_parser",
    "ocr_parser",
    "get_parser_for_file",
]
