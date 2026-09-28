import os
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.organization import Organization
from app.models.document import Document, DocumentVersion, ProcessingJob, DocumentPage, Table, TableRow
from app.models.chunk import Chunk
from app.services.storage import storage_service
from app.services.ingestion import process_document
from app.services.audit import log_audit_event
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def check_org_access(user: User, org_id: str, db: Session) -> bool:
    user_roles = [r.code for r in user.roles]
    if any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles):
        return True
    return user.organization_id == org_id

from app.core.rate_limit import RateLimiter
from app.core.config import settings

upload_rate_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_UPLOAD_PER_MINUTE, scope="upload")

@router.post("/upload", status_code=status.HTTP_201_CREATED, dependencies=[Depends(upload_rate_limiter)])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    organization_id: str = Form(...),
    title: Optional[str] = Form(None),
    document_type: str = Form("GEOLOGICAL_REPORT"),
    source_tier: str = Form("TIER_B"),
    supersedes_id: Optional[str] = Form(None),
    sync: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # 1. Organization Authorization
    if not check_org_access(current_user, organization_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot upload documents to an organization outside your authorized scope"
        )
        
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Selected organization does not exist")
        
    # 2. File and MIME validation
    mime_type = storage_service.validate_file(file.filename, file.content_type)
    
    # 3. Save file & compute SHA-256
    doc_id = str(uuid.uuid4())
    file_path, sha256_hash, file_size = await storage_service.save_uploaded_file(file, organization_id, doc_id)
    
    doc_title = title.strip() if title and title.strip() else file.filename
    
    # 4. Check for versioning / duplicate hash
    version_num = 1
    existing_doc = None
    if supersedes_id:
        existing_doc = db.query(Document).filter(Document.id == supersedes_id).first()
        if existing_doc:
            prev_versions = db.query(DocumentVersion).filter(DocumentVersion.document_id == existing_doc.id).count()
            version_num = prev_versions + 2
    else:
        existing_doc = db.query(Document).filter(
            Document.organization_id == organization_id,
            Document.sha256_hash == sha256_hash
        ).first()
        
    doc = Document(
        id=doc_id,
        organization_id=organization_id,
        title=doc_title,
        document_type=document_type,
        source_tier=source_tier,
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
    
    if supersedes_id and existing_doc:
        doc_version = DocumentVersion(
            document_id=doc.id,
            version_number=version_num,
            supersedes_id=existing_doc.id,
            file_path=file_path,
            sha256_hash=sha256_hash,
            change_summary=f"Supersedes document {existing_doc.id}"
        )
        db.add(doc_version)
        
    job = ProcessingJob(
        document_id=doc.id,
        job_type="INGESTION_PARSE",
        status="QUEUED",
        progress_pct=0,
        started_at=datetime.utcnow()
    )
    db.add(job)
    db.commit()
    db.refresh(doc)
    db.refresh(job)
    
    # 5. Audit upload event
    log_audit_event(
        db=db,
        action="DOCUMENT_UPLOADED",
        actor_id=current_user.id,
        actor_name=current_user.username,
        role_code=current_user.roles[0].code if current_user.roles else "NONE",
        organization_id=organization_id,
        object_type="document",
        object_id=doc.id,
        sha256_hash=sha256_hash,
        details={
            "filename": file.filename,
            "mime_type": mime_type,
            "size_bytes": file_size,
            "source_tier": source_tier,
            "job_id": job.id
        }
    )
    
    # 6. Execute processing
    if sync:
        process_document(doc.id, job.id)
        db.refresh(doc)
        db.refresh(job)
    else:
        try:
            from app.tasks.ingestion_tasks import process_document_task
            process_document_task.delay(doc.id, job.id)
        except Exception as e:
            logger.warning(f"Could not enqueue Celery task, falling back to background_tasks: {e}")
            background_tasks.add_task(process_document, doc.id, job.id)
        
    return {
        "id": doc.id,
        "title": doc.title,
        "organization_id": doc.organization_id,
        "document_type": doc.document_type,
        "source_tier": doc.source_tier,
        "original_filename": doc.original_filename,
        "sha256_hash": doc.sha256_hash,
        "file_size_bytes": doc.file_size_bytes,
        "status": doc.status,
        "job_id": job.id
    }

@router.get("/")
def list_documents(
    organization_id: Optional[str] = None,
    document_type: Optional[str] = None,
    source_tier: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    user_roles = [r.code for r in current_user.roles]
    is_hq_or_admin = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)
    
    query = db.query(Document)
    
    # Organization Scoping
    if not is_hq_or_admin:
        query = query.filter(Document.organization_id == current_user.organization_id)
    elif organization_id:
        query = query.filter(Document.organization_id == organization_id)
        
    if document_type:
        query = query.filter(Document.document_type == document_type)
    if source_tier:
        query = query.filter(Document.source_tier == source_tier)
    if status:
        query = query.filter(Document.status == status)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(Document.title.ilike(term), Document.original_filename.ilike(term)))
        
    total = query.count()
    docs = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for d in docs:
        org = db.query(Organization).filter(Organization.id == d.organization_id).first()
        result.append({
            "id": d.id,
            "title": d.title,
            "organization_id": d.organization_id,
            "organization_code": org.code if org else None,
            "organization_name": org.name if org else None,
            "document_type": d.document_type,
            "source_tier": d.source_tier,
            "original_filename": d.original_filename,
            "mime_type": d.mime_type,
            "file_size_bytes": d.file_size_bytes,
            "sha256_hash": d.sha256_hash,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        })
        
    return {"total": total, "items": result}

