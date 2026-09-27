import uuid
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.organization import Organization
from app.models.document import Document, ProcessingJob, DocumentPage, Table
from app.models.visual import VisualAsset
from app.models.extraction import ExtractedField
from app.models.verification import VerificationTask
from app.models.evidence import DocumentRelationship
from app.services.storage import storage_service
from app.services.ingestion import process_document
from app.services.audit import log_audit_event
from app.schemas.evidence import (
    UploadItemReceipt,
    UnifiedEvidenceUploadResponse,
    EvidenceSummaryResponse,
    UnifiedEvidenceItem,
    EvidenceListResponse,
    EvidenceReviewRequest,
    DocumentRelationshipResponse,
)

router = APIRouter()

def check_org_access(user: User, org_id: str) -> bool:
    user_roles = [r.code for r in user.roles]
    if any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles):
        return True
    return user.organization_id == org_id

def infer_document_type(filename: str, ext: str) -> str:
    fn_lower = filename.lower()
    if any(k in fn_lower for k in ["prod", "dispatch", "target", "offtake"]):
        return "PRODUCTION_REPORT"
    if any(k in fn_lower for k in ["geo", "reserve", "litho", "borehole", "drilling", "coal_seam"]):
        return "GEOLOGICAL_REPORT"
    if any(k in fn_lower for k in ["mine", "block", "plan", "ocp", "colliery"]):
        return "MINE_INFORMATION"
    if any(k in fn_lower for k in ["env", "forest", "clearance"]):
        return "ENVIRONMENTAL_CLEARANCE"
    if any(k in fn_lower for k in ["annex", "table", "data", "sheet"]) or ext in [".xlsx", ".xls", ".csv"]:
        return "ANNEXURE_SPREADSHEET"
    return "GEOLOGICAL_REPORT"

