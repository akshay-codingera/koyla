import re
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CalculationResult(BaseModel):
    operation: str
    entity_name: Optional[str] = None
    metric_name: Optional[str] = None
    unit: Optional[str] = None
    operand_a: Dict[str, Any] = Field(default_factory=dict)
    operand_b: Optional[Dict[str, Any]] = None
    absolute_change: Optional[float] = None
    percentage_change: Optional[float] = None
    calculated_value: float
    formula: str
    natural_language_summary: str
    verified: bool = True


class ArithmeticEngine:
    """
    Deterministic Arithmetic Engine for KOYLA.
    Ensures mathematical calculations (YoY change, percentages, ratios, totals, averages)
    are strictly computed in Python code, completely preventing LLM math hallucinations.
    """

    @staticmethod
    def absolute_change(val_a: float, val_b: float) -> float:
        """Delta = val_b - val_a"""
        return round(val_b - val_a, 4)

    @staticmethod
    def percentage_change(val_a: float, val_b: float) -> Optional[float]:
        """Percentage Delta = ((val_b - val_a) / abs(val_a)) * 100"""
        if abs(val_a) < 1e-9:
            return None
        return round(((val_b - val_a) / abs(val_a)) * 100.0, 2)

    @staticmethod
    def stripping_ratio(ob_volume_cum: float, coal_tonnage_mt: float) -> Optional[float]:
        """Stripping Ratio = OB (M.cum) / Coal (MT)"""
        if abs(coal_tonnage_mt) < 1e-9:
            return None
        return round(ob_volume_cum / coal_tonnage_mt, 4)

    @staticmethod
    def calculate_yoy(
        entity_name: str,
        metric_name: str,
        period_a: str,
        val_a: float,
        period_b: str,
        val_b: float,
        unit: Optional[str] = None,
        doc_a_id: Optional[str] = None,
        doc_b_id: Optional[str] = None,
        page_a: Optional[int] = None,
        page_b: Optional[int] = None
    ) -> CalculationResult:
        """
        Computes deterministic Year-over-Year (YoY) comparison between two periods.
        """
        abs_diff = round(val_b - val_a, 4)
        pct_diff = None
        if abs(val_a) > 1e-9:
            pct_diff = round(((val_b - val_a) / abs(val_a)) * 100.0, 2)

        direction = "increased" if abs_diff > 0 else "decreased" if abs_diff < 0 else "remained constant"
        sign = "+" if abs_diff > 0 else ""
        unit_str = f" {unit}" if unit else ""

        if pct_diff is not None:
            pct_sign = "+" if pct_diff > 0 else ""
            summary = (
                f"{entity_name} {metric_name.replace('_', ' ')} {direction} by {sign}{abs_diff}{unit_str} "
                f"({pct_sign}{pct_diff}%) from {period_a} ({val_a}{unit_str}) to {period_b} ({val_b}{unit_str})."
            )
            formula = f"(({val_b} - {val_a}) / {val_a}) * 100 = {pct_sign}{pct_diff}%"
        else:
            summary = (
                f"{entity_name} {metric_name.replace('_', ' ')} {direction} by {sign}{abs_diff}{unit_str} "
                f"from {period_a} ({val_a}{unit_str}) to {period_b} ({val_b}{unit_str})."
            )
            formula = f"{val_b} - {val_a} = {abs_diff}"

        return CalculationResult(
            operation="YOY_COMPARISON",
            entity_name=entity_name,
            metric_name=metric_name,
            unit=unit,
            operand_a={
                "period": period_a,
                "value": val_a,
                "unit": unit,
                "document_id": doc_a_id,
                "page_number": page_a
            },
            operand_b={
                "period": period_b,
                "value": val_b,
                "unit": unit,
                "document_id": doc_b_id,
                "page_number": page_b
            },
            absolute_change=abs_diff,
            percentage_change=pct_diff,
            calculated_value=abs_diff,
            formula=formula,
            natural_language_summary=summary,
            verified=True
        )

    @staticmethod
    def aggregate_metrics(
        values: List[float],
        operation: str = "SUM",
        entity_name: Optional[str] = None,
        metric_name: Optional[str] = None,
        unit: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> CalculationResult:
        """
        Computes deterministic aggregation (SUM, AVERAGE, MIN, MAX).
        """
        if not values:
            raise ValueError("Cannot aggregate empty value list")

        op = operation.upper()
        if op == "SUM":
            res_val = round(sum(values), 4)
            formula = " + ".join(str(v) for v in values) + f" = {res_val}"
            summary = f"Total {metric_name or 'metric'} is {res_val} {unit or ''}".strip()
        elif op in ["AVG", "AVERAGE", "MEAN"]:
            res_val = round(sum(values) / len(values), 4)
            formula = f"({ ' + '.join(str(v) for v in values) }) / {len(values)} = {res_val}"
            summary = f"Average {metric_name or 'metric'} across {len(values)} items is {res_val} {unit or ''}".strip()
        elif op == "MIN":
            res_val = min(values)
            formula = f"min({values}) = {res_val}"
            summary = f"Minimum {metric_name or 'metric'} is {res_val} {unit or ''}".strip()
        elif op == "MAX":
            res_val = max(values)
            formula = f"max({values}) = {res_val}"
            summary = f"Maximum {metric_name or 'metric'} is {res_val} {unit or ''}".strip()
        else:
            raise ValueError(f"Unsupported aggregation operation: {op}")

        return CalculationResult(
            operation=op,
            entity_name=entity_name,
            metric_name=metric_name,
            unit=unit,
            operand_a={"values": values, "labels": labels or []},
            calculated_value=res_val,
            formula=formula,
            natural_language_summary=summary,
            verified=True
        )

    def detect_and_execute_calculations(
        self,
        query: str,
        structured_records: List[Dict[str, Any]]
    ) -> List[CalculationResult]:
        """
        Inspects query intent and available structured records to deterministically
        compute YoY comparisons or aggregations where relevant.
        """
        calculations: List[CalculationResult] = []
        q_lower = query.lower()

        # Keywords triggering comparison or change
        is_comparison = any(k in q_lower for k in [
            "growth", "increase", "decrease", "change", "difference", "variance",
            "yoy", "year-over-year", "compared to", "versus", "vs", "trend"
        ])

        is_aggregation = any(k in q_lower for k in [
            "total", "sum", "combined", "aggregate", "average", "mean", "overall"
        ])

        if not structured_records:
            return calculations

        # Group records by (normalized entity_name, normalized metric_name)
        groups: Dict[tuple, List[Dict[str, Any]]] = {}
        for r in structured_records:
            val = r.get("numeric_value")
            if val is None and r.get("raw_value"):
                try:
                    num_clean = re.sub(r"[^\d\.\-]", "", str(r["raw_value"]))
                    if num_clean:
                        val = float(num_clean)
                        r["numeric_value"] = val
                except (ValueError, TypeError):
                    pass
            elif isinstance(val, str):
                try:
                    num_clean = re.sub(r"[^\d\.\-]", "", val)
                    if num_clean:
                        val = float(num_clean)
                        r["numeric_value"] = val
                except (ValueError, TypeError):
                    pass

            if r.get("numeric_value") is not None:
                ent_k = (r.get("entity_name") or "Entity").strip().lower()
                met_k = (r.get("metric_name") or r.get("field_name") or "Metric").strip().lower().replace("_", " ")
                groups.setdefault((ent_k, met_k), []).append(r)

        for (ent_k, met_k), recs in groups.items():
            ent = recs[0].get("entity_name") or "Entity"
            met = recs[0].get("metric_name") or recs[0].get("field_name") or "Metric"
            # If 2 or more periods exist and comparison is implied or multiple periods are queried
            if len(recs) >= 2 and is_comparison:
                # Sort by reporting period or fiscal year if possible
                sorted_recs = sorted(recs, key=lambda x: str(x.get("reporting_period") or x.get("fiscal_year") or ""))
                for i in range(len(sorted_recs) - 1):
                    rec_a = sorted_recs[i]
                    rec_b = sorted_recs[i + 1]
                    per_a = rec_a.get("reporting_period") or rec_a.get("fiscal_year") or "Period 1"
                    per_b = rec_b.get("reporting_period") or rec_b.get("fiscal_year") or "Period 2"
                    val_a = float(rec_a["numeric_value"])
                    val_b = float(rec_b["numeric_value"])
                    unit = rec_b.get("unit") or rec_a.get("unit")

                    calc = self.calculate_yoy(
                        entity_name=ent,
                        metric_name=met,
                        period_a=per_a,
                        val_a=val_a,
                        period_b=per_b,
                        val_b=val_b,
                        unit=unit,
                        doc_a_id=rec_a.get("document_id"),
                        doc_b_id=rec_b.get("document_id"),
                        page_a=rec_a.get("page_number"),
                        page_b=rec_b.get("page_number")
                    )
                    calculations.append(calc)

            elif len(recs) >= 2 and is_aggregation:
                vals = [float(r["numeric_value"]) for r in recs]
                labels = [str(r.get("reporting_period") or r.get("entity_name")) for r in recs]
                unit = recs[0].get("unit")
                op = "AVERAGE" if any(k in q_lower for k in ["average", "mean"]) else "SUM"
                calc = self.aggregate_metrics(
                    values=vals,
                    operation=op,
                    entity_name=ent,
                    metric_name=met,
                    unit=unit,
                    labels=labels
                )
                calculations.append(calc)

        return calculations


arithmetic_engine = ArithmeticEngine()
