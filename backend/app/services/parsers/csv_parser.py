import csv
from pathlib import Path
from typing import List, Any
from app.services.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParsedTable

class CSVParser(BaseParser):
    """
    Parser for Comma-Separated Values (.csv) files.
    Features:
    - Auto-detects delimiters (comma, tab, semicolon, pipe) via csv.Sniffer
    - Multi-encoding fallback (utf-8, utf-8-sig, latin-1, cp1252)
    - Row-level provenance coordinates
    """
    ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    def can_handle(self, mime_type: str, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext == ".csv" or "csv" in mime_type.lower()

    def _read_content_and_sniffer(self, file_path: str):
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
            # Fallback binary decode with errors replace
            with open(file_path, "rb") as f:
                content = f.read().decode("latin-1", errors="replace")
                used_encoding = "latin-1 (fallback)"

        delimiter = ","
        try:
            sample = content[:4096]
            if sample:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample, delimiters=[",", "\t", ";", "|"])
                delimiter = dialect.delimiter
        except Exception:
            delimiter = ","

        return content, delimiter, used_encoding

    def parse(self, file_path: str) -> ParsedDocument:
        content, delimiter, encoding = self._read_content_and_sniffer(file_path)

        lines = content.splitlines()
        reader = csv.reader(lines, delimiter=delimiter)

        rows_data: List[List[Any]] = []
        for row in reader:
            if any(cell.strip() for cell in row):
                cleaned_row = [cell.strip() for cell in row]
                rows_data.append(cleaned_row)

        if not rows_data:
            empty_page = ParsedPage(
                page_number=1,
                text="CSV Document (Empty)",
                ocr_applied=False,
                confidence=1.0,
                tables=[],
                metadata={"empty": True, "delimiter": delimiter, "encoding": encoding}
            )
            return ParsedDocument(
                pages=[empty_page],
                total_pages=1,
                tables=[],
                metadata={"format": "CSV", "row_count": 0, "delimiter": delimiter, "encoding": encoding},
                ocr_applied=False
            )

        headers = rows_data[0]
        headers = [h if h else f"Col_{i+1}" for i, h in enumerate(headers)]
        data_rows = rows_data[1:]

        parsed_table = ParsedTable(
            page_number=1,
            table_index=1,
            caption="CSV Data Table",
            headers=headers,
            rows=data_rows,
            metadata={
                "delimiter": delimiter,
                "encoding": encoding,
                "row_count": len(data_rows),
                "col_count": len(headers),
                "format": "CSV"
            }
        )

        text_lines = [
            f"# CSV Record: {Path(file_path).name}",
            f"Delimiter: '{delimiter}' | Encoding: {encoding}",
            f"Headers: {' | '.join(headers)}",
            "Data:"
        ]
        for idx, r in enumerate(data_rows[:100]):
            text_lines.append(f"Row {idx+1}: " + " | ".join(r))
        if len(data_rows) > 100:
            text_lines.append(f"... ({len(data_rows) - 100} more rows)")

        page_text = "\n".join(text_lines)

        page = ParsedPage(
            page_number=1,
            text=page_text,
            ocr_applied=False,
            confidence=1.0,
            tables=[parsed_table],
            metadata={
                "row_count": len(data_rows),
                "col_count": len(headers),
                "delimiter": delimiter,
                "encoding": encoding,
                "format": "CSV"
            }
        )

        return ParsedDocument(
            pages=[page],
            total_pages=1,
            tables=[parsed_table],
            metadata={
                "format": "CSV",
                "row_count": len(data_rows),
                "col_count": len(headers),
                "delimiter": delimiter,
                "encoding": encoding
            },
            ocr_applied=False
        )

csv_parser = CSVParser()