@router.post("/upload", response_model=UnifiedEvidenceUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_unified_evidence(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    organization_id: str = Form(...),
    source_tier: Optional[str] = Form("TIER_B"),
    sync: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    ONE-ACTION EVIDENCE UPLOAD:
    Accepts heterogeneous files (PDF, DOCX, XLSX, XLS, CSV, TXT, JPG, PNG).
    Automatically detects MIME, infers document category, computes SHA-256,
    stores partitioned files, registers processing jobs, and returns an evidence receipt.
    """
    if not check_org_access(current_user, organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot upload documents to an organization outside your authorized scope"
        )

    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Selected organization does not exist")

    batch_id = str(uuid.uuid4())
    uploaded_items: List[UploadItemReceipt] = []

    for file in files:
        ext = Path(file.filename).suffix.lower()
        mime_type = storage_service.validate_file(file.filename, file.content_type)
        inferred_type = infer_document_type(file.filename, ext)

        doc_id = str(uuid.uuid4())
        file_path, sha256_hash, file_size = await storage_service.save_uploaded_file(file, organization_id, doc_id)

        doc = Document(
            id=doc_id,
            organization_id=organization_id,
            title=file.filename,
            document_type=inferred_type,
            source_tier=source_tier or "TIER_B",
            original_filename=file.filename,
            file_path=file_path,
            mime_type=mime_type,
            file_size_bytes=file_size,
            sha256_hash=sha256_hash,
            status="QUEUED",
            created_by=current_user.id,
            updated_at=datetime.utcnow()
        )
        db.add(doc)

        job = ProcessingJob(
            document_id=doc.id,
            job_type="INGESTION_PARSE",
            status="QUEUED",
            progress_pct=0,
            started_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()

        # Execute processing
        if sync:
            process_document(doc.id, job.id)
        else:
            background_tasks.add_task(process_document, doc.id, job.id)

        format_label = ext.lstrip(".").upper()
        uploaded_items.append(
            UploadItemReceipt(
                document_id=doc.id,
                original_filename=file.filename,
                detected_format=format_label,
                inferred_type=inferred_type,
                status="PROCESSING" if sync else "QUEUED",
                file_size_bytes=file_size,
                sha256_hash=sha256_hash
            )
        )

    log_audit_event(
        db=db,
        action="EVIDENCE_BATCH_UPLOADED",
        actor_id=current_user.id,
        organization_id=organization_id,
        object_type="evidence_batch",
        object_id=batch_id,
        details={
            "file_count": len(files),
            "files": [f.filename for f in files]
        }
    )

    return UnifiedEvidenceUploadResponse(
        batch_id=batch_id,
        total_files=len(uploaded_items),
        organization_id=organization_id,
        items=uploaded_items
    )

@router.get("/summary", response_model=EvidenceSummaryResponse)
def get_evidence_summary(
    organization_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns live count metrics for the Universal Evidence Layer.
    """
    user_roles = [r.code for r in current_user.roles]
    is_admin_or_hq = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)

    org_filter = organization_id if organization_id else (None if is_admin_or_hq else current_user.organization_id)

    # Documents query
    doc_q = db.query(func.count(Document.id))
    if org_filter:
        doc_q = doc_q.filter(Document.organization_id == org_filter)
    total_docs = doc_q.scalar() or 0

    # Structured values query
    field_q = db.query(func.count(ExtractedField.id))
    if org_filter:
        field_q = field_q.filter(ExtractedField.organization_id == org_filter)
    structured_count = field_q.scalar() or 0

    # Visual assets query
    visual_q = db.query(func.count(VisualAsset.id)).join(Document, VisualAsset.document_id == Document.id)
    if org_filter:
        visual_q = visual_q.filter(Document.organization_id == org_filter)
    visual_count = visual_q.scalar() or 0

    # Tables query
    table_q = db.query(func.count(Table.id)).join(Document, Table.document_id == Document.id)
    if org_filter:
        table_q = table_q.filter(Document.organization_id == org_filter)
    table_count = table_q.scalar() or 0

    # Text pages query
    page_q = db.query(func.count(DocumentPage.id)).join(Document, DocumentPage.document_id == Document.id)
    if org_filter:
        page_q = page_q.filter(Document.organization_id == org_filter)
    text_count = page_q.scalar() or 0

    # Verification / Needs Review query
    review_q = db.query(func.count(VerificationTask.id)).filter(VerificationTask.status == "PENDING")
    if org_filter:
        review_q = review_q.filter(VerificationTask.organization_id == org_filter)
    needs_review_count = review_q.scalar() or 0

    # Relationships query
    rel_q = db.query(func.count(DocumentRelationship.id)).join(Document, DocumentRelationship.source_document_id == Document.id)
    if org_filter:
        rel_q = rel_q.filter(Document.organization_id == org_filter)
    relationships_count = rel_q.scalar() or 0

    return EvidenceSummaryResponse(
        total_documents=total_docs,
        text_evidence_count=text_count,
        table_evidence_count=table_count,
        structured_values_count=structured_count,
        visual_assets_count=visual_count,
        needs_review_count=needs_review_count,
        relationships_count=relationships_count
    )

@router.get("/items", response_model=EvidenceListResponse)
def get_evidence_items(
    organization_id: Optional[str] = None,
    document_id: Optional[str] = None,
    evidence_type: Optional[str] = Query("ALL"),  # ALL, TEXT, TABLE, STRUCTURED_VALUE, VISUAL, NEEDS_REVIEW
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Unified cross-modal evidence register.
    Combines structured fields, visual diagrams/plans, tables, and text citations
    with exact format-aware provenance (Sheet/Cell, Row/Col, Page, BBox).
    """
    user_roles = [r.code for r in current_user.roles]
    is_admin_or_hq = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)
    org_filter = organization_id if organization_id else (None if is_admin_or_hq else current_user.organization_id)

    unified_items: List[UnifiedEvidenceItem] = []

    # 1. Fetch Structured Values
    if evidence_type in ["ALL", "STRUCTURED_VALUE", "NEEDS_REVIEW"]:
        q = db.query(ExtractedField, Document).join(Document, ExtractedField.document_id == Document.id)
        if org_filter:
            q = q.filter(ExtractedField.organization_id == org_filter)
        if document_id:
            q = q.filter(ExtractedField.document_id == document_id)
        if evidence_type == "NEEDS_REVIEW":
            q = q.filter(or_(
                ExtractedField.validation_status.in_(["WARNING", "ERROR"]),
                ExtractedField.verification_status == "UNVERIFIED"
            ))
        if search:
            s = f"%{search}%"
            q = q.filter(or_(
                ExtractedField.field_name.ilike(s),
                ExtractedField.raw_value.ilike(s),
                ExtractedField.normalized_value.ilike(s)
            ))
        
        fields_with_docs = q.order_by(ExtractedField.created_at.desc()).limit(limit).all()
        for field, doc in fields_with_docs:
            meta = field.metadata_json or {}
            provenance = meta.get("provenance_display")
            if not provenance:
                if field.page_number:
                    provenance = f"Page {field.page_number}"
                else:
                    provenance = "Document Body"

            display_val = field.normalized_value or field.raw_value
            if field.unit:
                display_val = f"{display_val} {field.unit}"

            unified_items.append(
                UnifiedEvidenceItem(
                    id=f"val_{field.id}",
                    evidence_type="STRUCTURED_VALUE",
                    document_id=doc.id,
                    document_title=doc.title or doc.original_filename,
                    organization_id=field.organization_id,
                    page_number=field.page_number,
                    provenance_display=provenance,
                    content_preview=f"{field.field_name.replace('_', ' ').title()}: {display_val}",
                    field_name=field.field_name,
                    value=field.normalized_value or field.raw_value,
                    unit=field.unit,
                    numeric_value=field.numeric_value,
                    confidence_score=field.confidence_score,
                    verification_status=field.verification_status,
                    metadata={
                        "data_type": field.data_type,
                        "category": field.field_category,
                        "raw_value": field.raw_value,
                        **meta
                    }
                )
            )

    # 2. Fetch Visual Assets
    if evidence_type in ["ALL", "VISUAL", "NEEDS_REVIEW"]:
        q = db.query(VisualAsset, Document).join(Document, VisualAsset.document_id == Document.id)
        if org_filter:
            q = q.filter(Document.organization_id == org_filter)
        if document_id:
            q = q.filter(VisualAsset.document_id == document_id)
        if evidence_type == "NEEDS_REVIEW":
            q = q.filter(VisualAsset.verification_status == "REVIEW_REQUIRED")
        if search:
            s = f"%{search}%"
            q = q.filter(or_(
                VisualAsset.visual_type.ilike(s),
                VisualAsset.caption.ilike(s),
                VisualAsset.raw_ocr_text.ilike(s),
                VisualAsset.figure_number.ilike(s)
            ))

        visuals_with_docs = q.order_by(VisualAsset.created_at.desc()).limit(limit).all()
        for visual, doc in visuals_with_docs:
            bbox = visual.bbox_json or {}
            bbox_str = f" [bbox: {bbox.get('x0', 0):.0f},{bbox.get('y0', 0):.0f}-{bbox.get('x1', 0):.0f},{bbox.get('y1', 0):.0f}]" if bbox else ""
            prov = f"Page {visual.page_number}{bbox_str}"

            caption_disp = visual.caption or f"{visual.visual_type.replace('_', ' ').title()} ({visual.figure_number or 'Unlabeled'})"
            if visual.raw_ocr_text:
                caption_disp += f" — OCR: {visual.raw_ocr_text[:60]}"

            unified_items.append(
                UnifiedEvidenceItem(
                    id=f"vis_{visual.id}",
                    evidence_type="VISUAL",
                    document_id=doc.id,
                    document_title=doc.title or doc.original_filename,
                    organization_id=doc.organization_id,
                    page_number=visual.page_number,
                    provenance_display=prov,
                    content_preview=caption_disp,
                    field_name=visual.visual_type,
                    value=visual.visual_type,
                    confidence_score=visual.classification_confidence,
                    verification_status=visual.verification_status,
                    metadata={
                        "visual_type": visual.visual_type,
                        "figure_number": visual.figure_number,
                        "caption": visual.caption,
                        "bbox": visual.bbox_json,
                        "file_path": visual.file_path,
                        "image_id": visual.id,
                        "ocr_snippet": visual.normalized_ocr_text
                    }
                )
            )

    # 3. Fetch Tables
    if evidence_type in ["ALL", "TABLE"]:
        q = db.query(Table, Document).join(Document, Table.document_id == Document.id)
        if org_filter:
            q = q.filter(Document.organization_id == org_filter)
        if document_id:
            q = q.filter(Table.document_id == document_id)
        if search:
            s = f"%{search}%"
            q = q.filter(or_(Table.caption.ilike(s), Table.headers.astext.ilike(s) if hasattr(Table.headers, "astext") else Table.caption.ilike(s)))

        tables_with_docs = q.order_by(Table.created_at.desc()).limit(limit).all()
        for tbl, doc in tables_with_docs:
            meta = tbl.metadata_json or {}
            sheet_name = meta.get("sheet_name")
            prov = f"Sheet: '{sheet_name}'" if sheet_name else f"Page {tbl.page_number}, Table #{tbl.table_index}"
            preview = tbl.caption or f"Table ({tbl.row_count} rows, {tbl.col_count} cols)"
            if tbl.headers:
                preview += f" — Cols: {', '.join(tbl.headers[:4])}"

            unified_items.append(
                UnifiedEvidenceItem(
                    id=f"tbl_{tbl.id}",
                    evidence_type="TABLE",
                    document_id=doc.id,
                    document_title=doc.title or doc.original_filename,
                    organization_id=doc.organization_id,
                    page_number=tbl.page_number,
                    provenance_display=prov,
                    content_preview=preview,
                    confidence_score=tbl.continuation_confidence or 1.0,
                    verification_status="VERIFIED" if tbl.continuation_status == "AUTO_MERGED" else "PENDING",
                    metadata={
                        "headers": tbl.headers,
                        "row_count": tbl.row_count,
                        "col_count": tbl.col_count,
                        **meta
                    }
                )
            )

    # Paginate combined results
    total_count = len(unified_items)
    paged_items = unified_items[offset : offset + limit]

    return EvidenceListResponse(total=total_count, items=paged_items)

@router.get("/relationships", response_model=List[DocumentRelationshipResponse])
def get_evidence_relationships(
    organization_id: Optional[str] = None,
    document_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns discovered factual cross-document relationships.
    """
    user_roles = [r.code for r in current_user.roles]
    is_admin_or_hq = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)
    org_filter = organization_id if organization_id else (None if is_admin_or_hq else current_user.organization_id)

    q = db.query(DocumentRelationship)
    if document_id:
        q = q.filter(or_(
            DocumentRelationship.source_document_id == document_id,
            DocumentRelationship.target_document_id == document_id
        ))

    rels = q.order_by(DocumentRelationship.created_at.desc()).limit(100).all()

    # Preload doc titles
    doc_ids = set()
    for r in rels:
        doc_ids.add(r.source_document_id)
        doc_ids.add(r.target_document_id)

    docs_map = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()}

    results = []
    for r in rels:
        s_doc = docs_map.get(r.source_document_id)
        t_doc = docs_map.get(r.target_document_id)
        if not s_doc or not t_doc:
            continue
        if org_filter and (s_doc.organization_id != org_filter and t_doc.organization_id != org_filter):
            continue

        results.append(
            DocumentRelationshipResponse(
                id=r.id,
                source_document_id=r.source_document_id,
                source_title=s_doc.title or s_doc.original_filename,
                target_document_id=r.target_document_id,
                target_title=t_doc.title or t_doc.original_filename,
                relationship_type=r.relationship_type,
                confidence=r.confidence,
                matching_criteria=r.matching_criteria,
                description=r.description,
                created_at=r.created_at.isoformat() if r.created_at else ""
            )
        )

    return results

