import logging
from typing import Optional, Dict, Any
from app.core.celery_app import celery_app
from app.db.database import SessionLocal
from app.services.job_janitor import reap_stale_jobs

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.reap_stale_jobs_task")
def reap_stale_jobs_task(self, stale_timeout_minutes: Optional[int] = None) -> Dict[str, Any]:
    """
    Periodic Celery Beat task to detect, recover, and transition orphaned/stale
    processing jobs to FAILED status.
    """
    logger.info("Executing Celery janitor sweep for stale processing jobs", extra={"event": "janitor_sweep_started"})
    db = SessionLocal()
    try:
        result = reap_stale_jobs(db, stale_timeout_minutes=stale_timeout_minutes)
        logger.info(
            f"Celery janitor sweep completed: {result['reaped_count']} jobs reaped",
            extra={
                "event": "janitor_sweep_completed",
                "reaped_count": result["reaped_count"],
                "timeout_minutes": result["timeout_minutes"],
            },
        )
        return result
    finally:
        db.close()
