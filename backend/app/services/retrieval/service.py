import time
import uuid
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentVersion
from app.models.organization import Organization
from app.services.retrieval.query_normalizer import query_normalizer, NormalizedQuery
from app.services.retrieval.keyword_search import keyword_search_engine
from app.services.retrieval.dense_search import dense_search_engine
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval.reranker import local_reranker

logger = logging.getLogger(__name__)

class RetrievalResult:
    """
    Standardized, provenance-preserving result object consumed by
    Knowledge Explorer, grounded Q&A (Phase 6), and Report Studio (Phase 7).
    """
    def __init__(
        self,
        result_id: str,
        chunk_id: str,
        document_id: str,
        document_version_id: Optional[str],
        organization_id: str,
        organization_name: Optional[str],
        title: str,
        document_type: str,
        source_tier: str,
        fiscal_year: Optional[str],
        page_number: int,
        chunk_type: str,
        section_heading: Optional[str],
        source_text: str,
        retrieval_method: str,
        keyword_rank: Optional[int],
        keyword_score: Optional[float],
        dense_rank: Optional[int],
        dense_score: Optional[float],
        rrf_score: float,
        reranker_score: Optional[float],
        final_rank: int,
        provenance: Dict[str, Any]
    ):
        self.result_id = result_id
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.document_version_id = document_version_id
        self.organization_id = organization_id
        self.organization_name = organization_name
        self.title = title
        self.document_type = document_type
        self.source_tier = source_tier
        self.fiscal_year = fiscal_year
        self.page_number = page_number
        self.chunk_type = chunk_type
        self.section_heading = section_heading
        self.source_text = source_text
        self.retrieval_method = retrieval_method
        self.keyword_rank = keyword_rank
        self.keyword_score = keyword_score
        self.dense_rank = dense_rank
        self.dense_score = dense_score
        self.rrf_score = rrf_score
        self.reranker_score = reranker_score
        self.final_rank = final_rank
        self.provenance = provenance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_version_id": self.document_version_id,
            "organization_id": self.organization_id,
            "organization_name": self.organization_name,
            "title": self.title,
            "document_type": self.document_type,
            "source_tier": self.source_tier,
            "fiscal_year": self.fiscal_year,
            "page_number": self.page_number,
            "chunk_type": self.chunk_type,
            "section_heading": self.section_heading,
            "source_text": self.source_text,
            "retrieval_method": self.retrieval_method,
            "keyword_rank": self.keyword_rank,
            "keyword_score": self.keyword_score,
            "dense_rank": self.dense_rank,
            "dense_score": self.dense_score,
            "rrf_score": self.rrf_score,
            "reranker_score": self.reranker_score,
            "final_rank": self.final_rank,
            "provenance": self.provenance
        }


