from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import engine, Base

import app.models.organization
import app.models.user
import app.models.document
import app.models.audit
import app.models.system
import app.models.report
import app.models.topic
import app.models.visual
import app.models.evidence

Base.metadata.create_all(bind=engine)

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
)

from app.core.middleware import SecurityHeadersMiddleware

app = FastAPI(title=settings.PROJECT_NAME)

# 1. Defensive HTTP Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# 2. Configurable CORS with explicit trusted origins and credentials support
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

@app.on_event("startup")
def on_startup():
    settings.validate_security()

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

@app.get("/")
def root():
    return {"message": "Welcome to KOYLA API"}
