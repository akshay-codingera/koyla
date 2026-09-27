from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class UploadItemReceipt(BaseModel):
    document_id: str
    original_filename: str
    detected_format: str
    inferred_type: str
    status: str
    file_size_bytes: int
    sha256_hash: str

class UnifiedEvidenceUploadResponse(BaseModel):
    batch_id: str
    total_files: int
    organization_id: str
    items: List[UploadItemReceipt]

class EvidenceSummaryResponse(BaseModel):
    total_documents: int
    text_evidence_count: int
    table_evidence_count: int
    structured_values_count: int
    visual_assets_count: int
    needs_review_count: int
    relationships_count: int

class UnifiedEvidenceItem(BaseModel):
    id: str
    evidence_type: str  # TEXT, TABLE, STRUCTURED_VALUE, VISUAL
    document_id: str
    document_title: str
    organization_id: str
    page_number: Optional[int] = None
    provenance_display: str
    content_preview: str
    field_name: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None
    numeric_value: Optional[float] = None
    confidence_score: float = 1.0
    verification_status: str  # VERIFIED, PENDING, REVIEW_REQUIRED, REJECTED
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EvidenceListResponse(BaseModel):
    total: int
    items: List[UnifiedEvidenceItem]

class EvidenceReviewRequest(BaseModel):
    action: str  # APPROVE, REJECT, CORRECT
    corrected_value: Optional[str] = None
    notes: Optional[str] = None

class DocumentRelationshipResponse(BaseModel):
    id: str
    source_document_id: str
    source_title: str
    target_document_id: str
    target_title: str
    relationship_type: str
    confidence: float
    matching_criteria: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    created_at: str
