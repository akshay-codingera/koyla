import traceback
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document import Document, ProcessingJob, DocumentPage, Table, TableRow
from app.models.chunk import Chunk
from app.models.verification import VerificationTask
from app.services.parsers import get_parser_for_file
from app.services.chunking import chunking_service
from app.services.table_intelligence import table_intelligence_service
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.audit import log_audit_event

def process_document(document_id: str, job_id: str):
    """
    Worker task to process an ingested document.
    Executes parsing, table continuation detection, structure-preserving chunking,
    structured extraction, domain validation, and reconciliation.
    """
    db: Session = SessionLocal()
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        doc = db.query(Document).filter(Document.id == document_id).first()
        
        if not job or not doc:
            return
            
        job.status = "PROCESSING"
        job.started_at = datetime.utcnow()
        job.progress_pct = 10
        doc.status = "PROCESSING"
        db.commit()
        
        # 1. Parse document
        parser = get_parser_for_file(doc.mime_type, doc.original_filename)
        job.progress_pct = 25
        db.commit()
        
        parsed_doc = parser.parse(doc.file_path)
        job.progress_pct = 50
        db.commit()
        
        # 2. Persist Document Pages
        for page in parsed_doc.pages:
            db_page = DocumentPage(
                document_id=doc.id,
                page_number=page.page_number,
                extracted_text=page.text,
                ocr_applied=page.ocr_applied,
                confidence_score=page.confidence,
                width=page.width,
                height=page.height,
                metadata_json=page.metadata
            )
            db.add(db_page)
            
            # Check for low confidence OCR
            if page.ocr_applied and (page.confidence is not None and page.confidence < 0.6):
                verification_task = VerificationTask(
                    task_type="LOW_CONFIDENCE_OCR",
                    organization_id=doc.organization_id,
                    document_id=doc.id,
                    target_id=db_page.id,
                    status="PENDING",
                    review_notes=f"Low OCR confidence score ({page.confidence}) on Page {page.page_number} requiring human verification"
                )
                db.add(verification_task)
                
        # 3. Table Continuation Intelligence & Persistence
        parsed_doc.tables = table_intelligence_service.detect_continuations(parsed_doc.tables)
        
        table_id_map = {}  # (page_number, table_index) -> db_table.id
        logical_row_counters = {}  # logical_table_id -> int

        for table in parsed_doc.tables:
            continuation_of_id = None
            if table.is_continuation and table.continuation_of_idx is not None:
                continuation_of_id = table_id_map.get((table.page_number - 1, table.continuation_of_idx))

            db_table = Table(
                document_id=doc.id,
                page_number=table.page_number,
                table_index=table.table_index,
                caption=table.caption,
                headers=table.headers,
                row_count=len(table.rows),
                col_count=len(table.headers) if table.headers else (len(table.rows[0]) if table.rows else 0),
                logical_table_id=table.logical_table_id,
                is_continuation=table.is_continuation,
                continuation_of_id=continuation_of_id,
                part_number=table.part_number,
                total_parts=table.total_parts,
                has_repeated_headers=table.has_repeated_headers,
                continuation_confidence=table.continuation_confidence,
                continuation_status=table.continuation_status,
                metadata_json=table.metadata
            )
            db.add(db_table)
            db.flush()  # get db_table.id
            table_id_map[(table.page_number, table.table_index)] = db_table.id
            
            # Row persistence with logical row index and page provenance
            start_logical_row = logical_row_counters.get(table.logical_table_id, 0)
            for r_idx, row_cells in enumerate(table.rows):
                src_page = (
                    table.row_pages[r_idx]
                    if (table.row_pages and r_idx < len(table.row_pages))
                    else table.page_number
                )
                db_row = TableRow(
                    table_id=db_table.id,
                    row_index=r_idx + 1,
                    logical_row_index=start_logical_row + r_idx + 1,
                    source_page=src_page,
                    cells=row_cells
                )
                db.add(db_row)
            logical_row_counters[table.logical_table_id] = start_logical_row + len(table.rows)

            # Flag ambiguous continuations for human review
            if table.continuation_status == "REVIEW_REQUIRED":
                sig_info = table.metadata.get("continuation_signals", {})
                sig_summary = sig_info.get("summary", f"Score: {table.continuation_confidence}")
                v_task = VerificationTask(
                    task_type="TABLE_CONTINUATION_REVIEW",
                    organization_id=doc.organization_id,
                    document_id=doc.id,
                    target_id=db_table.id,
                    status="PENDING",
                    review_notes=f"Ambiguous table continuation detected between Page {table.page_number - 1} and Page {table.page_number} ({sig_summary}). Verification required."
                )
                db.add(v_task)
                
        # 4. Chunking
        job.progress_pct = 70
        db.commit()
        
        chunks = chunking_service.chunk_document(parsed_doc, doc.id)
        for c in chunks:
            db_chunk = Chunk(
                document_id=c.document_id,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                chunk_type=c.chunk_type,
                content=c.content,
                section_heading=c.section_heading,
                metadata_json=c.metadata_json
            )
            db.add(db_chunk)
        db.commit()

        # 4.5 Dense Vector Indexing (pgvector)
        job.progress_pct = 75
        db.commit()
        from app.services.indexing import indexing_service
        try:
            index_res = indexing_service.index_document_chunks(db, doc.id)
        except Exception as e:
            # Fallback defensively so ingestion never crashes if embedding is unconfigured
            index_res = {"indexed_count": 0, "error": str(e)}

        # 5. Structured Extraction, Validation & Reconciliation
        job.progress_pct = 85
        db.commit()
        
        extraction_pipeline = ExtractionPipeline()
        extraction_run = extraction_pipeline.run_pipeline(db, doc.id, doc.organization_id)
            
        # 6. Finalize Job & Document
        job.status = "COMPLETED"
        job.progress_pct = 100
        job.completed_at = datetime.utcnow()
        doc.status = "COMPLETED"
        doc.updated_at = datetime.utcnow()
        db.commit()
        
        log_audit_event(
            db=db,
            action="DOCUMENT_PROCESSED",
            actor_id=doc.created_by,
            organization_id=doc.organization_id,
            object_type="document",
            object_id=doc.id,
            sha256_hash=doc.sha256_hash,
            details={
                "pages": len(parsed_doc.pages),
                "tables": len(parsed_doc.tables),
                "chunks": len(chunks),
                "ocr_applied": parsed_doc.ocr_applied,
                "fields_extracted": extraction_run.fields_extracted_count
            }
        )
        
    except Exception as e:
        db.rollback()
        err = traceback.format_exc()
        if job:
            job.status = "FAILED"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
        if doc:
            doc.status = "FAILED"
            doc.updated_at = datetime.utcnow()
        db.commit()
        
        if doc:
            log_audit_event(
                db=db,
                action="DOCUMENT_PROCESSING_FAILED",
                actor_id=doc.created_by,
                organization_id=doc.organization_id,
                object_type="document",
                object_id=doc.id,
                sha256_hash=doc.sha256_hash,
                details={"error": str(e), "traceback": err}
            )
    finally:
        db.close()
