"""
Statutory Reports API Routes
Exposes endpoints for Official Formats Registry, Report Studio Generation,
Field Review & Correction, Certification Signing, Compliance Validation, DOCX Export, and Download.
Enforces strict server-side RBAC, Organization Isolation, and Audit Trails.
"""
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.report import Report, ReportFormat, ReportVersion
from app.models.organization import Organization
from app.services.reports.format_registry import FormatRegistry
from app.services.reports.report_generator import ReportGeneratorService
from app.services.reports.compliance import ReportComplianceValidator
from app.services.reports.review_service import ReportReviewService
from app.services.reports.docx_renderer import ReportDocxRenderer

router = APIRouter()


def check_report_org_access(user: User, org_id: str):
    """Enforces server-side organization scope."""
    user_roles = [r.code for r in user.roles]
    is_central = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)
    if not is_central and user.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not authorized to view or modify reports outside your assigned organization.",
        )


class GenerateReportRequest(BaseModel):
    format_id: str = Field(..., description="ID or report_type of registered authoritative format")
    organization_id: str = Field(..., description="Target subsidiary or organization ID")
    mine_name: str = Field(..., description="Exact mine / project name")
    block_name: str = Field(..., description="Exact coal / lignite block name")
    base_date: str = Field(..., description="Base date of the Mining Plan (e.g. '2026-03')")


class ReviewFieldRequest(BaseModel):
    mapping_id: str = Field(..., description="ID of ReportFieldMapping to review")
    action: str = Field(..., description="ACCEPTED, CORRECTED, or FLAGGED")
    corrected_value: Optional[str] = Field(None, description="Corrected value if action is CORRECTED")
    notes: Optional[str] = Field(None, description="Reviewer justification or note")


class SignCertificationRequest(BaseModel):
    certification_id: str = Field(..., description="ID of ReportCertification to sign")
    signatory_name: str = Field(..., description="Full legal name of Qualified Person / Signatory")
    signatory_designation: str = Field(..., description="Designation e.g. Qualified Person / Director")
    reg_number: Optional[str] = Field(None, description="QP Registration or Accreditation Number")


class ExportReportRequest(BaseModel):
    freeze_version: bool = Field(False, description="Whether to freeze an immutable version snapshot")
    change_summary: Optional[str] = Field("Official statutory draft exported", description="Version summary")


