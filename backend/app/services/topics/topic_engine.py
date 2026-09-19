"""
Central Topic Modeling Engine for KOYLA (Phase 8.2).
Provides corpus-size adaptive discovery, deterministic c-TF-IDF, relational provenance,
outlier isolation, and semantic quality diagnostics.
"""

import math
import uuid
import logging
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
import numpy as np

from app.models.topic import TopicAnalysis, Topic, TopicTerm, TopicDocument, TopicEvidence
from app.models.chunk import Chunk
from app.models.document import Document
from app.services.topics.c_tfidf import c_tfidf_transformer
from app.services.topics.clustering import topic_clusterer, DEFAULT_RANDOM_STATE
from app.services.topics.quality_metrics import topic_quality_evaluator

logger = logging.getLogger(__name__)

# Minimum thresholds for meaningful topic extraction
MIN_DOCUMENTS_THRESHOLD = 2
MIN_CHUNKS_THRESHOLD = 3

class TopicEngine:
    """
    Coordinates local topic discovery, method adaptation, and relational database persistence.
    """

    def discover_topics(
        self,
        db: Session,
        analysis: TopicAnalysis,
        corpus_res: Dict[str, Any],
        requested_method: Optional[str] = None,
        target_clusters: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute topic discovery on assembled corpus.
        """
        items: List[Dict[str, Any]] = corpus_res.get("items", [])
        total_chunks = len(items)
        unique_docs = corpus_res.get("document_ids", [])
        total_docs = len(unique_docs)

        # 1. Small-Corpus Safety Refusal
        if total_chunks < MIN_CHUNKS_THRESHOLD or total_docs < MIN_DOCUMENTS_THRESHOLD:
            refusal_reason = "INSUFFICIENT CORPUS FOR TOPIC MODELING"
            analysis.status = "INSUFFICIENT_CORPUS"
            analysis.document_count = total_docs
            analysis.chunk_count = total_chunks
            analysis.outlier_count = 0
            analysis.error_message = refusal_reason
            analysis.parameters = {
                **(analysis.parameters or {}),
                "minimum_threshold": {
                    "documents": MIN_DOCUMENTS_THRESHOLD,
                    "chunks": MIN_CHUNKS_THRESHOLD,
                },
                "recommended_action": "Ingest at least 2 documents with 3 or more content chunks for topic extraction",
            }
            db.commit()
            db.refresh(analysis)
            return {
                "status": "INSUFFICIENT_CORPUS",
                "message": refusal_reason,
                "document_count": total_docs,
                "chunk_count": total_chunks,
                "minimum_threshold": {
                    "documents": MIN_DOCUMENTS_THRESHOLD,
                    "chunks": MIN_CHUNKS_THRESHOLD,
                },
                "recommended_action": "Ingest at least 2 documents with 3 or more content chunks for topic extraction",
            }

        # 2. Adaptive Method Selection based on corpus size
        method = self._select_method(total_chunks, requested_method or analysis.analysis_method)
        logger.info(f"Selected topic discovery method '{method}' for corpus of {total_chunks} chunks ({total_docs} docs)")

        # 3. Clustering & Outlier Detection
        cluster_res = topic_clusterer.cluster_items(items, target_clusters=target_clusters)
        assignments = cluster_res["assignments"]
        outlier_count = cluster_res["outlier_count"]
        similarity_scores = cluster_res["similarity_scores"]

        # Group items by valid cluster (cluster >= 0)
        cluster_docs: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        chunk_sim_map: Dict[str, float] = {}

        for i, item in enumerate(items):
            cid = assignments[i]
            sim = similarity_scores[i] if i < len(similarity_scores) else 0.5
            chunk_sim_map[item["chunk_id"]] = sim
            if cid >= 0:
                cluster_docs[cid].append(item)

        # 4. Class-based TF-IDF term weighting & descriptive label generation
        c_tfidf_results = c_tfidf_transformer.fit_transform(cluster_docs, top_k_terms=10)

        # 5. Compute Quality Diagnostics (semantic_topic_coherence, diversity, size distribution)
        cluster_sizes = {cid: len(docs) for cid, docs in cluster_docs.items()}
        quality_eval = topic_quality_evaluator.evaluate(c_tfidf_results, cluster_sizes)

        # 6. Relational Database Persistence
        # Clean any preexisting topics for this analysis to prevent duplication
        db.query(Topic).filter(Topic.analysis_id == analysis.id).delete()

        created_topics = []
        for cid in sorted(c_tfidf_results.keys()):
            t_info = c_tfidf_results[cid]
            c_items = cluster_docs[cid]
            c_chunk_count = len(c_items)
            c_doc_ids = set(it["document_id"] for it in c_items)
            c_doc_count = len(c_doc_ids)
            prevalence = (c_chunk_count / float(total_chunks)) * 100.0 if total_chunks > 0 else 0.0

            topic = Topic(
                id=str(uuid.uuid4()),
                analysis_id=analysis.id,
                topic_index=cid,
                label=t_info["label"],
                document_count=c_doc_count,
                chunk_count=c_chunk_count,
                prevalence_pct=round(prevalence, 2),
                coherence_score=t_info.get("semantic_topic_coherence"),
                metadata_json={
                    "method": method,
                    "word_mass": t_info.get("word_mass", 0),
                    "outlier_count": outlier_count,
                },
            )
            db.add(topic)
            db.flush()

            # A. TopicTerms
            for term_data in t_info["top_terms"]:
                term_record = TopicTerm(
                    id=str(uuid.uuid4()),
                    topic_id=topic.id,
                    term=term_data["term"],
                    weight=term_data["weight"],
                    rank=term_data["rank"],
                    frequency=term_data.get("frequency", 0),
                    document_count=term_data.get("document_count", 0),
                )
                db.add(term_record)

            # B. TopicDocument associations
            doc_chunk_groups = defaultdict(list)
            for it in c_items:
                doc_chunk_groups[it["document_id"]].append(it)

            for d_id, d_chunks in doc_chunk_groups.items():
                d_sims = [chunk_sim_map.get(c["chunk_id"], 0.5) for c in d_chunks]
                avg_sim = float(np.mean(d_sims)) if d_sims else 0.5
                contrib = (len(d_chunks) / float(c_chunk_count)) * 100.0 if c_chunk_count > 0 else 0.0

                topic_doc = TopicDocument(
                    id=str(uuid.uuid4()),
                    topic_id=topic.id,
                    document_id=d_id,
                    similarity_score=round(avg_sim, 4),
                    contribution_pct=round(contrib, 2),
                )
                db.add(topic_doc)

            # C. TopicEvidence associations
            # Sort items by similarity score descending to prioritize strongest representatives
            sorted_c_items = sorted(
                c_items,
                key=lambda x: chunk_sim_map.get(x["chunk_id"], 0.0),
                reverse=True,
            )
            for it in sorted_c_items:
                evidence = TopicEvidence(
                    id=str(uuid.uuid4()),
                    topic_id=topic.id,
                    chunk_id=it["chunk_id"],
                    representative_score=round(chunk_sim_map.get(it["chunk_id"], 0.5), 4),
                )
                db.add(evidence)

            created_topics.append({
                "id": topic.id,
                "topic_index": topic.topic_index,
                "label": topic.label,
                "document_count": topic.document_count,
                "chunk_count": topic.chunk_count,
                "prevalence_pct": topic.prevalence_pct,
                "semantic_topic_coherence": topic.coherence_score,
                "top_terms": t_info["top_terms"],
            })

        # Update TopicAnalysis metadata
        analysis.analysis_method = method
        analysis.outlier_count = outlier_count
        analysis.quality_metrics = quality_eval
        analysis.parameters = {
            **(analysis.parameters or {}),
            "random_state": DEFAULT_RANDOM_STATE,
            "clustering_config": cluster_res.get("clustering_config", {}),
            "vectorizer_config": {
                "min_df": 1,
                "max_df_ratio": 0.95,
                "token_pattern": r"\b[a-zA-Z0-9_\-]+\b",
            },
        }
        db.commit()
        db.refresh(analysis)

        return {
            "status": "COMPLETED",
            "method": method,
            "embedding_model": analysis.embedding_model,
            "topic_count": len(created_topics),
            "document_count": total_docs,
            "chunk_count": total_chunks,
            "outlier_count": outlier_count,
            "quality_metrics": quality_eval,
            "topics": created_topics,
        }

    def _select_method(self, chunk_count: int, requested: Optional[str]) -> str:
        """Adaptive method selection preserving corpus-size awareness."""
        if requested and requested not in ["AUTO", "FOUNDATION"]:
            return requested
        if chunk_count < 10:
            return "TFIDF_KEYWORD"
        elif chunk_count < 50:
            return "NMF_TFIDF"
        else:
            return "EMBEDDING_CLUSTER_CTFIDF"

topic_engine = TopicEngine()
