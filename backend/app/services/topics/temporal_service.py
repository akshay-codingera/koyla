"""
Temporal and Comparative Topic Analytics Service for KOYLA.

Implements deterministic analysis of topic dynamics over fiscal years and across
operational dimensions (organizations, subsidiaries, mines, blocks, document types).
Enforces:
1. Single global topic model alignment
2. Exact separation of absolute count, percentage-point, and relative growth metrics
3. Minimum-evidence gates to guard against small-sample artifacts
4. Zero causal inference (strictly factual, empirical reporting)
5. Idempotent database persistence and query caching
"""

import re
import uuid
import logging
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.core.temporal import validate_fiscal_year_syntax
from app.models.topic import TopicAnalysis, Topic, TopicTerm, TopicDocument, TopicEvidence, TopicTrend, TopicComparison
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.organization import Organization
from app.services.topics.corpus_service import corpus_service

logger = logging.getLogger(__name__)

# Default evidence gate thresholds
DEFAULT_MIN_PERIOD_DOCS = 5
DEFAULT_MIN_TOPIC_DOCS = 2
DEFAULT_MIN_COMPARABLE_PERIODS = 2
DEFAULT_PP_THRESHOLD = 2.0  # percentage points


def parse_period_sort_key(period_str: str) -> Tuple[int, int]:
    """
    Returns a sortable integer tuple (start_year, sub_period) from a period string.
    Supports FY2023-24, 2023-24, CY2023, 2023.
    """
    p = period_str.strip()
    # FY YYYY-YY or YYYY-YY
    m_fy = re.match(r'^(?:(?:Q([1-4])|H([1-2]))\s+)?(?:FY\s*)?(\d{4})[-/](\d{2,4})$', p, re.IGNORECASE)
    if m_fy:
        quarter = int(m_fy.group(1)) if m_fy.group(1) else (int(m_fy.group(2)) * 2 if m_fy.group(2) else 0)
        start_year = int(m_fy.group(3))
        return (start_year, quarter)
    
    # CY YYYY or YYYY
    m_cy = re.match(r'^(?:CY\s*)?(\d{4})$', p, re.IGNORECASE)
    if m_cy:
        return (int(m_cy.group(1)), 0)
    
    return (9999, 0)


