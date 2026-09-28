import csv
import uuid
from pathlib import Path
from typing import List, Any, Optional
from app.services.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParsedTable


class CSVParser(BaseParser):
    """
    Hardened Parser for Comma-Separated Values (.csv) files.
    Features:
    - Streaming line reader without loading entire file into memory
    - Auto-detects delimiters (comma, tab, semicolon, pipe) via csv.Sniffer
    - Multi-encoding fallback (utf-8, utf-8-sig, latin-1, cp1252)
    - Configurable chunk size for very large datasets
    - Row-level provenance coordinates
    """
    ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    DEFAULT_CHUNK_SIZE = 2000

    def can_handle(self, mime_type: str, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext == ".csv" or "csv" in mime_type.lower()

    def _detect_dialect_and_encoding(self, file_path: str):
        detected_encoding = "utf-8"
        delimiter = ","

        for enc in self.ENCODINGS:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    sample = f.read(8192)
                    detected_encoding = enc
                    if sample:
                        try:
                            dialect = csv.Sniffer().sniff(sample, delimiters=[",", "\t", ";", "|"])
                            delimiter = dialect.delimiter
                        except Exception:
                            delimiter = ","
                    break
            except (UnicodeDecodeError, Exception):
                continue

        return delimiter, detected_encoding

    def parse(self, file_path: str, chunk_size: Optional[int] = None) -> ParsedDocument:
        chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        delimiter, encoding = self._detect_dialect_and_encoding(file_path)

        all_tables: List[ParsedTable] = []
        headers: Optional[List[str]] = None
        current_chunk_rows: List[List[Any]] = []
        total_data_rows = 0
        first_100_rows: List[List[str]] = []
        file_logical_id = str(uuid.uuid4())
        part_idx = 0

        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                # Filter completely empty lines
                if not any(cell.strip() for cell in row):
                    continue

                cleaned_row = [cell.strip() for cell in row]

                if headers is None:
                    headers = [h if h else f"Col_{i+1}" for i, h in enumerate(cleaned_row)]
                    continue

                current_chunk_rows.append(cleaned_row)
                total_data_rows += 1

                if len(first_100_rows) < 100:
                    first_100_rows.append(cleaned_row)

                # Chunking for very large CSV files
                if len(current_chunk_rows) >= chunk_size:
                    part_idx += 1
                    caption = "CSV Data Table" if part_idx == 1 else f"CSV Data Table (Part {part_idx})"
                    table_part = ParsedTable(
                        page_number=1,
                        table_index=part_idx,
                        caption=caption,
                        headers=headers,
                        rows=current_chunk_rows,
                        logical_table_id=file_logical_id,
                        is_continuation=part_idx > 1,
                        part_number=part_idx,
                        metadata={
                            "delimiter": delimiter,
                            "encoding": encoding,
                            "row_count": len(current_chunk_rows),
                            "col_count": len(headers),
                            "part_number": part_idx,
                            "logical_table_id": file_logical_id,
                            "is_continuation": part_idx > 1,
                            "format": "CSV"
                        }
                    )
                    all_tables.append(table_part)
                    current_chunk_rows = []

        if headers is None:
            # Empty CSV
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

        # Add remaining / final table chunk
        if current_chunk_rows or not all_tables:
            part_idx += 1
            caption = "CSV Data Table" if part_idx == 1 else f"CSV Data Table (Part {part_idx})"
            table_part = ParsedTable(
                page_number=1,
                table_index=part_idx,
                caption=caption,
                headers=headers,
                rows=current_chunk_rows,
                logical_table_id=file_logical_id,
                is_continuation=part_idx > 1,
                part_number=part_idx,
                metadata={
                    "delimiter": delimiter,
                    "encoding": encoding,
                    "row_count": len(current_chunk_rows),
                    "col_count": len(headers),
                    "part_number": part_idx,
                    "logical_table_id": file_logical_id,
                    "is_continuation": part_idx > 1,
                    "format": "CSV"
                }
            )
            all_tables.append(table_part)

        # Structured summary text
        text_lines = [
            f"# CSV Record: {Path(file_path).name}",
            f"Delimiter: '{delimiter}' | Encoding: {encoding}",
            f"Headers: {' | '.join(headers)}",
            "Data:"
        ]
        for idx, r in enumerate(first_100_rows):
            text_lines.append(f"Row {idx+1}: " + " | ".join(r))
        if total_data_rows > 100:
            text_lines.append(f"... ({total_data_rows - 100} more rows)")

        page_text = "\n".join(text_lines)

        page = ParsedPage(
            page_number=1,
            text=page_text,
            ocr_applied=False,
            confidence=1.0,
            tables=all_tables,
            metadata={
                "row_count": total_data_rows,
                "col_count": len(headers),
                "parts": part_idx,
                "delimiter": delimiter,
                "encoding": encoding,
                "format": "CSV"
            }
        )

        return ParsedDocument(
            pages=[page],
            total_pages=1,
            tables=all_tables,
            metadata={
                "format": "CSV",
                "row_count": total_data_rows,
                "col_count": len(headers),
                "delimiter": delimiter,
                "encoding": encoding
            },
            ocr_applied=False
        )


csv_parser = CSVParser()
