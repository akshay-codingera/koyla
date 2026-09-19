import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.services.retrieval import retrieval_service
from app.services.indexing import indexing_service
from app.services.audit import log_audit_event

router = APIRouter()

class SearchQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language or keyword query")
    search_mode: str = Field("HYBRID", description="'HYBRID', 'KEYWORD', or 'SEMANTIC'")
    top_k: int = Field(10, ge=1, le=50, description="Max results to return")
    enable_reranker: bool = Field(True, description="Enable local cross-encoder reranking")
    organization_id: Optional[str] = Field(None, description="Optional organization filter")
    fiscal_year: Optional[str] = Field(None, description="Optional FY filter (e.g. 'FY2024-25')")
    document_type: Optional[str] = Field(None, description="Optional document type filter")
    source_tier: Optional[str] = Field(None, description="Optional source tier filter")
    document_id: Optional[str] = Field(None, description="Optional single document filter")

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
        return None # None implies all organizations permitted
    else:
        # Strict restriction to user's assigned organization
        user_org = user.organization_id
        if requested_org_id and requested_org_id != user_org:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot query evidence outside your authorized organization scope"
            )
        return [user_org] if user_org else []

@router.post("/query")
def execute_search(
    req: SearchQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # 1. Server-side organization authorization check
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
    if req.document_id:
        filters["document_id"] = req.document_id

    # 2. Execute Hybrid Retrieval with Trace
    search_res = retrieval_service.retrieve(
        db=db,
        query=req.query,
        allowed_org_ids=allowed_org_ids,
        filters=filters,
        search_mode=req.search_mode.upper(),
        top_k=req.top_k,
        enable_reranker=req.enable_reranker
    )

    # 3. Log Immutable Audit Event
    log_audit_event(
        db=db,
        action="SEARCH_QUERY_EXECUTED",
        actor_id=current_user.id,
        organization_id=current_user.organization_id or "CENTRAL",
        object_type="search_query",
        object_id=search_res["trace"]["trace_id"],
        details={
            "query": req.query,
            "search_mode": req.search_mode,
            "result_count": len(search_res["results"]),
            "filters": filters,
            "timings_ms": search_res["trace"]["timings_ms"]
        }
    )

    return search_res

@router.get("/status")
def get_search_and_vector_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Returns vector store health, embedding metadata, and indexed chunk counts."""
    return indexing_service.get_status(db)

@router.post("/index/{document_id}")
def index_document(
    document_id: str,
    force: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Trigger dense embedding generation for all chunks of a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    user_roles = [r.code for r in current_user.roles]
    is_central = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)
    if not is_central and current_user.organization_id != doc.organization_id:
        raise HTTPException(status_code=403, detail="Access denied: Cannot index document outside your organization")

    res = indexing_service.index_document_chunks(db, document_id, force=force)

    log_audit_event(
        db=db,
        action="DOCUMENT_CHUNKS_INDEXED",
        actor_id=current_user.id,
        organization_id=doc.organization_id,
        object_type="document",
        object_id=document_id,
        details=res
    )

    return res

@router.post("/reindex")
def reindex_all_documents(
    force: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Admin endpoint to re-index all chunks across the repository."""
    user_roles = [r.code for r in current_user.roles]
    if not any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Admin authorization required to trigger repository-wide re-indexing")

    res = indexing_service.reindex_all(db, force=force)

    log_audit_event(
        db=db,
        action="ALL_CHUNKS_REINDEXED",
        actor_id=current_user.id,
        organization_id="CENTRAL",
        object_type="system",
        object_id="all",
        details=res
    )

    return res
