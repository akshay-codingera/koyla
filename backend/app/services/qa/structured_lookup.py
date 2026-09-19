import re
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.models.document import Document
from app.models.extraction import ExtractedField, ReconciliationGroup, ReconciliationCandidate
from app.services.retrieval.query_normalizer import query_normalizer, NormalizedQuery

logger = logging.getLogger(__name__)


class ConflictWarning(BaseModel):
    conflict_detected: bool = True
    entity_name: str
    metric_name: str
    reporting_period: str
    status: str = "CONFLICT_REQUIRES_REVIEW"
    message: str
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    reconciliation_group_id: str


class StructuredFact(BaseModel):
    field_id: str
    document_id: str
    document_title: Optional[str] = None
    page_number: Optional[int] = None
    entity_name: Optional[str] = None
    metric_name: str
    raw_value: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    reporting_period: Optional[str] = None
    confidence_score: float = 1.0
    verification_status: str = "UNVERIFIED"
    table_id: Optional[str] = None
    row_id: Optional[str] = None
    source_text: Optional[str] = None


class StructuredLookupResult(BaseModel):
    facts: List[StructuredFact] = Field(default_factory=list)
    conflict_warning: Optional[ConflictWarning] = None
    entities_matched: List[str] = Field(default_factory=list)
    metrics_matched: List[str] = Field(default_factory=list)


