import logging
from fastapi import FastAPI, Depends, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import engine, Base, get_db
from app.core.logging.setup import setup_logging
from app.core.logging.context import get_request_id
from app.core.middleware import SecurityHeadersMiddleware, RequestTracingMiddleware
from app.services.health import get_system_health, check_readiness, check_liveness

import app.models.organization
import app.models.user
import app.models.document
import app.models.audit
import app.models.system
import app.models.report
import app.models.topic
import app.models.visual
import app.models.evidence
import app.models.geology

# Initialize database schema
Base.metadata.create_all(bind=engine)

# Setup structured logging
setup_logging()
logger = logging.getLogger("app.main")

from app.api.v1 import (
    auth,
    system,
    dashboard,
    documents,
    ingestion,
    organizations,
    extraction,
    validation,
    reconciliation,
    verification,
    audit,
    search,
    qa,
    reports,
    topics,
    visuals,
    evidence,
    backup,
    geology,
)

app = FastAPI(title=settings.PROJECT_NAME)

# 1. Defensive HTTP Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# 2. Configurable CORS with explicit trusted origins and credentials support
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-Request-ID",
    ],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)

# 3. Request Correlation & Tracing Middleware (Times requests, sanitizes & propagates X-Request-ID)
app.add_middleware(RequestTracingMiddleware)


@app.on_event("startup")
def on_startup():
    settings.validate_security()


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    """
    Standardized structured error observability.
    Captures exception details in structured logs while withholding raw tracebacks from API clients.
    """
    if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
        # Let FastAPI and Starlette default exception handlers format expected client errors
        raise exc

    req_id = getattr(request.state, "request_id", None) or get_request_id() or "unknown"
    logger.error(
        f"Unhandled exception during {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
        extra={
            "event": "unhandled_exception",
            "request_id": req_id,
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An internal error occurred. Quote the request ID for tracking.",
            "request_id": req_id,
        },
        headers={"X-Request-ID": req_id},
    )


# Root Liveness & Readiness endpoints for container/orchestrator health probes
@app.get("/health")
def root_health(db: Session = Depends(get_db)):
    """Root health probe delegating to canonical system health service."""
    return get_system_health(db)


@app.get("/ready")
def root_ready(response: Response, db: Session = Depends(get_db)):
    """Root container readiness probe. Returns HTTP 503 if core database is unreachable."""
    is_ready, details = check_readiness(db)
    if not is_ready:
        response.status_code = 503
    return details


@app.get("/live")
def root_live():
    """Root container liveness probe confirming process responsiveness."""
    return check_liveness()


# API v1 Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(system.router, prefix=f"{settings.API_V1_STR}/system", tags=["system"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}/documents", tags=["documents"])
app.include_router(ingestion.router, prefix=f"{settings.API_V1_STR}/ingestion", tags=["ingestion"])
app.include_router(organizations.router, prefix=f"{settings.API_V1_STR}/organizations", tags=["organizations"])
app.include_router(extraction.router, prefix=f"{settings.API_V1_STR}/extraction", tags=["extraction"])
app.include_router(validation.router, prefix=f"{settings.API_V1_STR}/validation", tags=["validation"])
app.include_router(reconciliation.router, prefix=f"{settings.API_V1_STR}/reconciliation", tags=["reconciliation"])
app.include_router(verification.router, prefix=f"{settings.API_V1_STR}/verification", tags=["verification"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["audit"])
app.include_router(search.router, prefix=f"{settings.API_V1_STR}/search", tags=["search"])
app.include_router(qa.router, prefix=f"{settings.API_V1_STR}/qa", tags=["qa"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["reports"])
app.include_router(topics.router, prefix=f"{settings.API_V1_STR}/topics", tags=["topics"])
app.include_router(visuals.router, prefix=f"{settings.API_V1_STR}/visuals", tags=["visuals"])
app.include_router(evidence.router, prefix=f"{settings.API_V1_STR}/evidence", tags=["evidence"])
app.include_router(geology.router, prefix=f"{settings.API_V1_STR}/geology", tags=["geology"])
app.include_router(backup.router, prefix=f"{settings.API_V1_STR}/admin/backup", tags=["backup"])
app.include_router(backup.router, prefix=f"{settings.API_V1_STR}/backup", tags=["backup"])


@app.get("/")
def root():
    return {"message": "Welcome to KOYLA API"}
