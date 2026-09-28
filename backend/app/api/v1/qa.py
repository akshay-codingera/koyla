import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.qa import QueryRecord, AnswerRecord, AnswerCitation
from app.services.qa import qa_service
from app.services.llm import get_llm_provider
from app.services.embedding import get_embedding_provider
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class QAQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question text")
    organization_id: Optional[str] = Field(None, description="Optional organization scope filter")
    fiscal_year: Optional[str] = Field(None, description="Optional fiscal year filter (e.g. 'FY2023-24')")
    document_type: Optional[str] = Field(None, description="Optional document type filter")
    source_tier: Optional[str] = Field(None, description="Optional source tier filter")
    top_k: int = Field(5, ge=1, le=10, description="Max evidence chunks to retrieve")
    enable_reranker: bool = Field(True, description="Enable local cross-encoder reranking")


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
        return None  # None implies all organizations permitted
    else:
        # Strict restriction to user's assigned organization
        user_org = user.organization_id
        if requested_org_id and requested_org_id != user_org:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot query evidence outside your authorized organization scope"
            )
        return [user_org] if user_org else []


from app.core.rate_limit import RateLimiter

qa_rate_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_QA_PER_MINUTE, scope="qa")

@router.post("/query", dependencies=[Depends(qa_rate_limiter)])
def execute_qa_query(
    req: QAQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Execute grounded AI Q&A over retrieved unstructured chunks and structured database records.
    """
    allowed_org_ids = get_authorized_org_scope(current_user, req.organization_id)

    filters = {}
    if req.organization_id:
        filters["organization_id"] = req.organization_id
    if req.fiscal_year:
        filters["fiscal_year"] = req.fiscal_year
    if req.document_type:
        filters["document_type"] = req.document_type
    if req.source_tier:
        filters["source_tier"] = req.source_tier

    qa_res = qa_service.answer_query(
        db=db,
        query=req.query,
        current_user=current_user,
        allowed_org_ids=allowed_org_ids,
        filters=filters,
        top_k=req.top_k,
        enable_reranker=req.enable_reranker
    )

    return qa_res


@router.get("/status")
def get_qa_status():
    """
    Returns live health status of local LLM provider, embedding engine, and arithmetic engine.
    """
    llm_provider = get_llm_provider()
    llm_health = llm_provider.health()
    llm_info = llm_provider.model_info()

    emb_provider = get_embedding_provider()

    return {
        "status": "OPERATIONAL",
        "llm": {
            "provider": llm_info.provider,
            "model_name": llm_info.model_name,
            "is_local": llm_info.is_local,
            "is_healthy": llm_health.is_healthy,
            "endpoint": llm_health.endpoint,
            "error": llm_health.error_message,
            "context_window": llm_info.context_window,
            "supports_structured": llm_info.supports_structured
        },
        "embeddings": {
            "provider": emb_provider.model_info().get("provider"),
            "model_name": emb_provider.model_info().get("model_name"),
            "dimension": emb_provider.dimension,
            "is_neural": emb_provider.model_info().get("is_neural", False)
        },
        "arithmetic_engine": {
            "status": "ACTIVE",
            "deterministic_execution": True,
            "supported_operations": [
                "YOY_COMPARISON",
                "PERCENTAGE_CHANGE",
                "STRIPPING_RATIO",
                "AGGREGATION_SUM",
                "AGGREGATION_AVERAGE"
            ]
        },
        "grounding_verification": {
            "status": "ACTIVE",
            "refusal_threshold": settings.QA_REFUSAL_THRESHOLD,
            "standard_refusal": "Insufficient verified evidence found in the selected knowledge base."
        }
    }


@router.get("/history")
def get_qa_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns recent queries executed within authorized scope.
    """
    user_roles = [r.code for r in current_user.roles]
    is_central = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)

    query = db.query(QueryRecord, AnswerRecord)\
              .join(AnswerRecord, AnswerRecord.query_id == QueryRecord.id)

    if not is_central and current_user.organization_id:
        query = query.filter(QueryRecord.organization_id == current_user.organization_id)

    records = query.order_by(QueryRecord.executed_at.desc()).limit(limit).all()

    history = []
    for q_rec, a_rec in records:
        history.append({
            "query_id": q_rec.id,
            "answer_id": a_rec.id,
            "query": q_rec.query_text,
            "answer": a_rec.answer_text,
            "verification_status": a_rec.verification_status,
            "confidence_score": a_rec.confidence_score,
            "latency_ms": a_rec.latency_ms,
            "llm_provider": a_rec.llm_provider,
            "llm_model": a_rec.llm_model,
            "arithmetic_used": a_rec.arithmetic_used,
            "conflict_detected": a_rec.conflict_detected,
            "executed_at": q_rec.executed_at.isoformat() if q_rec.executed_at else None
        })

    return {"history": history, "total": len(history)}
