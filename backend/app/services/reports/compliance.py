"""
Deterministic Report Compliance Validator
Enforces statutory constraints, reserve deduction integrity, mandatory 2025 Just Transition rule,
conditional applicability, technical plate attachments, and execution signatures.
Derives rigorous readiness state transitions without fabricated approval claims.
"""
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from app.models.report import (
    Report,
    ReportFieldMapping,
    ReportTable,
    ReportAnnexure,
    ReportPlate,
    ReportCertification,
    ReportComplianceIssue,
)
from app.services.reports.narrative import OFFICIAL_UNAVAILABLE_NOTICE


class ReportComplianceValidator:

    @classmethod
    def validate_report(cls, db: Session, report: Report) -> Dict[str, Any]:
        """
        Executes comprehensive statutory compliance checks on a report instance.
        Updates compliance_status, readiness state, and records ReportComplianceIssue items.
        """
        # Delete existing unresolved issues for this report
        db.query(ReportComplianceIssue).filter(
            ReportComplianceIssue.report_id == report.id,
            ReportComplianceIssue.is_resolved == False
        ).delete()

        issues: List[ReportComplianceIssue] = []

        field_map = {f.internal_id: f for f in report.field_mappings}
        table_map = {t.internal_id: t for t in report.tables}
        annexure_map = {a.internal_id: a for a in report.annexures}
        plate_map = {p.internal_id: p for p in report.plates}
        cert_map = {c.internal_id: c for c in report.certifications}

        critical_count = 0
        warning_count = 0
        info_count = 0

        # 1. Mandatory Fields Completeness & Data Availability Check
        for fld in report.field_mappings:
            val = fld.generated_value
            if not val or val.strip() == "" or val.strip() == OFFICIAL_UNAVAILABLE_NOTICE:
                severity = "CRITICAL" if fld.internal_id in (
                    "fm_block_name", "fm_allottee_name", "fld_1_1_1", "fld_1_3_6", "fld_2_2_17", "fld_2_2_21"
                ) else "WARNING"

                if severity == "CRITICAL":
                    critical_count += 1
                else:
                    warning_count += 1

                issues.append(ReportComplianceIssue(
                    report_id=report.id,
                    severity=severity,
                    issue_type="MISSING_DATA",
                    target_node_id=fld.internal_id,
                    target_official_id=fld.official_id,
                    description=f"Statutory requirement '{fld.exact_official_label}' lacks verified data in knowledge base.",
                    statutory_reference=f"Appendix-I {fld.official_id or fld.internal_id}",
                    resolution_hint="Upload corresponding Geological Report, Allotment Order, or DPR to ingest source evidence."
                ))

        # 2. Reserves Mathematical Consistency Check (UNFC / ISP 7-step Hierarchy)
        gross_fld = field_map.get("fld_2_2_17") or field_map.get("fld_2_3_2")
        net_fld = field_map.get("fld_2_2_18") or field_map.get("fld_2_3_3")
        minable_fld = field_map.get("fld_2_2_19") or field_map.get("fld_2_3_5")
        extractable_fld = field_map.get("fld_2_2_21") or field_map.get("fld_2_3_7")
        balance_fld = field_map.get("fld_2_2_24") or field_map.get("fld_2_3_10")

        if gross_fld and net_fld and gross_fld.numeric_value and net_fld.numeric_value:
            if net_fld.numeric_value > gross_fld.numeric_value:
                critical_count += 1
                issues.append(ReportComplianceIssue(
                    report_id=report.id,
                    severity="CRITICAL",
                    issue_type="ARITHMETIC_INCONSISTENCY",
                    target_node_id=net_fld.internal_id,
                    target_official_id="2.2.18",
                    description=f"Net Geological Reserve ({net_fld.numeric_value} MT) exceeds Gross Reserve ({gross_fld.numeric_value} MT).",
                    statutory_reference="Appendix-I Section 2.2.18",
                    resolution_hint="Ensure geological deduction percentage is non-negative and correctly subtracted."
                ))

        if net_fld and minable_fld and net_fld.numeric_value and minable_fld.numeric_value:
            if minable_fld.numeric_value > net_fld.numeric_value:
                critical_count += 1
                issues.append(ReportComplianceIssue(
                    report_id=report.id,
                    severity="CRITICAL",
                    issue_type="ARITHMETIC_INCONSISTENCY",
                    target_node_id=minable_fld.internal_id,
                    target_official_id="2.2.19",
                    description=f"Minable Reserve ({minable_fld.numeric_value} MT) exceeds Net Geological Reserve ({net_fld.numeric_value} MT).",
                    statutory_reference="Appendix-I Section 2.2.19",
                    resolution_hint="Blocked reserves under safety barriers must be deducted from Net Reserves."
                ))

        if minable_fld and extractable_fld and minable_fld.numeric_value and extractable_fld.numeric_value:
            if extractable_fld.numeric_value > minable_fld.numeric_value:
                critical_count += 1
                issues.append(ReportComplianceIssue(
                    report_id=report.id,
                    severity="CRITICAL",
                    issue_type="ARITHMETIC_INCONSISTENCY",
                    target_node_id=extractable_fld.internal_id,
                    target_official_id="2.2.21",
                    description=f"Extractable Reserve ({extractable_fld.numeric_value} MT) exceeds Minable Reserve ({minable_fld.numeric_value} MT).",
                    statutory_reference="Appendix-I Section 2.2.21",
                    resolution_hint="Operational mining losses must be subtracted from Minable Reserves."
                ))

        # 3. Statutory Rule A: Community Development 25% Minimum Earmarking (Section 3.5.5(ii))
        escrow_fld = field_map.get("fld_8_10_2") or field_map.get("fld_8_4_1")
        if escrow_fld and escrow_fld.numeric_value:
            # Check if five-yearly community development lineage is present
            expected_min_cd = round(escrow_fld.numeric_value * 0.25, 2)
            # If explicit CD field exists, validate against 25%
            cd_fld = field_map.get("fld_cd_earmark")
            if cd_fld and cd_fld.numeric_value and cd_fld.numeric_value < expected_min_cd - 0.05:
                critical_count += 1
                issues.append(ReportComplianceIssue(
                    report_id=report.id,
                    severity="CRITICAL",
                    issue_type="STATUTORY_NON_COMPLIANCE",
                    target_node_id=escrow_fld.internal_id,
                    target_official_id="8.10.2",
                    description=f"Community development escrow allocation is less than mandatory 25% minimum ({expected_min_cd} Lakh).",
                    statutory_reference="Ministry of Coal 2025 Guidelines Section 3.5.5(ii)",
                    resolution_hint="Section 3.5.5(ii) strictly mandates minimum 25% of five-yearly escrow deposit for community development & livelihood (Appendix-IX)."
                ))

        # 4. Mandatory Statutory Annexures Attachment Check
        for ann in report.annexures:
            if ann.requirement_type == "MANDATORY" and ann.attachment_status == "MISSING":
                warning_count += 1
                issues.append(ReportComplianceIssue(
                    report_id=report.id,
                    severity="WARNING",
                    issue_type="MISSING_ANNEXURE",
                    target_node_id=ann.internal_id,
                    target_official_id=ann.official_reference,
                    description=f"Mandatory statutory annexure '{ann.official_reference}: {ann.title}' has not been uploaded.",
                    statutory_reference=f"Appendix-I {ann.official_reference}",
                    resolution_hint="Attach scanned certified copy or electronic document prior to authorized submission."
                ))

        # 5. Technical Plates Verification Check
        for plt in report.plates:
            if plt.attachment_status == "SOURCE_REQUIRED":
                warning_count += 1
                issues.append(ReportComplianceIssue(
                    report_id=report.id,
                    severity="WARNING",
                    issue_type="MISSING_TECHNICAL_DRAWING",
                    target_node_id=plt.internal_id,
                    target_official_id=plt.plate_id,
                    description=f"Technical plate '{plt.plate_id}: {plt.official_title}' (Scale {plt.scale_requirement}) requires CAD/GIS source upload.",
                    statutory_reference=f"Appendix-I {plt.plate_id}",
                    resolution_hint="Upload authenticated geo-referenced drawing or DGPS surface plan."
                ))

        # 6. Statutory Certifications & Signature Check
        for cert in report.certifications:
            if cert.audit_state == "SYSTEM_GENERATED":
                warning_count += 1
                issues.append(ReportComplianceIssue(
                    report_id=report.id,
                    severity="WARNING",
                    issue_type="EXECUTION_SIGNATURE_PENDING",
                    target_node_id=cert.internal_id,
                    target_official_id=None,
                    description=f"Certification block '{cert.official_purpose}' ({cert.signatory_role}) is in SYSTEM_GENERATED state.",
                    statutory_reference="Appendix-I Execution Certificates",
                    resolution_hint="Requires Qualified Person / Authorized Signatory review and signature."
                ))

        # Save issues to database
        for iss in issues:
            db.add(iss)

        # 7. Evaluate Compliance Status & Readiness State
        if critical_count > 0:
            compliance_status = "NON_COMPLIANT"
            readiness_state = "DATA_INCOMPLETE"
        elif warning_count > 0:
            compliance_status = "PARTIALLY_COMPLIANT"
            # Check if review has been completed
            has_unreviewed = any(f.reviewer_action == "PENDING" for f in report.field_mappings)
            if has_unreviewed:
                readiness_state = "REVIEW_REQUIRED"
            else:
                readiness_state = "FORMAT_COMPLIANT"
        else:
            compliance_status = "COMPLIANT"
            # Check signatures
            all_signed = all(c.audit_state == "AUTHORIZED_SIGNED" for c in report.certifications)
            if all_signed:
                readiness_state = "READY_FOR_AUTHORIZED_SUBMISSION"
            else:
                readiness_state = "VERIFIED"

        report.compliance_status = compliance_status
        report.status = readiness_state
        db.commit()
        db.refresh(report)

        return {
            "report_id": report.id,
            "compliance_status": compliance_status,
            "readiness_state": readiness_state,
            "critical_issues": critical_count,
            "warning_issues": warning_count,
            "info_issues": info_count,
            "total_issues": len(issues),
            "issues": [
                {
                    "id": iss.id,
                    "severity": iss.severity,
                    "issue_type": iss.issue_type,
                    "target_node_id": iss.target_node_id,
                    "target_official_id": iss.target_official_id,
                    "description": iss.description,
                    "statutory_reference": iss.statutory_reference,
                    "resolution_hint": iss.resolution_hint,
                }
                for iss in issues
            ],
        }
