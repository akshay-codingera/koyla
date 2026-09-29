import re
import logging
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from pydantic import BaseModel, Field

from app.models.document import Document
from app.models.organization import Organization
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


class ContributingRecord(BaseModel):
    field_id: str
    document_id: str
    document_title: str
    page_number: Optional[int] = None
    entity_name: Optional[str] = None
    metric_name: str
    raw_value: str
    numeric_value: float
    unit: Optional[str] = None
    reporting_period: Optional[str] = None
    verification_status: str = "UNVERIFIED"


class AggregatedMetricResult(BaseModel):
    operation: str  # "SUM", "AVG", "MIN", "MAX", "COUNT"
    metric_name: str
    canonical_field: str
    calculated_value: float
    unit: Optional[str] = None
    record_count: int
    formula: str
    natural_language_summary: str
    contributing_records: List[ContributingRecord] = Field(default_factory=list)
    conflict_warning: Optional[str] = None
    unit_mismatch: bool = False
    scope_description: str = ""
    verified: bool = True


class AggregationIntent(BaseModel):
    is_aggregation: bool = False
    operation: str = "SUM"
    metric_label: Optional[str] = None
    canonical_fields: List[str] = Field(default_factory=list)
    target_subsidiary: Optional[str] = None
    target_entity: Optional[str] = None
    target_period: Optional[str] = None
    scope_description: str = ""


class StructuredLookupResult(BaseModel):
    facts: List[StructuredFact] = Field(default_factory=list)
    conflict_warning: Optional[ConflictWarning] = None
    aggregation_result: Optional[AggregatedMetricResult] = None
    is_aggregation_query: bool = False
    entities_matched: List[str] = Field(default_factory=list)
    metrics_matched: List[str] = Field(default_factory=list)