@router.get("/{document_id}")
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not check_org_access(current_user, doc.organization_id, db):
        raise HTTPException(status_code=403, detail="Access denied to document outside authorized organization")
        
    org = db.query(Organization).filter(Organization.id == doc.organization_id).first()
    page_count = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).count()
    table_count = db.query(Table).filter(Table.document_id == doc.id).count()
    chunk_count = db.query(Chunk).filter(Chunk.document_id == doc.id).count()
    latest_job = db.query(ProcessingJob).filter(ProcessingJob.document_id == doc.id).order_by(ProcessingJob.created_at.desc()).first()
    versions = db.query(DocumentVersion).filter(DocumentVersion.document_id == doc.id).all()
    
    return {
        "id": doc.id,
        "title": doc.title,
        "organization_id": doc.organization_id,
        "organization_code": org.code if org else None,
        "organization_name": org.name if org else None,
        "document_type": doc.document_type,
        "source_tier": doc.source_tier,
        "original_filename": doc.original_filename,
        "mime_type": doc.mime_type,
        "file_size_bytes": doc.file_size_bytes,
        "sha256_hash": doc.sha256_hash,
        "status": doc.status,
        "page_count": page_count,
        "table_count": table_count,
        "chunk_count": chunk_count,
        "latest_job": {
            "id": latest_job.id if latest_job else None,
            "status": latest_job.status if latest_job else None,
            "progress_pct": latest_job.progress_pct if latest_job else None,
            "error_message": latest_job.error_message if latest_job else None
        } if latest_job else None,
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "supersedes_id": v.supersedes_id,
                "sha256_hash": v.sha256_hash,
                "created_at": v.created_at.isoformat() if v.created_at else None
            }
            for v in versions
        ],
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
    }

@router.get("/{document_id}/pages")
def get_document_pages(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not check_org_access(current_user, doc.organization_id, db):
        raise HTTPException(status_code=403, detail="Access denied")
        
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id
    ).order_by(DocumentPage.page_number.asc()).all()
    
    return [
        {
            "id": p.id,
            "page_number": p.page_number,
            "extracted_text": p.extracted_text,
            "ocr_applied": p.ocr_applied,
            "confidence_score": p.confidence_score,
            "width": p.width,
            "height": p.height,
            "metadata": p.metadata_json or {}
        }
        for p in pages
    ]