@router.post("/{item_id}/review")
def review_evidence_item(
    item_id: str,
    req: EvidenceReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Review action for an evidence item (APPROVE, REJECT, CORRECT).
    """
    prefix = item_id.split("_")[0]
    actual_id = item_id[len(prefix)+1:] if "_" in item_id else item_id

    if prefix == "val":
        field = db.query(ExtractedField).filter(ExtractedField.id == actual_id).first()
        if not field:
            raise HTTPException(status_code=404, detail="Extracted value not found")

        if req.action == "APPROVE":
            field.verification_status = "VERIFIED"
            field.validation_status = "PASS"
        elif req.action == "REJECT":
            field.verification_status = "REJECTED"
        elif req.action == "CORRECT":
            field.verification_status = "CORRECTED"
            field.is_corrected = True
            field.corrected_value = req.corrected_value
            field.corrected_by = current_user.id
            field.corrected_at = datetime.utcnow()
            if req.corrected_value:
                field.normalized_value = req.corrected_value

        # Resolve associated verification tasks if any
        v_tasks = db.query(VerificationTask).filter(
            VerificationTask.target_id == actual_id,
            VerificationTask.status == "PENDING"
        ).all()
        for vt in v_tasks:
            vt.status = "RESOLVED"
            vt.reviewed_by = current_user.id
            vt.resolved_at = datetime.utcnow()
            vt.review_notes = f"{req.action}: {req.notes or 'Reviewed in Evidence Control Room'}"

        db.commit()

        log_audit_event(
            db=db,
            action="EVIDENCE_VERIFIED",
            actor_id=current_user.id,
            organization_id=field.organization_id,
            object_type="extracted_field",
            object_id=field.id,
            details={"action": req.action, "corrected_value": req.corrected_value, "notes": req.notes}
        )

        return {"status": "SUCCESS", "item_id": item_id, "verification_status": field.verification_status}

    elif prefix == "vis":
        visual = db.query(VisualAsset).filter(VisualAsset.id == actual_id).first()
        if not visual:
            raise HTTPException(status_code=404, detail="Visual asset not found")

        doc = db.query(Document).filter(Document.id == visual.document_id).first()

        if req.action == "APPROVE":
            visual.verification_status = "VERIFIED"
        elif req.action == "REJECT":
            visual.verification_status = "REJECTED"
        elif req.action == "CORRECT":
            visual.verification_status = "VERIFIED"
            if req.corrected_value:
                visual.visual_type = req.corrected_value

        v_tasks = db.query(VerificationTask).filter(
            VerificationTask.target_id == actual_id,
            VerificationTask.status == "PENDING"
        ).all()
        for vt in v_tasks:
            vt.status = "RESOLVED"
            vt.reviewed_by = current_user.id
            vt.resolved_at = datetime.utcnow()

        db.commit()

        log_audit_event(
            db=db,
            action="VISUAL_EVIDENCE_VERIFIED",
            actor_id=current_user.id,
            organization_id=doc.organization_id if doc else current_user.organization_id,
            object_type="visual_asset",
            object_id=visual.id,
            details={"action": req.action, "notes": req.notes}
        )

        return {"status": "SUCCESS", "item_id": item_id, "verification_status": visual.verification_status}

    raise HTTPException(status_code=400, detail=f"Unsupported evidence type prefix '{prefix}' for direct review")