class StructuredLookupService:
    """
    Retrieves verified structured facts and inspects cross-document reconciliation
    conflicts to correlate with retrieved unstructured chunks.
    """

    def lookup(
        self,
        db: Session,
        query: str,
        allowed_org_ids: Optional[List[str]] = None,
        normalized_query: Optional[NormalizedQuery] = None
    ) -> StructuredLookupResult:
        if normalized_query is None:
            normalized_query = query_normalizer.normalize(query)

        detected_entities = list(normalized_query.entities)
        detected_metrics = list(normalized_query.metrics)
        detected_periods = list(normalized_query.fiscal_years)

        # Build base queries for ExtractedField
        field_query = db.query(
            ExtractedField,
            Document.title.label("document_title"),
            Document.organization_id.label("org_id")
        ).join(Document, ExtractedField.document_id == Document.id)

        if allowed_org_ids is not None:
            field_query = field_query.filter(Document.organization_id.in_(allowed_org_ids))

        # Filter by detected metrics and entities
        matched_fields = []
        from sqlalchemy import or_

        metric_filters = []
        for m in detected_metrics:
            m_str = m.strip().lower()
            m_under = m_str.replace(" ", "_")
            metric_filters.append(ExtractedField.field_name.ilike(f"%{m_str}%"))
            metric_filters.append(ExtractedField.field_name.ilike(f"%{m_under}%"))

        entity_filters = []
        for e in detected_entities:
            entity_filters.append(ExtractedField.source_text.ilike(f"%{e}%"))

        if metric_filters and entity_filters:
            matched_fields = field_query.filter(
                or_(*metric_filters),
                or_(*entity_filters)
            ).all()
            if not matched_fields:
                # Try metric alone
                matched_fields = field_query.filter(
                    or_(*metric_filters)
                ).all()
        elif metric_filters:
            matched_fields = field_query.filter(
                or_(*metric_filters)
            ).all()
        elif entity_filters:
            matched_fields = field_query.filter(or_(*entity_filters)).limit(20).all()
        else:
            matched_fields = []

        facts: List[StructuredFact] = []
        for ef, doc_title, org_id in matched_fields:
            # Extract reporting period from metadata_json or source_text
            rep_period = None
            if ef.metadata_json and "reporting_period" in ef.metadata_json:
                rep_period = ef.metadata_json["reporting_period"]
            elif ef.source_text:
                fy_m = re.findall(r'\b(?:FY\s*)?(20\d{2}[-/]\d{2,4})\b', ef.source_text, re.IGNORECASE)
                if fy_m:
                    rep_period = f"FY{fy_m[0]}"

            # Determine entity name
            ent_name = None
            if ef.metadata_json and "entity_name" in ef.metadata_json:
                ent_name = ef.metadata_json["entity_name"]
            elif detected_entities:
                ent_name = detected_entities[0]

            facts.append(StructuredFact(
                field_id=ef.id,
                document_id=ef.document_id,
                document_title=doc_title,
                page_number=ef.page_number,
                entity_name=ent_name,
                metric_name=ef.field_name,
                raw_value=ef.raw_value,
                numeric_value=ef.numeric_value,
                unit=ef.unit,
                reporting_period=rep_period,
                confidence_score=ef.confidence_score,
                verification_status=ef.verification_status,
                table_id=ef.table_id,
                row_id=ef.row_id,
                source_text=ef.source_text
            ))

        # Check for Reconciliation Conflicts
        conflict_warning = None
        recon_query = db.query(ReconciliationGroup)
        if allowed_org_ids is not None:
            recon_query = recon_query.filter(ReconciliationGroup.organization_id.in_(allowed_org_ids))

        # Filter by active conflict status
        recon_groups = recon_query.filter(
            ReconciliationGroup.conflict_status == "CONFLICT",
            ReconciliationGroup.resolution_status != "RESOLVED"
        ).all()

        for rg in recon_groups:
            # Query MUST explicitly match this entity or this metric (never trigger on generic/unrelated queries)
            has_entity_match = bool(detected_entities) and any(e.lower() in rg.entity_name.lower() or rg.entity_name.lower() in e.lower() for e in detected_entities)
            norm_rg_metric = rg.metric_name.lower().replace("_", " ")
            has_metric_match = bool(detected_metrics) and any(
                m.lower().replace("_", " ") in norm_rg_metric or norm_rg_metric in m.lower().replace("_", " ")
                for m in detected_metrics
            )

            if has_entity_match or (has_metric_match and not detected_entities):
                from app.core.temporal import validate_fiscal_year_syntax
                is_valid_period, period_info = validate_fiscal_year_syntax(rg.reporting_period)
                period_warning = ""
                if not is_valid_period and rg.reporting_period not in ["Current", "Lifetime", None]:
                    period_warning = f" [INVALID_PERIOD_FORMAT: {period_info}]"

                # Fetch candidates
                candidates = db.query(
                    ReconciliationCandidate,
                    Document.title.label("document_title")
                ).join(Document, ReconciliationCandidate.document_id == Document.id)\
                 .filter(ReconciliationCandidate.group_id == rg.id).all()

                candidate_list = []
                for cand, d_title in candidates:
                    # Get page number from ExtractedField
                    ef_obj = db.query(ExtractedField.page_number).filter(ExtractedField.id == cand.field_id).first()
                    p_num = ef_obj[0] if ef_obj else None
                    candidate_list.append({
                        "candidate_id": cand.id,
                        "document_id": cand.document_id,
                        "document_title": d_title,
                        "page_number": p_num,
                        "value": cand.value,
                        "numeric_value": cand.numeric_value,
                        "unit": cand.unit,
                        "confidence_score": cand.confidence_score
                    })

                vals_str = " vs ".join([f"{c['value']} ({c['document_title']}, P.{c['page_number']})" for c in candidate_list])
                conflict_warning = ConflictWarning(
                    conflict_detected=True,
                    entity_name=rg.entity_name,
                    metric_name=rg.metric_name,
                    reporting_period=rg.reporting_period,
                    status="CONFLICT_REQUIRES_REVIEW",
                    message=(
                        f"Cross-document discrepancy detected for {rg.entity_name} ({rg.metric_name}, {rg.reporting_period}{period_warning}): "
                        f"{vals_str}. This conflict has been registered in the verification queue."
                    ),
                    candidates=candidate_list,
                    reconciliation_group_id=rg.id
                )
                break  # Surface primary relevant conflict

        return StructuredLookupResult(
            facts=facts,
            conflict_warning=conflict_warning,
            entities_matched=detected_entities,
            metrics_matched=detected_metrics
        )


structured_lookup_service = StructuredLookupService()
