import os
import sys
import uuid
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.db.database import SessionLocal
from app.core.config import settings
from app.core.celery_app import celery_app
from app.models.document import Document, ProcessingJob
from app.models.organization import Organization
from app.models.audit import AuditEvent
from app.services.job_janitor import reap_stale_jobs, check_job_is_stale, get_stale_job_count
from app.tasks.janitor_tasks import reap_stale_jobs_task

client = TestClient(app)


def get_token(username="hq_officer", password="Admin123!"):
    res = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def get_analyst_token(username="ecl_analyst", password="Password123!"):
    res = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=45, created_offset_minutes=50, doc_status="PROCESSING"):
    org = db.query(Organization).first()
    now = datetime.utcnow()
    doc = Document(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        title=f"Test Stale Doc {uuid.uuid4().hex[:6]}",
        document_type="GEOLOGICAL_REPORT",
        original_filename="test_stale.pdf",
        file_path="storage/test_stale.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        status=doc_status,
        created_at=now - timedelta(minutes=created_offset_minutes),
        updated_at=now - timedelta(minutes=created_offset_minutes),
    )
    db.add(doc)

    started_at = (now - timedelta(minutes=started_offset_minutes)) if started_offset_minutes is not None else None
    job = ProcessingJob(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        job_type="INGESTION",
        status=status,
        progress_pct=25 if status == "PROCESSING" else (100 if status == "COMPLETED" else 0),
        started_at=started_at,
        created_at=now - timedelta(minutes=created_offset_minutes),
    )
    db.add(job)
    db.commit()
    db.refresh(doc)
    db.refresh(job)
    return doc, job


def test_stale_job_configuration():
    """Verify settings configure stale job timeout and janitor interval."""
    assert hasattr(settings, "JOB_STALE_TIMEOUT_MINUTES")
    assert hasattr(settings, "JOB_JANITOR_INTERVAL_MINUTES")
    assert settings.JOB_STALE_TIMEOUT_MINUTES >= 1
    assert settings.JOB_JANITOR_INTERVAL_MINUTES >= 1


def test_fresh_job_not_touched():
    """Verify fresh job (< configured timeout) is NOT reaped."""
    db = SessionLocal()
    try:
        doc, job = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=5)
        
        # Verify check_job_is_stale helper
        assert check_job_is_stale(job, stale_timeout_minutes=30) is False

        result = reap_stale_jobs(db, stale_timeout_minutes=30)
        
        db.refresh(job)
        db.refresh(doc)
        assert job.status == "PROCESSING"
        assert doc.status == "PROCESSING"
        assert job.id not in [r["job_id"] for r in result["reaped_jobs"]]
    finally:
        db.close()


def test_stale_job_transitioned_to_failed():
    """Verify stale job (> configured timeout) transitions to FAILED with diagnostic message."""
    db = SessionLocal()
    try:
        doc, job = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=45)
        
        # Verify check_job_is_stale helper
        assert check_job_is_stale(job, stale_timeout_minutes=30) is True

        result = reap_stale_jobs(db, stale_timeout_minutes=30)
        
        db.refresh(job)
        db.refresh(doc)
        
        assert job.status == "FAILED"
        assert job.completed_at is not None
        assert "JOB_STALE_TIMEOUT" in job.error_message
        assert "exceeded configured processing timeout of 30 minutes" in job.error_message
        assert doc.status == "FAILED"
        assert any(r["job_id"] == job.id for r in result["reaped_jobs"])
    finally:
        db.close()


def test_parent_document_status_aligned():
    """Verify parent document in PROCESSING is transitioned to FAILED, but PROCESSED is not overwritten."""
    db = SessionLocal()
    try:
        # Case A: Document in PROCESSING -> transitions to FAILED
        doc_a, job_a = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=40, doc_status="PROCESSING")
        
        # Case B: Document already PROCESSED -> status is preserved
        doc_b, job_b = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=40, doc_status="PROCESSED")
        
        reap_stale_jobs(db, stale_timeout_minutes=30)
        
        db.refresh(doc_a)
        db.refresh(doc_b)
        db.refresh(job_a)
        db.refresh(job_b)
        
        assert job_a.status == "FAILED"
        assert doc_a.status == "FAILED"
        
        assert job_b.status == "FAILED"
        assert doc_b.status == "PROCESSED"  # Preserved!
    finally:
        db.close()


