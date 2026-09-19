from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.extraction import ExtractedField, ReconciliationGroup, ReconciliationCandidate
from app.models.verification import VerificationTask

class ReconciliationService:
    """
    Cross-document reconciliation engine.
    Detects metric divergences across documents within the same organization scope.
    Preserves all conflicting sources without loss of provenance.

    NOTE: The variance threshold is a configurable system reconciliation policy rule,
    NOT an asserted or official CIL/CMPDI institutional threshold.
    """

    def __init__(self, default_threshold: Optional[float] = None):
        from app.core.config import settings
        self.default_threshold = (
            default_threshold
            if default_threshold is not None
            else settings.RECONCILIATION_VARIANCE_THRESHOLD
        )

    def reconcile_organization_fields(
        self,
        db: Session,
        organization_id: str,
        variance_threshold: Optional[float] = None
    ) -> List[ReconciliationGroup]:
        """
        Scans all extracted fields for an organization and groups metrics by (entity_name, metric_name, reporting_period).
        Identifies cross-document conflicts using a configurable variance policy threshold and creates verification tasks when discrepancies exist.
        """
        threshold = variance_threshold if variance_threshold is not None else self.default_threshold
        # Fetch all fields with numeric values in this organization
        fields = db.query(ExtractedField).filter(
            ExtractedField.organization_id == organization_id,
            ExtractedField.numeric_value.isnot(None)
        ).all()

        # Group by (entity_name, metric_name, reporting_period)
        # Entity name can be derived from metadata or adjacent fields in same document
        grouped: Dict[Tuple[str, str, str], List[ExtractedField]] = {}

        # Look up reporting period and mine/project per document to contextualize isolated metrics
        doc_contexts: Dict[str, Dict[str, str]] = {}
        all_doc_fields = db.query(ExtractedField).filter(
            ExtractedField.organization_id == organization_id
        ).all()
        
        for f in all_doc_fields:
            if f.document_id not in doc_contexts:
                doc_contexts[f.document_id] = {"entity": "General Mine", "period": "Current"}
            if f.field_name in ["mine_name", "project_name"]:
                doc_contexts[f.document_id]["entity"] = f.normalized_value or f.raw_value
            elif f.field_name in ["fiscal_year", "reporting_period"]:
                doc_contexts[f.document_id]["period"] = f.normalized_value or f.raw_value

        for field in fields:
            ctx = doc_contexts.get(field.document_id, {"entity": "General Mine", "period": "Current"})
            entity = field.metadata_json.get("entity_name") if (field.metadata_json and field.metadata_json.get("entity_name")) else ctx["entity"]
            period = ctx["period"]
            key = (str(entity).strip().lower(), field.field_name.strip().lower(), str(period).strip().lower())

            if key not in grouped:
                grouped[key] = []
            grouped[key].append(field)

        reconciliation_groups: List[ReconciliationGroup] = []

        for (entity_clean, metric_name, period_clean), candidate_fields in grouped.items():
            # Only consider cross-document comparisons (fields from at least 2 distinct documents)
            doc_ids = {f.document_id for f in candidate_fields}
            if len(doc_ids) < 2:
                continue

            # Check for existing group or create new one
            entity_display = candidate_fields[0].metadata_json.get("entity_name") if (candidate_fields[0].metadata_json and candidate_fields[0].metadata_json.get("entity_name")) else doc_contexts[candidate_fields[0].document_id]["entity"]
            period_display = doc_contexts[candidate_fields[0].document_id]["period"]

            group = db.query(ReconciliationGroup).filter(
                ReconciliationGroup.organization_id == organization_id,
                ReconciliationGroup.entity_name == entity_display,
                ReconciliationGroup.metric_name == metric_name,
                ReconciliationGroup.reporting_period == period_display
            ).first()

            if not group:
                group = ReconciliationGroup(
                    organization_id=organization_id,
                    entity_name=entity_display,
                    metric_name=metric_name,
                    reporting_period=period_display
                )
                db.add(group)
                db.flush()

            # Compare numeric values across distinct documents
            values = [f.numeric_value for f in candidate_fields if f.numeric_value is not None]
            min_val = min(values)
            max_val = max(values)
            
            # Conflict threshold: relative divergence exceeding configurable policy threshold
            divergence = abs(max_val - min_val) / (min_val if min_val > 0 else 1.0)
            is_conflict = divergence > threshold

            group.conflict_status = "CONFLICT" if is_conflict else "MATCHED"

            # Sync candidates
            # Remove existing candidate links for fresh sync
            db.query(ReconciliationCandidate).filter(ReconciliationCandidate.group_id == group.id).delete()
            for f in candidate_fields:
                f.reconciliation_status = "CONFLICT" if is_conflict else "MATCHED"
                cand = ReconciliationCandidate(
                    group_id=group.id,
                    document_id=f.document_id,
                    field_id=f.id,
                    value=f.raw_value,
                    numeric_value=f.numeric_value,
                    unit=f.unit,
                    confidence_score=f.confidence_score
                )
                db.add(cand)

            # If conflict, create or update verification task
            if is_conflict:
                existing_task = db.query(VerificationTask).filter(
                    VerificationTask.reconciliation_group_id == group.id,
                    VerificationTask.task_type == "EXTRACTION_CONFLICT"
                ).first()
                if not existing_task:
                    verif_task = VerificationTask(
                        task_type="EXTRACTION_CONFLICT",
                        organization_id=organization_id,
                        reconciliation_group_id=group.id,
                        status="PENDING",
                        evidence_context={
                            "entity_name": entity_display,
                            "metric_name": metric_name,
                            "reporting_period": period_display,
                            "min_value": min_val,
                            "max_value": max_val,
                            "divergence_pct": round(divergence * 100, 2),
                            "policy_threshold_pct": round(threshold * 100, 2),
                            "policy_note": "Configurable system reconciliation policy; not an official institutional threshold",
                            "documents_count": len(doc_ids)
                        }
                    )
                    db.add(verif_task)

            reconciliation_groups.append(group)

        db.commit()
        return reconciliation_groups
