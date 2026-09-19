"""
Topic Analysis Foundation Job Runner (Phase 8.1).
Orchestrates corpus query, deterministic cleaning, SHA-256 fingerprinting,
and analysis persistence without running topic modeling algorithms.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.topic import TopicAnalysis
from app.services.topics.corpus_service import corpus_service
from app.services.topics.hashing import compute_corpus_hash
from app.services.topics.preprocessor import PREPROCESSOR_VERSION

logger = logging.getLogger(__name__)

class TopicFoundationJob:
    """
    Executes Phase 8.1 foundation analysis workflow.
    """

    def execute(
        self,
        db: Session,
        analysis_id: str,
        allowed_org_ids: Optional[List[str]] = None,
    ) -> TopicAnalysis:
        """
        Execute the foundation corpus preparation and fingerprinting job.
        """
        start_time = time.perf_counter()
        analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
        if not analysis:
            raise ValueError(f"TopicAnalysis record '{analysis_id}' not found")

        try:
            # 1. State: RUNNING (10%)
            analysis.status = "RUNNING"
            analysis.progress_pct = 10
            db.commit()
            db.refresh(analysis)

            # 2. Query Corpus (40%)
            corpus_res = corpus_service.build_corpus(
                db=db,
                allowed_org_ids=allowed_org_ids,
                filters=analysis.corpus_filters or {},
            )
            analysis.progress_pct = 40
            db.commit()

            # 3. Text Preparation & Validation (70%)
            items = corpus_res["items"]
            doc_count = corpus_res["total_documents"]
            chunk_count = corpus_res["total_chunks"]
            chunk_ids = corpus_res["chunk_ids"]
            doc_ids = corpus_res["document_ids"]

            analysis.progress_pct = 70
            db.commit()

            # 4. Deterministic Corpus Hash Computation (90%)
            corpus_hash = compute_corpus_hash(
                chunk_ids=chunk_ids,
                document_ids=doc_ids,
                filters=corpus_res["effective_filters"],
                preprocessor_version=PREPROCESSOR_VERSION,
                embedding_model=analysis.embedding_model,
                analysis_method=analysis.analysis_method,
                parameters=analysis.parameters,
            )
            analysis.progress_pct = 90
            db.commit()

            # 5. Complete Foundation or Execute Topic Discovery (100%)
            end_time = time.perf_counter()
            analysis.corpus_hash = corpus_hash
            analysis.document_count = doc_count
            analysis.chunk_count = chunk_count
            analysis.runtime_seconds = round(end_time - start_time, 3)
            analysis.completed_at = datetime.utcnow()
            analysis.error_message = None

            # If analysis_method is explicitly "FOUNDATION", keep topics table empty (Phase 8.1)
            if analysis.analysis_method == "FOUNDATION":
                analysis.outlier_count = 0
                analysis.status = "COMPLETED"
                analysis.progress_pct = 100
            else:
                # Phase 8.2: Run Topic Discovery Engine
                from app.services.topics.topic_engine import topic_engine
                disc_res = topic_engine.discover_topics(
                    db=db,
                    analysis=analysis,
                    corpus_res=corpus_res,
                    requested_method=analysis.analysis_method,
                )
                if disc_res.get("status") == "INSUFFICIENT_CORPUS":
                    analysis.status = "INSUFFICIENT_CORPUS"
                    analysis.progress_pct = 100
                else:
                    analysis.status = "COMPLETED"
                    analysis.progress_pct = 100

            db.commit()
            db.refresh(analysis)
            logger.info(
                f"Topic analysis foundation completed successfully: id={analysis.id}, "
                f"docs={doc_count}, chunks={chunk_count}, hash={corpus_hash[:16]}..."
            )
            return analysis

        except Exception as e:
            logger.exception(f"Topic foundation job failed for analysis {analysis_id}: {e}")
            analysis.status = "FAILED"
            analysis.error_message = str(e)
            analysis.progress_pct = 0
            db.commit()
            db.refresh(analysis)
            raise e

foundation_job = TopicFoundationJob()
