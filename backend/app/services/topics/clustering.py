"""
Deterministic Clustering and Outlier Isolation Engine for Topic Analysis.
Uses local dense embeddings (BAAI/bge-small-en-v1.5) with TruncatedSVD and KMeans.
Enforces fixed random_state=42 and deterministic distance-based outlier isolation.
"""

import logging
from collections import Counter
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_distances, cosine_similarity

from app.services.embedding import get_embedding_provider

logger = logging.getLogger(__name__)

DEFAULT_RANDOM_STATE = 42

class TopicClusterer:
    """
    Performs deterministic dimensionality reduction, clustering, and outlier detection.
    """

    def __init__(
        self,
        random_state: int = DEFAULT_RANDOM_STATE,
        outlier_z_threshold: float = 1.5,
        max_cosine_distance: float = 0.65,
        min_cluster_size: int = 2,
    ):
        self.random_state = random_state
        self.outlier_z_threshold = outlier_z_threshold
        self.max_cosine_distance = max_cosine_distance
        self.min_cluster_size = min_cluster_size

    def cluster_items(
        self,
        items: List[Dict[str, Any]],
        target_clusters: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Cluster corpus items and identify outliers.
        Returns:
            {
                "assignments": List[int], # Cluster ID per item (-1 for outliers)
                "cluster_counts": Dict[int, int],
                "outlier_count": int,
                "n_clusters": int,
                "centroids": np.ndarray,
                "embeddings": np.ndarray,
                "reduced_embeddings": np.ndarray,
                "similarity_scores": List[float],
            }
        """
        N = len(items)
        if N == 0:
            return {
                "assignments": [],
                "cluster_counts": {},
                "outlier_count": 0,
                "n_clusters": 0,
                "similarity_scores": [],
            }

        # 1. Obtain dense embeddings (BAAI/bge-small-en-v1.5)
        embeddings = self._get_embeddings(items)

        # 2. Determine number of clusters k
        if target_clusters is not None:
            k = max(2, min(target_clusters, N - 1))
        else:
            # Heuristic for topics based on corpus size
            if N <= 5:
                k = 2
            elif N <= 15:
                k = min(3, N - 1)
            elif N <= 50:
                k = min(4, N - 1)
            else:
                k = min(6, int(np.sqrt(N / 2)))
            k = max(2, min(k, N - 1))

        # 3. Dimensionality reduction via TruncatedSVD if N > k
        if N > 5:
            n_comp = min(10, N - 1)
            svd = TruncatedSVD(n_components=n_comp, random_state=self.random_state)
            reduced = svd.fit_transform(embeddings)
        else:
            reduced = embeddings

        # 4. Deterministic KMeans clustering
        kmeans = KMeans(
            n_clusters=k,
            random_state=self.random_state,
            n_init=10,
            algorithm="lloyd",
        )
        raw_labels = kmeans.fit_predict(reduced)
        centroids = kmeans.cluster_centers_

        # 5. Outlier Detection
        # Compute cosine distance of each sample to its assigned cluster centroid
        sample_distances = np.zeros(N)
        similarities = np.zeros(N)

        for i in range(N):
            cluster_id = raw_labels[i]
            centroid = centroids[cluster_id]
            # Reshape for 2D distance calculation
            dist = float(cosine_distances(reduced[i : i + 1], centroid.reshape(1, -1))[0, 0])
            sim = float(cosine_similarity(reduced[i : i + 1], centroid.reshape(1, -1))[0, 0])
            sample_distances[i] = dist
            similarities[i] = max(0.0, sim)

        mean_dist = float(np.mean(sample_distances))
        std_dist = float(np.std(sample_distances)) if N > 1 else 0.0

        raw_counts = Counter(raw_labels)
        effective_min_size = self.min_cluster_size if N >= 4 else 1

        assignments = []
        outlier_count = 0
        cluster_counts = {}

        for i in range(N):
            raw_cid = int(raw_labels[i])
            dist = sample_distances[i]
            # Flag outlier if cluster is undersized (e.g. singleton isolated item) or distance exceeds thresholds
            is_under_sized = (raw_counts[raw_cid] < effective_min_size)
            is_dist_outlier = (dist > self.max_cosine_distance) or (std_dist > 0 and dist > mean_dist + self.outlier_z_threshold * std_dist)

            if (is_under_sized or is_dist_outlier) and N >= 4:
                assignments.append(-1)
                outlier_count += 1
            else:
                assignments.append(raw_cid)
                cluster_counts[raw_cid] = cluster_counts.get(raw_cid, 0) + 1

        # Check if any cluster became empty after outlier removal; if so, re-index clusters
        active_clusters = sorted([c for c, count in cluster_counts.items() if count > 0])
        cluster_map = {old_c: new_c for new_c, old_c in enumerate(active_clusters)}
        cluster_map[-1] = -1

        final_assignments = [cluster_map.get(a, -1) for a in assignments]
        final_cluster_counts = {cluster_map[c]: count for c, count in cluster_counts.items() if count > 0}

        return {
            "assignments": final_assignments,
            "cluster_counts": final_cluster_counts,
            "outlier_count": outlier_count,
            "n_clusters": len(final_cluster_counts),
            "centroids": centroids,
            "embeddings": embeddings,
            "reduced_embeddings": reduced,
            "similarity_scores": similarities.tolist(),
            "clustering_config": {
                "algorithm": "KMeans",
                "random_state": self.random_state,
                "n_init": 10,
                "target_clusters": k,
                "min_cluster_size": self.min_cluster_size,
                "outlier_z_threshold": self.outlier_z_threshold,
                "max_cosine_distance": self.max_cosine_distance,
            },
        }

    def _get_embeddings(self, items: List[Dict[str, Any]]) -> np.ndarray:
        """Fetch or generate 384-dimensional embeddings using the local provider."""
        texts = [item.get("cleaned_text") or item.get("raw_text") or "" for item in items]
        provider = get_embedding_provider()
        emb_list = provider.embed_batch(texts)
        arr = np.array(emb_list, dtype=np.float32)
        # Normalize vectors for cosine consistency
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

topic_clusterer = TopicClusterer()