class TemporalTopicService:
    """
    Analytical engine computing temporal dynamics and multi-dimensional comparisons
    from a unified global topic model.
    """

    def compute_analysis_trends(
        self,
        db: Session,
        analysis_id: str,
        min_period_documents: int = DEFAULT_MIN_PERIOD_DOCS,
        min_topic_documents: int = DEFAULT_MIN_TOPIC_DOCS,
        percentage_point_threshold: float = DEFAULT_PP_THRESHOLD,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Computes or retrieves cached temporal trends for all topics in an analysis.
        """
        analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
        if not analysis:
            raise ValueError(f"TopicAnalysis '{analysis_id}' not found")

        # 1. Check cache if force_refresh is False
        if not force_refresh:
            existing_trends = db.query(TopicTrend).filter(TopicTrend.analysis_id == analysis_id).all()
            if existing_trends:
                logger.info(f"Returning {len(existing_trends)} cached TopicTrend records for analysis {analysis_id}")
                return self._format_trends_response(analysis, existing_trends, db=db)

        # 2. Extract corpus documents and chunks with period information
        topics = db.query(Topic).filter(Topic.analysis_id == analysis_id).order_by(Topic.topic_index).all()
        if not topics:
            return {
                "analysis_id": analysis_id,
                "status": "NO_TOPICS",
                "topics_analyzed": 0,
                "periods": [],
                "trends": [],
            }

        topic_ids = [t.id for t in topics]

        # Fetch evidence and documents
        evidence_rows = db.query(TopicEvidence).filter(TopicEvidence.topic_id.in_(topic_ids)).all()
        doc_assoc_rows = db.query(TopicDocument).filter(TopicDocument.topic_id.in_(topic_ids)).all()

        # Build mappings of chunk_id -> topic_id, doc_id -> set of topic_ids
        chunk_to_topic: Dict[str, str] = {ev.chunk_id: ev.topic_id for ev in evidence_rows}
        doc_to_topics: Dict[str, Set[str]] = defaultdict(set)
        for da in doc_assoc_rows:
            doc_to_topics[da.document_id].add(da.topic_id)

        # Get all chunk details from DB for this corpus
        all_chunk_ids = list(chunk_to_topic.keys())
        chunks = db.query(Chunk).filter(Chunk.id.in_(all_chunk_ids)).all() if all_chunk_ids else []
        chunk_map = {c.id: c for c in chunks}

        # Get all document details
        doc_ids_set = set(c.document_id for c in chunks).union(set(doc_to_topics.keys()))
        docs = db.query(Document).filter(Document.id.in_(list(doc_ids_set))).all() if doc_ids_set else []
        doc_map = {d.id: d for d in docs}

        # 3. Determine Period (Fiscal Year) per document and chunk
        doc_period_map: Dict[str, str] = {}
        chunk_period_map: Dict[str, str] = {}

        for doc_id, doc in doc_map.items():
            py = self._resolve_fiscal_year(doc=doc)
            doc_period_map[doc_id] = py

        for chunk_id, chunk in chunk_map.items():
            # Check chunk metadata first, then inherit from document
            c_meta = chunk.metadata_json or {}
            c_fy = c_meta.get("fiscal_year")
            if c_fy:
                valid, norm = validate_fiscal_year_syntax(c_fy)
                chunk_period_map[chunk_id] = norm if valid else doc_period_map.get(chunk.document_id, "UNSPECIFIED")
            else:
                chunk_period_map[chunk_id] = doc_period_map.get(chunk.document_id, "UNSPECIFIED")

        # 4. Compute Period Totals (Denominators)
        period_docs: Dict[str, Set[str]] = defaultdict(set)
        period_chunks: Dict[str, Set[str]] = defaultdict(set)

        for d_id, p_val in doc_period_map.items():
            if p_val != "UNSPECIFIED":
                period_docs[p_val].add(d_id)

        for c_id, p_val in chunk_period_map.items():
            if p_val != "UNSPECIFIED":
                period_chunks[p_val].add(c_id)

        all_periods = sorted(list(set(period_docs.keys()).union(set(period_chunks.keys()))), key=parse_period_sort_key)

        # 5. Clean prior trend records for this analysis
        db.query(TopicTrend).filter(TopicTrend.analysis_id == analysis_id).delete()

        created_trends: List[TopicTrend] = []

        # 6. Compute metrics per Topic per Period
        for topic in topics:
            t_id = topic.id
            prev_doc_share: Optional[float] = None
            prev_doc_count: Optional[int] = None
            history_presence: List[bool] = []

            for p_idx, period_val in enumerate(all_periods):
                p_tot_docs = len(period_docs[period_val])
                p_tot_chunks = len(period_chunks[period_val])

                # Documents belonging to this topic in this period
                topic_p_docs = [d_id for d_id in period_docs[period_val] if t_id in doc_to_topics.get(d_id, set())]
                topic_p_chunks = [c_id for c_id in period_chunks[period_val] if chunk_to_topic.get(c_id) == t_id]

                t_doc_count = len(topic_p_docs)
                t_chunk_count = len(topic_p_chunks)

                doc_share = round((t_doc_count / float(p_tot_docs) * 100.0), 2) if p_tot_docs > 0 else 0.0
                chunk_share = round((t_chunk_count / float(p_tot_chunks) * 100.0), 2) if p_tot_chunks > 0 else 0.0

                # Shifts compared to previous period
                abs_change: Optional[int] = None
                pp_change: Optional[float] = None
                rel_growth: Optional[float] = None

                if prev_doc_share is not None and prev_doc_count is not None:
                    abs_change = t_doc_count - prev_doc_count
                    pp_change = round(doc_share - prev_doc_share, 2)
                    if prev_doc_share > 0:
                        rel_growth = round(((doc_share - prev_doc_share) / prev_doc_share) * 100.0, 2)
                    else:
                        rel_growth = 100.0 if doc_share > 0 else 0.0

                is_present = (t_doc_count >= min_topic_documents)
                history_presence.append(is_present)

                # Determine Trend Status with Minimum-Evidence Gate
                trend_status = self._classify_trend(
                    period_index=p_idx,
                    total_periods=len(all_periods),
                    doc_share=doc_share,
                    prev_doc_share=prev_doc_share,
                    t_doc_count=t_doc_count,
                    prev_doc_count=prev_doc_count,
                    p_tot_docs=p_tot_docs,
                    prev_p_tot_docs=len(period_docs[all_periods[p_idx - 1]]) if p_idx > 0 else 0,
                    pp_change=pp_change,
                    history_presence=history_presence,
                    min_period_documents=min_period_documents,
                    min_topic_documents=min_topic_documents,
                    percentage_point_threshold=percentage_point_threshold,
                )

                trend = TopicTrend(
                    id=str(uuid.uuid4()),
                    analysis_id=analysis_id,
                    topic_id=t_id,
                    period_type="FISCAL_YEAR",
                    period_value=period_val,
                    document_count=t_doc_count,
                    chunk_count=t_chunk_count,
                    corpus_document_count=p_tot_docs,
                    corpus_chunk_count=p_tot_chunks,
                    document_share_pct=round(doc_share, 2),
                    chunk_share_pct=round(chunk_share, 2),
                    absolute_change=abs_change,
                    percentage_point_change=pp_change,
                    growth_rate_pct=rel_growth,
                    trend_status=trend_status,
                    metadata_json={
                        "topic_label": topic.label,
                        "min_period_documents_gate": min_period_documents,
                        "min_topic_documents_gate": min_topic_documents,
                    },
                )
                db.add(trend)
                created_trends.append(trend)

                prev_doc_share = doc_share
                prev_doc_count = t_doc_count

        db.commit()

        return self._format_trends_response(analysis, created_trends, db=db)

    def _resolve_fiscal_year(self, doc: Document) -> str:
        """Deterministically extracts or canonicalizes the fiscal year of a document."""
        # 1. From document title
        m = re.search(r'(?:FY\s*)?(\d{4})[-/](\d{2,4})', doc.title or "", re.IGNORECASE)
        if m:
            candidate = m.group(0)
            valid, norm = validate_fiscal_year_syntax(candidate)
            if valid and norm:
                return norm

        # 2. From creation date (Indian fiscal year: April 1 to March 31)
        if doc.created_at:
            year = doc.created_at.year
            month = doc.created_at.month
            if month >= 4:
                start_year = year
            else:
                start_year = year - 1
            return f"FY{start_year}-{(start_year + 1) % 100:02d}"

        return "UNSPECIFIED"

    def _classify_trend(
        self,
        period_index: int,
        total_periods: int,
        doc_share: float,
        prev_doc_share: Optional[float],
        t_doc_count: int,
        prev_doc_count: Optional[int],
        p_tot_docs: int,
        prev_p_tot_docs: int,
        pp_change: Optional[float],
        history_presence: List[bool],
        min_period_documents: int,
        min_topic_documents: int,
        percentage_point_threshold: float,
    ) -> str:
        """
        Applies deterministic trend classification rules with minimum evidence gates.
        """
        # Gate 1: First period has no preceding historical point
        if period_index == 0 or prev_doc_share is None or pp_change is None or prev_doc_count is None:
            return "INSUFFICIENT_HISTORY"

        # Gate 2: Minimum period documents in both periods
        if p_tot_docs < min_period_documents or prev_p_tot_docs < min_period_documents:
            return "INSUFFICIENT_HISTORY"

        # Gate 3: Check Recurring pattern (Present -> Absent -> Present) across >= 3 periods
        if len(history_presence) >= 3 and history_presence[-1] and not history_presence[-2] and any(history_presence[:-2]):
            return "RECURRING"

        # Gate 4: Emerging
        # Topic had 0 or negligible docs previously, and now establishes presence with >= min_topic_documents
        if prev_doc_count == 0 and t_doc_count >= min_topic_documents:
            return "EMERGING"

        # Gate 5: Disappearing
        # Topic had >= min_topic_documents previously and drops to 0 in current period
        if prev_doc_count >= min_topic_documents and t_doc_count == 0:
            return "DISAPPEARING"

        # Gate 6: Minimum topic documents for growth/decline/stable
        if t_doc_count < min_topic_documents or prev_doc_count < min_topic_documents:
            return "INSUFFICIENT_HISTORY"

        # Gate 7: Growing / Declining / Stable
        if pp_change > percentage_point_threshold:
            return "GROWING"
        elif pp_change < -percentage_point_threshold:
            return "DECLINING"
        else:
            return "STABLE"

    def _format_trends_response(self, analysis: TopicAnalysis, trends: List[TopicTrend], db: Optional[Session] = None) -> Dict[str, Any]:
        """Formats trend records into a structured JSON response with strict version integrity checking."""
        # Strict Version Integrity Guard
        for t in trends:
            if t.analysis_id != analysis.id:
                raise ValueError(
                    f"Version Integrity Violation: TopicTrend record '{t.id}' has analysis_id '{t.analysis_id}' "
                    f"which does not match target analysis '{analysis.id}'"
                )

        topic_order = {}
        if db:
            topics_list = db.query(Topic).filter(Topic.analysis_id == analysis.id).order_by(Topic.topic_index).all()
            topic_order = {t.id: t.topic_index for t in topics_list}
        elif hasattr(analysis, "topics") and analysis.topics:
            topic_order = {t.id: t.topic_index for t in analysis.topics}

        topic_trends_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        all_periods = sorted(list(set(t.period_value for t in trends)), key=parse_period_sort_key)

        for t in trends:
            topic_trends_map[t.topic_id].append({
                "id": t.id,
                "period_value": t.period_value,
                "document_count": t.document_count,
                "corpus_document_count": t.corpus_document_count,
                "document_share_pct": t.document_share_pct,
                "chunk_count": t.chunk_count,
                "corpus_chunk_count": t.corpus_chunk_count,
                "chunk_share_pct": t.chunk_share_pct,
                "absolute_change": t.absolute_change,
                "percentage_point_change": t.percentage_point_change,
                "growth_rate_pct": t.growth_rate_pct,
                "trend_status": t.trend_status,
            })

        for t_id in topic_trends_map:
            topic_trends_map[t_id].sort(key=lambda s: parse_period_sort_key(s["period_value"]))

        topic_label_map = {
            t.topic_id: (t.metadata_json or {}).get("topic_label")
            for t in trends
            if (t.metadata_json or {}).get("topic_label")
        }

        formatted_topics = []
        for t_id, t_series in topic_trends_map.items():
            topic_record = t_series[0] if t_series else {}
            # Compute persistence
            obs_periods = [s for s in t_series if s["document_count"] > 0]
            first_seen = obs_periods[0]["period_value"] if obs_periods else None
            last_seen = obs_periods[-1]["period_value"] if obs_periods else None
            obs_count = len(obs_periods)
            tot_count = len(all_periods)

            persistence = self._classify_persistence(obs_count, tot_count, t_series)

            formatted_topics.append({
                "topic_id": t_id,
                "label": topic_label_map.get(t_id, f"Topic {t_id[:6]}"),
                "first_seen": first_seen,
                "last_seen": last_seen,
                "observed_periods": obs_count,
                "total_periods": tot_count,
                "persistence_status": persistence,
                "series": t_series,
            })

        formatted_topics.sort(key=lambda ft: (topic_order.get(ft["topic_id"], 999999), ft["topic_id"]))

        return {
            "analysis_id": analysis.id,
            "corpus_hash": analysis.corpus_hash,
            "embedding_model": analysis.embedding_model,
            "analysis_method": analysis.analysis_method,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
            "status": "COMPLETED",
            "topics_analyzed": len(formatted_topics),
            "periods": all_periods,
            "trends": formatted_topics,
        }

    def _classify_persistence(self, obs_count: int, tot_count: int, series: List[Dict[str, Any]]) -> str:
        """Determines persistence status: PERSISTENT, INTERMITTENT, NEW, DISAPPEARED."""
        if tot_count <= 1:
            return "INSUFFICIENT_HISTORY"
        if obs_count == 0:
            return "DISAPPEARED"
        if series[-1]["document_count"] > 0 and all(s["document_count"] == 0 for s in series[:-1]):
            return "NEW"
        if series[-1]["document_count"] == 0 and any(s["document_count"] > 0 for s in series[:-1]):
            return "DISAPPEARED"
        if (obs_count / float(tot_count)) >= 0.75:
            return "PERSISTENT"
        return "INTERMITTENT"

    def compare_periods(
        self,
        db: Session,
        analysis_id: str,
        period_a: str,
        period_b: str,
    ) -> Dict[str, Any]:
        """
        Compares topic prevalence between two specific periods (e.g. FY2023-24 vs FY2024-25).
        Separates absolute change, percentage-point change, and relative percentage growth.
        """
        trends_res = self.compute_analysis_trends(db, analysis_id)
        period_a_norm = validate_fiscal_year_syntax(period_a)[1] or period_a
        period_b_norm = validate_fiscal_year_syntax(period_b)[1] or period_b

        comparisons = []
        for topic in trends_res.get("trends", []):
            series_map = {s["period_value"]: s for s in topic["series"]}
            s_a = series_map.get(period_a_norm)
            s_b = series_map.get(period_b_norm)

            if not s_a or not s_b:
                continue

            doc_cnt_a = s_a["document_count"]
            doc_cnt_b = s_b["document_count"]
            share_a = s_a["document_share_pct"]
            share_b = s_b["document_share_pct"]

            abs_change = doc_cnt_b - doc_cnt_a
            pp_diff = round(share_b - share_a, 2)
            rel_growth = round(((share_b - share_a) / share_a) * 100.0, 2) if share_a > 0 else (100.0 if share_b > 0 else 0.0)

            comparisons.append({
                "topic_id": topic["topic_id"],
                "topic_label": topic["label"],
                "period_a": period_a_norm,
                "period_b": period_b_norm,
                "document_count_a": doc_cnt_a,
                "document_count_b": doc_cnt_b,
                "corpus_document_count_a": s_a["corpus_document_count"],
                "corpus_document_count_b": s_b["corpus_document_count"],
                "document_share_a_pct": share_a,
                "document_share_b_pct": share_b,
                "absolute_change": abs_change,
                "percentage_point_change": pp_diff,
                "relative_growth_pct": rel_growth,
                "chunk_share_a_pct": s_a["chunk_share_pct"],
                "chunk_share_b_pct": s_b["chunk_share_pct"],
                "trend_status": s_b.get("trend_status", "INSUFFICIENT_HISTORY"),
            })

        return {
            "analysis_id": analysis_id,
            "corpus_hash": trends_res.get("corpus_hash"),
            "embedding_model": trends_res.get("embedding_model"),
            "analysis_method": trends_res.get("analysis_method"),
            "period_a": period_a_norm,
            "period_b": period_b_norm,
            "topic_count": len(comparisons),
            "comparisons": comparisons,
        }

    def compare_dimension(
        self,
        db: Session,
        analysis_id: str,
        dimension_type: str,  # "ORGANIZATION", "MINE", "BLOCK", "DOCUMENT_TYPE"
        dimension_a: Optional[str] = None,
        dimension_b: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compares topic distributions across a given operational dimension using the same global model.
        """
        analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
        if not analysis:
            raise ValueError(f"TopicAnalysis '{analysis_id}' not found")

        topics = db.query(Topic).filter(Topic.analysis_id == analysis_id).all()
        topic_ids = [t.id for t in topics]

        # Fetch evidence and documents
        evidence_rows = db.query(TopicEvidence).filter(TopicEvidence.topic_id.in_(topic_ids)).all()
        chunk_to_topic = {ev.chunk_id: ev.topic_id for ev in evidence_rows}

        all_chunk_ids = list(chunk_to_topic.keys())
        chunks = db.query(Chunk).filter(Chunk.id.in_(all_chunk_ids)).all() if all_chunk_ids else []
        doc_ids_set = set(c.document_id for c in chunks)
        docs = db.query(Document).filter(Document.id.in_(list(doc_ids_set))).all() if doc_ids_set else []
        doc_map = {d.id: d for d in docs}

        # Map chunks and docs to the target dimension
        dim_docs: Dict[str, Set[str]] = defaultdict(set)
        dim_chunks: Dict[str, Set[str]] = defaultdict(set)
        doc_dim_map: Dict[str, str] = {}
        chunk_dim_map: Dict[str, str] = {}

        for doc_id, doc in doc_map.items():
            val = self._extract_dimension_value(doc=doc, dimension_type=dimension_type, db=db)
            if val:
                dim_docs[val].add(doc_id)
                doc_dim_map[doc_id] = val

        for chunk in chunks:
            val = self._extract_chunk_dimension_value(chunk=chunk, doc=doc_map.get(chunk.document_id), dimension_type=dimension_type, db=db)
            if val:
                dim_chunks[val].add(chunk.id)
                chunk_dim_map[chunk.id] = val

        available_dimensions = sorted(list(set(dim_docs.keys()).union(set(dim_chunks.keys()))))

        # If dimension_a and dimension_b are specified, compute direct pair comparison
        if dimension_a and dimension_b:
            return self._compute_pair_comparison(
                analysis_id=analysis_id,
                topics=topics,
                dimension_type=dimension_type,
                dim_a=dimension_a,
                dim_b=dimension_b,
                dim_docs=dim_docs,
                dim_chunks=dim_chunks,
                doc_dim_map=doc_dim_map,
                chunk_to_topic=chunk_to_topic,
                db=db,
            )

        # General distribution across all values of this dimension
        distribution: Dict[str, Any] = {}
        for dim_val in available_dimensions:
            tot_docs = len(dim_docs[dim_val])
            tot_chunks = len(dim_chunks[dim_val])

            topic_breakdown = []
            for topic in topics:
                t_id = topic.id
                t_docs = [d_id for d_id in dim_docs[dim_val] if any(ev.topic_id == t_id for ev in evidence_rows if chunk_dim_map.get(ev.chunk_id) == dim_val or doc_dim_map.get(ev.chunk_id) == dim_val)]
                t_chunks = [c_id for c_id in dim_chunks[dim_val] if chunk_to_topic.get(c_id) == t_id]

                d_share = round((len(t_docs) / float(tot_docs) * 100.0), 2) if tot_docs > 0 else 0.0
                c_share = round((len(t_chunks) / float(tot_chunks) * 100.0), 2) if tot_chunks > 0 else 0.0

                topic_breakdown.append({
                    "topic_id": t_id,
                    "topic_label": topic.label,
                    "document_count": len(t_docs),
                    "document_share_pct": d_share,
                    "chunk_count": len(t_chunks),
                    "chunk_share_pct": c_share,
                })

            distribution[dim_val] = {
                "corpus_document_count": tot_docs,
                "corpus_chunk_count": tot_chunks,
                "topics": topic_breakdown,
            }

        return {
            "analysis_id": analysis_id,
            "corpus_hash": analysis.corpus_hash,
            "embedding_model": analysis.embedding_model,
            "analysis_method": analysis.analysis_method,
            "dimension_type": dimension_type,
            "available_values": available_dimensions,
            "distribution": distribution,
        }

    def _extract_dimension_value(self, doc: Document, dimension_type: str, db: Session) -> Optional[str]:
        if dimension_type in ["ORGANIZATION", "SUBSIDIARY"]:
            org = db.query(Organization).filter(Organization.id == doc.organization_id).first()
            return org.code if org else None
        elif dimension_type == "DOCUMENT_TYPE":
            return doc.document_type
        return None

    def _extract_chunk_dimension_value(self, chunk: Chunk, doc: Optional[Document], dimension_type: str, db: Session) -> Optional[str]:
        meta = chunk.metadata_json or {}
        if dimension_type == "MINE":
            return meta.get("mine_name")
        elif dimension_type == "BLOCK":
            return meta.get("block_name")
        elif dimension_type in ["ORGANIZATION", "SUBSIDIARY"]:
            if doc:
                org = db.query(Organization).filter(Organization.id == doc.organization_id).first()
                return org.code if org else None
        elif dimension_type == "DOCUMENT_TYPE":
            return doc.document_type if doc else None
        return None

    def _compute_pair_comparison(
        self,
        analysis_id: str,
        topics: List[Topic],
        dimension_type: str,
        dim_a: str,
        dim_b: str,
        dim_docs: Dict[str, Set[str]],
        dim_chunks: Dict[str, Set[str]],
        doc_dim_map: Dict[str, str],
        chunk_to_topic: Dict[str, str],
        db: Session,
    ) -> Dict[str, Any]:
        tot_docs_a = len(dim_docs[dim_a])
        tot_docs_b = len(dim_docs[dim_b])
        tot_chunks_a = len(dim_chunks[dim_a])
        tot_chunks_b = len(dim_chunks[dim_b])

        topic_comparisons = []
        common_topics = []
        unique_to_a = []
        unique_to_b = []

        for topic in topics:
            t_id = topic.id
            chunks_a = [c_id for c_id in dim_chunks[dim_a] if chunk_to_topic.get(c_id) == t_id]
            chunks_b = [c_id for c_id in dim_chunks[dim_b] if chunk_to_topic.get(c_id) == t_id]

            c_count_a = len(chunks_a)
            c_count_b = len(chunks_b)

            share_a = round((c_count_a / float(tot_chunks_a) * 100.0), 2) if tot_chunks_a > 0 else 0.0
            share_b = round((c_count_b / float(tot_chunks_b) * 100.0), 2) if tot_chunks_b > 0 else 0.0
            diff = round(share_b - share_a, 2)

            comp_entry = {
                "topic_id": t_id,
                "topic_label": topic.label,
                "chunk_count_a": c_count_a,
                "chunk_count_b": c_count_b,
                "share_a_pct": share_a,
                "share_b_pct": share_b,
                "difference_pct_points": diff,
            }
            topic_comparisons.append(comp_entry)

            if c_count_a > 0 and c_count_b > 0:
                common_topics.append(topic.label)
            elif c_count_a > 0:
                unique_to_a.append(topic.label)
            elif c_count_b > 0:
                unique_to_b.append(topic.label)

        return {
            "analysis_id": analysis_id,
            "dimension_type": dimension_type,
            "dimension_a": dim_a,
            "dimension_b": dim_b,
            "corpus_chunks_a": tot_chunks_a,
            "corpus_chunks_b": tot_chunks_b,
            "corpus_docs_a": tot_docs_a,
            "corpus_docs_b": tot_docs_b,
            "common_topics": common_topics,
            "unique_to_dimension_a": unique_to_a,
            "unique_to_dimension_b": unique_to_b,
            "comparisons": topic_comparisons,
        }

    def get_emerging_topics(self, db: Session, analysis_id: str) -> List[Dict[str, Any]]:
        """Returns emerging topics with verified supporting documents and evidence cards."""
        trends_res = self.compute_analysis_trends(db, analysis_id)
        emerging = []
        for topic in trends_res.get("trends", []):
            series = topic.get("series", [])
            if any(s.get("trend_status") == "EMERGING" for s in series):
                latest = series[-1]
                # Fetch supporting evidence
                evidences = db.query(TopicEvidence).filter(TopicEvidence.topic_id == topic["topic_id"]).limit(10).all()
                evidence_list = []
                for ev in evidences:
                    c = db.query(Chunk).filter(Chunk.id == ev.chunk_id).first()
                    if c:
                        evidence_list.append({
                            "chunk_id": c.id,
                            "page_number": c.page_number,
                            "section_heading": c.section_heading,
                            "representative_score": ev.representative_score,
                        })

                emerging.append({
                    "topic_id": topic["topic_id"],
                    "label": topic["label"],
                    "first_seen": topic["first_seen"],
                    "latest_period": latest.get("period_value"),
                    "latest_share_pct": latest.get("document_share_pct"),
                    "supporting_documents": latest.get("document_count"),
                    "supporting_chunks": latest.get("chunk_count"),
                    "evidence": evidence_list,
                })
        return emerging

    def get_declining_topics(self, db: Session, analysis_id: str) -> List[Dict[str, Any]]:
        """Returns declining topics with verified historical documents."""
        trends_res = self.compute_analysis_trends(db, analysis_id)
        declining = []
        for topic in trends_res.get("trends", []):
            series = topic.get("series", [])
            dec_points = [s for s in series if s.get("trend_status") in ["DECLINING", "DISAPPEARING"]]
            if dec_points:
                latest = series[-1]
                dec_ref = dec_points[-1]
                declining.append({
                    "topic_id": topic["topic_id"],
                    "label": topic["label"],
                    "first_seen": topic["first_seen"],
                    "latest_period": latest.get("period_value"),
                    "latest_share_pct": latest.get("document_share_pct"),
                    "percentage_point_change": dec_ref.get("percentage_point_change"),
                    "trend_status": dec_ref.get("trend_status"),
                    "supporting_documents": latest.get("document_count"),
                })
        return declining

    def get_term_evolution(self, db: Session, analysis_id: str, topic_id: str) -> Dict[str, Any]:
        """
        Tracks term importance, frequency, and weights across periods for a specific topic.
        """
        topic = db.query(Topic).filter(Topic.id == topic_id, Topic.analysis_id == analysis_id).first()
        if not topic:
            raise ValueError(f"Topic '{topic_id}' not found in analysis '{analysis_id}'")

        terms = db.query(TopicTerm).filter(TopicTerm.topic_id == topic.id).order_by(TopicTerm.rank.asc()).limit(15).all()
        term_strings = [t.term for t in terms]

        trends_res = self.compute_analysis_trends(db, analysis_id)
        periods = trends_res.get("periods", [])

        # Get evidence chunks for this topic
        evidences = db.query(TopicEvidence).filter(TopicEvidence.topic_id == topic.id).all()
        chunk_ids = [ev.chunk_id for ev in evidences]
        chunks = db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all() if chunk_ids else []

        # Group chunks by period
        period_term_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for c in chunks:
            c_meta = c.metadata_json or {}
            c_fy = c_meta.get("fiscal_year") or "UNSPECIFIED"
            valid, norm = validate_fiscal_year_syntax(c_fy)
            p_val = norm if valid else "UNSPECIFIED"

            c_text = (c.content or "").lower()
            for tm in term_strings:
                cnt = len(re.findall(rf"\b{re.escape(tm)}\b", c_text))
                if cnt > 0:
                    period_term_counts[p_val][tm] += cnt

        evolution = []
        for tm in terms:
            evolution.append({
                "term": tm.term,
                "global_weight": tm.weight,
                "global_rank": tm.rank,
                "period_frequencies": {p: period_term_counts[p][tm.term] for p in periods},
            })

        return {
            "analysis_id": analysis_id,
            "topic_id": topic.id,
            "topic_label": topic.label,
            "periods": periods,
            "term_evolution": evolution,
        }


temporal_service = TemporalTopicService()
