import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentPage, Table, TableRow
from app.models.chunk import Chunk
from app.models.extraction import ExtractionRun, ExtractedField, ValidationResult
from app.models.verification import VerificationTask
from app.services.extraction.rule_based import RuleBasedExtractionProvider
from app.services.extraction.local_llm import LocalLLMExtractionProvider
from app.services.validation.validator import ValidationService
from app.services.reconciliation.reconciler import ReconciliationService

logger = logging.getLogger(__name__)

class ExtractionPipeline:
    """
    Central orchestration service for document extraction, validation, and reconciliation.
    Executes rule-based extraction and local LLM adaptation, computes confidence,
    enforces physical source-page provenance, triggers domain validation, and queues verification tasks.
    """

    def __init__(self):
        self.rule_provider = RuleBasedExtractionProvider()
        self.llm_provider = LocalLLMExtractionProvider()
        self.validator = ValidationService()
        self.reconciler = ReconciliationService()

    def run_pipeline(
        self,
        db: Session,
        document_id: str,
        organization_id: Optional[str] = None
    ) -> ExtractionRun:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found.")

        org_id = organization_id or doc.organization_id

        # 1. Create extraction run
        run = ExtractionRun(
            document_id=document_id,
            provider="RULE_BASED",
            status="RUNNING",
            started_at=datetime.utcnow()
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            # 2. Fetch document components
            chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
            tables = db.query(Table).filter(Table.document_id == document_id).all()
            pages = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).all()

            # Ensure table rows are loaded
            for t in tables:
                rows = db.query(TableRow).filter(TableRow.table_id == t.id).order_by(TableRow.row_index).all()
                t.table_rows = rows

            # 3. Extract candidates via Rule-based provider
            candidates = self.rule_provider.extract(chunks=chunks, tables=tables, pages=pages)

            # 4. Attempt Local LLM provider if available
            llm_available = self.llm_provider.check_availability()
            if llm_available:
                llm_candidates = self.llm_provider.extract(chunks=chunks, tables=tables, pages=pages)
                candidates.extend(llm_candidates)
                run.provider = "HYBRID"
            else:
                run.metadata_json = {"local_llm_status": "MODEL_UNAVAILABLE"}

            # 5. Deduplicate candidates by (field_name, normalized_value, page_number)
            unique_candidates = []
            seen = set()
            for cand in candidates:
                key = (cand.field_name, str(cand.normalized_value).strip().lower(), cand.page_number)
                if key not in seen:
                    seen.add(key)
                    unique_candidates.append(cand)

            # 6. Persist ExtractedFields and run validation
            created_fields: List[ExtractedField] = []
            for cand in unique_candidates:
                field = ExtractedField(
                    extraction_run_id=run.id,
                    organization_id=org_id,
                    document_id=document_id,
                    field_name=cand.field_name,
                    field_category=cand.field_category,
                    data_type=cand.data_type,
                    raw_value=cand.raw_value,
                    normalized_value=cand.normalized_value,
                    numeric_value=cand.numeric_value,
                    unit=cand.unit,
                    page_number=cand.page_number,
                    table_id=cand.table_id,
                    row_id=cand.row_id,
                    chunk_id=cand.chunk_id,
                    source_text=cand.source_text,
                    extraction_method=cand.extraction_method,
                    confidence_score=cand.confidence_score,
                    confidence_level=cand.confidence_level,
                    metadata_json=cand.metadata
                )
                db.add(field)
                db.flush()

                # Run validation
                val_results = self.validator.validate_field(field)
                for vr in val_results:
                    db.add(vr)

                # Queue verification task for low confidence
                if field.confidence_level == "LOW" or field.confidence_score < 0.60:
                    task = VerificationTask(
                        task_type="LOW_CONFIDENCE_EXTRACTION",
                        organization_id=org_id,
                        document_id=document_id,
                        field_id=field.id,
                        status="PENDING",
                        evidence_context={
                            "field_name": field.field_name,
                            "raw_value": field.raw_value,
                            "confidence_score": field.confidence_score,
                            "source_page": field.page_number,
                            "source_text": field.source_text
                        }
                    )
                    db.add(task)

                # Queue verification task for validation ERROR
                if field.validation_status == "ERROR":
                    err_msgs = [vr.message for vr in val_results if vr.status == "ERROR"]
                    task = VerificationTask(
                        task_type="VALIDATION_ERROR",
                        organization_id=org_id,
                        document_id=document_id,
                        field_id=field.id,
                        status="PENDING",
                        evidence_context={
                            "field_name": field.field_name,
                            "raw_value": field.raw_value,
                            "errors": err_msgs,
                            "source_page": field.page_number,
                            "source_text": field.source_text
                        }
                    )
                    db.add(task)

                created_fields.append(field)

            # 7. Complete run
            run.status = "COMPLETED"
            run.fields_extracted_count = len(created_fields)
            run.completed_at = datetime.utcnow()
            db.commit()

            # 8. Run cross-document reconciliation for the organization
            try:
                self.reconciler.reconcile_organization_fields(db, org_id)
            except Exception as rec_err:
                logger.warning(f"Reconciliation check warning: {rec_err}")

            return run

        except Exception as e:
            db.rollback()
            run.status = "FAILED"
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            db.add(run)
            db.commit()
            logger.error(f"Extraction pipeline failed for document {document_id}: {e}", exc_info=True)
            raise
