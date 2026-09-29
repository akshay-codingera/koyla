"""
Phase 11 P1-1: Normalized Lithological Strata Sequence Model — API Routes

Endpoints:
    GET  /api/v1/geology/boreholes/{borehole_id}/strata   - Ordered strata sequence for a borehole
    GET  /api/v1/geology/boreholes/{borehole_id}/summary  - Analytical summary (depth, coal thickness, seams)
    GET  /api/v1/geology/strata/{stratum_id}              - Retrieve single stratum by ID
    POST /api/v1/geology/strata                           - Create a new validated borehole stratum

Enforces server-side authentication, role-based access control, and strict organization scoping.
"""
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.models.geology import BoreholeStratum
from app.services.geology.strata_service import strata_service
from app.services.geology.normalizer import normalize_lithology, extract_seam_and_lithology
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_allowed_org_ids(user: User) -> Optional[List[str]]:
    """Returns None for apex users (all orgs allowed), or a single-item list for subsidiary users."""
    user_roles = [r.code for r in user.roles]
    if any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles):
        return None
    return [user.organization_id] if user.organization_id else []


def _check_org_access(user: User, org_id: str) -> bool:
    """Verifies that the user has authority to access the given organization's records."""
    user_roles = [r.code for r in user.roles]
    if any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles):
        return True
    return user.organization_id == org_id


# Schemas
class BoreholeStratumCreate(BaseModel):
    borehole_id: str = Field(..., description="Borehole identifier (e.g. BH-01, BH-TEST-001)")
    document_id: str = Field(..., description="Source document UUID")
    stratum_order: int = Field(1, description="1-based vertical position in borehole sequence")
    depth_from_m: float = Field(..., description="Top depth of stratum in meters (>= 0)")
    depth_to_m: float = Field(..., description="Bottom depth of stratum in meters (>= depth_from_m)")
    stated_thickness_m: Optional[float] = Field(None, description="Explicit thickness stated in source text")
    lithology_type: Optional[str] = Field(None, description="Normalized lithology (e.g. Coal, Sandstone, Shale)")
    raw_lithology: Optional[str] = Field(None, description="Original verbatim lithology text")
    seam_name: Optional[str] = Field(None, description="Identified coal seam name (e.g. Seam III)")
    page_number: Optional[int] = Field(None, description="Source page number")
    chunk_id: Optional[str] = Field(None, description="Source chunk UUID")
    table_id: Optional[str] = Field(None, description="Source table UUID")
    row_id: Optional[str] = Field(None, description="Source table row UUID")
    source_text: Optional[str] = Field(None, description="Verbatim source sentence or cell content")
    organization_id: Optional[str] = Field(None, description="Optional organization override for apex users")


class BoreholeStratumResponse(BaseModel):
    id: str
    organization_id: str
    document_id: str
    borehole_id: str
    stratum_order: int
    depth_from_m: float
    depth_to_m: float
    thickness_m: float
    stated_thickness_m: Optional[float] = None
    lithology_type: str
    raw_lithology: Optional[str] = None
    seam_name: Optional[str] = None
    page_number: Optional[int] = None
    chunk_id: Optional[str] = None
    table_id: Optional[str] = None
    row_id: Optional[str] = None
    source_text: Optional[str] = None
    extraction_method: str
    confidence_score: float
    has_thickness_discrepancy: bool
    discrepancy_details: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class BoreholeSummaryResponse(BaseModel):
    borehole_id: str
    organization_id: Optional[str] = None
    strata_count: int
    total_depth_m: float
    total_coal_thickness_m: float
    coal_strata_count: int
    seams: List[str]
    lithology_breakdown: Dict[str, float]
    discrepancy_count: int
    found: bool


