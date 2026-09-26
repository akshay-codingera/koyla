"""
Phase 9: Visual & Figure Intelligence — API Routes

Endpoints:
    GET /api/v1/visuals/{visual_id}           — Visual asset metadata
    GET /api/v1/visuals/{visual_id}/content   — Stream binary image
    GET /api/v1/documents/{document_id}/visuals — List visuals for a document

All endpoints enforce authentication and organization-scope access control.
Audit events are logged for visual access.
"""
import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.models.document import Document
from app.models.visual import VisualAsset, VISUAL_TYPES
from app.services.audit import log_audit_event

router = APIRouter()


def _get_user_from_header_or_query(
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()
    elif token:
        raw_token = token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(raw_token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def _check_org_access(user: User, org_id: str) -> bool:
    """Reusable organization-scope check matching documents.py pattern."""
    user_roles = [r.code for r in user.roles]
    if any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles):
        return True
    return user.organization_id == org_id


@router.get("/types")
def list_visual_types(
    current_user: User = Depends(get_current_active_user),
):
    """Return the approved visual taxonomy."""
    return {"visual_types": VISUAL_TYPES}


@router.get("/{visual_id}")
def get_visual_metadata(
    visual_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve full metadata for a visual asset including provenance,
    classification, OCR evidence, and verification status.
    """
    visual = db.query(VisualAsset).filter(VisualAsset.id == visual_id).first()
    if not visual:
        raise HTTPException(status_code=404, detail="Visual asset not found")

    # Organization-scope enforcement via the parent document
    doc = db.query(Document).filter(Document.id == visual.document_id).first()
    if not doc or not _check_org_access(current_user, doc.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: visual belongs to an organization outside your authorized scope",
        )

    log_audit_event(
        db=db,
        action="VISUAL_ACCESSED",
        actor_id=current_user.id,
        organization_id=doc.organization_id,
        object_type="visual_asset",
        object_id=visual.id,
        details={"visual_type": visual.visual_type, "page_number": visual.page_number},
    )

    return {
        "id": visual.id,
        "document_id": visual.document_id,
        "page_id": visual.page_id,
        "page_number": visual.page_number,
        "visual_type": visual.visual_type,
        "classification_confidence": visual.classification_confidence,
        "classification_method": visual.classification_method,
        "bbox": visual.bbox_json,
        "file_path": visual.file_path,
        "image_hash": visual.image_hash,
        "width_px": visual.width_px,
        "height_px": visual.height_px,
        "extraction_method": visual.extraction_method,
        "figure_number": visual.figure_number,
        "caption": visual.caption,
        "raw_ocr_text": visual.raw_ocr_text,
        "normalized_ocr_text": visual.normalized_ocr_text,
        "ocr_confidence": visual.ocr_confidence,
        "verification_status": visual.verification_status,
        "metadata": visual.metadata_json,
        "created_at": str(visual.created_at) if visual.created_at else None,
        "updated_at": str(visual.updated_at) if visual.updated_at else None,
    }


@router.get("/{visual_id}/content")
def get_visual_content(
    visual_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_user_from_header_or_query),
):
    """
    Stream the binary image content for a visual asset.
    Returns the extracted PNG/JPEG file.
    """
    visual = db.query(VisualAsset).filter(VisualAsset.id == visual_id).first()
    if not visual:
        raise HTTPException(status_code=404, detail="Visual asset not found")

    doc = db.query(Document).filter(Document.id == visual.document_id).first()
    if not doc or not _check_org_access(current_user, doc.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if not visual.file_path or not os.path.isfile(visual.file_path):
        raise HTTPException(
            status_code=404,
            detail="Visual image file not found on storage",
        )

    # Determine media type from file extension
    ext = os.path.splitext(visual.file_path)[1].lower()
    media_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    media_type = media_types.get(ext, "image/png")

    return FileResponse(
        path=visual.file_path,
        media_type=media_type,
        filename=f"visual_{visual.id}{ext}",
    )


@router.get("/document/{document_id}")
def list_document_visuals(
    document_id: str,
    page_number: int = Query(None, description="Filter by page number"),
    visual_type: str = Query(None, description="Filter by visual type"),
    verification_status: str = Query(None, description="Filter by verification status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all visual assets for a document with optional filters.
    Returns a visual register with provenance and classification.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not _check_org_access(current_user, doc.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: document belongs to an organization outside your authorized scope",
        )

    query = db.query(VisualAsset).filter(VisualAsset.document_id == document_id)

    if page_number is not None:
        query = query.filter(VisualAsset.page_number == page_number)
    if visual_type:
        query = query.filter(VisualAsset.visual_type == visual_type)
    if verification_status:
        query = query.filter(VisualAsset.verification_status == verification_status)

    visuals = query.order_by(VisualAsset.page_number, VisualAsset.created_at).all()

    return {
        "document_id": document_id,
        "total_visuals": len(visuals),
        "visuals": [
            {
                "id": v.id,
                "page_number": v.page_number,
                "visual_type": v.visual_type,
                "classification_confidence": v.classification_confidence,
                "extraction_method": v.extraction_method,
                "figure_number": v.figure_number,
                "caption": v.caption,
                "ocr_confidence": v.ocr_confidence,
                "verification_status": v.verification_status,
                "width_px": v.width_px,
                "height_px": v.height_px,
                "bbox": v.bbox_json,
                "image_hash": v.image_hash,
                "created_at": str(v.created_at) if v.created_at else None,
            }
            for v in visuals
        ],
    }
