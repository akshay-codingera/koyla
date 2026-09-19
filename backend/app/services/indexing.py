import time
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.document import Document
from app.models.chunk import Chunk, Embedding
from app.services.embedding import get_embedding_provider
from app.core.config import settings

logger = logging.getLogger(__name__)

class IndexingService:
    """
    Service responsible for generating and persisting dense pgvector embeddings
    for document chunks, ensuring safe re-indexing, duplicate prevention, and batching.
    """

    def __init__(self):
        self.embedding_provider = get_embedding_provider()

    def index_document_chunks(self, db: Session, document_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Generate and persist embeddings for all chunks of a document.
        If force is True, overwrites existing embeddings for the current model.
        """
        start_time = time.perf_counter()
        
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()
        if not chunks:
            return {
                "document_id": document_id,
                "total_chunks": 0,
                "indexed_count": 0,
                "skipped_count": 0,
                "failed_count": 0,
                "status": "COMPLETED",
                "time_taken_ms": 0.0,
                "model_name": self.embedding_provider.model_name
            }

        if force:
            db.query(Embedding).filter(Embedding.chunk_id.in_([c.id for c in chunks])).delete(synchronize_session=False)
            db.flush()
            existing_embeddings = {}
        else:
            existing_embeddings = {
                emb.chunk_id: emb for emb in db.query(Embedding).filter(
                    Embedding.chunk_id.in_([c.id for c in chunks]),
                    Embedding.model_name == self.embedding_provider.model_name
                ).all()
            }

        chunks_to_embed: List[Chunk] = []
        for c in chunks:
            if c.id in existing_embeddings:
                pass
            else:
                chunks_to_embed.append(c)

        indexed_count = 0
        failed_count = 0

        if chunks_to_embed:
            # Batch embedding generation
            batch_size = getattr(settings, "EMBEDDING_BATCH_SIZE", 32)
            for i in range(0, len(chunks_to_embed), batch_size):
                batch = chunks_to_embed[i:i + batch_size]
                texts = [c.content for c in batch]
                try:
                    vectors = self.embedding_provider.embed_batch(texts)
                    for chunk_obj, vec in zip(batch, vectors):
                        emb = Embedding(
                            chunk_id=chunk_obj.id,
                            model_name=self.embedding_provider.model_name,
                            dimensions=self.embedding_provider.dimension,
                            embedding_version=self.embedding_provider.version,
                            vector_data=vec
                        )
                        db.add(emb)
                        indexed_count += 1
                except Exception as e:
                    logger.error(f"Failed to generate embeddings for batch in doc {document_id}: {e}")
                    failed_count += len(batch)

            db.commit()

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        skipped_count = len(chunks) - len(chunks_to_embed)
        status = "COMPLETED" if failed_count == 0 else ("PARTIAL" if indexed_count > 0 else "FAILED")

        return {
            "document_id": document_id,
            "total_chunks": len(chunks),
            "indexed_count": indexed_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "model_name": self.embedding_provider.model_name,
            "dimensions": self.embedding_provider.dimension,
            "version": self.embedding_provider.version,
            "time_taken_ms": round(duration_ms, 2),
            "status": status
        }

    def reindex_all(self, db: Session, force: bool = False) -> Dict[str, Any]:
        """Re-index all documents across all organizations that have chunks."""
        start_time = time.perf_counter()
        docs = db.query(Document).filter(Document.chunks.any()).all()
        
        total_docs = len(docs)
        total_chunks = 0
        total_indexed = 0
        total_failed = 0

        for doc in docs:
            res = self.index_document_chunks(db, doc.id, force=force)
            total_chunks += res["total_chunks"]
            total_indexed += res["indexed_count"]
            total_failed += res["failed_count"]

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "total_indexed": total_indexed,
            "total_failed": total_failed,
            "time_taken_ms": round(duration_ms, 2),
            "model_name": self.embedding_provider.model_name
        }

    def delete_document_embeddings(self, db: Session, document_id: str) -> int:
        """Safely delete all embeddings for a document's chunks."""
        chunks = db.query(Chunk.id).filter(Chunk.document_id == document_id).all()
        chunk_ids = [c[0] for c in chunks]
        if not chunk_ids:
            return 0
        deleted = db.query(Embedding).filter(Embedding.chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
        db.commit()
        return deleted

    def get_status(self, db: Session) -> Dict[str, Any]:
        """Retrieve overall vector index status and database counts."""
        total_chunks = db.query(func.count(Chunk.id)).scalar() or 0
        total_embeddings = db.query(func.count(Embedding.id)).scalar() or 0
        distinct_embedded_chunks = db.query(func.count(func.distinct(Embedding.chunk_id))).scalar() or 0

        provider_info = self.embedding_provider.model_info()
        health_info = self.embedding_provider.health()

        from app.services.embedding.sentence_transformer import LocalSentenceTransformerProvider
        from app.core.config import settings
        neural_probe = LocalSentenceTransformerProvider(
            model_name=getattr(settings, "NEURAL_MODEL_NAME", "BAAI/bge-small-en-v1.5"),
            model_path=getattr(settings, "NEURAL_MODEL_PATH", None),
            dimension=settings.EMBEDDING_DIMENSION
        )
        neural_health = neural_probe.health()

        return {
            "total_chunks": total_chunks,
            "total_embeddings": total_embeddings,
            "distinct_embedded_chunks": distinct_embedded_chunks,
            "coverage_pct": round((distinct_embedded_chunks / total_chunks * 100.0), 1) if total_chunks > 0 else 0.0,
            "provider_info": provider_info,
            "health": health_info,
            "neural_model_availability": {
                "target_model": getattr(settings, "NEURAL_MODEL_NAME", "BAAI/bge-small-en-v1.5"),
                "status": neural_health.get("status"),
                "available": neural_health.get("available", False),
                "detail": neural_health.get("detail") or ("Loaded from " + str(neural_health.get("local_path")) if neural_health.get("available") else "SentenceTransformer weights unprovisioned")
            }
        }

indexing_service = IndexingService()
