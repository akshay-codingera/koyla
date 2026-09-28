from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.health import (
    get_system_health,
    check_readiness,
    check_liveness,
)

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Genuine technical health check for all core KOYLA platform subsystems.
    Reports operational status, pgvector capability, latency metrics, and safe diagnostics.
    """
    return get_system_health(db)


@router.get("/ready")
def readiness_check(response: Response, db: Session = Depends(get_db)):
    """
    Kubernetes/container readiness probe.
    Returns HTTP 200 when core database and storage dependencies are operational.
    Returns HTTP 503 when core dependencies are unavailable.
    """
    is_ready, details = check_readiness(db)
    if not is_ready:
        response.status_code = 503
    return details


@router.get("/live")
def liveness_check():
    """
    Kubernetes/container liveness probe.
    Fast confirmation that the API process is alive and responsive.
    """
    return check_liveness()


@router.get("/adapters")
def list_enterprise_adapters():
    """
    Lists configured enterprise integration adapters, their operational postures,
    and capability flags. Sanitizes all endpoints and hides credentials.
    """
    from app.services.adapters import get_system_manager
    adapters_mgr = get_system_manager()
    return {
        "adapters": adapters_mgr.list_adapters(),
        "health": adapters_mgr.get_all_health(),
    }
