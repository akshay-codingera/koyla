"""
Topic Quality Diagnostics Service for KOYLA.

Metrics Calculated:
1. semantic_topic_coherence:
   "This is a KOYLA semantic similarity diagnostic based on cosine similarity
    between embeddings of top topic terms. It is not an externally standardized topic-coherence score."
2. topic_diversity:
   Proportion of unique terms across the top terms of all discovered topics.
3. cluster_size_distribution:
   Summary statistics (min, max, mean, median, std_dev) of chunks per topic.

Note: In accordance with enterprise engineering standards, these metrics are
presented strictly as diagnostics and are never referred to as "accuracy".
"""

import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity
from app.services.embedding import get_embedding_provider

class TopicQualityEvaluator:
    """
    Computes diagnostic quality metrics for discovered topics.
    """

    def evaluate(
        self,
        topics_data: Dict[int, Dict[str, Any]],
        cluster_sizes: Dict[int, int],
    ) -> Dict[str, Any]:
        """
        Evaluate semantic coherence, diversity, and size distribution across topics.
        topics_data: mapping from topic_id/index to topic dictionary containing 'top_terms'.
        cluster_sizes: mapping from topic_id/index to chunk count.
        """
        if not topics_data:
            return {
                "mean_semantic_coherence": 0.0,
                "topic_diversity": 0.0,
                "cluster_size_distribution": {
                    "min": 0, "max": 0, "mean": 0.0, "median": 0.0, "std_dev": 0.0
                },
                "diagnostic_note": "This is a KOYLA semantic similarity diagnostic based on cosine similarity between embeddings of top topic terms. It is not an externally standardized topic-coherence score.",
            }

        # 1. Compute semantic_topic_coherence per topic
        coherences: List[float] = []
        topic_top_terms: List[List[str]] = []

        for tid, tinfo in topics_data.items():
            terms = [t["term"] for t in tinfo.get("top_terms", [])[:10]]
            topic_top_terms.append(terms)
            coh = self._compute_topic_semantic_coherence(terms)
            tinfo["semantic_topic_coherence"] = round(coh, 4)
            coherences.append(coh)

        mean_coherence = float(np.mean(coherences)) if coherences else 0.0

        # 2. Compute topic_diversity
        diversity = self._compute_topic_diversity(topic_top_terms)

        # 3. Compute cluster_size_distribution
        sizes = [count for tid, count in cluster_sizes.items() if count > 0]
        if sizes:
            size_dist = {
                "min": int(np.min(sizes)),
                "max": int(np.max(sizes)),
                "mean": round(float(np.mean(sizes)), 2),
                "median": float(np.median(sizes)),
                "std_dev": round(float(np.std(sizes)), 2),
            }
        else:
            size_dist = {"min": 0, "max": 0, "mean": 0.0, "median": 0.0, "std_dev": 0.0}

        return {
            "mean_semantic_coherence": round(mean_coherence, 4),
            "topic_diversity": round(diversity, 4),
            "cluster_size_distribution": size_dist,
            "diagnostic_note": "This is a KOYLA semantic similarity diagnostic based on cosine similarity between embeddings of top topic terms. It is not an externally standardized topic-coherence score.",
        }

    def _compute_topic_semantic_coherence(self, terms: List[str]) -> float:
        """
        Compute mean pairwise cosine similarity between embeddings of top terms.
        """
        if len(terms) < 2:
            return 1.0

        provider = get_embedding_provider()
        term_vecs = provider.embed_batch(terms)
        arr = np.array(term_vecs, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = arr / norms

        sim_matrix = cosine_similarity(normalized)
        # Extract upper triangle without diagonal
        upper_indices = np.triu_indices(len(terms), k=1)
        pairwise_sims = sim_matrix[upper_indices]

        return float(np.mean(pairwise_sims)) if len(pairwise_sims) > 0 else 1.0

    def _compute_topic_diversity(self, all_topic_terms: List[List[str]]) -> float:
        """
        Compute proportion of unique words across top terms of all topics.
        """
        total_term_instances = sum(len(terms) for terms in all_topic_terms)
        if total_term_instances == 0:
            return 0.0

        unique_terms = set()
        for terms in all_topic_terms:
            unique_terms.update(terms)

        return len(unique_terms) / float(total_term_instances)

topic_quality_evaluator = TopicQualityEvaluator()
