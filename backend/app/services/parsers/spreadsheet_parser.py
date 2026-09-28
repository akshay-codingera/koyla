import uuid
from pathlib import Path
from typing import List, Any, Optional
import openpyxl
from app.services.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParsedTable


class SpreadsheetParser(BaseParser):
    """
    Hardened Spreadsheet Parser for Excel (.xlsx) workbooks.
    Features:
    - Memory-conscious read_only streaming mode
    - Incremental sheet iteration without full DOM instantiation
    - Configurable chunk size for very large sheets
    - Table provenance preservation across workbook sheets
    - Fallback to standard loader if read_only fails
    """
    DEFAULT_CHUNK_SIZE = 2000

    def can_handle(self, mime_type: str, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        if ext == ".xls":
            return False
        return ext == ".xlsx" or "openxmlformats-officedocument.spreadsheetml" in mime_type

    def parse(self, file_path: str, chunk_size: Optional[int] = None) -> ParsedDocument:
        chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        
        # Attempt memory-efficient read_only streaming first
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            read_only_mode = True
        except Exception:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            read_only_mode = False

        pages: List[ParsedPage] = []
        all_tables: List[ParsedTable] = []

        try:
            for s_idx, sheet_name in enumerate(wb.sheetnames):
                sheet = wb[sheet_name]
                page_num = s_idx + 1

                headers: Optional[List[str]] = None
                current_chunk_rows: List[List[Any]] = []
                sheet_tables: List[ParsedTable] = []
                total_data_rows = 0
                first_100_rows: List[List[str]] = []
                sheet_logical_id = str(uuid.uuid4())
                part_idx = 0

                row_iter = sheet.iter_rows(values_only=True)
                for row in row_iter:
                    # Filter completely empty rows
                    if not any(cell is not None for cell in row):
                        continue

                    cleaned_row = [str(c).strip() if c is not None else "" for c in row]

                    if headers is None:
                        headers = [h if h else f"Col_{i+1}" for i, h in enumerate(cleaned_row)]
                        continue

                    current_chunk_rows.append(cleaned_row)
                    total_data_rows += 1

                    if len(first_100_rows) < 100:
                        first_100_rows.append(cleaned_row)

                    # Chunking for very large sheets
                    if len(current_chunk_rows) >= chunk_size:
                        part_idx += 1
                        caption = f"Sheet: {sheet_name}" if part_idx == 1 else f"Sheet: {sheet_name} (Part {part_idx})"
                        table_part = ParsedTable(
                            page_number=page_num,
                            table_index=part_idx,
                            caption=caption,
                            headers=headers,
                            rows=current_chunk_rows,
                            logical_table_id=sheet_logical_id,
                            is_continuation=part_idx > 1,
                            part_number=part_idx,
                            metadata={
                                "sheet_name": sheet_name,
                                "row_count": len(current_chunk_rows),
                                "col_count": len(headers),
                                "part_number": part_idx,
                                "logical_table_id": sheet_logical_id,
                                "is_continuation": part_idx > 1,
                                "read_only_mode": read_only_mode
                            }
                        )
                        sheet_tables.append(table_part)
                        all_tables.append(table_part)
                        current_chunk_rows = []

                if headers is None:
                    # Empty sheet
                    pages.append(
                        ParsedPage(
                            page_number=page_num,
                            text=f"Sheet: {sheet_name} (Empty)",
                            ocr_applied=False,
                            confidence=1.0,
                            tables=[],
                            metadata={"sheet_name": sheet_name, "empty": True, "read_only_mode": read_only_mode}
                        )
                    )
                    continue

                # Add final / remaining chunk
                if current_chunk_rows or not sheet_tables:
                    part_idx += 1
                    caption = f"Sheet: {sheet_name}" if part_idx == 1 else f"Sheet: {sheet_name} (Part {part_idx})"
                    table_part = ParsedTable(
                        page_number=page_num,
                        table_index=part_idx,
                        caption=caption,
                        headers=headers,
                        rows=current_chunk_rows,
                        logical_table_id=sheet_logical_id,
                        is_continuation=part_idx > 1,
                        part_number=part_idx,
                        metadata={
                            "sheet_name": sheet_name,
                            "row_count": len(current_chunk_rows),
                            "col_count": len(headers),
                            "part_number": part_idx,
                            "logical_table_id": sheet_logical_id,
                            "is_continuation": part_idx > 1,
                            "read_only_mode": read_only_mode
                        }
                    )
                    sheet_tables.append(table_part)
                    all_tables.append(table_part)

                # Generate structured sheet text summary
                text_lines = [f"# Sheet: {sheet_name}", f"Headers: {' | '.join(headers)}", "Data:"]
                for r in first_100_rows:
                    text_lines.append(" | ".join(r))
                if total_data_rows > 100:
                    text_lines.append(f"... ({total_data_rows - 100} more rows)")

                page_text = "\n".join(text_lines)

                pages.append(
                    ParsedPage(
                        page_number=page_num,
                        text=page_text,
                        ocr_applied=False,
                        confidence=1.0,
                        tables=sheet_tables,
                        metadata={
                            "sheet_name": sheet_name,
                            "row_count": total_data_rows,
                            "parts": part_idx,
                            "read_only_mode": read_only_mode
                        }
                    )
                )

            return ParsedDocument(
                pages=pages,
                total_pages=len(pages),
                tables=all_tables,
                metadata={
                    "format": "Spreadsheet",
                    "sheet_count": len(wb.sheetnames),
                    "sheet_names": wb.sheetnames,
                    "read_only_mode": read_only_mode
                },
                ocr_applied=False
            )
        finally:
            wb.close()


spreadsheet_parser = SpreadsheetParser()
