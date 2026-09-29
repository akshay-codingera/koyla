from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.document import ProcessingJob, Document

router = APIRouter()

@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Processing job not found")
        
    doc = db.query(Document).filter(Document.id == job.document_id).first()
    if doc:
        user_roles = [r.code for r in current_user.roles]
        is_hq_or_admin = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)
        if not is_hq_or_admin and current_user.organization_id != doc.organization_id:
            raise HTTPException(status_code=403, detail="Access denied to job outside authorized organization")

    return {
        "id": job.id,
        "document_id": job.document_id,
        "job_type": job.job_type,
        "status": job.status,
        "progress_pct": job.progress_pct,
        "retry_count": getattr(job, "retry_count", 0) or 0,
        "error_message": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.post("/jobs/reap-stale")
def trigger_stale_job_sweep(
    timeout_minutes: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Administrative on-demand trigger for stuck job recovery / Celery janitor.
    Authorized for HQ officers, ministry reviewers, and system admins.
    """
    user_roles = [r.code for r in current_user.roles]
    is_authorized = any(r in ["MINISTRY_OFFICER", "CMPDI_HQ_OFFICER", "SYSTEM_ADMIN"] for r in user_roles)
    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to run stuck job recovery"
        )
    
    from app.services.job_janitor import reap_stale_jobs
    result = reap_stale_jobs(db=db, stale_timeout_minutes=timeout_minutes, actor_id=current_user.id)
    return result
