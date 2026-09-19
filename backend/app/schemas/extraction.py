from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class FieldProvenance(BaseModel):
    page_number: Optional[int] = None
    table_id: Optional[str] = None
    row_id: Optional[str] = None
    chunk_id: Optional[str] = None
    source_text: Optional[str] = None

class ValidationResultResponse(BaseModel):
    id: str
    field_id: str
    rule_name: str
    rule_category: str
    status: str
    severity: str
    message: str
    observed_value: Optional[str] = None
    expected_constraint: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ExtractedFieldResponse(BaseModel):
    id: str
    extraction_run_id: Optional[str] = None
    organization_id: str
    document_id: str
    version_id: Optional[str] = None
    field_name: str
    field_category: str
    data_type: str
    raw_value: str
    normalized_value: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    page_number: Optional[int] = None
    table_id: Optional[str] = None
    row_id: Optional[str] = None
    chunk_id: Optional[str] = None
    source_text: Optional[str] = None
    extraction_method: str
    confidence_score: float
    confidence_level: str
    validation_status: str
    reconciliation_status: str
    verification_status: str
    is_corrected: bool
    corrected_value: Optional[str] = None
    corrected_by: Optional[str] = None
    corrected_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    validation_results: List[ValidationResultResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ExtractionRunResponse(BaseModel):
    id: str
    document_id: str
    version_id: Optional[str] = None
    provider: str
    status: str
    fields_extracted_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class VerificationActionRequest(BaseModel):
    action: str  # 'APPROVE', 'CORRECT', 'REJECT', 'DEFER'
    corrected_value: Optional[str] = None
    review_notes: Optional[str] = None

class VerificationTaskResponse(BaseModel):
    id: str
    task_type: str
    organization_id: Optional[str] = None
    document_id: Optional[str] = None
    document_title: Optional[str] = None
    field_id: Optional[str] = None
    reconciliation_group_id: Optional[str] = None
    status: str
    action_taken: Optional[str] = None
    corrected_value: Optional[str] = None
    evidence_context: Optional[Dict[str, Any]] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    field_details: Optional[ExtractedFieldResponse] = None

    model_config = ConfigDict(from_attributes=True)

class ReconciliationCandidateResponse(BaseModel):
    id: str
    group_id: str
    document_id: str
    document_title: Optional[str] = None
    field_id: str
    value: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    confidence_score: float

    model_config = ConfigDict(from_attributes=True)

class ReconciliationGroupResponse(BaseModel):
    id: str
    organization_id: str
    entity_name: str
    metric_name: str
    reporting_period: str
    conflict_status: str
    resolution_status: str
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    candidates: List[ReconciliationCandidateResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ReconciliationResolveRequest(BaseModel):
    resolution_status: str = "RESOLVED"  # 'RESOLVED', 'DEFERRED'
    chosen_candidate_id: Optional[str] = None
    resolution_notes: Optional[str] = None
