"""
Topic Analysis API Routes (Phase 8.1 Foundation).
Exposes endpoints for corpus exploration, foundation job execution, and analysis retrieval.
Enforces strict server-side RBAC, Organization Isolation, and Audit Trails.
"""

import uuid
import json
import logging
import urllib.request
from app.models.report import Report, ReportAnnexure
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.organization import Organization
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.topic import TopicAnalysis, Topic, TopicTerm, TopicDocument, TopicEvidence
from app.services.topics.corpus_service import corpus_service
from app.services.topics.foundation_job import foundation_job
from app.services.topics.temporal_service import temporal_service
from app.services.audit import log_audit_event

router = APIRouter()

def get_authorized_org_scope(user: User, requested_org_id: Optional[str] = None) -> Optional[List[str]]:
    """
    Enforces server-side organization scope.
    Central officers (Ministry, CMPDI HQ, System Admin) have cross-subsidiary visibility.
    Subsidiary / Regional Institute analysts are strictly confined to their own unit.
    """
    user_roles = [r.code for r in user.roles]
    is_central = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)

    if is_central:
        if requested_org_id:
            return [requested_org_id]
        return None  # All organizations permitted
    else:
        user_org = user.organization_id
        if requested_org_id and requested_org_id != user_org:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot access or analyze topic data outside your authorized organization scope."
            )
        return [user_org] if user_org else []


class AnalyzeRequest(BaseModel):
    organization_id: Optional[str] = Field(None, description="Target organization / subsidiary ID")
    corpus_filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Filters such as subsidiary, mine_name, block_name, fiscal_year, document_type")
    embedding_model: Optional[str] = Field("BAAI/bge-small-en-v1.5", description="Verified production embedding model")
    analysis_method: Optional[str] = Field("AUTO", description="Analysis method ('AUTO', 'EMBEDDING_CLUSTER_CTFIDF', 'NMF_TFIDF', 'TFIDF_KEYWORD', 'FOUNDATION')")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional hyper-parameters")
    force_refresh: Optional[bool] = Field(False, description="Force recomputation bypassing cache")