class RetrievalService:
    """
    Unified Hybrid Retrieval Coordinator for KOYLA.
    Coordinates Query Normalization -> Scope/Filter Validation -> Dual Engine Search
    -> RRF Fusion -> Cross-Encoder Reranking -> Provenance-Enriched Results & Trace.
    """

    def retrieve(
        self,
        db: Session,
        query: str,
        allowed_org_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        search_mode: str = "HYBRID", # "HYBRID", "KEYWORD", "SEMANTIC"
        top_k: int = 10,
        enable_reranker: bool = True
    ) -> Dict[str, Any]:
        overall_start = time.perf_counter()
        filters = dict(filters or {})

        # 1. Query Normalization
        t_norm_start = time.perf_counter()
        norm_query: NormalizedQuery = query_normalizer.normalize(query)
        t_norm_ms = (time.perf_counter() - t_norm_start) * 1000.0

        # Keep user filters explicit; suggested filters remain visible in normalized query trace
        effective_query = norm_query.clean_query or query
        candidate_pool_size = max(top_k * 3, 30)

        keyword_results = []
        dense_results = []
        t_kw_ms = 0.0
        t_dense_ms = 0.0

        # 2. Dual Search Paths
        if search_mode in ["HYBRID", "KEYWORD"]:
            t_kw_start = time.perf_counter()
            keyword_results = keyword_search_engine.search(
                db=db,
                query=effective_query,
                allowed_org_ids=allowed_org_ids,
                filters=filters,
                top_k=candidate_pool_size
            )
            t_kw_ms = (time.perf_counter() - t_kw_start) * 1000.0

        if search_mode in ["HYBRID", "SEMANTIC"]:
            t_dense_start = time.perf_counter()
            dense_results = dense_search_engine.search(
                db=db,
                query=query, # dense search benefits from natural language query
                allowed_org_ids=allowed_org_ids,
                filters=filters,
                top_k=candidate_pool_size
            )
            t_dense_ms = (time.perf_counter() - t_dense_start) * 1000.0

        # 3. Fusion or Selection
        t_rrf_start = time.perf_counter()
        if search_mode == "HYBRID":
            fused_candidates = reciprocal_rank_fusion.fuse(
                keyword_results=keyword_results,
                dense_results=dense_results,
                top_k=candidate_pool_size
            )
        elif search_mode == "KEYWORD":
            fused_candidates = []
            for r in keyword_results:
                fused_candidates.append({
                    **r,
                    "keyword_rank": r.get("rank"),
                    "keyword_score": r.get("score"),
                    "dense_rank": None,
                    "dense_score": None,
                    "rrf_score": round(1.0 / (60 + r.get("rank", 1)), 6),
                    "retrieval_method": "KEYWORD"
                })
        else: # SEMANTIC
            fused_candidates = []
            for r in dense_results:
                fused_candidates.append({
                    **r,
                    "keyword_rank": None,
                    "keyword_score": None,
                    "dense_rank": r.get("rank"),
                    "dense_score": r.get("score"),
                    "rrf_score": round(1.0 / (60 + r.get("rank", 1)), 6),
                    "retrieval_method": "DENSE"
                })
        t_rrf_ms = (time.perf_counter() - t_rrf_start) * 1000.0

        # 4. Local Cross-Encoder Reranking
        t_rerank_start = time.perf_counter()
        if enable_reranker and search_mode == "HYBRID" and fused_candidates:
            reranked_candidates, reranker_status = local_reranker.rerank(
                query=query,
                candidates=fused_candidates,
                top_k=top_k
            )
        else:
            reranked_candidates = fused_candidates[:top_k]
            for c in reranked_candidates:
                c["reranker_score"] = None
            reranker_status = "DISABLED" if not enable_reranker else "BYPASSED"
        t_rerank_ms = (time.perf_counter() - t_rerank_start) * 1000.0

        # 5. Enrich with Provenance and Organization Metadata
        # Pre-fetch organization names
        org_ids = list(set(c["organization_id"] for c in reranked_candidates))
        org_map = {}
        if org_ids:
            orgs = db.query(Organization.id, Organization.name).filter(Organization.id.in_(org_ids)).all()
            org_map = {o[0]: o[1] for o in orgs}

        # Pre-fetch latest document versions
        doc_ids = list(set(c["document_id"] for c in reranked_candidates))
        version_map = {}
        if doc_ids:
            vers = db.query(DocumentVersion).filter(DocumentVersion.document_id.in_(doc_ids)).all()
            for v in vers:
                version_map[v.document_id] = v.id

        final_results: List[RetrievalResult] = []
        for idx, item in enumerate(reranked_candidates):
            c_meta = item.get("metadata_json") or {}
            c_type = item.get("chunk_type", "TEXT")
            p_num = item.get("page_number", 1)

            # Extract fiscal year if mentioned in content or metadata
            fy_match = None
            import re
            fy_in_content = re.findall(r'\b(?:FY\s*)?(20\d{2}[-/]\d{2,4})\b', item.get("content", ""), re.IGNORECASE)
            if fy_in_content:
                fy_match = f"FY{fy_in_content[0]}"
            elif filters.get("fiscal_year"):
                fy_match = filters["fiscal_year"]

            # Structure-preserving table provenance
            table_info = None
            if c_type == "TABLE":
                table_info = {
                    "logical_table_id": c_meta.get("logical_table_id"),
                    "table_index": c_meta.get("table_index"),
                    "caption": c_meta.get("caption") or item.get("section_heading"),
                    "part_number": c_meta.get("part", 1),
                    "total_parts": c_meta.get("total_parts", 1),
                    "pages_spanned": c_meta.get("pages", [p_num]),
                    "headers": c_meta.get("headers", []),
                    "row_count": c_meta.get("row_count", 0)
                }

            provenance_chain = {
                "document_id": item["document_id"],
                "document_title": item["document_title"],
                "version_id": version_map.get(item["document_id"]),
                "page_number": p_num,
                "chunk_id": item["chunk_id"],
                "chunk_type": c_type,
                "section_heading": item.get("section_heading"),
                "table": table_info
            }

            res = RetrievalResult(
                result_id=str(uuid.uuid4()),
                chunk_id=item["chunk_id"],
                document_id=item["document_id"],
                document_version_id=version_map.get(item["document_id"]),
                organization_id=item["organization_id"],
                organization_name=org_map.get(item["organization_id"], "Unknown Unit"),
                title=item["document_title"],
                document_type=item["document_type"],
                source_tier=item["source_tier"],
                fiscal_year=fy_match,
                page_number=p_num,
                chunk_type=c_type,
                section_heading=item.get("section_heading"),
                source_text=item.get("content", ""),
                retrieval_method=item.get("retrieval_method", search_mode),
                keyword_rank=item.get("keyword_rank"),
                keyword_score=item.get("keyword_score"),
                dense_rank=item.get("dense_rank"),
                dense_score=item.get("dense_score"),
                rrf_score=item.get("rrf_score", 0.0),
                reranker_score=item.get("reranker_score"),
                final_rank=idx + 1,
                provenance=provenance_chain
            )
            final_results.append(res)

        total_ms = (time.perf_counter() - overall_start) * 1000.0

        trace = {
            "trace_id": str(uuid.uuid4()),
            "query": query,
            "normalized_query": norm_query.to_dict(),
            "applied_filters": filters,
            "search_mode": search_mode,
            "keyword_candidate_count": len(keyword_results),
            "dense_candidate_count": len(dense_results),
            "fused_candidate_count": len(fused_candidates),
            "reranker_status": reranker_status,
            "embedding_provider": {
                "provider": dense_search_engine.embedding_provider.model_info().get("provider"),
                "model_name": dense_search_engine.embedding_provider.model_name,
                "is_neural": dense_search_engine.embedding_provider.model_info().get("is_neural", False)
            },
            "timings_ms": {
                "query_normalization": round(t_norm_ms, 2),
                "keyword_search": round(t_kw_ms, 2),
                "dense_search": round(t_dense_ms, 2),
                "rrf_fusion": round(t_rrf_ms, 2),
                "reranking": round(t_rerank_ms, 2),
                "total": round(total_ms, 2)
            }
        }

        return {
            "results": [r.to_dict() for r in final_results],
            "trace": trace
        }

retrieval_service = RetrievalService()