@router.get("/boreholes/{borehole_id}/strata", response_model=List[BoreholeStratumResponse])
def get_borehole_strata(
    borehole_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve the ordered vertical lithological strata sequence for a given borehole.
    Enforces strict organization-level access control.
    """
    allowed_orgs = _get_allowed_org_ids(current_user)
    strata = strata_service.get_strata_by_borehole(
        db=db,
        borehole_id=borehole_id,
        allowed_org_ids=allowed_orgs,
    )

    if strata:
        log_audit_event(
            db=db,
            action="BOREHOLE_STRATA_ACCESSED",
            actor_id=current_user.id,
            organization_id=strata[0].organization_id,
            object_type="borehole",
            object_id=borehole_id,
            details={"strata_count": len(strata)},
        )

    return strata


@router.get("/boreholes/{borehole_id}/summary", response_model=BoreholeSummaryResponse)
def get_borehole_summary(
    borehole_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve analytical summary metrics (total depth, total coal thickness, seams,
    lithology breakdown, discrepancy counts) for a borehole.
    """
    allowed_orgs = _get_allowed_org_ids(current_user)
    summary = strata_service.get_borehole_summary(
        db=db,
        borehole_id=borehole_id,
        allowed_org_ids=allowed_orgs,
    )

    if not summary.get("found"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Borehole '{borehole_id}' not found or access is restricted.",
        )

    log_audit_event(
        db=db,
        action="BOREHOLE_SUMMARY_ACCESSED",
        actor_id=current_user.id,
        organization_id=summary.get("organization_id") or (allowed_orgs[0] if allowed_orgs else "CENTRAL"),
        object_type="borehole_summary",
        object_id=borehole_id,
        details={
            "total_depth_m": summary["total_depth_m"],
            "total_coal_thickness_m": summary["total_coal_thickness_m"],
            "strata_count": summary["strata_count"],
        },
    )

    return summary


@router.get("/strata/{stratum_id}", response_model=BoreholeStratumResponse)
def get_stratum_by_id(
    stratum_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve a specific stratum by ID, enforcing organization scope.
    """
    stratum = db.query(BoreholeStratum).filter(BoreholeStratum.id == stratum_id).first()
    if not stratum:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stratum not found")

    if not _check_org_access(current_user, stratum.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: stratum belongs to an organization outside your authorized scope",
        )

    log_audit_event(
        db=db,
        action="STRATUM_ACCESSED",
        actor_id=current_user.id,
        organization_id=stratum.organization_id,
        object_type="stratum",
        object_id=stratum.id,
        details={
            "borehole_id": stratum.borehole_id,
            "lithology_type": stratum.lithology_type,
            "depth_from_m": stratum.depth_from_m,
            "depth_to_m": stratum.depth_to_m,
        },
    )

    return stratum


@router.post("/strata", response_model=BoreholeStratumResponse, status_code=status.HTTP_201_CREATED)
def create_stratum(
    payload: BoreholeStratumCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Manually create and persist a validated borehole stratum.
    Requires write permissions to the document's organization.
    """
    doc = db.query(Document).filter(Document.id == payload.document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referenced document not found")

    target_org_id = payload.organization_id or doc.organization_id
    if not _check_org_access(current_user, target_org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cannot create strata for organizations outside your authorized scope",
        )

    # Normalize lithology and extract seam if not already structured
    lith_type = payload.lithology_type
    raw_lith = payload.raw_lithology or lith_type or "Unknown"
    seam = payload.seam_name

    if not lith_type:
        detected_seam, detected_lith = extract_seam_and_lithology(raw_lith)
        lith_type = normalize_lithology(detected_lith)
        if not seam:
            seam = detected_seam
    else:
        lith_type = normalize_lithology(lith_type)

    try:
        stratum_data = payload.dict()
        stratum_data["lithology_type"] = lith_type
        stratum_data["raw_lithology"] = raw_lith
        stratum_data["seam_name"] = seam

        new_stratum = strata_service.create_stratum(
            db=db,
            data=stratum_data,
            organization_id=target_org_id,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))

    log_audit_event(
        db=db,
        action="BOREHOLE_STRATUM_CREATED",
        actor_id=current_user.id,
        organization_id=target_org_id,
        object_type="stratum",
        object_id=new_stratum.id,
        details={
            "borehole_id": new_stratum.borehole_id,
            "stratum_order": new_stratum.stratum_order,
            "depth_from_m": new_stratum.depth_from_m,
            "depth_to_m": new_stratum.depth_to_m,
            "thickness_m": new_stratum.thickness_m,
            "lithology_type": new_stratum.lithology_type,
        },
    )

    return new_stratum
