import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.models.document import ProcessingJob, Document
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)


def check_job_is_stale(
    job: ProcessingJob,
    stale_timeout_minutes: Optional[int] = None,
    now: Optional[datetime] = None,
) -> bool:
    """
    Evaluates whether a given ProcessingJob has exceeded the stale timeout threshold.
    """
    if job.status != "PROCESSING":
        return False

    effective_timeout = (
        stale_timeout_minutes
        if stale_timeout_minutes is not None
        else settings.JOB_STALE_TIMEOUT_MINUTES
    )
    current_time = now or datetime.utcnow()
    cutoff = current_time - timedelta(minutes=effective_timeout)

    ref_time = job.started_at or job.created_at
    if not ref_time:
        return False

    return ref_time < cutoff


def get_stale_job_count(
    db: Session,
    stale_timeout_minutes: Optional[int] = None,
) -> int:
    """
    Returns the count of processing jobs that have exceeded the stale timeout threshold.
    """
    effective_timeout = (
        stale_timeout_minutes
        if stale_timeout_minutes is not None
        else settings.JOB_STALE_TIMEOUT_MINUTES
    )
    cutoff = datetime.utcnow() - timedelta(minutes=effective_timeout)

    return (
        db.query(func.count(ProcessingJob.id))
        .filter(
            ProcessingJob.status == "PROCESSING",
            func.coalesce(ProcessingJob.started_at, ProcessingJob.created_at) < cutoff,
        )
        .scalar()
        or 0
    )


def reap_stale_jobs(
    db: Session,
    stale_timeout_minutes: Optional[int] = None,
    actor_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Identifies, recovers, and safely transitions orphaned/stale background jobs
    from PROCESSING to FAILED status.

    Concurrency safety:
    Uses conditional SQL updates ensuring that only jobs that are still actively
    in 'PROCESSING' status at execution time are transitioned. If another worker
    completes the job or another janitor instance reaps it first, the transition
    is cleanly skipped.

    Audit trail & Observability:
    Creates an immutable AuditEvent and emits structured logs for every reaped job.
    Also cleans up associated Redis deduplication locks if reachable.
    """
    effective_timeout = (
        stale_timeout_minutes
        if stale_timeout_minutes is not None
        else settings.JOB_STALE_TIMEOUT_MINUTES
    )
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=effective_timeout)

    candidates = (
        db.query(ProcessingJob)
        .filter(
            ProcessingJob.status == "PROCESSING",
            func.coalesce(ProcessingJob.started_at, ProcessingJob.created_at) < cutoff,
        )
        .all()
    )

    reaped_jobs: List[Dict[str, Any]] = []

    for candidate in candidates:
        try:
            error_message = (
                f"JOB_STALE_TIMEOUT: Job exceeded configured processing timeout of "
                f"{effective_timeout} minutes and was marked FAILED by the job janitor."
            )

            # Atomic conditional update: only update if still 'PROCESSING'
            affected_rows = (
                db.query(ProcessingJob)
                .filter(
                    ProcessingJob.id == candidate.id,
                    ProcessingJob.status == "PROCESSING",
                )
                .update(
                    {
                        ProcessingJob.status: "FAILED",
                        ProcessingJob.error_message: error_message,
                        ProcessingJob.completed_at: now,
                    },
                    synchronize_session=False,
                )
            )

            if affected_rows == 0:
                logger.info(
                    f"Job {candidate.id} was no longer in PROCESSING status during reap attempt; skipping.",
                    extra={"event": "job_reap_race_skipped", "job_id": candidate.id},
                )
                continue

            # Calculate duration
            ref_time = candidate.started_at or candidate.created_at
            duration_seconds = (
                round((now - ref_time).total_seconds(), 2) if ref_time else 0.0
            )

            # Align parent Document status to FAILED if it was in PROCESSING
            doc = db.query(Document).filter(Document.id == candidate.document_id).first()
            if doc and doc.status == "PROCESSING":
                doc.status = "FAILED"
                doc.updated_at = now

            db.commit()

            # Clean up Redis deduplication lock
            try:
                from app.tasks.ingestion_tasks import get_redis_client
                redis_client = get_redis_client()
                if redis_client:
                    redis_client.delete(f"job_lock:{candidate.id}")
            except Exception as redis_exc:
                logger.debug(
                    f"Redis lock release skipped for {candidate.id}: {redis_exc}"
                )

            # Record immutable audit event
            try:
                log_audit_event(
                    db=db,
                    action="JOB_STALE_TIMEOUT",
                    actor_id=actor_id,
                    actor_name="JobJanitor" if not actor_id else None,
                    role_code="SYSTEM" if not actor_id else None,
                    organization_id=doc.organization_id if doc else None,
                    object_type="processing_job",
                    object_id=candidate.id,
                    sha256_hash=doc.sha256_hash if doc else None,
                    details={
                        "reason": "JOB_STALE_TIMEOUT",
                        "job_id": candidate.id,
                        "document_id": candidate.document_id,
                        "organization_id": doc.organization_id if doc else None,
                        "started_at": (
                            candidate.started_at.isoformat()
                            if candidate.started_at
                            else None
                        ),
                        "created_at": (
                            candidate.created_at.isoformat()
                            if candidate.created_at
                            else None
                        ),
                        "duration_seconds": duration_seconds,
                        "timeout_minutes": effective_timeout,
                        "error_message": error_message,
                    },
                )
            except Exception as audit_exc:
                logger.warning(
                    f"Failed to record audit event for reaped job {candidate.id}: {audit_exc}"
                )

            # Structured logging
            logger.warning(
                f"JobJanitor reaped stale job {candidate.id} for document {candidate.document_id} "
                f"(elapsed: {duration_seconds}s, threshold: {effective_timeout}m)",
                extra={
                    "event": "job_reaped",
                    "job_id": candidate.id,
                    "document_id": candidate.document_id,
                    "organization_id": doc.organization_id if doc else None,
                    "duration_seconds": duration_seconds,
                    "timeout_minutes": effective_timeout,
                    "status": "FAILED",
                },
            )

            reaped_jobs.append(
                {
                    "job_id": candidate.id,
                    "document_id": candidate.document_id,
                    "organization_id": doc.organization_id if doc else None,
                    "duration_seconds": duration_seconds,
                    "error_message": error_message,
                }
            )

        except Exception as job_exc:
            db.rollback()
            logger.error(
                f"Unexpected error while reaping job {candidate.id}: {job_exc}",
                exc_info=True,
                extra={"event": "job_reap_error", "job_id": candidate.id},
            )

    return {
        "status": "COMPLETED",
        "reaped_count": len(reaped_jobs),
        "reaped_jobs": reaped_jobs,
        "timeout_minutes": effective_timeout,
        "cutoff": cutoff.isoformat(),
        "timestamp": now.isoformat(),
    }