class StructuredLookupService:
    """
    Retrieves verified structured facts, inspects cross-document reconciliation
    conflicts, and executes deterministic multi-document SQL aggregations (SUM, AVG, MIN, MAX, COUNT).
    """

    def detect_aggregation_intent(
        self,
        query: str,
        normalized_query: Optional[NormalizedQuery] = None
    ) -> AggregationIntent:
        if normalized_query is None:
            normalized_query = query_normalizer.normalize(query)

        q_lower = query.lower()

        # Exclude pure YoY comparisons e.g. "growth from FY23 to FY24" or "change between 2023 and 2024"
        if re.search(r'\b(?:yoy|year-over-year|growth from|increase from|decrease from|change from|variance between)\b', q_lower):
            if not re.search(r'\b(?:total|sum|combined|aggregate|overall|average|avg|mean)\b', q_lower):
                return AggregationIntent(is_aggregation=False)

        operation = None
        if re.search(r'\b(?:average|avg|mean)\b', q_lower):
            operation = "AVG"
        elif re.search(r'\b(?:minimum|min|lowest)\b', q_lower):
            operation = "MIN"
        elif re.search(r'\b(?:maximum|max|highest)\b', q_lower):
            operation = "MAX"
        elif re.search(r'\b(?:how many|count of|number of mines|number of blocks|number of records|number of sources)\b', q_lower):
            operation = "COUNT"
        elif re.search(r'\b(?:total|sum|combined|aggregate|overall)\b', q_lower):
            operation = "SUM"

        if not operation:
            return AggregationIntent(is_aggregation=False)

        # Resolve metric & canonical fields
        metric_label = None
        canonical_fields = []

        if re.search(r'\b(?:stripping ratio|strip ratio|sr)\b', q_lower):
            metric_label = "stripping ratio"
            canonical_fields = ["stripping_ratio"]
        elif re.search(r'\b(?:dispatch|offtake)\b', q_lower):
            metric_label = "coal dispatch"
            canonical_fields = ["dispatch_quantity", "coal_dispatch"]
        elif re.search(r'\b(?:overburden|ob removal|ob excavation)\b', q_lower):
            metric_label = "overburden removal"
            canonical_fields = ["overburden_removal"]
        elif re.search(r'\b(?:target|planned)\b', q_lower) and "production" in q_lower:
            metric_label = "target production"
            canonical_fields = ["target_quantity"]
        elif re.search(r'\b(?:proved reserve|proved reserves)\b', q_lower):
            metric_label = "proved reserves"
            canonical_fields = ["reserves_proved"]
        elif re.search(r'\b(?:reserve|reserves)\b', q_lower):
            metric_label = "coal reserves"
            canonical_fields = ["reserves_proved", "reserves_total"]
        elif re.search(r'\b(?:drilling|metreage|drilled)\b', q_lower):
            metric_label = "drilling metreage"
            canonical_fields = ["drilling_metreage"]
        elif re.search(r'\b(?:ash|ash content)\b', q_lower):
            metric_label = "ash content"
            canonical_fields = ["ash_content"]
        elif re.search(r'\b(?:gcv|calorific value)\b', q_lower):
            metric_label = "gross calorific value"
            canonical_fields = ["gcv"]
        elif re.search(r'\b(?:thickness|seam thickness)\b', q_lower):
            metric_label = "seam thickness"
            canonical_fields = ["seam_thickness"]
        elif re.search(r'\b(?:production|output|tonnage|extracted|raw coal|coal production)\b', q_lower):
            metric_label = "raw coal production"
            canonical_fields = ["production_quantity", "coal_production"]
        else:
            # Check normalized_query.metrics
            if normalized_query and normalized_query.metrics:
                m = normalized_query.metrics[0].lower().replace(" ", "_")
                metric_label = normalized_query.metrics[0]
                canonical_fields = [m, f"{m}_quantity"]
            else:
                return AggregationIntent(is_aggregation=False)

        # Resolve target subsidiary
        target_subsidiary = None
        known_subs = ["ECL", "BCCL", "CCL", "WCL", "SECL", "MCL", "NCL", "CMPDI", "CIL"]
        for sub in known_subs:
            if re.search(r'\b' + sub + r'\b', query, re.IGNORECASE):
                target_subsidiary = sub.upper()
                break

        # Resolve target entity/area
        target_entity = None
        for mine in query_normalizer.KNOWN_MINES_BLOCKS:
            if re.search(r'\b' + re.escape(mine) + r'\b', query, re.IGNORECASE):
                target_entity = mine
                break

        if not target_entity:
            area_m = re.findall(r'\b([A-Za-z0-9_\-]+)\s+area\b', query, re.IGNORECASE)
            if area_m and area_m[0].lower() not in ("the", "this", "that", "each", "every", "all"):
                target_entity = area_m[0]

        if not target_entity and normalized_query and normalized_query.entities:
            for ent in normalized_query.entities:
                if ent.upper() not in known_subs and not ent.lower().startswith("area in"):
                    target_entity = ent
                    break

        # Resolve target period / fiscal year
        target_period = None
        if normalized_query and normalized_query.fiscal_years:
            target_period = normalized_query.fiscal_years[0]
        else:
            fy_m = re.findall(r'\b(?:FY\s*[-_]?)?((?:19|20)\d{2}[-/]\d{2,4})\b', query, re.IGNORECASE)
            if fy_m:
                target_period = fy_m[0]
            else:
                yr_m = re.findall(r'\b(?:19|20)\d{2}\b', query)
                if yr_m:
                    target_period = yr_m[0]

        # Construct scope description
        parts = []
        if target_subsidiary:
            parts.append(f"Subsidiary: {target_subsidiary}")
        if target_entity:
            parts.append(f"Entity/Area: {target_entity}")
        if target_period:
            parts.append(f"Period: {target_period}")
        scope_desc = ", ".join(parts) if parts else "Enterprise Scope"

        return AggregationIntent(
            is_aggregation=True,
            operation=operation,
            metric_label=metric_label,
            canonical_fields=canonical_fields,
            target_subsidiary=target_subsidiary,
            target_entity=target_entity,
            target_period=target_period,
            scope_description=scope_desc
        )

    def execute_aggregation(
        self,
        db: Session,
        intent: AggregationIntent,
        allowed_org_ids: Optional[List[str]] = None
    ) -> Optional[AggregatedMetricResult]:
        """
        Executes deterministic multi-document SQL aggregation over ExtractedField
        with strict tenant isolation, period filtering, conflict exclusion, and provenance tracking.
        """
        # 1. Organization filtering & server-side tenant isolation
        effective_org_ids: Optional[List[str]] = None
        if intent.target_subsidiary:
            sub_orgs = db.query(Organization.id).filter(
                or_(
                    Organization.code.ilike(f"%{intent.target_subsidiary}%"),
                    Organization.name.ilike(f"%{intent.target_subsidiary}%")
                )
            ).all()
            sub_ids = [str(o[0]) for o in sub_orgs]
            if allowed_org_ids is not None:
                effective_org_ids = [oid for oid in sub_ids if oid in allowed_org_ids]
                if not effective_org_ids:
                    logger.warning(f"Tenant isolation: user denied access to subsidiary {intent.target_subsidiary}")
                    return AggregatedMetricResult(
                        operation=intent.operation,
                        metric_name=intent.metric_label or "metric",
                        canonical_field=intent.canonical_fields[0] if intent.canonical_fields else "unknown",
                        calculated_value=0.0,
                        record_count=0,
                        formula="0 records accessible under current permissions",
                        natural_language_summary=f"No accessible verified records found for {intent.target_subsidiary} under tenant permissions.",
                        scope_description=intent.scope_description,
                        verified=True
                    )
            else:
                effective_org_ids = sub_ids
        elif allowed_org_ids is not None:
            effective_org_ids = allowed_org_ids

        # 2. Base Query on ExtractedField joined with Document
        base_query = db.query(
            ExtractedField,
            Document.title.label("document_title"),
            Document.organization_id.label("org_id")
        ).join(Document, ExtractedField.document_id == Document.id)\
         .filter(
            ExtractedField.field_name.in_(intent.canonical_fields),
            ExtractedField.numeric_value.isnot(None),
            ExtractedField.verification_status != "REJECTED"
        )

        if effective_org_ids is not None:
            base_query = base_query.filter(Document.organization_id.in_(effective_org_ids))

        # 3. Period filtering
        if intent.target_period:
            clean_period = intent.target_period.replace("FY", "").strip()
            period_parts = re.split(r'[-/]', clean_period)
            y_start = period_parts[0] if period_parts else clean_period
            
            period_filters = [
                ExtractedField.source_text.ilike(f"%{y_start}%"),
                Document.title.ilike(f"%{y_start}%")
            ]
            base_query = base_query.filter(or_(*period_filters))

        # 4. Entity filtering
        if intent.target_entity:
            entity_filters = [
                ExtractedField.source_text.ilike(f"%{intent.target_entity}%"),
                Document.title.ilike(f"%{intent.target_entity}%")
            ]
            base_query = base_query.filter(or_(*entity_filters))

        candidates = base_query.all()
        if not candidates:
            return AggregatedMetricResult(
                operation=intent.operation,
                metric_name=intent.metric_label or "metric",
                canonical_field=intent.canonical_fields[0] if intent.canonical_fields else "unknown",
                calculated_value=0.0,
                record_count=0,
                formula="0 records matched query criteria",
                natural_language_summary=f"No verified structured records found for {intent.metric_label} in {intent.scope_description}.",
                scope_description=intent.scope_description,
                verified=True
            )

        # 5. Conflict resolution & candidate exclusion
        conflicting_field_ids: Set[str] = set()
        recon_conflicts = db.query(
            ReconciliationCandidate.field_id,
            ReconciliationGroup.entity_name,
            ReconciliationGroup.metric_name
        ).join(ReconciliationGroup, ReconciliationCandidate.group_id == ReconciliationGroup.id)\
         .filter(
            ReconciliationGroup.conflict_status == "CONFLICT",
            ReconciliationGroup.resolution_status != "RESOLVED"
        ).all()
        conflicting_field_ids = {str(c[0]) for c in recon_conflicts}

        conflict_warning_msg = None
        filtered_candidates = []
        has_excluded_conflict = False

        for ef, d_title, o_id in candidates:
            if ef.id in conflicting_field_ids:
                has_excluded_conflict = True
                continue
            filtered_candidates.append((ef, d_title, o_id))

        if has_excluded_conflict:
            conflict_warning_msg = (
                "Cross-document discrepancy detected among source records. Conflicting candidates "
                "have been excluded from this aggregation pending human verification in the Verification Queue."
            )

        if not filtered_candidates:
            return AggregatedMetricResult(
                operation=intent.operation,
                metric_name=intent.metric_label or "metric",
                canonical_field=intent.canonical_fields[0],
                calculated_value=0.0,
                record_count=0,
                formula="All candidate records have unresolved cross-document conflicts",
                natural_language_summary=(
                    f"Candidate records for {intent.metric_label} ({intent.scope_description}) have unresolved "
                    f"cross-document conflicts. Aggregation withheld pending human verification."
                ),
                conflict_warning=conflict_warning_msg,
                scope_description=intent.scope_description,
                verified=False
            )

        # 6. Deduplication & Verification Preference
        dedup_map: Dict[str, Any] = {}
        for ef, d_title, o_id in filtered_candidates:
            ent_name = (ef.metadata_json or {}).get("entity_name") or ""
            rep_p = (ef.metadata_json or {}).get("reporting_period") or ""
            
            if not ent_name and ef.source_text:
                for m_name in query_normalizer.KNOWN_MINES_BLOCKS:
                    if m_name.lower() in ef.source_text.lower():
                        ent_name = m_name
                        break
            if not ent_name and d_title:
                for m_name in query_normalizer.KNOWN_MINES_BLOCKS:
                    if m_name.lower() in d_title.lower():
                        ent_name = m_name
                        break

            dedup_key = f"{ent_name}_{ef.field_name}_{rep_p}" if ent_name else f"{ef.document_id}_{ef.field_name}_{ef.page_number}"
            prio = 2 if ef.verification_status in ("VERIFIED", "CORRECTED") else 1

            if dedup_key not in dedup_map or prio > dedup_map[dedup_key]["priority"]:
                dedup_map[dedup_key] = {
                    "priority": prio,
                    "entity_name": ent_name or None,
                    "item": (ef, d_title, o_id)
                }

        deduped_items = list(dedup_map.values())

        # 7. Unit consistency inspection
        units = [item["item"][0].unit for item in deduped_items if item["item"][0].unit]
        unit_mismatch = False
        canonical_unit = units[0] if units else None

        if len(set(u.upper() for u in units if u)) > 1:
            upper_units = set(u.upper() for u in units if u)
            if upper_units.issubset({"MT", "TONNES", "TONNE", "TE"}):
                canonical_unit = "MT"
            else:
                unit_mismatch = True
                canonical_unit = units[0]

        # 8. Compute Result & Populate Contributing Records
        values = []
        contributing: List[ContributingRecord] = []

        for item_data in deduped_items:
            ef, d_title, o_id = item_data["item"]
            val = float(ef.numeric_value)
            if canonical_unit == "MT" and ef.unit and ef.unit.upper() in ("TONNES", "TONNE", "TE"):
                val = round(val / 1000000.0, 4)
            values.append(val)

            contributing.append(ContributingRecord(
                field_id=ef.id,
                document_id=ef.document_id,
                document_title=d_title,
                page_number=ef.page_number,
                entity_name=item_data["entity_name"],
                metric_name=ef.field_name,
                raw_value=ef.raw_value,
                numeric_value=val,
                unit=canonical_unit,
                reporting_period=(ef.metadata_json or {}).get("reporting_period"),
                verification_status=ef.verification_status
            ))

        op = intent.operation.upper()
        if op == "SUM":
            calc_val = round(sum(values), 4)
        elif op in ("AVG", "AVERAGE", "MEAN"):
            calc_val = round(sum(values) / len(values), 4)
        elif op == "MIN":
            calc_val = min(values)
        elif op == "MAX":
            calc_val = max(values)
        elif op == "COUNT":
            calc_val = float(len(values))
        else:
            calc_val = round(sum(values), 4)

        # 9. Build Formula with Provenance Trace
        terms = []
        for c in contributing[:8]:
            lbl = c.entity_name or c.document_title[:20]
            p_str = f"P.{c.page_number}" if c.page_number else "N/A"
            terms.append(f"{c.numeric_value:,.1f} ({lbl}, {p_str})")

        if len(contributing) > 8:
            terms.append(f"... + {len(contributing) - 8} more records")

        unit_str = f" {canonical_unit}" if canonical_unit else ""

        if op == "SUM":
            formula = f"{' + '.join(terms)} = {calc_val:,.1f}{unit_str}".strip()
        elif op in ("AVG", "AVERAGE", "MEAN"):
            formula = f"({' + '.join(terms)}) / {len(values)} = {calc_val:,.1f}{unit_str}".strip()
        elif op == "MIN":
            formula = f"min({', '.join(terms)}) = {calc_val:,.1f}{unit_str}".strip()
        elif op == "MAX":
            formula = f"max({', '.join(terms)}) = {calc_val:,.1f}{unit_str}".strip()
        elif op == "COUNT":
            formula = f"count({len(values)} records across {len(contributing)} sources) = {int(calc_val)}"

        # 10. Human-readable Summary
        mismatch_note = " (Warning: mixed or converted units detected across sources)" if unit_mismatch else ""

        if op == "SUM":
            summary = f"Total {intent.metric_label} across {len(contributing)} source records is {calc_val:,.1f}{unit_str} ({intent.scope_description}).{mismatch_note}"
        elif op in ("AVG", "AVERAGE", "MEAN"):
            summary = f"Average {intent.metric_label} across {len(contributing)} source records is {calc_val:,.1f}{unit_str} ({intent.scope_description}).{mismatch_note}"
        elif op == "MIN":
            summary = f"Minimum {intent.metric_label} across {len(contributing)} source records is {calc_val:,.1f}{unit_str} ({intent.scope_description})."
        elif op == "MAX":
            summary = f"Maximum {intent.metric_label} across {len(contributing)} source records is {calc_val:,.1f}{unit_str} ({intent.scope_description})."
        elif op == "COUNT":
            summary = f"Total count of {intent.metric_label} records matching {intent.scope_description} is {int(calc_val)}."

        return AggregatedMetricResult(
            operation=op,
            metric_name=intent.metric_label or "metric",
            canonical_field=intent.canonical_fields[0] if intent.canonical_fields else "unknown",
            calculated_value=calc_val,
            unit=canonical_unit,
            record_count=len(contributing),
            formula=formula,
            natural_language_summary=summary,
            contributing_records=contributing,
            conflict_warning=conflict_warning_msg,
            unit_mismatch=unit_mismatch,
            scope_description=intent.scope_description,
            verified=True
        )

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

        # 1. Check for Aggregation Intent
        agg_intent = self.detect_aggregation_intent(query, normalized_query)
        agg_result = None
        if agg_intent.is_aggregation:
            agg_result = self.execute_aggregation(db, agg_intent, allowed_org_ids)

        # 2. Build base queries for ExtractedField
        field_query = db.query(
            ExtractedField,
            Document.title.label("document_title"),
            Document.organization_id.label("org_id")
        ).join(Document, ExtractedField.document_id == Document.id)

        if allowed_org_ids is not None:
            field_query = field_query.filter(Document.organization_id.in_(allowed_org_ids))

        # Filter by detected metrics and entities
        matched_fields = []
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
                matched_fields = field_query.filter(or_(*metric_filters)).all()
        elif metric_filters:
            matched_fields = field_query.filter(or_(*metric_filters)).all()
        elif entity_filters:
            matched_fields = field_query.filter(or_(*entity_filters)).limit(20).all()
        else:
            matched_fields = []

        facts: List[StructuredFact] = []

        # If aggregation result produced contributing records, prioritize them in facts
        if agg_result and agg_result.contributing_records:
            for cr in agg_result.contributing_records:
                facts.append(StructuredFact(
                    field_id=cr.field_id,
                    document_id=cr.document_id,
                    document_title=cr.document_title,
                    page_number=cr.page_number,
                    entity_name=cr.entity_name,
                    metric_name=cr.metric_name,
                    raw_value=cr.raw_value,
                    numeric_value=cr.numeric_value,
                    unit=cr.unit,
                    reporting_period=cr.reporting_period,
                    confidence_score=1.0,
                    verification_status=cr.verification_status
                ))

        for ef, doc_title, org_id in matched_fields:
            # Avoid duplicate field_ids if already added from aggregation
            if any(f.field_id == ef.id for f in facts):
                continue

            rep_period = None
            if ef.metadata_json and "reporting_period" in ef.metadata_json:
                rep_period = ef.metadata_json["reporting_period"]
            elif ef.source_text:
                fy_m = re.findall(r'\b(?:FY\s*)?(20\d{2}[-/]\d{2,4})\b', ef.source_text, re.IGNORECASE)
                if fy_m:
                    rep_period = f"FY{fy_m[0]}"

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

        recon_groups = recon_query.filter(
            ReconciliationGroup.conflict_status == "CONFLICT",
            ReconciliationGroup.resolution_status != "RESOLVED"
        ).all()

        for rg in recon_groups:
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

                candidates = db.query(
                    ReconciliationCandidate,
                    Document.title.label("document_title")
                ).join(Document, ReconciliationCandidate.document_id == Document.id)\
                 .filter(ReconciliationCandidate.group_id == rg.id).all()

                candidate_list = []
                for cand, d_title in candidates:
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
                break

        return StructuredLookupResult(
            facts=facts,
            conflict_warning=conflict_warning,
            aggregation_result=agg_result,
            is_aggregation_query=agg_intent.is_aggregation,
            entities_matched=detected_entities,
            metrics_matched=detected_metrics
        )


structured_lookup_service = StructuredLookupService()
