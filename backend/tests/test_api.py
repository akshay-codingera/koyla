import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.audit import AuditEvent
import pytest

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert data["database_type"] == "PostgreSQL"
    assert data["pgvector_enabled"] is True
    assert data["services"]["database"] == "UP"
    assert data["services"]["vector_store"] == "UP"

def test_auth_login():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "hq_officer", "password": "Admin123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "hq_officer"
    assert data["user"]["role"] == "CMPDI_HQ_OFFICER"

def test_audit_event_persisted():
    db = SessionLocal()
    try:
        # Check that login created an audit event in PostgreSQL
        events = db.query(AuditEvent).filter(AuditEvent.action == "AUTH_LOGIN").all()
        assert len(events) >= 1
        latest = events[-1]
        assert latest.actor_name == "hq_officer"
        assert latest.role_code == "CMPDI_HQ_OFFICER"
    finally:
        db.close()

def test_auth_invalid_login():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "hq_officer", "password": "WrongPassword"},
    )
    assert response.status_code == 400

def test_dashboard_metrics_unauthorized():
    response = client.get("/api/v1/dashboard/metrics")
    assert response.status_code == 401

def test_dashboard_metrics_hq_scoping():
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "hq_officer", "password": "Admin123!"},
    )
    token = login_res.json()["access_token"]
    
    response = client.get(
        "/api/v1/dashboard/metrics",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data_source"] == "PostgreSQL 16 (koyla)"
    assert data["organization_scope"]["is_unrestricted"] is True
    assert data["documents_ingested"] >= 3
    assert data["documents_processed"] >= 2
    assert data["documents_awaiting_verification"] >= 1
    assert data["verification_backlog"] >= 1
    assert data["is_demo_data"] is True

def test_dashboard_metrics_ri1_scoping():
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "ri1_analyst", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    
    response = client.get(
        "/api/v1/dashboard/metrics",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["organization_scope"]["code"] == "RI_1"
    assert data["organization_scope"]["is_unrestricted"] is False
    # RI-1 only has 1 document seeded
    assert data["documents_ingested"] == 1
    assert data["documents_processed"] == 1
    assert data["documents_awaiting_verification"] == 0
