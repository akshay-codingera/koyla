"""
Human & Qualified Person (QP) Review Service
Enables verification, correction with value preservation, certificate signing,
and immutable version freezing with audit logging.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.report import (
    Report,
    ReportFieldMapping,
    ReportCertification,
    ReportVersion,
)
from app.models.audit import AuditEvent
from app.services.reports.compliance import ReportComplianceValidator


class ReportReviewService:

    @classmethod
    def review_field(
        cls,
        db: Session,
        report_id: str,
        mapping_id: str,
        action: str,  # "ACCEPTED", "CORRECTED", "FLAGGED"
        corrected_value: Optional[str] = None,
        notes: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ReportFieldMapping:
        mapping = (
            db.query(ReportFieldMapping)
            .filter(
                ReportFieldMapping.id == mapping_id,
                ReportFieldMapping.report_id == report_id,
            )
            .first()
        )
        if not mapping:
            raise ValueError(f"Field mapping '{mapping_id}' not found for report '{report_id}'.")

        old_value = mapping.generated_value
        mapping.reviewer_action = action
        mapping.reviewer_notes = notes
        mapping.reviewed_by = user_id
        mapping.reviewed_at = datetime.utcnow()

        if action == "CORRECTED" and corrected_value is not None:
            if not mapping.original_generated_value:
                mapping.original_generated_value = old_value
            mapping.generated_value = corrected_value
            mapping.normalized_value = corrected_value

        db.commit()
        db.refresh(mapping)

        # Record Audit Event
        audit = AuditEvent(
            actor_id=user_id or "QP_REVIEWER",
            actor_name=user_id or "QP_REVIEWER",
            role_code="VERIFICATION_OFFICER",
            organization_id=mapping.report.organization_id,
            action=f"REPORT_FIELD_{action}",
            object_type="REPORT_FIELD_MAPPING",
            object_id=mapping.id,
            details={
                "report_id": report_id,
                "internal_id": mapping.internal_id,
                "official_id": mapping.official_id,
                "action": action,
                "old_value": old_value,
                "new_value": mapping.generated_value,
                "notes": notes,
                "result": "SUCCESS",
            },
        )
        db.add(audit)
        db.commit()

        # Re-validate report
        ReportComplianceValidator.validate_report(db, mapping.report)

        return mapping

    @classmethod
    def sign_certification(
        cls,
        db: Session,
        report_id: str,
        certification_id: str,
        signatory_name: str,
        signatory_designation: str,
        reg_number: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ReportCertification:
        cert = (
            db.query(ReportCertification)
            .filter(
                ReportCertification.id == certification_id,
                ReportCertification.report_id == report_id,
            )
            .first()
        )
        if not cert:
            raise ValueError(f"Certification '{certification_id}' not found for report '{report_id}'.")

        cert.signatory_name = signatory_name
        cert.signatory_designation = signatory_designation
        cert.registration_or_accreditation_number = reg_number
        cert.signed_at = datetime.utcnow()
        cert.audit_state = "AUTHORIZED_SIGNED"

        db.commit()
        db.refresh(cert)

        audit = AuditEvent(
            actor_id=user_id or "AUTHORIZED_SIGNATORY",
            actor_name=user_id or "AUTHORIZED_SIGNATORY",
            role_code="VERIFICATION_OFFICER",
            organization_id=cert.report.organization_id,
            action="REPORT_CERTIFICATION_SIGNED",
            object_type="REPORT_CERTIFICATION",
            object_id=cert.id,
            details={
                "report_id": report_id,
                "official_purpose": cert.official_purpose,
                "signatory_role": cert.signatory_role,
                "signatory_name": signatory_name,
                "designation": signatory_designation,
                "audit_state": "AUTHORIZED_SIGNED",
                "result": "SUCCESS",
            },
        )
        db.add(audit)
        db.commit()

        ReportComplianceValidator.validate_report(db, cert.report)

        return cert

    @classmethod
    def freeze_version(
        cls,
        db: Session,
        report_id: str,
        docx_file_path: str,
        sha256_hash: str,
        change_summary: str = "Frozen approved statutory draft",
        user_id: Optional[str] = None,
    ) -> ReportVersion:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise ValueError(f"Report '{report_id}' not found.")

        # Create complete snapshot
        snapshot = {
            "report_id": report.id,
            "title": report.report_title,
            "status": report.status,
            "compliance_status": report.compliance_status,
            "base_date": report.base_date,
            "version_number": report.version_number,
            "fields": [
                {
                    "internal_id": f.internal_id,
                    "official_id": f.official_id,
                    "label": f.exact_official_label,
                    "value": f.generated_value,
                    "numeric_value": f.numeric_value,
                    "unit": f.unit,
                    "reviewer_action": f.reviewer_action,
                }
                for f in report.field_mappings
            ],
            "tables": [
                {
                    "official_id": t.official_id,
                    "title": t.exact_official_label,
                    "row_count": t.row_count,
                    "rows": t.rows_data,
                }
                for t in report.tables
            ],
            "plates": [
                {
                    "plate_id": p.plate_id,
                    "title": p.official_title,
                    "scale": p.scale_requirement,
                    "status": p.attachment_status,
                }
                for p in report.plates
            ],
            "annexures": [
                {
                    "reference": a.official_reference,
                    "title": a.title,
                    "status": a.attachment_status,
                }
                for a in report.annexures
            ],
            "certifications": [
                {
                    "purpose": c.official_purpose,
                    "role": c.signatory_role,
                    "state": c.audit_state,
                    "signatory": c.signatory_name,
                }
                for c in report.certifications
            ],
        }

        version = ReportVersion(
            report_id=report.id,
            version_number=report.version_number,
            status=report.status,
            docx_file_path=docx_file_path,
            sha256_hash=sha256_hash,
            change_summary=change_summary,
            snapshot_json=snapshot,
            created_by=user_id,
            created_at=datetime.utcnow(),
        )
        db.add(version)

        report.version_number += 1
        report.docx_file_path = docx_file_path
        report.sha256_hash = sha256_hash
        report.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(version)

        audit = AuditEvent(
            actor_id=user_id or "QP_OFFICER",
            actor_name=user_id or "QP_OFFICER",
            role_code="VERIFICATION_OFFICER",
            organization_id=report.organization_id,
            action="REPORT_VERSION_FROZEN",
            object_type="REPORT_VERSION",
            object_id=version.id,
            details={
                "report_id": report.id,
                "version_number": version.version_number,
                "sha256_hash": sha256_hash,
                "docx_file_path": docx_file_path,
                "result": "SUCCESS",
            },
        )
        db.add(audit)
        db.commit()

        return version