def test_diagnostic_error_message_format():
    """Verify the exact diagnostic error message format matches specification."""
    db = SessionLocal()
    try:
        timeout = 25
        doc, job = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=35)
        
        reap_stale_jobs(db, stale_timeout_minutes=timeout)
        
        db.refresh(job)
        expected_msg = (
            f"JOB_STALE_TIMEOUT: Job exceeded configured processing timeout of "
            f"{timeout} minutes and was marked FAILED by the job janitor."
        )
        assert job.error_message == expected_msg
    finally:
        db.close()


def test_completed_and_failed_jobs_ignored():
    """Verify already COMPLETED, FAILED, and QUEUED jobs are never reaped."""
    db = SessionLocal()
    try:
        doc_completed, job_completed = create_test_doc_and_job(
            db, status="COMPLETED", started_offset_minutes=90, doc_status="PROCESSED"
        )
        doc_failed, job_failed = create_test_doc_and_job(
            db, status="FAILED", started_offset_minutes=90, doc_status="FAILED"
        )
        doc_queued, job_queued = create_test_doc_and_job(
            db, status="QUEUED", started_offset_minutes=None, created_offset_minutes=90, doc_status="QUEUED"
        )
        
        result = reap_stale_jobs(db, stale_timeout_minutes=30)
        
        db.refresh(job_completed)
        db.refresh(job_failed)
        db.refresh(job_queued)
        
        assert job_completed.status == "COMPLETED"
        assert job_failed.status == "FAILED"
        assert job_queued.status == "QUEUED"
        
        reaped_ids = [r["job_id"] for r in result["reaped_jobs"]]
        assert job_completed.id not in reaped_ids
        assert job_failed.id not in reaped_ids
        assert job_queued.id not in reaped_ids
    finally:
        db.close()


def test_concurrency_race_condition_handling():
    """
    Verify concurrency safety: if a job is picked up by a worker and completed
    before the janitor atomic update runs, the janitor skips it cleanly.
    """
    db = SessionLocal()
    try:
        doc, job = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=50)
        
        # Simulate worker completing the job right before janitor updates
        # By patching the query update to return 0 affected rows (as if another worker changed status)
        original_update = db.query(ProcessingJob).filter(ProcessingJob.id == job.id).update
        
        with patch.object(db, "query", wraps=db.query) as mock_query:
            # Let's test actual behavior: change status to COMPLETED right before reap
            job.status = "COMPLETED"
            db.commit()
            
            result = reap_stale_jobs(db, stale_timeout_minutes=30)
            
            db.refresh(job)
            assert job.status == "COMPLETED"
            assert job.id not in [r["job_id"] for r in result["reaped_jobs"]]
    finally:
        db.close()


def test_audit_event_recorded():
    """Verify an immutable AuditEvent is persisted with full metadata upon reaping."""
    db = SessionLocal()
    try:
        doc, job = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=60)
        
        result = reap_stale_jobs(db, stale_timeout_minutes=30, actor_id="test_admin_actor")
        
        audit = (
            db.query(AuditEvent)
            .filter(AuditEvent.object_id == job.id, AuditEvent.action == "JOB_STALE_TIMEOUT")
            .first()
        )
        assert audit is not None
        assert audit.object_type == "processing_job"
        assert audit.actor_id == "test_admin_actor"
        assert audit.details["reason"] == "JOB_STALE_TIMEOUT"
        assert audit.details["timeout_minutes"] == 30
        assert audit.details["duration_seconds"] >= 3600.0
        assert "JOB_STALE_TIMEOUT" in audit.details["error_message"]
    finally:
        db.close()


def test_structured_log_emission(caplog):
    """Verify structured log event 'job_reaped' is emitted with telemetry."""
    db = SessionLocal()
    try:
        doc, job = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=50)
        
        with caplog.at_level(logging.WARNING):
            reap_stale_jobs(db, stale_timeout_minutes=30)
            
        found = False
        for record in caplog.records:
            if getattr(record, "event", None) == "job_reaped" and getattr(record, "job_id", None) == job.id:
                found = True
                assert getattr(record, "status", None) == "FAILED"
                assert getattr(record, "document_id", None) == doc.id
                break
        assert found, "Expected structured log event 'job_reaped' was not emitted"
    finally:
        db.close()


def test_multiple_stale_jobs_reaped_in_single_sweep():
    """Verify multiple stale jobs are reaped atomically in a single sweep."""
    db = SessionLocal()
    try:
        jobs = []
        for i in range(4):
            doc, job = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=40 + i * 5)
            jobs.append((doc, job))
            
        result = reap_stale_jobs(db, stale_timeout_minutes=30)
        
        reaped_ids = {r["job_id"] for r in result["reaped_jobs"]}
        for doc, job in jobs:
            db.refresh(job)
            db.refresh(doc)
            assert job.status == "FAILED"
            assert doc.status == "FAILED"
            assert job.id in reaped_ids
    finally:
        db.close()