@router.get("/{document_id}/tables")
def get_document_tables(
    document_id: str,
    view: str = Query("physical", pattern="^(physical|logical)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not check_org_access(current_user, doc.organization_id, db):
        raise HTTPException(status_code=403, detail="Access denied")
        
    tables = db.query(Table).filter(
        Table.document_id == document_id
    ).order_by(Table.page_number.asc(), Table.table_index.asc()).all()
    
    physical_items = []
    for t in tables:
        rows = db.query(TableRow).filter(TableRow.table_id == t.id).order_by(TableRow.row_index.asc()).all()
        physical_items.append({
            "id": t.id,
            "page_number": t.page_number,
            "table_index": t.table_index,
            "caption": t.caption,
            "headers": t.headers,
            "row_count": t.row_count,
            "col_count": t.col_count,
            "logical_table_id": t.logical_table_id,
            "is_continuation": t.is_continuation,
            "continuation_of_id": t.continuation_of_id,
            "part_number": t.part_number,
            "total_parts": t.total_parts,
            "has_repeated_headers": t.has_repeated_headers,
            "continuation_confidence": t.continuation_confidence,
            "continuation_status": t.continuation_status,
            "metadata": t.metadata_json or {},
            "rows": [r.cells for r in rows],
            "row_details": [
                {
                    "row_index": r.row_index,
                    "logical_row_index": r.logical_row_index,
                    "source_page": r.source_page,
                    "cells": r.cells
                }
                for r in rows
            ]
        })

    if view == "physical":
        return physical_items

    # Logical view: Group physical slices by logical_table_id
    logical_groups = {}
    for p in physical_items:
        grp_key = p["logical_table_id"] or p["id"]
        if grp_key not in logical_groups:
            logical_groups[grp_key] = []
        logical_groups[grp_key].append(p)

    logical_items = []
    for grp_id, slices in logical_groups.items():
        first_slice = slices[0]
        all_row_details = []
        all_rows = []
        pages_spanned = sorted(list(set(s["page_number"] for s in slices)))
        
        for s in slices:
            all_rows.extend(s["rows"])
            all_row_details.extend(s["row_details"])

        statuses = [s["continuation_status"] for s in slices]
        if "REVIEW_REQUIRED" in statuses:
            comp_status = "REVIEW_REQUIRED"
        elif len(slices) > 1 or any(s["is_continuation"] for s in slices):
            comp_status = "AUTO_MERGED"
        else:
            comp_status = "STANDALONE"

        min_conf = min(s["continuation_confidence"] for s in slices) if slices else 1.0
        page_label = f"Pages {pages_spanned[0]}–{pages_spanned[-1]}" if len(pages_spanned) > 1 else f"Page {pages_spanned[0]}"

        logical_items.append({
            "id": grp_id,
            "logical_table_id": grp_id,
            "page_number": first_slice["page_number"],
            "caption": first_slice["caption"] or f"Logical Table ({page_label})",
            "headers": first_slice["headers"],
            "row_count": len(all_rows),
            "col_count": first_slice["col_count"],
            "total_parts": len(slices),
            "part_number": 1,
            "spanned_pages": pages_spanned,
            "page_label": page_label,
            "continuation_status": comp_status,
            "continuation_confidence": min_conf,
            "has_repeated_headers": any(s["has_repeated_headers"] for s in slices),
            "metadata": first_slice.get("metadata", {}),
            "rows": all_rows,
            "row_details": all_row_details,
            "physical_slices": [
                {
                    "id": s["id"],
                    "page_number": s["page_number"],
                    "table_index": s["table_index"],
                    "part_number": s["part_number"],
                    "row_count": s["row_count"],
                    "continuation_status": s["continuation_status"]
                }
                for s in slices
            ]
        })

    return logical_items

@router.get("/{document_id}/chunks")
def get_document_chunks(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not check_org_access(current_user, doc.organization_id, db):
        raise HTTPException(status_code=403, detail="Access denied")
        
    chunks = db.query(Chunk).filter(
        Chunk.document_id == document_id
    ).order_by(Chunk.chunk_index.asc()).all()
    
    return [
        {
            "id": c.id,
            "chunk_index": c.chunk_index,
            "page_number": c.page_number,
            "chunk_type": c.chunk_type,
            "section_heading": c.section_heading,
            "content": c.content,
            "metadata": c.metadata_json or {}
        }
        for c in chunks
    ]

@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not check_org_access(current_user, doc.organization_id, db):
        raise HTTPException(status_code=403, detail="Access denied")
        
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Stored physical file not found on disk")
        
    return FileResponse(
        path=doc.file_path,
        filename=doc.original_filename,
        media_type=doc.mime_type
    )
