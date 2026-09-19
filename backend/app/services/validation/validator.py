import re
from typing import List, Tuple, Optional
from app.models.extraction import ExtractedField, ValidationResult

class ValidationService:
    """
    Deterministic domain validation engine for geological and mining reporting fields.
    Evaluates type consistency, physical range constraints, unit validity, and reporting periods.
    Separates extraction confidence from domain validity.
    """

    ALLOWED_MASS_UNITS = {"mt", "million tonnes", "million tonne", "tonnes", "tonne", "lt", "lakh tonnes", "t"}
    ALLOWED_LENGTH_UNITS = {"m", "metre", "metres", "meter", "meters"}
    ALLOWED_ENERGY_UNITS = {"kcal/kg", "kcal / kg"}
    ALLOWED_RATIO_UNITS = {"cum/tonne", "cum/t", "m3/tonne", "m3/t", "cum / tonne", ":1", "m3/tonne"}
    ALLOWED_VOLUME_UNITS = {"mm3", "million m3", "m3", "lakh m3", "cum", "million cum"}

    def validate_field(self, field: ExtractedField) -> List[ValidationResult]:
        """Runs all applicable validation rules against an extracted field."""
        results: List[ValidationResult] = []
        name = field.field_name.lower()
        val_num = field.numeric_value
        unit = (field.unit or "").strip().lower()

        # 1. Type check
        if field.data_type == "NUMBER":
            if val_num is None:
                results.append(ValidationResult(
                    field_id=field.id,
                    rule_name="NUMERIC_TYPE_CHECK",
                    rule_category="TYPE",
                    status="ERROR",
                    severity="CRITICAL",
                    message=f"Field {field.field_name} declared as NUMBER but raw value '{field.raw_value}' could not be parsed as a float.",
                    observed_value=field.raw_value,
                    expected_constraint="Valid floating-point number"
                ))
            else:
                results.append(ValidationResult(
                    field_id=field.id,
                    rule_name="NUMERIC_TYPE_CHECK",
                    rule_category="TYPE",
                    status="PASS",
                    severity="INFO",
                    message="Numeric type parsed successfully.",
                    observed_value=str(val_num),
                    expected_constraint="Valid floating-point number"
                ))

        # 2. Unit check
        if field.data_type == "NUMBER" and val_num is not None:
            unit_res = self._validate_units(field, name, unit)
            if unit_res:
                results.append(unit_res)

        # 3. Physical range checks
        if val_num is not None:
            range_results = self._validate_ranges(field, name, val_num)
            results.extend(range_results)

        # 4. Period / format check
        if name == "fiscal_year":
            period_res = self._validate_fiscal_year(field)
            if period_res:
                results.append(period_res)

        # Determine overall validation_status
        has_error = any(r.status == "ERROR" for r in results)
        has_warning = any(r.status == "WARNING" for r in results)
        
        if has_error:
            field.validation_status = "ERROR"
        elif has_warning:
            field.validation_status = "WARNING"
        else:
            field.validation_status = "PASS"

        return results

    def _validate_units(self, field: ExtractedField, name: str, unit: str) -> Optional[ValidationResult]:
        if not unit:
            # Unit missing is a warning for domain metrics
            if any(k in name for k in ["production", "target", "dispatch", "reserves", "drilling", "gcv", "stripping", "ash"]):
                return ValidationResult(
                    field_id=field.id,
                    rule_name="UNIT_PRESENCE_CHECK",
                    rule_category="UNIT",
                    status="WARNING",
                    severity="WARNING",
                    message=f"Measurement unit is missing for field '{field.field_name}'. Expected explicit unit.",
                    observed_value="None",
                    expected_constraint="Documented unit of measure"
                )
            return None

        # Mass checks
        if any(k in name for k in ["production", "target", "dispatch", "reserves"]):
            if unit not in self.ALLOWED_MASS_UNITS:
                if any(bad in unit for bad in ["m", "metre", "kcal", "%"]):
                    return ValidationResult(
                        field_id=field.id,
                        rule_name="MASS_UNIT_COMPATIBILITY",
                        rule_category="UNIT",
                        status="ERROR",
                        severity="CRITICAL",
                        message=f"Incompatible unit '{field.unit}' for mass/weight metric {field.field_name}.",
                        observed_value=field.unit,
                        expected_constraint="One of: MT, Million Tonnes, Tonnes, LT"
                    )
        # Drilling length checks
        elif "drilling" in name:
            if unit not in self.ALLOWED_LENGTH_UNITS:
                return ValidationResult(
                    field_id=field.id,
                    rule_name="LENGTH_UNIT_COMPATIBILITY",
                    rule_category="UNIT",
                    status="ERROR",
                    severity="CRITICAL",
                    message=f"Incompatible unit '{field.unit}' for drilling metreage.",
                    observed_value=field.unit,
                    expected_constraint="One of: m, metres"
                )
        # GCV energy checks
        elif name == "gcv":
            if unit not in self.ALLOWED_ENERGY_UNITS:
                return ValidationResult(
                    field_id=field.id,
                    rule_name="ENERGY_UNIT_COMPATIBILITY",
                    rule_category="UNIT",
                    status="ERROR",
                    severity="CRITICAL",
                    message=f"Incompatible unit '{field.unit}' for Gross Calorific Value (GCV).",
                    observed_value=field.unit,
                    expected_constraint="kcal/kg"
                )
        return None

    def _validate_ranges(self, field: ExtractedField, name: str, val: float) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        # Non-negative checks for physical quantities
        if any(k in name for k in ["production", "target", "dispatch", "reserves", "drilling", "overburden", "gcv"]):
            if val < 0:
                results.append(ValidationResult(
                    field_id=field.id,
                    rule_name="NON_NEGATIVE_CONSTRAINT",
                    rule_category="RANGE",
                    status="ERROR",
                    severity="CRITICAL",
                    message=f"Physical metric '{field.field_name}' cannot be negative (observed: {val}).",
                    observed_value=str(val),
                    expected_constraint="value >= 0"
                ))

        # Stripping ratio rules
        if name == "stripping_ratio":
            if val < 0:
                results.append(ValidationResult(
                    field_id=field.id,
                    rule_name="STRIPPING_RATIO_NON_NEGATIVE",
                    rule_category="RANGE",
                    status="ERROR",
                    severity="CRITICAL",
                    message=f"Stripping ratio (OB:Coal) cannot be negative (observed: {val}).",
                    observed_value=str(val),
                    expected_constraint="stripping_ratio >= 0.0"
                ))
            elif val > 50.0:
                results.append(ValidationResult(
                    field_id=field.id,
                    rule_name="STRIPPING_RATIO_UPPER_BOUND",
                    rule_category="RANGE",
                    status="WARNING",
                    severity="WARNING",
                    message=f"Stripping ratio {val} m3/tonne is unusually high (> 50.0). Requires verification.",
                    observed_value=str(val),
                    expected_constraint="0.5 <= stripping_ratio <= 50.0"
                ))
            else:
                results.append(ValidationResult(
                    field_id=field.id,
                    rule_name="STRIPPING_RATIO_PLAUSIBLE_RANGE",
                    rule_category="RANGE",
                    status="PASS",
                    severity="INFO",
                    message=f"Stripping ratio {val} is within plausible operating bounds.",
                    observed_value=str(val),
                    expected_constraint="0.0 <= stripping_ratio <= 50.0"
                ))

        # Ash content rules
        if name == "ash_content":
            if val < 0.0 or val > 100.0:
                results.append(ValidationResult(
                    field_id=field.id,
                    rule_name="ASH_PERCENT_PHYSICAL_BOUNDS",
                    rule_category="RANGE",
                    status="ERROR",
                    severity="CRITICAL",
                    message=f"Ash content {val}% is impossible. Must be between 0.0% and 100.0%.",
                    observed_value=str(val),
                    expected_constraint="0.0 <= ash_content <= 100.0"
                ))
            elif val > 65.0:
                results.append(ValidationResult(
                    field_id=field.id,
                    rule_name="ASH_CONTENT_HIGH_WARNING",
                    rule_category="RANGE",
                    status="WARNING",
                    severity="WARNING",
                    message=f"Ash content {val}% exceeds typical washing limits (> 65%). Verify coal grade.",
                    observed_value=str(val),
                    expected_constraint="ash_content <= 65.0%"
                ))
            else:
                results.append(ValidationResult(
                    field_id=field.id,
                    rule_name="ASH_PERCENT_PLAUSIBLE_RANGE",
                    rule_category="RANGE",
                    status="PASS",
                    severity="INFO",
                    message=f"Ash content {val}% is within typical commercial coal parameters.",
                    observed_value=str(val),
                    expected_constraint="0.0 <= ash_content <= 65.0"
                ))

        # GCV rules
        if name == "gcv":
            if val < 0.0 or val > 9000.0:
                results.append(ValidationResult(
                    field_id=field.id,
                    rule_name="GCV_PHYSICAL_BOUNDS",
                    rule_category="RANGE",
                    status="ERROR",
                    severity="CRITICAL",
                    message=f"GCV {val} kcal/kg is outside physically possible coal calorific limits (0-9000).",
                    observed_value=str(val),
                    expected_constraint="0 <= GCV <= 9000 kcal/kg"
                ))
            elif val < 1500.0:
                results.append(ValidationResult(
                    field_id=field.id,
                    rule_name="GCV_LOW_WARNING",
                    rule_category="RANGE",
                    status="WARNING",
                    severity="WARNING",
                    message=f"GCV {val} kcal/kg is unusually low for commercial grade coal (< 1500 kcal/kg).",
                    observed_value=str(val),
                    expected_constraint="GCV >= 1500 kcal/kg"
                ))

        return results

    def _validate_fiscal_year(self, field: ExtractedField) -> Optional[ValidationResult]:
        val = field.raw_value.strip()
        match = re.match(r"^(?:FY\s*)?([0-9]{4})[-\/]([0-9]{2,4})$", val, re.IGNORECASE)
        if not match:
            return ValidationResult(
                field_id=field.id,
                rule_name="FISCAL_YEAR_FORMAT",
                rule_category="CONSISTENCY",
                status="WARNING",
                severity="WARNING",
                message=f"Fiscal year '{val}' does not conform to standard format YYYY-YY or YYYY-YYYY.",
                observed_value=val,
                expected_constraint="YYYY-YY (e.g. 2024-25)"
            )
        return ValidationResult(
            field_id=field.id,
            rule_name="FISCAL_YEAR_FORMAT",
            rule_category="CONSISTENCY",
            status="PASS",
            severity="INFO",
            message="Fiscal year conforms to standard Indian reporting convention.",
            observed_value=val,
            expected_constraint="YYYY-YY"
        )
