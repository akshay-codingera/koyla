import logging
from datetime import datetime
import redis
from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.database import SessionLocal
from app.models.document import ProcessingJob, Document
from app.services.ingestion import process_document

logger = logging.getLogger(__name__)


def get_redis_client():
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception as e:
        logger.debug(f"Redis not reachable for lock: {e}")
        return None


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5, name="app.tasks.process_document_task")
def process_document_task(self, document_id: str, job_id: str):
    """
    Persistent Celery task for processing ingested documents.
    Supports retry on transient failure, deduplication locking,
    and state survival across restarts.
    """
    logger.info(f"Worker picked up job {job_id} for document {document_id} (Attempt {self.request.retries + 1})")

    # 1. Deduplication Lock
    redis_client = get_redis_client()
    lock_key = f"job_lock:{job_id}"
    lock_acquired = False
    if redis_client:
        lock_acquired = bool(redis_client.set(lock_key, "active", nx=True, ex=3600))
        if not lock_acquired:
            logger.warning(f"Job {job_id} is already actively being processed by another worker. Skipping duplicate.")
            return {"status": "SKIPPED_DUPLICATE", "job_id": job_id}

    db = SessionLocal()
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        doc = db.query(Document).filter(Document.id == document_id).first()

        if not job or not doc:
            logger.error(f"Job {job_id} or Document {document_id} not found in database.")
            return {"status": "NOT_FOUND"}

        if job.status == "COMPLETED":
            logger.info(f"Job {job_id} is already completed. Skipping.")
            return {"status": "ALREADY_COMPLETED"}

        # Update state to PROCESSING
        job.status = "PROCESSING"
        job.retry_count = self.request.retries
        if not job.started_at:
            job.started_at = datetime.utcnow()
        doc.status = "PROCESSING"
        db.commit()
    finally:
        db.close()

    try:
        # Run actual document ingestion pipeline
        process_document(document_id, job_id, raise_on_error=True)

        # Verify job marked completed
        db = SessionLocal()
        try:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if job and job.status != "COMPLETED":
                job.status = "COMPLETED"
                job.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

        return {"status": "COMPLETED", "job_id": job_id}

    except Exception as exc:
        logger.error(f"Error in task processing document {document_id}: {exc}")

        db = SessionLocal()
        try:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            doc = db.query(Document).filter(Document.id == document_id).first()

            if self.request.retries < self.max_retries:
                # Transient failure -> mark RETRYING
                if job:
                    job.status = "RETRYING"
                    job.retry_count = self.request.retries + 1
                    job.error_message = f"Attempt {self.request.retries + 1} failed: {str(exc)}"
                if doc:
                    doc.status = "RETRYING"
                db.commit()

                # Release deduplication lock before retry
                if redis_client and lock_acquired:
                    redis_client.delete(lock_key)

                raise self.retry(exc=exc)
            else:
                # Final failure -> mark FAILED
                if job:
                    job.status = "FAILED"
                    job.retry_count = self.request.retries + 1
                    job.error_message = f"Exceeded max retries: {str(exc)}"
                    job.completed_at = datetime.utcnow()
                if doc:
                    doc.status = "FAILED"
                db.commit()
                return {"status": "FAILED", "job_id": job_id, "error": str(exc)}
        finally:
            db.close()

    finally:
        if redis_client and lock_acquired:
            redis_client.delete(lock_key)
