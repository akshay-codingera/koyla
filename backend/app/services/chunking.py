from typing import List, Dict, Any
from app.services.parsers.base import ParsedDocument, ParsedPage, ParsedTable

class ChunkDTO:
    def __init__(
        self,
        document_id: str,
        chunk_index: int,
        page_number: int,
        chunk_type: str,
        content: str,
        section_heading: str = None,
        metadata_json: Dict[str, Any] = None
    ):
        self.document_id = document_id
        self.chunk_index = chunk_index
        self.page_number = page_number
        self.chunk_type = chunk_type
        self.content = content
        self.section_heading = section_heading
        self.metadata_json = metadata_json or {}

class ChunkingService:
    def __init__(self, target_chunk_size: int = 1000, max_table_rows_per_chunk: int = 25):
        self.target_chunk_size = target_chunk_size
        self.max_table_rows_per_chunk = max_table_rows_per_chunk

    def chunk_document(self, doc: ParsedDocument, document_id: str) -> List[ChunkDTO]:
        chunks: List[ChunkDTO] = []
        chunk_idx = 1
        
        for page in doc.pages:
            # 1. Text chunks for this page
            page_text = page.text.strip()
            if page_text:
                paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
                current_heading = None
                current_buf = []
                current_len = 0
                
                for para in paragraphs:
                    if para.startswith("#") or para.startswith("##") or para.startswith("SECTION:"):
                        current_heading = para.lstrip("#").strip().split("\n")[0][:200]
                        
                    if current_len + len(para) > self.target_chunk_size and current_buf:
                        content_block = "\n\n".join(current_buf)
                        chunks.append(
                            ChunkDTO(
                                document_id=document_id,
                                chunk_index=chunk_idx,
                                page_number=page.page_number,
                                chunk_type="TEXT",
                                content=content_block,
                                section_heading=current_heading,
                                metadata_json={
                                    "page_number": page.page_number,
                                    "char_count": len(content_block),
                                    "type": "text"
                                }
                            )
                        )
                        chunk_idx += 1
                        current_buf = [para]
                        current_len = len(para)
                    else:
                        current_buf.append(para)
                        current_len += len(para)
                        
                if current_buf:
                    content_block = "\n\n".join(current_buf)
                    chunks.append(
                        ChunkDTO(
                            document_id=document_id,
                            chunk_index=chunk_idx,
                            page_number=page.page_number,
                            chunk_type="TEXT",
                            content=content_block,
                            section_heading=current_heading,
                            metadata_json={
                                "page_number": page.page_number,
                                "char_count": len(content_block),
                                "type": "text"
                            }
                        )
                    )
                    chunk_idx += 1

            # 2. Text chunks for page completed above.

        # 2. Structure-preserving table chunks (grouped by logical table)
        # Collect all tables
        raw_tables = doc.tables if doc.tables else [t for p in doc.pages for t in p.tables]
        
        # Group tables by logical_table_id
        logical_groups: Dict[str, List[ParsedTable]] = {}
        for t in raw_tables:
            group_key = t.logical_table_id or f"single_{t.page_number}_{t.table_index}"
            if group_key not in logical_groups:
                logical_groups[group_key] = []
            logical_groups[group_key].append(t)

        for group_key, tbl_parts in logical_groups.items():
            first_tbl = tbl_parts[0]
            master_headers = first_tbl.headers
            header_str = " | ".join(str(h) for h in master_headers)
            caption = first_tbl.caption or f"Table {first_tbl.table_index}"

            # Aggregate all rows and their page provenance
            all_rows = []
            all_row_pages = []
            for part in tbl_parts:
                for r_idx, r in enumerate(part.rows):
                    all_rows.append(r)
                    p_num = part.row_pages[r_idx] if (part.row_pages and r_idx < len(part.row_pages)) else part.page_number
                    all_row_pages.append(p_num)

            distinct_pages = sorted(list(set(all_row_pages))) if all_row_pages else [first_tbl.page_number]
            is_multi_page = len(distinct_pages) > 1

            if len(all_rows) <= self.max_table_rows_per_chunk:
                row_lines = []
                for r, p in zip(all_rows, all_row_pages):
                    r_str = " | ".join(str(c) for c in r)
                    row_lines.append(f"[P.{p}] {r_str}" if is_multi_page else r_str)

                page_label = f"Pages {distinct_pages[0]}-{distinct_pages[-1]}" if is_multi_page else f"Page {distinct_pages[0]}"
                table_content = (
                    f"[TABLE: {caption} ({page_label})]\n"
                    f"Headers: {header_str}\n"
                    + "\n".join(row_lines)
                )

                chunks.append(
                    ChunkDTO(
                        document_id=document_id,
                        chunk_index=chunk_idx,
                        page_number=first_tbl.page_number,
                        chunk_type="TABLE",
                        content=table_content,
                        section_heading=caption,
                        metadata_json={
                            "logical_table_id": first_tbl.logical_table_id,
                            "page_number": first_tbl.page_number,
                            "table_index": first_tbl.table_index,
                            "caption": caption,
                            "headers": master_headers,
                            "row_count": len(all_rows),
                            "total_parts": len(tbl_parts),
                            "pages": distinct_pages,
                            "type": "table"
                        }
                    )
                )
                chunk_idx += 1
            else:
                # Large logical table split into chunks with repeated headers
                total_chunks = ((len(all_rows) - 1) // self.max_table_rows_per_chunk) + 1
                for i in range(0, len(all_rows), self.max_table_rows_per_chunk):
                    batch_rows = all_rows[i:i + self.max_table_rows_per_chunk]
                    batch_pages = all_row_pages[i:i + self.max_table_rows_per_chunk]
                    part_num = (i // self.max_table_rows_per_chunk) + 1

                    row_lines = []
                    for r, p in zip(batch_rows, batch_pages):
                        r_str = " | ".join(str(c) for c in r)
                        row_lines.append(f"[P.{p}] {r_str}" if is_multi_page else r_str)

                    chunk_pages = sorted(list(set(batch_pages))) if batch_pages else [first_tbl.page_number]
                    page_label = f"Pages {chunk_pages[0]}-{chunk_pages[-1]}" if len(chunk_pages) > 1 else f"Page {chunk_pages[0]}"

                    table_content = (
                        f"[TABLE: {caption} ({page_label}) - Part {part_num}/{total_chunks}]\n"
                        f"Headers: {header_str}\n"
                        + "\n".join(row_lines)
                    )

                    chunks.append(
                        ChunkDTO(
                            document_id=document_id,
                            chunk_index=chunk_idx,
                            page_number=chunk_pages[0],
                            chunk_type="TABLE",
                            content=table_content,
                            section_heading=f"{caption} (Part {part_num}/{total_chunks})",
                            metadata_json={
                                "logical_table_id": first_tbl.logical_table_id,
                                "page_number": chunk_pages[0],
                                "table_index": first_tbl.table_index,
                                "caption": caption,
                                "headers": master_headers,
                                "row_count": len(batch_rows),
                                "part": part_num,
                                "total_parts": total_chunks,
                                "pages": chunk_pages,
                                "type": "table"
                            }
                        )
                    )
                    chunk_idx += 1

        return chunks

chunking_service = ChunkingService()
