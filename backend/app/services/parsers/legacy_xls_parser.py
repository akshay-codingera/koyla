from pathlib import Path
from typing import List, Any
import xlrd
from app.services.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParsedTable

class LegacyXLSParser(BaseParser):
    """
    Parser for legacy Excel binary files (.xls / BIFF8 format) using xlrd.
    openpyxl does not support .xls files.
    """
    def can_handle(self, mime_type: str, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        if ext == ".xls":
            return True
        if ext == ".xlsx":
            return False
        return "ms-excel" in mime_type and not ("openxmlformats" in mime_type)

    def parse(self, file_path: str) -> ParsedDocument:
        # Open workbook with xlrd (ignore formatting info to avoid BIFF font issues)
        book = xlrd.open_workbook(file_path, formatting_info=False)
        pages: List[ParsedPage] = []
        all_tables: List[ParsedTable] = []

        try:
            for s_idx in range(book.nsheets):
                sheet = book.sheet_by_index(s_idx)
                sheet_name = sheet.name
                page_num = s_idx + 1

                rows_data: List[List[Any]] = []
                for r_idx in range(sheet.nrows):
                    row_vals = []
                    for c_idx in range(sheet.ncols):
                        cell = sheet.cell(r_idx, c_idx)
                        if cell.ctype == xlrd.XL_CELL_NUMBER:
                            # If it's an integer value represented as float, cast to int
                            val = int(cell.value) if cell.value.is_integer() else cell.value
                            row_vals.append(str(val))
                        elif cell.ctype == xlrd.XL_CELL_DATE:
                            try:
                                date_tuple = xlrd.xldate_as_tuple(cell.value, book.datemode)
                                row_vals.append(f"{date_tuple[0]:04d}-{date_tuple[1]:02d}-{date_tuple[2]:02d}")
                            except Exception:
                                row_vals.append(str(cell.value))
                        elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                            row_vals.append("TRUE" if cell.value else "FALSE")
                        elif cell.ctype == xlrd.XL_CELL_EMPTY:
                            row_vals.append("")
                        else:
                            row_vals.append(str(cell.value).strip())

                    # If row has any non-empty value
                    if any(v for v in row_vals):
                        rows_data.append(row_vals)

                if not rows_data:
                    pages.append(
                        ParsedPage(
                            page_number=page_num,
                            text=f"Sheet: {sheet_name} (Empty)",
                            ocr_applied=False,
                            confidence=1.0,
                            tables=[],
                            metadata={"sheet_name": sheet_name, "empty": True, "format": "XLS"}
                        )
                    )
                    continue

                headers = rows_data[0]
                headers = [h if h else f"Col_{i+1}" for i, h in enumerate(headers)]
                data_rows = rows_data[1:]

                parsed_table = ParsedTable(
                    page_number=page_num,
                    table_index=1,
                    caption=f"Sheet: {sheet_name}",
                    headers=headers,
                    rows=data_rows,
                    metadata={
                        "sheet_name": sheet_name,
                        "row_count": len(data_rows),
                        "col_count": len(headers),
                        "format": "XLS_LEGACY",
                        "range": f"A1:{chr(ord('A') + min(len(headers) - 1, 25))}{len(rows_data)}"
                    }
                )
                all_tables.append(parsed_table)

                # Generate structured text representation for BM25 and vector search
                text_lines = [
                    f"# Sheet: {sheet_name} [Legacy XLS]",
                    f"Headers: {' | '.join(headers)}",
                    "Data:"
                ]
                for r in data_rows[:100]:
                    text_lines.append(" | ".join(r))
                if len(data_rows) > 100:
                    text_lines.append(f"... ({len(data_rows) - 100} more rows)")

                page_text = "\n".join(text_lines)

                pages.append(
                    ParsedPage(
                        page_number=page_num,
                        text=page_text,
                        ocr_applied=False,
                        confidence=1.0,
                        tables=[parsed_table],
                        metadata={
                            "sheet_name": sheet_name,
                            "row_count": len(data_rows),
                            "format": "XLS_LEGACY"
                        }
                    )
                )

            return ParsedDocument(
                pages=pages,
                total_pages=len(pages),
                tables=all_tables,
                metadata={
                    "format": "Legacy XLS (BIFF8)",
                    "sheet_count": book.nsheets,
                    "sheet_names": book.sheet_names()
                },
                ocr_applied=False
            )
        finally:
            book.release_resources()

legacy_xls_parser = LegacyXLSParser()