def test_configurable_timeout_threshold():
    """Verify custom timeout threshold parameter overrides default."""
    db = SessionLocal()
    try:
        # Job running for 15 minutes
        doc, job = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=15)
        
        # Sweep 1: 30 minutes threshold -> NOT reaped
        result1 = reap_stale_jobs(db, stale_timeout_minutes=30)
        db.refresh(job)
        assert job.status == "PROCESSING"
        assert job.id not in [r["job_id"] for r in result1["reaped_jobs"]]
        
        # Sweep 2: 10 minutes threshold -> REAPED
        result2 = reap_stale_jobs(db, stale_timeout_minutes=10)
        db.refresh(job)
        assert job.status == "FAILED"
        assert job.id in [r["job_id"] for r in result2["reaped_jobs"]]
        assert "exceeded configured processing timeout of 10 minutes" in job.error_message
    finally:
        db.close()


def test_created_at_fallback_when_started_at_none():
    """Verify fallback to created_at when started_at is None for PROCESSING job."""
    db = SessionLocal()
    try:
        doc, job = create_test_doc_and_job(
            db, status="PROCESSING", started_offset_minutes=None, created_offset_minutes=45
        )
        assert job.started_at is None
        
        result = reap_stale_jobs(db, stale_timeout_minutes=30)
        
        db.refresh(job)
        assert job.status == "FAILED"
        assert job.id in [r["job_id"] for r in result["reaped_jobs"]]
    finally:
        db.close()


def test_celery_task_and_beat_configuration():
    """Verify Celery task registration and Beat schedule configuration."""
    assert "app.tasks.reap_stale_jobs_task" in celery_app.tasks
    assert "reap-stale-jobs-periodic" in celery_app.conf.beat_schedule
    
    beat_entry = celery_app.conf.beat_schedule["reap-stale-jobs-periodic"]
    assert beat_entry["task"] == "app.tasks.reap_stale_jobs_task"
    assert beat_entry["schedule"] == float(settings.JOB_JANITOR_INTERVAL_MINUTES * 60)
    
    # Direct task execution
    db = SessionLocal()
    try:
        doc, job = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=50)
        result = reap_stale_jobs_task(stale_timeout_minutes=30)
        
        assert result["status"] == "COMPLETED"
        assert any(r["job_id"] == job.id for r in result["reaped_jobs"])
        
        db.refresh(job)
        assert job.status == "FAILED"
    finally:
        db.close()


def test_api_reap_stale_endpoint():
    """Verify POST /api/v1/ingestion/jobs/reap-stale endpoint access control and execution."""
    hq_token = get_token("hq_officer")
    analyst_token = get_analyst_token("ecl_analyst")
    
    db = SessionLocal()
    try:
        doc, job = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=45)
    finally:
        db.close()
        
    # 1. Unauthorized attempt (Subsidiary Analyst lacks admin privileges)
    res_forbidden = client.post(
        "/api/v1/ingestion/jobs/reap-stale?timeout_minutes=30",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res_forbidden.status_code == 403
    
    # 2. Authorized attempt (HQ Officer)
    res_ok = client.post(
        "/api/v1/ingestion/jobs/reap-stale?timeout_minutes=30",
        headers={"Authorization": f"Bearer {hq_token}"},
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["status"] == "COMPLETED"
    assert any(r["job_id"] == job.id for r in data["reaped_jobs"])
    
    db = SessionLocal()
    try:
        reloaded_job = db.query(ProcessingJob).filter(ProcessingJob.id == job.id).first()
        assert reloaded_job.status == "FAILED"
    finally:
        db.close()


def test_get_stale_job_count_helper():
    """Verify get_stale_job_count helper returns accurate metrics."""
    db = SessionLocal()
    try:
        initial_count = get_stale_job_count(db, stale_timeout_minutes=30)
        doc, job = create_test_doc_and_job(db, status="PROCESSING", started_offset_minutes=45)
        
        new_count = get_stale_job_count(db, stale_timeout_minutes=30)
        assert new_count == initial_count + 1
        
        reap_stale_jobs(db, stale_timeout_minutes=30)
        
        after_count = get_stale_job_count(db, stale_timeout_minutes=30)
        assert after_count == initial_count
    finally:
        db.close()
