import time
import math
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.models.chunk import Chunk, Embedding
from app.models.document import Document
from app.services.embedding import get_embedding_provider

logger = logging.getLogger(__name__)

class DenseSearchEngine:
    """
    pgvector Dense Semantic Retrieval Engine.
    Generates local query vector embeddings and computes cosine similarity
    against chunk embeddings stored in PostgreSQL.
    Enforces server-side organization isolation before returning results.
    """

    def __init__(self):
        self.embedding_provider = get_embedding_provider()

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

        # 1. Generate local query embedding
        try:
            query_vector = self.embedding_provider.embed_text(query)
        except Exception as e:
            logger.warning(f"Dense search embedding generation failed: {e}")
            return []

        # 2. Base Query joining Chunk, Embedding, and Document
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
            Embedding.vector_data
        ).join(
            Embedding, Embedding.chunk_id == Chunk.id
        ).join(
            Document, Document.id == Chunk.document_id
        ).filter(
            Embedding.model_name == self.embedding_provider.model_name
        )

        # 3. Server-Side Organization Scoping
        if allowed_org_ids is not None:
            q = q.filter(Document.organization_id.in_(allowed_org_ids))

        # 4. Metadata Filters
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

        # 5. Execute pgvector cosine similarity search
        is_postgres = "postgresql" in str(db.bind.url).lower() if db.bind else True
        results: List[Dict[str, Any]] = []

        if is_postgres:
            try:
                # pgvector cosine distance operator <=>
                cosine_dist_expr = Embedding.vector_data.cosine_distance(query_vector)
                rows = q.order_by(cosine_dist_expr).limit(top_k).all()

                for r in rows:
                    # Cosine distance ranges [0, 2]; similarity = 1 - (dist / 2) or 1 / (1 + dist)
                    # For unit normalized vectors: cosine similarity in [-1, 1], dist = 1 - cos_sim
                    # Let's compute cosine similarity accurately:
                    if r.vector_data is not None:
                        # pgvector allows calculating similarity directly
                        v = [float(x) for x in r.vector_data]
                        dot = sum(a * b for a, b in zip(query_vector, v))
                        norm_q = math.sqrt(sum(a * a for a in query_vector))
                        norm_v = math.sqrt(sum(b * b for b in v))
                        sim = (dot / (norm_q * norm_v)) if (norm_q * norm_v) > 0 else 0.0
                        score = round(max(0.0, min(1.0, (sim + 1.0) / 2.0)), 4)
                    else:
                        score = 0.5

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
                        "method": "DENSE"
                    })
            except Exception as e:
                logger.warning(f"PostgreSQL pgvector query failed, falling back to python similarity: {e}")
                is_postgres = False

        if not is_postgres:
            # Fallback for SQLite / unit tests
            rows = q.all()
            scored_rows = []
            for r in rows:
                if r.vector_data is not None:
                    v = [float(x) for x in r.vector_data]
                    dot = sum(a * b for a, b in zip(query_vector, v))
                    norm_q = math.sqrt(sum(a * a for a in query_vector))
                    norm_v = math.sqrt(sum(b * b for b in v))
                    sim = (dot / (norm_q * norm_v)) if (norm_q * norm_v) > 0 else 0.0
                    score = round(max(0.0, min(1.0, (sim + 1.0) / 2.0)), 4)
                else:
                    score = 0.0
                scored_rows.append((score, r))

            scored_rows.sort(key=lambda x: x[0], reverse=True)
            for score, r in scored_rows[:top_k]:
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
                    "method": "DENSE"
                })

        # Assign ranks 1..N
        for idx, res in enumerate(results):
            res["rank"] = idx + 1

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        logger.debug(f"Dense search for '{query}' returned {len(results)} chunks in {duration_ms:.2f}ms")
        return results

dense_search_engine = DenseSearchEngine()
