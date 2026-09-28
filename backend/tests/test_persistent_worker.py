import os
import sys
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.db.database import SessionLocal
from app.models.document import Document, ProcessingJob, DocumentPage
from app.models.organization import Organization
from app.models.user import User
from app.core.celery_app import celery_app, check_celery_health
from app.tasks.ingestion_tasks import process_document_task

client = TestClient(app)


def get_token(username="hq_officer", password="Admin123!"):
    res = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_celery_app_configuration():
    """Verify Celery application configures serializers, UTC, and task registry."""
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert "json" in celery_app.conf.accept_content
    assert celery_app.conf.timezone == "UTC"
    assert "app.tasks.process_document_task" in celery_app.tasks


def test_system_health_worker_and_redis():
    """Verify system health endpoint includes redis and worker telemetry."""
    res = client.get("/api/v1/system/health")
    assert res.status_code == 200
    data = res.json()
    assert "services" in data
    assert "redis" in data["services"]
    assert "workers" in data["services"]
    assert "worker_details" in data


def test_job_status_includes_retry_count():
    """Verify ingestion job status API returns retry_count."""
    token = get_token()
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        doc = Document(
            organization_id=org.id,
            title="Test Retry Doc",
            document_type="TEST",
            original_filename="test_retry.txt",
            file_path="storage/test_retry.txt",
            mime_type="text/plain",
            file_size_bytes=100,
            sha256_hash="dummyhash_retry_" + str(uuid.uuid4())[:8],
            status="QUEUED"
        )
        db.add(doc)
        db.commit()

        job = ProcessingJob(
            document_id=doc.id,
            job_type="INGESTION",
            status="QUEUED",
            progress_pct=0,
            retry_count=2,
            error_message="Initial transient attempt",
            started_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()

        res = client.get(f"/api/v1/ingestion/jobs/{job.id}", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        job_data = res.json()
        assert job_data["status"] == "QUEUED"
        assert job_data["retry_count"] == 2
        assert "Initial transient attempt" in job_data["error_message"]
    finally:
        db.close()


def test_integration_worker_task_eager_flow(tmp_path):
    """Integration test: upload -> queue -> worker execution -> COMPLETED with evidence."""
    # Create a real test document on disk
    test_file = tmp_path / "mining_production_record.txt"
    test_file.write_text(
        "CENTRAL COALFIELDS LIMITED\n"
        "Gevra OC Production Report\n"
        "Coal Production for FY 2023-24: 52.5 MT\n"
        "Target: 50.0 MT\n"
        "Stripping Ratio: 1.45 cum/tonne\n"
    )

    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        user = db.query(User).first()

        doc = Document(
            organization_id=org.id,
            title="Worker Integration Test Doc",
            document_type="PRODUCTION_REPORT",
            original_filename="mining_production_record.txt",
            file_path=str(test_file),
            mime_type="text/plain",
            file_size_bytes=os.path.getsize(str(test_file)),
            sha256_hash="eager_test_hash_" + str(uuid.uuid4())[:8],
            status="QUEUED",
            created_by=user.id
        )
        db.add(doc)
        db.commit()

        job = ProcessingJob(
            document_id=doc.id,
            job_type="DOCUMENT_INGESTION",
            status="QUEUED",
            progress_pct=0,
            retry_count=0
        )
        db.add(job)
        db.commit()

        # Execute task via Celery task function
        result = process_document_task(doc.id, job.id)
        assert result["status"] == "COMPLETED"

        # Verify DB state updated
        db.refresh(job)
        db.refresh(doc)
        assert job.status == "COMPLETED"
        assert job.completed_at is not None
        assert job.started_at is not None
        assert job.retry_count == 0
        assert doc.status == "COMPLETED"

        # Verify pages were created
        pages = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).all()
        assert len(pages) >= 1
    finally:
        db.close()


def test_worker_task_retry_and_final_failure():
    """Failure test: worker task failure triggers retry state and records error."""
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        doc = Document(
            organization_id=org.id,
            title="Failing Test Doc",
            document_type="TEST",
            original_filename="failing.txt",
            file_path="nonexistent_failing_path.txt",
            mime_type="text/plain",
            file_size_bytes=100,
            sha256_hash="fail_hash_" + str(uuid.uuid4())[:8],
            status="QUEUED"
        )
        db.add(doc)
        db.commit()

        job = ProcessingJob(
            document_id=doc.id,
            job_type="DOCUMENT_INGESTION",
            status="QUEUED",
            progress_pct=0,
            retry_count=0
        )
        db.add(job)
        db.commit()

        # Simulate task execution with failure on final retry
        with patch.object(process_document_task, "retry", side_effect=RuntimeError("Retry simulated")):
            with patch("app.tasks.ingestion_tasks.process_document", side_effect=RuntimeError("Corrupt stream error")):
                # Should attempt retry
                with pytest.raises(RuntimeError):
                    process_document_task(doc.id, job.id)

                db.refresh(job)
                assert job.status == "RETRYING"
                assert job.retry_count == 1
                assert "Corrupt stream error" in (job.error_message or "")

        # Now simulate max retries reached
        process_document_task.push_request(retries=3)
        try:
            with patch("app.tasks.ingestion_tasks.process_document", side_effect=RuntimeError("Fatal permanent parser crash")):
                res = process_document_task(doc.id, job.id)
                assert res["status"] == "FAILED"

                db.refresh(job)
                db.refresh(doc)
                assert job.status == "FAILED"
                assert "Fatal permanent parser crash" in job.error_message
                assert doc.status == "FAILED"
        finally:
            process_document_task.pop_request()
    finally:
        db.close()


def test_worker_task_deduplication():
    """Verify deduplication lock prevents simultaneous duplicate runs."""
    mock_redis = MagicMock()
    mock_redis.set.return_value = False  # Lock already held!

    with patch("app.tasks.ingestion_tasks.get_redis_client", return_value=mock_redis):
        res = process_document_task("dummy_doc_id", "dummy_job_id")
        assert res["status"] == "SKIPPED_DUPLICATE"