@router.get("/formats", summary="List Registered Official Report Formats")
def list_formats(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return FormatRegistry.list_formats(db)


@router.get("/formats/{format_id}", summary="Get Official Format Details & Source Record")
def get_format(format_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    fmt = FormatRegistry.get_format(db, format_id)
    if not fmt:
        raise HTTPException(status_code=404, detail=f"Format '{format_id}' not found.")
    return {
        "id": fmt.id,
        "report_type": fmt.report_type,
        "issuing_authority": fmt.issuing_authority,
        "document_title": fmt.document_title,
        "om_number": fmt.om_number,
        "om_date": fmt.om_date,
        "guideline_year": fmt.guideline_year,
        "effective_status": fmt.effective_status,
        "official_source_url": fmt.official_source_url,
        "source_document_hash": fmt.source_document_hash,
        "format_tier": fmt.format_tier,
        "schema_json": fmt.schema_json,
    }


@router.get("", summary="List Reports with Organization Isolation")
def list_reports(
    organization_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(Report)
    user_roles = [r.code for r in current_user.roles]
    is_central = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)

    if not is_central:
        query = query.filter(Report.organization_id == current_user.organization_id)
    elif organization_id:
        query = query.filter(Report.organization_id == organization_id)

    reports = query.order_by(Report.created_at.desc()).all()
    results = []
    for r in reports:
        org = db.query(Organization).filter(Organization.id == r.organization_id).first()
        results.append({
            "id": r.id,
            "report_title": r.report_title,
            "mine_name": r.mine_name,
            "block_name": r.block_name,
            "organization_id": r.organization_id,
            "organization_name": org.name if org else "Unknown",
            "base_date": r.base_date,
            "status": r.status,
            "compliance_status": r.compliance_status,
            "version_number": r.version_number,
            "has_docx": bool(r.docx_file_path and os.path.exists(r.docx_file_path)),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })
    return results


@router.post("/generate", summary="Generate Prescribed Statutory Report")
def generate_report(
    req: GenerateReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    check_report_org_access(current_user, req.organization_id)
    try:
        report = ReportGeneratorService.generate_report(
            db=db,
            format_id=req.format_id,
            organization_id=req.organization_id,
            mine_name=req.mine_name,
            block_name=req.block_name,
            base_date=req.base_date,
            user_id=current_user.id,
        )
        return {
            "message": "Statutory Mining Plan generated successfully",
            "report_id": report.id,
            "status": report.status,
            "compliance_status": report.compliance_status,
            "version_number": report.version_number,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{report_id}", summary="Get Full Report Details")
def get_report_details(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    check_report_org_access(current_user, report.organization_id)

    org = db.query(Organization).filter(Organization.id == report.organization_id).first()
    fmt = db.query(ReportFormat).filter(ReportFormat.id == report.format_id).first()

    return {
        "id": report.id,
        "format": {
            "id": fmt.id if fmt else None,
            "report_type": fmt.report_type if fmt else None,
            "issuing_authority": fmt.issuing_authority if fmt else None,
            "document_title": fmt.document_title if fmt else None,
            "om_number": fmt.om_number if fmt else None,
            "om_date": fmt.om_date if fmt else None,
        },
        "organization_id": report.organization_id,
        "organization_name": org.name if org else "Unknown",
        "mine_name": report.mine_name,
        "block_name": report.block_name,
        "report_title": report.report_title,
        "base_date": report.base_date,
        "status": report.status,
        "compliance_status": report.compliance_status,
        "version_number": report.version_number,
        "docx_file_path": report.docx_file_path,
        "sha256_hash": report.sha256_hash,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "field_mappings": [
            {
                "id": f.id,
                "internal_id": f.internal_id,
                "official_id": f.official_id,
                "exact_official_label": f.exact_official_label,
                "chapter": f.chapter,
                "field_status": f.field_status,
                "generated_value": f.generated_value,
                "numeric_value": f.numeric_value,
                "unit": f.unit,
                "confidence": f.confidence,
                "calculation_lineage": f.calculation_lineage,
                "grounding_evidence": f.grounding_evidence,
                "reviewer_action": f.reviewer_action,
                "original_generated_value": f.original_generated_value,
                "reviewer_notes": f.reviewer_notes,
                "source_document_id": f.source_document_id,
                "source_page": f.source_page,
            }
            for f in report.field_mappings
        ],
        "tables": [
            {
                "id": t.id,
                "internal_id": t.internal_id,
                "official_id": t.official_id,
                "exact_official_label": t.exact_official_label,
                "chapter": t.chapter,
                "columns": t.columns_schema,
                "rows": t.rows_data,
                "row_count": t.row_count,
            }
            for t in report.tables
        ],
        "plates": [
            {
                "id": p.id,
                "internal_id": p.internal_id,
                "plate_id": p.plate_id,
                "official_title": p.official_title,
                "scale_requirement": p.scale_requirement,
                "attachment_status": p.attachment_status,
                "verification_status": p.verification_status,
                "display_notice": p.display_notice,
            }
            for p in report.plates
        ],
        "annexures": [
            {
                "id": a.id,
                "internal_id": a.internal_id,
                "official_reference": a.official_reference,
                "title": a.title,
                "requirement_type": a.requirement_type,
                "attachment_status": a.attachment_status,
                "notes": a.notes,
            }
            for a in report.annexures
        ],
        "certifications": [
            {
                "id": c.id,
                "internal_id": c.internal_id,
                "official_purpose": c.official_purpose,
                "signatory_role": c.signatory_role,
                "undertaking_text": c.undertaking_text,
                "signatory_name": c.signatory_name,
                "signatory_designation": c.signatory_designation,
                "registration_or_accreditation_number": c.registration_or_accreditation_number,
                "audit_state": c.audit_state,
                "signed_at": c.signed_at.isoformat() if c.signed_at else None,
            }
            for c in report.certifications
        ],
        "compliance_issues": [
            {
                "id": i.id,
                "severity": i.severity,
                "issue_type": i.issue_type,
                "target_node_id": i.target_node_id,
                "target_official_id": i.target_official_id,
                "description": i.description,
                "statutory_reference": i.statutory_reference,
                "resolution_hint": i.resolution_hint,
                "is_resolved": i.is_resolved,
            }
            for i in report.compliance_issues
        ],
    }


@router.post("/{report_id}/review", summary="Review & Correct Field Value")
def review_field(
    report_id: str,
    req: ReviewFieldRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    check_report_org_access(current_user, report.organization_id)

    try:
        mapping = ReportReviewService.review_field(
            db=db,
            report_id=report_id,
            mapping_id=req.mapping_id,
            action=req.action,
            corrected_value=req.corrected_value,
            notes=req.notes,
            user_id=current_user.id,
        )
        return {
            "message": f"Field '{mapping.exact_official_label}' marked {req.action}",
            "mapping_id": mapping.id,
            "reviewer_action": mapping.reviewer_action,
            "current_value": mapping.generated_value,
            "report_status": mapping.report.status,
            "compliance_status": mapping.report.compliance_status,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{report_id}/certify", summary="Sign Execution Certification")
def sign_certification(
    report_id: str,
    req: SignCertificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    check_report_org_access(current_user, report.organization_id)

    try:
        cert = ReportReviewService.sign_certification(
            db=db,
            report_id=report_id,
            certification_id=req.certification_id,
            signatory_name=req.signatory_name,
            signatory_designation=req.signatory_designation,
            reg_number=req.reg_number,
            user_id=current_user.id,
        )
        return {
            "message": f"Certificate '{cert.official_purpose}' signed successfully",
            "certification_id": cert.id,
            "audit_state": cert.audit_state,
            "signed_at": cert.signed_at.isoformat() if cert.signed_at else None,
            "report_status": cert.report.status,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{report_id}/validate", summary="Re-validate Statutory Compliance")
def validate_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    check_report_org_access(current_user, report.organization_id)

    res = ReportComplianceValidator.validate_report(db, report)
    return res


@router.post("/{report_id}/export", summary="Export Real Submission-Ready DOCX Document")
def export_docx(
    report_id: str,
    req: ExportReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    check_report_org_access(current_user, report.organization_id)

    file_path, file_size, sha256_hash = ReportDocxRenderer.render_report_docx(report)
    report.docx_file_path = file_path
    report.docx_file_size_bytes = file_size
    report.sha256_hash = sha256_hash
    db.commit()

    if req.freeze_version:
        ReportReviewService.freeze_version(
            db=db,
            report_id=report.id,
            docx_file_path=file_path,
            sha256_hash=sha256_hash,
            change_summary=req.change_summary or "Official statutory draft exported",
            user_id=current_user.id,
        )

    return {
        "message": "Submission-ready DOCX exported successfully",
        "report_id": report.id,
        "docx_file_path": file_path,
        "file_size_bytes": file_size,
        "sha256_hash": sha256_hash,
        "status": report.status,
        "download_url": f"/api/v1/reports/{report.id}/download",
    }


@router.get("/{report_id}/download", summary="Download Generated Statutory DOCX Document")
def download_docx(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    check_report_org_access(current_user, report.organization_id)

    if not report.docx_file_path or not os.path.exists(report.docx_file_path):
        # Render on demand
        file_path, file_size, sha256_hash = ReportDocxRenderer.render_report_docx(report)
        report.docx_file_path = file_path
        report.docx_file_size_bytes = file_size
        report.sha256_hash = sha256_hash
        db.commit()

    filename = os.path.basename(report.docx_file_path)
    return FileResponse(
        path=report.docx_file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@router.get("/{report_id}/versions", summary="List Frozen Version Snapshots")
def list_versions(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    check_report_org_access(current_user, report.organization_id)

    versions = (
        db.query(ReportVersion)
        .filter(ReportVersion.report_id == report_id)
        .order_by(ReportVersion.version_number.desc())
        .all()
    )

    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "status": v.status,
            "sha256_hash": v.sha256_hash,
            "change_summary": v.change_summary,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]
