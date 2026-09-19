from typing import List, Dict, Any, Optional
from app.core.config import settings

class ReciprocalRankFusion:
    """
    Reciprocal Rank Fusion (RRF) for merging keyword (lexical) and dense (semantic) candidate lists.
    Calculates: RRF(d) = sum(w_m / (k + rank_m(d)))
    Preserves exact individual ranks, individual scores, and combined RRF scores.
    """

    def __init__(
        self,
        k: int = None,
        keyword_weight: float = None,
        dense_weight: float = None
    ):
        self.k = k if k is not None else getattr(settings, "RRF_K", 60)
        self.keyword_weight = keyword_weight if keyword_weight is not None else getattr(settings, "RRF_KEYWORD_WEIGHT", 1.0)
        self.dense_weight = dense_weight if dense_weight is not None else getattr(settings, "RRF_DENSE_WEIGHT", 1.0)

    def fuse(
        self,
        keyword_results: List[Dict[str, Any]],
        dense_results: List[Dict[str, Any]],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        fused_map: Dict[str, Dict[str, Any]] = {}

        # 1. Process Keyword Results
        for kw in keyword_results:
            c_id = kw["chunk_id"]
            kw_rank = kw.get("rank", 1)
            kw_score = kw.get("score", 0.0)
            score_contrib = self.keyword_weight / (self.k + kw_rank)

            fused_map[c_id] = {
                "chunk_id": c_id,
                "document_id": kw["document_id"],
                "page_number": kw["page_number"],
                "chunk_type": kw["chunk_type"],
                "section_heading": kw.get("section_heading"),
                "content": kw["content"],
                "metadata_json": kw.get("metadata_json", {}),
                "document_title": kw.get("document_title"),
                "organization_id": kw["organization_id"],
                "document_type": kw.get("document_type"),
                "source_tier": kw.get("source_tier"),
                "keyword_rank": kw_rank,
                "keyword_score": kw_score,
                "dense_rank": None,
                "dense_score": None,
                "rrf_score": score_contrib,
                "retrieval_method": "KEYWORD"
            }

        # 2. Process Dense Results
        for dn in dense_results:
            c_id = dn["chunk_id"]
            dn_rank = dn.get("rank", 1)
            dn_score = dn.get("score", 0.0)
            score_contrib = self.dense_weight / (self.k + dn_rank)

            if c_id in fused_map:
                fused_map[c_id]["dense_rank"] = dn_rank
                fused_map[c_id]["dense_score"] = dn_score
                fused_map[c_id]["rrf_score"] += score_contrib
                fused_map[c_id]["retrieval_method"] = "HYBRID"
            else:
                fused_map[c_id] = {
                    "chunk_id": c_id,
                    "document_id": dn["document_id"],
                    "page_number": dn["page_number"],
                    "chunk_type": dn["chunk_type"],
                    "section_heading": dn.get("section_heading"),
                    "content": dn["content"],
                    "metadata_json": dn.get("metadata_json", {}),
                    "document_title": dn.get("document_title"),
                    "organization_id": dn["organization_id"],
                    "document_type": dn.get("document_type"),
                    "source_tier": dn.get("source_tier"),
                    "keyword_rank": None,
                    "keyword_score": None,
                    "dense_rank": dn_rank,
                    "dense_score": dn_score,
                    "rrf_score": score_contrib,
                    "retrieval_method": "DENSE"
                }

        # 3. Sort by RRF score descending
        fused_list = list(fused_map.values())
        fused_list.sort(key=lambda x: x["rrf_score"], reverse=True)

        for idx, item in enumerate(fused_list):
            item["rrf_score"] = round(item["rrf_score"], 6)
            item["fused_rank"] = idx + 1

        return fused_list[:top_k]

reciprocal_rank_fusion = ReciprocalRankFusion()
