from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class StatutoryReserveEditCreate(BaseModel):
    proposed_value: str = Field(..., min_length=1, description="Proposed new numerical reserve value (e.g. '1200' or '1200 MT')")
    reason: str = Field(..., min_length=3, description="Audit justification for the statutory reserve edit")
    comment: Optional[str] = Field(None, description="Optional maker comment or contextual notes")
    unit: Optional[str] = Field(None, description="Optional unit constraint (e.g. 'MT')")


class StatutoryReserveApprovalRequest(BaseModel):
    comment: Optional[str] = Field(None, description="Optional checker approval comment or QP note")


class StatutoryReserveRejectionRequest(BaseModel):
    comment: Optional[str] = Field(None, description="Rejection rationale explaining why proposed edit was declined")


class StatutoryReserveVerificationResponse(BaseModel):
    id: str
    organization_id: str
    reserve_record_id: str
    field_name: str
    entity_name: Optional[str] = None
    original_value: str
    original_numeric_value: Optional[float] = None
    proposed_value: str
    proposed_numeric_value: float
    unit: Optional[str] = None
    status: str
    maker_user_id: str
    maker_name: Optional[str] = None
    maker_comment: Optional[str] = None
    reason: str
    verifier_user_id: Optional[str] = None
    verifier_name: Optional[str] = None
    verifier_comment: Optional[str] = None
    created_at: datetime
    verified_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    metadata_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
