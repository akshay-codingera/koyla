from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.health.dependencies import (
    STATUS_HEALTHY,
    STATUS_DEGRADED,
    STATUS_UNAVAILABLE,
    STATUS_DISABLED,
    STATUS_NOT_CONFIGURED,
    check_postgresql,
    check_redis,
    check_celery,
    check_storage,
    check_ocr,
    check_llm,
    check_clamav,
    check_identity_provider,
    check_enterprise_adapters,
)


def get_system_health(db: Session) -> Dict[str, Any]:
    """
    Executes comprehensive operational health probes across all Koyla subsystems.
    Maintains 100% backward compatibility with existing tests and frontend, while
    providing structured dependency diagnostics, latency metrics, and safe status indicators.
    """
    # 1. Core infrastructure
    pg_diag = check_postgresql(db)
    redis_diag = check_redis()
    celery_diag = check_celery()
    storage_diag = check_storage()
    ocr_diag = check_ocr()
    llm_diag = check_llm()
    av_diag = check_clamav()
    id_diag = check_identity_provider()
    adapters_diag = check_enterprise_adapters()

    # 2. Embedding provider
    try:
        from app.services.embedding.sentence_transformer import LocalSentenceTransformerProvider
        emb_provider = LocalSentenceTransformerProvider()
        emb_health = emb_provider.health()
        emb_status = "UP" if emb_health.get("available") else "DEGRADED"
    except Exception:
        emb_status = "DOWN"

    # 3. Topic & Temporal Analytics
    try:
        from app.services.topics.c_tfidf import c_tfidf_transformer
        dummy_clusters = {0: [{"tokens": ["coal", "mining"], "clean_text": "coal mining"}]}
        res = c_tfidf_transformer.fit_transform(dummy_clusters, top_k_terms=1)
        topic_engine_status = "UP" if 0 in res else "DEGRADED"
    except Exception:
        topic_engine_status = "DOWN"

    try:
        from app.services.topics.temporal_service import temporal_service
        has_methods = callable(getattr(temporal_service, "compute_analysis_trends", None)) and \
                      callable(getattr(temporal_service, "compare_dimension", None))
        temporal_status = "UP" if has_methods else "DEGRADED"
    except Exception:
        temporal_status = "DOWN"

    # 4. Report Engine
    try:
        from app.services.reports.compliance import ReportComplianceValidator
        from app.services.reports.docx_renderer import ReportDocxRenderer
        has_validator = callable(getattr(ReportComplianceValidator, "validate_report", None))
        has_renderer = callable(getattr(ReportDocxRenderer, "render_report_docx", None))
        report_engine_status = "UP" if (has_validator and has_renderer) else "DEGRADED"
    except Exception:
        report_engine_status = "DOWN"

    # Map dependency diagnostics to backward-compatible service strings
    db_status = "UP" if pg_diag["status"] == STATUS_HEALTHY else ("DEGRADED" if pg_diag["status"] == STATUS_DEGRADED else "DOWN")
    vec_status = "UP" if pg_diag.get("pgvector", {}).get("enabled") else ("DEGRADED" if pg_diag["status"] != STATUS_UNAVAILABLE else "DOWN")
    ocr_status = "UP" if ocr_diag["status"] == STATUS_HEALTHY else ("DEGRADED" if ocr_diag["status"] == STATUS_DEGRADED else "DOWN")
    redis_status = "UP" if redis_diag["status"] == STATUS_HEALTHY else ("DEGRADED" if redis_diag["status"] == STATUS_DEGRADED else "OFFLINE")
    worker_status = "UP" if celery_diag["status"] == STATUS_HEALTHY else ("DEGRADED" if celery_diag["status"] == STATUS_DEGRADED else "OFFLINE")
    llm_status = "UP" if llm_diag["status"] == STATUS_HEALTHY else ("DEGRADED" if llm_diag["status"] == STATUS_DEGRADED else ("NOT_CONFIGURED" if llm_diag["status"] == STATUS_NOT_CONFIGURED else "OFFLINE"))
    av_status = av_diag.get("status", "DISABLED")
    id_status = "UP" if id_diag["status"] == STATUS_HEALTHY else "ERROR"
    storage_status = "UP" if storage_diag["status"] == STATUS_HEALTHY else "DOWN"

    # Overall calculation
    is_ready, _ = check_readiness(db)
    if pg_diag["status"] == STATUS_UNAVAILABLE:
        overall = "DOWN"
    elif not is_ready or any(s == "DEGRADED" for s in [db_status, vec_status, redis_status]):
        overall = "DEGRADED"
    else:
        overall = "UP"

    return {
        "status": overall,
        "database_type": "PostgreSQL",
        "pgvector_enabled": pg_diag.get("pgvector", {}).get("enabled", False),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "application": {
            "name": settings.PROJECT_NAME,
            "version": "1.2.0",
            "environment": settings.ENVIRONMENT,
        },
        "services": {
            "backend": "UP",
            "api": "UP",
            "database": db_status,
            "vector_store": vec_status,
            "storage": storage_status,
            "ocr_engine": ocr_status,
            "embedding_service": emb_status,
            "llm_service": llm_status,
            "topic_engine": topic_engine_status,
            "temporal_analytics": temporal_status,
            "report_engine": report_engine_status,
            "redis": redis_status,
            "workers": worker_status,
            "antivirus": av_status,
            "identity_provider": id_status,
        },
        "identity_provider_type": id_diag.get("provider_type", "local"),
        "enterprise_adapters": adapters_diag,
        "worker_details": celery_diag,
        "dependencies": {
            "postgresql": pg_diag,
            "redis": redis_diag,
            "celery": celery_diag,
            "storage": storage_diag,
            "ocr": ocr_diag,
            "llm": llm_diag,
            "antivirus": av_diag,
            "identity_provider": id_diag,
        },
    }


def check_readiness(db: Session) -> Tuple[bool, Dict[str, Any]]:
    """
    Evaluates whether the Koyla platform can accept and process workloads.
    Only strictly required core infrastructure is evaluated:
    - PostgreSQL is reachable
    - Storage is accessible and writable
    Optional dependencies (SAP, CoalNet, DMS, ClamAV, LLM) do NOT prevent readiness when disabled/unavailable.
    """
    pg_res = check_postgresql(db)
    storage_res = check_storage()

    core_checks = {
        "postgresql": pg_res["status"] in (STATUS_HEALTHY, STATUS_DEGRADED),
        "storage": storage_res["status"] == STATUS_HEALTHY,
    }

    is_ready = all(core_checks.values())
    return is_ready, {
        "status": "READY" if is_ready else "NOT_READY",
        "is_ready": is_ready,
        "checks": core_checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def check_liveness() -> Dict[str, Any]:
    """
    Fast liveness probe confirming process responsiveness.
    """
    return {
        "status": "ALIVE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
