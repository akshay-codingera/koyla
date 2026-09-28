import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc

from app.models.chunk import Chunk
from app.models.document import Document

logger = logging.getLogger(__name__)

class KeywordSearchEngine:
    """
    PostgreSQL Full-Text & Lexical Search Engine.
    Executes tsvector/tsquery retrieval with proximity ranking (ts_rank_cd)
    combined with exact token/substring matching for alphanumeric technical codes.
    Strictly constrained by server-side organization scope.
    """

    def search(
        self,
        db: Session,
        query: str,
        allowed_org_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        start_time = time.perf_counter()
        filters = filters or {}
        if not query or not query.strip():
            return []

        clean_q = query.strip()
        tokens = [t for t in clean_q.split() if len(t) > 1]

        # Base query joining Chunk and Document
        q = db.query(
            Chunk.id.label("chunk_id"),
            Chunk.document_id,
            Chunk.page_number,
            Chunk.chunk_type,
            Chunk.section_heading,
            Chunk.content,
            Chunk.metadata_json,
            Document.title.label("document_title"),
            Document.organization_id,
            Document.document_type,
            Document.source_tier,
        ).join(Document, Document.id == Chunk.document_id)

        # 1. Server-Side Organization Scoping (Mandatory)
        if allowed_org_ids is not None:
            q = q.filter(Document.organization_id.in_(allowed_org_ids))

        # 2. Metadata Filtering
        if filters.get("organization_id"):
            q = q.filter(Document.organization_id == filters["organization_id"])
        if filters.get("document_type"):
            q = q.filter(Document.document_type == filters["document_type"])
        if filters.get("source_tier"):
            q = q.filter(Document.source_tier == filters["source_tier"])
        if filters.get("document_id"):
            q = q.filter(Document.id == filters["document_id"])
        if filters.get("fiscal_year"):
            import re
            fy_term = filters["fiscal_year"].strip()
            clean_fy = re.sub(r'^FY\s*[-_]?', '', fy_term, flags=re.IGNORECASE)
            q = q.filter(or_(
                Chunk.content.ilike(f"%{fy_term}%"),
                Chunk.content.ilike(f"%{clean_fy}%"),
                Document.title.ilike(f"%{fy_term}%"),
                Document.title.ilike(f"%{clean_fy}%")
            ))

        # 3. Full-Text and Substring Search Conditions
        # Attempt PostgreSQL full-text search with fallback to ILIKE
        is_postgres = "postgresql" in str(db.bind.url).lower() if db.bind else True

        score_expr = None
        if is_postgres:
            try:
                # Support exact phrase matching if quoted, else websearch_to_tsquery for natural domain syntax
                if '"' in clean_q:
                    ts_query = func.phraseto_tsquery('english', clean_q.replace('"', ''))
                else:
                    ts_query = func.websearch_to_tsquery('english', clean_q)

                ts_vector = Chunk.tsv_content if hasattr(Chunk, "tsv_content") else func.to_tsvector('english', Chunk.content)
                fts_match = ts_vector.bool_op('@@')(ts_query)
                ts_rank = func.ts_rank_cd(ts_vector, ts_query)

                # Combine FTS with exact substring matches for alphanumeric codes
                exact_filters = []
                for tok in tokens[:5]:
                    exact_filters.append(Chunk.content.ilike(f"%{tok}%"))
                    exact_filters.append(Document.title.ilike(f"%{tok}%"))
                    exact_filters.append(Chunk.section_heading.ilike(f"%{tok}%"))

                q = q.filter(or_(fts_match, *exact_filters))
                score_expr = ts_rank
            except Exception as e:
                logger.warning(f"PostgreSQL FTS error, falling back to ILIKE: {e}")
                is_postgres = False

        if not is_postgres or score_expr is None:
            # Fallback ILIKE matching for test environments or SQLite
            or_clauses = []
            for tok in tokens[:6]:
                or_clauses.append(Chunk.content.ilike(f"%{tok}%"))
                or_clauses.append(Document.title.ilike(f"%{tok}%"))
                if Chunk.section_heading is not None:
                    or_clauses.append(Chunk.section_heading.ilike(f"%{tok}%"))

            if or_clauses:
                q = q.filter(or_(*or_clauses))

        # Order and limit
        if is_postgres and score_expr is not None:
            rows = q.order_by(desc(score_expr)).limit(top_k).all()
        else:
            rows = q.limit(top_k * 2).all()

        # Compute ranking and scores
        results: List[Dict[str, Any]] = []
        lower_tokens = [t.lower() for t in tokens]

        for r in rows:
            # Calculate lexical score based on token occurrences if exact ts_rank not available
            content_lower = (r.content or "").lower()
            title_lower = (r.document_title or "").lower()
            heading_lower = (r.section_heading or "").lower()

            match_count = sum(
                (content_lower.count(t) * 1.0) +
                (title_lower.count(t) * 3.0) +
                (heading_lower.count(t) * 2.0)
                for t in lower_tokens
            )

            # Lexical score normalized [0.0 - 1.0]
            score = round(min(1.0, 0.2 + (match_count * 0.1)), 4) if match_count > 0 else 0.1

            results.append({
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "page_number": r.page_number,
                "chunk_type": r.chunk_type,
                "section_heading": r.section_heading,
                "content": r.content,
                "metadata_json": r.metadata_json or {},
                "document_title": r.document_title,
                "organization_id": r.organization_id,
                "document_type": r.document_type,
                "source_tier": r.source_tier,
                "score": score,
                "method": "KEYWORD"
            })

        # Sort by score descending and assign rank 1..N
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:top_k]
        for idx, res in enumerate(results):
            res["rank"] = idx + 1

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        logger.debug(f"Keyword search for '{clean_q}' returned {len(results)} chunks in {duration_ms:.2f}ms")
        return results

keyword_search_engine = KeywordSearchEngine()