@router.get("", summary="List Topic Analyses with Organization Scoping")
def list_analyses(
    organization_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    allowed_org_ids = get_authorized_org_scope(current_user, organization_id)
    query = db.query(TopicAnalysis)

    if allowed_org_ids is not None:
        query = query.filter(TopicAnalysis.organization_id.in_(allowed_org_ids))
    elif organization_id:
        query = query.filter(TopicAnalysis.organization_id == organization_id)

    if status_filter:
        query = query.filter(TopicAnalysis.status == status_filter.upper())

    total = query.count()
    analyses = query.order_by(TopicAnalysis.created_at.desc()).offset(offset).limit(limit).all()

    results = []
    for a in analyses:
        org = db.query(Organization).filter(Organization.id == a.organization_id).first()
        results.append({
            "id": a.id,
            "organization_id": a.organization_id,
            "organization_code": org.code if org else None,
            "organization_name": org.name if org else "Unknown",
            "corpus_filters": a.corpus_filters,
            "corpus_hash": a.corpus_hash,
            "embedding_model": a.embedding_model,
            "analysis_method": a.analysis_method,
            "status": a.status,
            "progress_pct": a.progress_pct,
            "runtime_seconds": a.runtime_seconds,
            "document_count": a.document_count,
            "chunk_count": a.chunk_count,
            "outlier_count": a.outlier_count,
            "error_message": a.error_message,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        })

    return {"total": total, "items": results}


@router.post("/analyze", summary="Execute Topic Analysis Foundation Job")
def analyze_corpus(
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    allowed_org_ids = get_authorized_org_scope(current_user, req.organization_id)

    # Determine effective organization_id for record
    target_org_id = req.organization_id or current_user.organization_id
    if not target_org_id:
        if allowed_org_ids and len(allowed_org_ids) == 1:
            target_org_id = allowed_org_ids[0]
        else:
            first_org = db.query(Organization).first()
            target_org_id = first_org.id if first_org else str(uuid.uuid4())

    # 1. Deterministic Cache Hit Check (if force_refresh is False)
    if not req.force_refresh:
        try:
            from app.services.topics.hashing import compute_corpus_hash
            from app.services.topics.preprocessor import PREPROCESSOR_VERSION
            preview_corpus = corpus_service.build_corpus(
                db=db,
                allowed_org_ids=allowed_org_ids,
                filters=req.corpus_filters or {},
            )
            expected_hash = compute_corpus_hash(
                chunk_ids=preview_corpus["chunk_ids"],
                document_ids=preview_corpus["document_ids"],
                filters=preview_corpus["effective_filters"],
                preprocessor_version=PREPROCESSOR_VERSION,
                embedding_model=req.embedding_model or "BAAI/bge-small-en-v1.5",
                analysis_method=req.analysis_method or "FOUNDATION",
                parameters=req.parameters,
            )

            cached_analysis = db.query(TopicAnalysis).filter(
                TopicAnalysis.corpus_hash == expected_hash,
                TopicAnalysis.status == "COMPLETED"
            ).order_by(TopicAnalysis.created_at.desc()).first()

            if cached_analysis:
                cached_topics_count = db.query(Topic).filter(Topic.analysis_id == cached_analysis.id).count()
                if cached_analysis.analysis_method == "FOUNDATION" or cached_topics_count > 0:
                    org = db.query(Organization).filter(Organization.id == cached_analysis.organization_id).first()
                    log_audit_event(
                        db=db,
                        action="TOPIC_ANALYSIS_CACHE_HIT",
                        actor_id=current_user.id,
                        actor_name=current_user.username,
                        organization_id=cached_analysis.organization_id,
                        object_type="TopicAnalysis",
                        object_id=cached_analysis.id,
                        sha256_hash=cached_analysis.corpus_hash,
                        details={
                            "reused_analysis_id": cached_analysis.id,
                            "corpus_hash": cached_analysis.corpus_hash,
                            "cache_hit": True
                        }
                    )
                    return {
                        "id": cached_analysis.id,
                        "organization_id": cached_analysis.organization_id,
                        "organization_code": org.code if org else None,
                        "organization_name": org.name if org else "Unknown",
                        "corpus_filters": cached_analysis.corpus_filters,
                        "corpus_hash": cached_analysis.corpus_hash,
                        "embedding_model": cached_analysis.embedding_model,
                        "analysis_method": cached_analysis.analysis_method,
                        "status": cached_analysis.status,
                        "progress_pct": cached_analysis.progress_pct,
                        "runtime_seconds": cached_analysis.runtime_seconds,
                        "document_count": cached_analysis.document_count,
                        "chunk_count": cached_analysis.chunk_count,
                        "topic_count": cached_topics_count,
                        "outlier_count": cached_analysis.outlier_count,
                        "quality_metrics": cached_analysis.quality_metrics,
                        "created_at": cached_analysis.created_at.isoformat() if cached_analysis.created_at else None,
                        "completed_at": cached_analysis.completed_at.isoformat() if cached_analysis.completed_at else None,
                        "cache_hit": True,
                    }
        except Exception as ce:
            logger = logging.getLogger(__name__)
            logger.warning(f"Topic analysis cache pre-check skipped: {ce}")

    # 2. CACHE MISS or FORCE REFRESH: Create new TopicAnalysis record
    analysis = TopicAnalysis(
        id=str(uuid.uuid4()),
        organization_id=target_org_id,
        corpus_filters=req.corpus_filters or {},
        corpus_hash="pending",
        embedding_model=req.embedding_model or "BAAI/bge-small-en-v1.5",
        analysis_method=req.analysis_method or "FOUNDATION",
        parameters=req.parameters or {},
        status="QUEUED",
        progress_pct=0,
        created_by=current_user.id,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Execute foundation job
    try:
        completed_analysis = foundation_job.execute(
            db=db,
            analysis_id=analysis.id,
            allowed_org_ids=allowed_org_ids,
        )

        log_audit_event(
            db=db,
            action="TOPIC_ANALYSIS_REFRESHED" if req.force_refresh else "TOPIC_ANALYSIS_CREATED",
            actor_id=current_user.id,
            actor_name=current_user.username,
            organization_id=target_org_id,
            object_type="TopicAnalysis",
            object_id=completed_analysis.id,
            sha256_hash=completed_analysis.corpus_hash,
            details={
                "status": completed_analysis.status,
                "document_count": completed_analysis.document_count,
                "chunk_count": completed_analysis.chunk_count,
                "embedding_model": completed_analysis.embedding_model,
                "filters": completed_analysis.corpus_filters,
                "force_refresh": req.force_refresh,
            }
        )

        org = db.query(Organization).filter(Organization.id == target_org_id).first()
        topic_count = db.query(Topic).filter(Topic.analysis_id == completed_analysis.id).count()

        if completed_analysis.status == "INSUFFICIENT_CORPUS":
            params = completed_analysis.parameters or {}
            return {
                "id": completed_analysis.id,
                "organization_id": completed_analysis.organization_id,
                "status": "INSUFFICIENT_CORPUS",
                "message": completed_analysis.error_message or "INSUFFICIENT CORPUS FOR TOPIC MODELING",
                "document_count": completed_analysis.document_count,
                "chunk_count": completed_analysis.chunk_count,
                "minimum_threshold": params.get("minimum_threshold", {"documents": 2, "chunks": 3}),
                "recommended_action": params.get("recommended_action", "Ingest at least 2 documents with 3 or more content chunks for topic extraction"),
                "cache_hit": False,
            }

        return {
            "id": completed_analysis.id,
            "organization_id": completed_analysis.organization_id,
            "organization_code": org.code if org else None,
            "organization_name": org.name if org else "Unknown",
            "corpus_filters": completed_analysis.corpus_filters,
            "corpus_hash": completed_analysis.corpus_hash,
            "embedding_model": completed_analysis.embedding_model,
            "analysis_method": completed_analysis.analysis_method,
            "status": completed_analysis.status,
            "progress_pct": completed_analysis.progress_pct,
            "runtime_seconds": completed_analysis.runtime_seconds,
            "document_count": completed_analysis.document_count,
            "chunk_count": completed_analysis.chunk_count,
            "topic_count": topic_count,
            "outlier_count": completed_analysis.outlier_count,
            "quality_metrics": completed_analysis.quality_metrics,
            "created_at": completed_analysis.created_at.isoformat() if completed_analysis.created_at else None,
            "completed_at": completed_analysis.completed_at.isoformat() if completed_analysis.completed_at else None,
            "cache_hit": False,
        }

    except Exception as e:
        log_audit_event(
            db=db,
            action="TOPIC_ANALYSIS_FAILED",
            actor_id=current_user.id,
            actor_name=current_user.username,
            organization_id=target_org_id,
            object_type="TopicAnalysis",
            object_id=analysis.id if "analysis" in locals() else None,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Foundation analysis failed: {str(e)}"
        )


@router.get("/{analysis_id}", summary="Get Topic Analysis Details")
def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    # Check organization access
    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access topic analysis outside your authorized organization scope."
        )

    org = db.query(Organization).filter(Organization.id == analysis.organization_id).first()
    return {
        "id": analysis.id,
        "organization_id": analysis.organization_id,
        "organization_code": org.code if org else None,
        "organization_name": org.name if org else "Unknown",
        "corpus_filters": analysis.corpus_filters,
        "corpus_hash": analysis.corpus_hash,
        "embedding_model": analysis.embedding_model,
        "analysis_method": analysis.analysis_method,
        "parameters": analysis.parameters,
        "status": analysis.status,
        "progress_pct": analysis.progress_pct,
        "runtime_seconds": analysis.runtime_seconds,
        "document_count": analysis.document_count,
        "chunk_count": analysis.chunk_count,
        "topic_count": db.query(Topic).filter(Topic.analysis_id == analysis.id).count(),
        "outlier_count": analysis.outlier_count,
        "quality_metrics": analysis.quality_metrics,
        "error_message": analysis.error_message,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
    }


@router.get("/{analysis_id}/topics", summary="List Discovered Topics for Analysis")
def get_analysis_topics(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access topics outside your authorized organization scope."
        )

    topics = db.query(Topic).filter(Topic.analysis_id == analysis_id).order_by(Topic.topic_index.asc()).all()
    results = []

    for t in topics:
        terms = db.query(TopicTerm).filter(TopicTerm.topic_id == t.id).order_by(TopicTerm.rank.asc()).limit(10).all()
        results.append({
            "id": t.id,
            "analysis_id": t.analysis_id,
            "topic_index": t.topic_index,
            "label": t.label,
            "document_count": t.document_count,
            "chunk_count": t.chunk_count,
            "prevalence_pct": t.prevalence_pct,
            "semantic_topic_coherence": t.coherence_score,
            "top_terms": [
                {
                    "term": tm.term,
                    "weight": tm.weight,
                    "rank": tm.rank,
                    "frequency": tm.frequency,
                    "document_count": tm.document_count,
                }
                for tm in terms
            ],
            "metadata": t.metadata_json or {},
        })

    return {
        "analysis_id": analysis.id,
        "topic_count": len(results),
        "outlier_count": analysis.outlier_count,
        "quality_metrics": analysis.quality_metrics,
        "topics": results,
    }


@router.get("/{analysis_id}/topics/{topic_id}", summary="Get Detailed Topic Info with Provenance")
def get_topic_detail(
    analysis_id: str,
    topic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access topic details outside your authorized organization scope."
        )

    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.analysis_id == analysis_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Terms
    terms = db.query(TopicTerm).filter(TopicTerm.topic_id == topic.id).order_by(TopicTerm.rank.asc()).all()

    # Associated Documents
    topic_docs = db.query(TopicDocument).filter(TopicDocument.topic_id == topic.id).order_by(TopicDocument.contribution_pct.desc()).all()
    doc_results = []
    for td in topic_docs:
        doc = db.query(Document).filter(Document.id == td.document_id).first()
        doc_results.append({
            "document_id": td.document_id,
            "document_title": doc.title if doc else "Unknown",
            "document_type": doc.document_type if doc else "Unknown",
            "similarity_score": td.similarity_score,
            "contribution_pct": td.contribution_pct,
        })

    return {
        "id": topic.id,
        "analysis_id": topic.analysis_id,
        "topic_index": topic.topic_index,
        "label": topic.label,
        "document_count": topic.document_count,
        "chunk_count": topic.chunk_count,
        "prevalence_pct": topic.prevalence_pct,
        "semantic_topic_coherence": topic.coherence_score,
        "metadata": topic.metadata_json or {},
        "terms": [
            {
                "term": tm.term,
                "weight": tm.weight,
                "rank": tm.rank,
                "frequency": tm.frequency,
                "document_count": tm.document_count,
            }
            for tm in terms
        ],
        "documents": doc_results,
    }


@router.get("/{analysis_id}/topics/{topic_id}/evidence", summary="Get Topic Representative Evidence Chunks")
def get_topic_evidence(
    analysis_id: str,
    topic_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access topic evidence outside your authorized organization scope."
        )

    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.analysis_id == analysis_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    evidence_query = db.query(TopicEvidence).filter(
        TopicEvidence.topic_id == topic.id
    ).order_by(TopicEvidence.representative_score.desc())

    total = evidence_query.count()
    evidence_rows = evidence_query.offset(offset).limit(limit).all()

    evidence_cards = []
    for ev in evidence_rows:
        chunk = db.query(Chunk).filter(Chunk.id == ev.chunk_id).first()
        if not chunk:
            continue
        doc = db.query(Document).filter(Document.id == chunk.document_id).first()
        org = db.query(Organization).filter(Organization.id == doc.organization_id).first() if doc else None

        chunk_meta = chunk.metadata_json or {}
        evidence_cards.append({
            "evidence_id": ev.id,
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "document_title": doc.title if doc else "Unknown",
            "document_type": doc.document_type if doc else "Unknown",
            "organization_code": org.code if org else None,
            "page_number": chunk.page_number,
            "section_heading": chunk.section_heading,
            "content": chunk.content,
            "representative_score": ev.representative_score,
            "mine_name": chunk_meta.get("mine_name"),
            "block_name": chunk_meta.get("block_name"),
            "fiscal_year": chunk_meta.get("fiscal_year"),
        })

    return {
        "analysis_id": analysis.id,
        "topic_id": topic.id,
        "topic_label": topic.label,
        "total_evidence": total,
        "offset": offset,
        "limit": limit,
        "items": evidence_cards,
    }


@router.get("/{analysis_id}/corpus", summary="Inspect Prepared Corpus Items")
def get_analysis_corpus(
    analysis_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access topic corpus outside your authorized organization scope."
        )

    corpus_res = corpus_service.build_corpus(
        db=db,
        allowed_org_ids=allowed_org_ids,
        filters=analysis.corpus_filters or {},
    )

    all_items = corpus_res["items"]
    total_items = len(all_items)
    paginated_items = all_items[offset : offset + limit]

    return {
        "analysis_id": analysis.id,
        "corpus_hash": analysis.corpus_hash,
        "total_items": total_items,
        "total_documents": corpus_res["total_documents"],
        "offset": offset,
        "limit": limit,
        "items": paginated_items,
    }


# ==============================================================================
# PHASE 8.3: TEMPORAL & COMPARATIVE ANALYTICS ENDPOINTS
# ==============================================================================

@router.get("/{analysis_id}/trends", summary="Get Topic Temporal Trends")
def get_topic_trends(
    analysis_id: str,
    min_period_documents: int = Query(5, ge=1, description="Minimum documents required per period"),
    min_topic_documents: int = Query(2, ge=1, description="Minimum documents required for topic presence"),
    percentage_point_threshold: float = Query(2.0, ge=0.1, description="PP threshold for growth/decline"),
    force_refresh: bool = Query(False, description="Recompute trends instead of using cached records"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access topic trends outside your authorized organization scope."
        )

    res = temporal_service.compute_analysis_trends(
        db=db,
        analysis_id=analysis_id,
        min_period_documents=min_period_documents,
        min_topic_documents=min_topic_documents,
        percentage_point_threshold=percentage_point_threshold,
        force_refresh=force_refresh,
    )
    return res


@router.get("/{analysis_id}/trends/{topic_id}", summary="Get Single Topic Trend Series")
def get_single_topic_trend(
    analysis_id: str,
    topic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access topic trends outside your authorized organization scope."
        )

    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.analysis_id == analysis_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found in this analysis")

    trends_res = temporal_service.compute_analysis_trends(db, analysis_id)
    for t_entry in trends_res.get("trends", []):
        if t_entry["topic_id"] == topic_id:
            return {
                "analysis_id": analysis_id,
                "topic_id": topic_id,
                "label": topic.label,
                "series": t_entry["series"],
                "persistence_status": t_entry.get("persistence_status"),
                "first_seen": t_entry.get("first_seen"),
                "last_seen": t_entry.get("last_seen"),
            }

    raise HTTPException(status_code=404, detail="Topic trends not found for the requested topic")


@router.get("/{analysis_id}/comparison", summary="Compare Topic Prevalence Between Two Periods")
def compare_topic_periods(
    analysis_id: str,
    period_a: str = Query(..., description="First period (e.g. 'FY2023-24')"),
    period_b: str = Query(..., description="Second period (e.g. 'FY2024-25')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access topic comparison outside your authorized organization scope."
        )

    return temporal_service.compare_periods(db, analysis_id, period_a, period_b)


@router.get("/{analysis_id}/comparison/organizations", summary="Compare Topic Distribution Across Organizations")
def compare_organizations(
    analysis_id: str,
    org_a: Optional[str] = Query(None, description="First organization code (e.g. 'ECL')"),
    org_b: Optional[str] = Query(None, description="Second organization code (e.g. 'BCCL')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    user_roles = [r.code for r in current_user.roles]
    is_central = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)

    # Subsidiary isolation check
    if not is_central:
        user_org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
        user_code = user_org.code if user_org else None
        if (org_a and org_a != user_code) or (org_b and org_b != user_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cross-subsidiary comparison requires central officer privileges."
            )

    return temporal_service.compare_dimension(
        db=db,
        analysis_id=analysis_id,
        dimension_type="ORGANIZATION",
        dimension_a=org_a,
        dimension_b=org_b,
    )


@router.get("/{analysis_id}/comparison/mines", summary="Compare Topic Distribution Across Mines")
def compare_mines(
    analysis_id: str,
    mine_a: Optional[str] = Query(None, description="First mine name"),
    mine_b: Optional[str] = Query(None, description="Second mine name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return temporal_service.compare_dimension(
        db=db,
        analysis_id=analysis_id,
        dimension_type="MINE",
        dimension_a=mine_a,
        dimension_b=mine_b,
    )


@router.get("/{analysis_id}/comparison/blocks", summary="Compare Topic Distribution Across Blocks")
def compare_blocks(
    analysis_id: str,
    block_a: Optional[str] = Query(None, description="First block name"),
    block_b: Optional[str] = Query(None, description="Second block name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return temporal_service.compare_dimension(
        db=db,
        analysis_id=analysis_id,
        dimension_type="BLOCK",
        dimension_a=block_a,
        dimension_b=block_b,
    )


@router.get("/{analysis_id}/comparison/document-types", summary="Compare Topic Distribution Across Document Types")
def compare_document_types(
    analysis_id: str,
    doc_type_a: Optional[str] = Query(None, description="First document type"),
    doc_type_b: Optional[str] = Query(None, description="Second document type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return temporal_service.compare_dimension(
        db=db,
        analysis_id=analysis_id,
        dimension_type="DOCUMENT_TYPE",
        dimension_a=doc_type_a,
        dimension_b=doc_type_b,
    )


@router.get("/{analysis_id}/term-evolution", summary="Track Topic Term Evolution Over Periods")
def get_topic_term_evolution(
    analysis_id: str,
    topic_id: str = Query(..., description="Target topic ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return temporal_service.get_term_evolution(db=db, analysis_id=analysis_id, topic_id=topic_id)


@router.get("/{analysis_id}/emerging", summary="Get Emerging Topics with Supporting Evidence")
def get_emerging_topics(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    emerging = temporal_service.get_emerging_topics(db=db, analysis_id=analysis_id)
    return {
        "analysis_id": analysis_id,
        "count": len(emerging),
        "emerging_topics": emerging,
    }


@router.get("/{analysis_id}/declining", summary="Get Declining and Disappearing Topics")
def get_declining_topics(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    declining = temporal_service.get_declining_topics(db=db, analysis_id=analysis_id)
    return {
        "analysis_id": analysis_id,
        "count": len(declining),
        "declining_topics": declining,
    }


# ==============================================================================
# PHASE 8.4: REPORT INTEGRATION & FACTUAL SUMMARY
# ==============================================================================

class AddAnalysisToReportRequest(BaseModel):
    report_id: str = Field(..., description="Target statutory report ID")
    topic_id: Optional[str] = Field(None, description="Optional specific topic ID, or None for entire analysis")
    include_trends: bool = Field(True, description="Include temporal trend progression")
    include_evidence: bool = Field(True, description="Include representative source evidence cards")


@router.post("/{analysis_id}/add-to-report", summary="Attach Topic Analysis as Optional Analytical Annexure to Statutory Report")
def attach_to_report(
    analysis_id: str,
    req: AddAnalysisToReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Analysis outside organization scope")

    report = db.query(Report).filter(Report.id == req.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Statutory report '{req.report_id}' not found")

    user_roles = [r.code for r in current_user.roles]
    is_central = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)
    if not is_central and report.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Cannot attach to report outside assigned organization")

    trends_data = temporal_service.compute_analysis_trends(db, analysis_id)
    target_topics = []
    if req.topic_id:
        t = db.query(Topic).filter(Topic.id == req.topic_id, Topic.analysis_id == analysis_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Selected topic not found in this analysis")
        target_topics = [t]
    else:
        target_topics = db.query(Topic).filter(Topic.analysis_id == analysis_id).all()

    topics_payload = []
    for t in target_topics:
        terms = db.query(TopicTerm).filter(TopicTerm.topic_id == t.id).order_by(TopicTerm.rank.asc()).limit(10).all()
        t_trend_entry = next((item for item in trends_data.get("trends", []) if item["topic_id"] == t.id), None)
        
        evidence_payload = []
        if req.include_evidence:
            evidences = db.query(TopicEvidence).filter(TopicEvidence.topic_id == t.id).order_by(TopicEvidence.representative_score.desc()).limit(5).all()
            for ev in evidences:
                c = db.query(Chunk).filter(Chunk.id == ev.chunk_id).first()
                if c:
                    d = db.query(Document).filter(Document.id == c.document_id).first()
                    evidence_payload.append({
                        "document_title": d.title if d else "Unknown",
                        "page_number": c.page_number,
                        "section_heading": c.section_heading,
                        "content_snippet": (c.content or "")[:250],
                        "representative_score": ev.representative_score,
                    })

        topics_payload.append({
            "topic_id": t.id,
            "label": t.label,
            "document_count": t.document_count,
            "chunk_count": t.chunk_count,
            "prevalence_pct": t.prevalence_pct,
            "coherence_score": t.coherence_score,
            "top_terms": [{"term": tm.term, "weight": tm.weight, "rank": tm.rank} for tm in terms],
            "series": t_trend_entry["series"] if (req.include_trends and t_trend_entry) else [],
            "persistence_status": t_trend_entry.get("persistence_status") if t_trend_entry else None,
            "evidence": evidence_payload,
        })

    title_label = target_topics[0].label if len(target_topics) == 1 else "Corpus Thematic Synthesis"
    internal_ref = f"annexure_topic_{analysis_id[:8]}"

    existing_annexure = db.query(ReportAnnexure).filter(
        ReportAnnexure.report_id == report.id,
        ReportAnnexure.internal_id == internal_ref
    ).first()

    annexure_notes = json.dumps({
        "analysis_id": analysis.id,
        "corpus_filters": analysis.corpus_filters,
        "embedding_model": analysis.embedding_model,
        "analysis_method": analysis.analysis_method,
        "periods": trends_data.get("periods", []),
        "topics": topics_payload,
    }, indent=2)

    if existing_annexure:
        existing_annexure.title = f"Thematic Intelligence & Temporal Trend Brief: {title_label}"
        existing_annexure.attachment_status = "ATTACHED"
        existing_annexure.notes = annexure_notes
        target_annexure = existing_annexure
    else:
        target_annexure = ReportAnnexure(
            id=str(uuid.uuid4()),
            report_id=report.id,
            internal_id=internal_ref,
            official_reference="Annexure (Optional)",
            title=f"Thematic Intelligence & Temporal Trend Brief: {title_label}",
            requirement_type="OPTIONAL",
            applicability="Internal Technical Dossier & Verification Reference",
            attachment_status="ATTACHED",
            notes=annexure_notes,
        )
        db.add(target_annexure)

    db.commit()

    log_audit_event(
        db=db,
        action="REPORT_TOPIC_ANALYSIS_ATTACHED",
        actor_id=current_user.id,
        actor_name=current_user.username,
        organization_id=report.organization_id,
        object_type="ReportAnnexure",
        object_id=target_annexure.id,
        details={
            "report_id": report.id,
            "analysis_id": analysis.id,
            "topic_count": len(target_topics),
            "official_reference": target_annexure.official_reference,
            "title": target_annexure.title,
        }
    )

    return {
        "message": "Topic analysis attached as an optional analytical annexure to statutory report.",
        "report_id": report.id,
        "report_title": report.report_title,
        "annexure_id": target_annexure.id,
        "official_reference": target_annexure.official_reference,
        "title": target_annexure.title,
        "requirement_type": target_annexure.requirement_type,
        "attachment_status": target_annexure.attachment_status,
    }


class SummaryRequest(BaseModel):
    topic_id: Optional[str] = Field(None, description="Optional focus topic")


@router.post("/{analysis_id}/summary", summary="Generate Grounded Factual Non-Speculative Summary")
def generate_analysis_summary(
    analysis_id: str,
    req: SummaryRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    analysis = db.query(TopicAnalysis).filter(TopicAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Topic analysis not found")

    allowed_org_ids = get_authorized_org_scope(current_user, analysis.organization_id)
    if allowed_org_ids is not None and analysis.organization_id not in allowed_org_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    trends_data = temporal_service.compute_analysis_trends(db, analysis_id)
    emerging = temporal_service.get_emerging_topics(db, analysis_id)
    declining = temporal_service.get_declining_topics(db, analysis_id)

    periods = trends_data.get("periods", [])
    topics = trends_data.get("trends", [])

    emerging_names = [e["label"] for e in emerging]
    declining_names = [d["label"] for d in declining]
    persistent_count = sum(1 for t in topics if t.get("persistence_status") == "PERSISTENT")

    period_span = f"{periods[0]} to {periods[-1]}" if len(periods) > 1 else (periods[0] if periods else "the analyzed periods")
    
    factual_points = [
        f"Analyzed {analysis.document_count} documents ({analysis.chunk_count} text chunks) across {period_span}.",
        f"Identified {len(topics)} coherent topics using {analysis.analysis_method} ({analysis.embedding_model}).",
    ]
    if emerging_names:
        factual_points.append(f"Emerging topic(s) with confirmed document evidence: {', '.join(emerging_names)}.")
    if declining_names:
        factual_points.append(f"Topic(s) showing contracted prevalence: {', '.join(declining_names)}.")
    factual_points.append(f"{persistent_count} topic(s) maintained continuous presence across all evaluated periods.")

    deterministic_summary = " ".join(factual_points)

    llm_summary = None
    try:
        prompt_data = f"Document Count: {analysis.document_count}. Periods: {period_span}. Topics: {len(topics)}. Emerging: {emerging_names}. Declining: {declining_names}. Persistent: {persistent_count}."
        base_url = (getattr(settings, "OLLAMA_BASE_URL", None) or "http://localhost:11434").rstrip("/")
        model_name = getattr(settings, "OLLAMA_MODEL", "SmolLM2-135M-Instruct")
        llm_payload = {
            "model": model_name,
            "prompt": f"You are KOYLA technical reporter. Write exactly 2-3 objective, non-speculative sentences summarizing these coal reporting facts. Do not guess causes or make recommendations:\n{prompt_data}\nSummary:",
            "stream": False,
        }
        req_obj = urllib.request.Request(
            f"{base_url}/api/generate",
            data=json.dumps(llm_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req_obj, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidate = data.get("response", "").strip()
            if candidate and len(candidate) > 20:
                llm_summary = candidate
    except Exception:
        llm_summary = None

    return {
        "analysis_id": analysis.id,
        "summary": llm_summary or deterministic_summary,
        "factual_points": factual_points,
        "source": "LOCAL_LLM" if llm_summary else "DETERMINISTIC_SYNTHESIS",
        "model": "SmolLM2-135M-Instruct" if llm_summary else "KOYLA_DETERMINISTIC_RULES",
    }
