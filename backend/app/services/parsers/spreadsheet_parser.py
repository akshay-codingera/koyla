from pathlib import Path
from typing import List, Any
import openpyxl
from app.services.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParsedTable

class SpreadsheetParser(BaseParser):
    def can_handle(self, mime_type: str, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        if ext == ".xls":
            return False
        return ext == ".xlsx" or "openxmlformats-officedocument.spreadsheetml" in mime_type

    def parse(self, file_path: str) -> ParsedDocument:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        pages: List[ParsedPage] = []
        all_tables: List[ParsedTable] = []
        
        try:
            for s_idx, sheet_name in enumerate(wb.sheetnames):
                sheet = wb[sheet_name]
                page_num = s_idx + 1
                
                rows_data: List[List[Any]] = []
                for row in sheet.iter_rows(values_only=True):
                    # Check if row has any non-None value
                    if any(cell is not None for cell in row):
                        # Clean cell values
                        cleaned_row = [str(c).strip() if c is not None else "" for c in row]
                        rows_data.append(cleaned_row)
                        
                if not rows_data:
                    # Empty sheet
                    pages.append(
                        ParsedPage(
                            page_number=page_num,
                            text=f"Sheet: {sheet_name} (Empty)",
                            ocr_applied=False,
                            confidence=1.0,
                            tables=[],
                            metadata={"sheet_name": sheet_name, "empty": True}
                        )
                    )
                    continue
                    
                headers = rows_data[0]
                # If header is empty string, provide fallback
                headers = [h if h else f"Col_{i+1}" for i, h in enumerate(headers)]
                data_rows = rows_data[1:]
                
                parsed_table = ParsedTable(
                    page_number=page_num,
                    table_index=1,
                    caption=f"Sheet: {sheet_name}",
                    headers=headers,
                    rows=data_rows,
                    metadata={"sheet_name": sheet_name, "row_count": len(data_rows), "col_count": len(headers)}
                )
                all_tables.append(parsed_table)
                
                # Generate human-readable structured sheet text
                text_lines = [f"# Sheet: {sheet_name}", f"Headers: {' | '.join(headers)}", "Data:"]
                for r in data_rows[:100]:  # up to 100 rows in text summary
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
                        metadata={"sheet_name": sheet_name, "row_count": len(data_rows)}
                    )
                )
                
            return ParsedDocument(
                pages=pages,
                total_pages=len(pages),
                tables=all_tables,
                metadata={
                    "format": "Spreadsheet",
                    "sheet_count": len(wb.sheetnames),
                    "sheet_names": wb.sheetnames
                },
                ocr_applied=False
            )
        finally:
            wb.close()

spreadsheet_parser = SpreadsheetParser()
