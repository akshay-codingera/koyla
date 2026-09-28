import io
import os
import time
import json
import logging
import urllib.request
from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# Canonical Health Status Constants per Phase 8 specification
STATUS_HEALTHY = "HEALTHY"
STATUS_DEGRADED = "DEGRADED"
STATUS_UNAVAILABLE = "UNAVAILABLE"
STATUS_DISABLED = "DISABLED"
STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"


def sanitize_url_for_telemetry(url: Optional[str]) -> Optional[str]:
    """Sanitizes connection URLs to strip passwords and user credentials."""
    if not url:
        return None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host_port = parsed.hostname or "unknown"
        if parsed.port:
            host_port = f"{host_port}:{parsed.port}"
        return f"{parsed.scheme}://{host_port}{parsed.path}"
    except Exception:
        return "[REDACTED_URL]"


def check_postgresql(db: Session) -> Dict[str, Any]:
    """
    Genuine PostgreSQL relational connectivity probe.
    Measures query latency and verifies pgvector dense vector extension.
    """
    start = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        
        # Check pgvector extension and vector distance capability
        vec_ok = False
        vec_version = None
        try:
            vec_res = db.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")).fetchone()
            if vec_res is not None:
                vec_version = vec_res[1]
                v_test = db.execute(text("SELECT '[1.0, 2.0, 3.0]'::vector <-> '[1.0, 2.0, 3.0]'::vector")).scalar()
                if v_test is not None and abs(float(v_test)) < 1e-5:
                    vec_ok = True
        except Exception as ve:
            logger.debug(f"pgvector check failed: {ve}")

        status = STATUS_HEALTHY if vec_ok else STATUS_DEGRADED
        return {
            "status": status,
            "database_type": "PostgreSQL",
            "latency_ms": latency_ms,
            "pgvector": {
                "enabled": vec_ok,
                "version": vec_version,
                "status": STATUS_HEALTHY if vec_ok else STATUS_DEGRADED,
            },
        }
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": STATUS_UNAVAILABLE,
            "database_type": "PostgreSQL",
            "latency_ms": latency_ms,
            "error": str(e),
            "pgvector": {
                "enabled": False,
                "version": None,
                "status": STATUS_UNAVAILABLE,
            },
        }


def check_redis() -> Dict[str, Any]:
    """
    Genuine Redis broker & cache connectivity probe.
    Measures ping latency without leaking credentials.
    """
    start = time.perf_counter()
    try:
        import redis
        r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=0.5)
        if r.ping():
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "status": STATUS_HEALTHY,
                "latency_ms": latency_ms,
                "endpoint": sanitize_url_for_telemetry(settings.REDIS_URL),
            }
        else:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "status": STATUS_DEGRADED,
                "latency_ms": latency_ms,
                "endpoint": sanitize_url_for_telemetry(settings.REDIS_URL),
            }
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": STATUS_UNAVAILABLE,
            "latency_ms": latency_ms,
            "error": str(e),
            "endpoint": sanitize_url_for_telemetry(settings.REDIS_URL),
        }


def check_celery() -> Dict[str, Any]:
    """
    Genuine Celery worker inspection probe.
    Reports broker state and registered active worker count.
    """
    try:
        from app.core.celery_app import check_celery_health
        w_health = check_celery_health()
        active = w_health.get("active_workers", 0)
        broker_ok = w_health.get("broker_connected", False)

        if active > 0:
            status = STATUS_HEALTHY
        elif broker_ok:
            status = STATUS_DEGRADED  # Broker up, but no background worker pinged
        else:
            status = STATUS_UNAVAILABLE

        return {
            "status": status,
            "active_workers": active,
            "broker_connected": broker_ok,
            "registered_tasks": w_health.get("registered_tasks", []),
            "error": w_health.get("error"),
        }
    except Exception as e:
        return {
            "status": STATUS_UNAVAILABLE,
            "active_workers": 0,
            "broker_connected": False,
            "error": str(e),
        }


def check_storage() -> Dict[str, Any]:
    """
    Storage directory accessibility and write probe.
    Ensures safe temporary probe cleanup.
    """
    storage_dir = settings.STORAGE_DIR
    try:
        os.makedirs(storage_dir, exist_ok=True)
        probe_path = os.path.join(storage_dir, ".health_probe_tmp")
        
        # Write test
        with open(probe_path, "w") as f:
            f.write("koyla_health_probe")
        
        # Read test
        with open(probe_path, "r") as f:
            content = f.read()
        
        # Cleanup
        if os.path.exists(probe_path):
            os.remove(probe_path)

        writable = content == "koyla_health_probe"
        return {
            "status": STATUS_HEALTHY if writable else STATUS_UNAVAILABLE,
            "storage_dir": storage_dir,
            "writable": writable,
            "accessible": True,
        }
    except Exception as e:
        return {
            "status": STATUS_UNAVAILABLE,
            "storage_dir": storage_dir,
            "writable": False,
            "accessible": False,
            "error": str(e),
        }


def check_ocr() -> Dict[str, Any]:
    """
    OCR and document vision engine probe.
    Checks Tesseract OCR binary and PyMuPDF bindings.
    """
    try:
        from app.services.parsers.ocr_parser import ocr_parser
        tess_ok = ocr_parser.check_tesseract_available()
        import pymupdf
        pymupdf_ok = True
    except Exception:
        tess_ok = False
        pymupdf_ok = False

    status = STATUS_HEALTHY if tess_ok else (STATUS_DEGRADED if pymupdf_ok else STATUS_UNAVAILABLE)
    return {
        "status": status,
        "tesseract_available": bool(tess_ok),
        "pymupdf_available": bool(pymupdf_ok),
    }


def check_llm() -> Dict[str, Any]:
    """
    Local LLM operational probe.
    Probes configured Ollama endpoint without sending prompt payloads.
    """
    base_url = (getattr(settings, "OLLAMA_BASE_URL", None) or "http://localhost:11434").rstrip("/")
    llm_endpoint = f"{base_url}/api/tags"
    model_name = getattr(settings, "OLLAMA_MODEL", "SmolLM2-135M-Instruct")

    try:
        req = urllib.request.Request(llm_endpoint, headers={"User-Agent": "KOYLA-Health/1.0"})
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                models = [m.get("name", "") for m in data.get("models", [])]
                found = any(model_name.lower() in m.lower() for m in models) or len(models) > 0
                return {
                    "status": STATUS_HEALTHY if found else STATUS_DEGRADED,
                    "provider": "ollama",
                    "configured_model": model_name,
                    "endpoint": sanitize_url_for_telemetry(base_url),
                    "models_available": models,
                }
            else:
                return {
                    "status": STATUS_DEGRADED,
                    "provider": "ollama",
                    "configured_model": model_name,
                    "endpoint": sanitize_url_for_telemetry(base_url),
                }
    except urllib.error.URLError:
        return {
            "status": STATUS_UNAVAILABLE,
            "provider": "ollama",
            "configured_model": model_name,
            "endpoint": sanitize_url_for_telemetry(base_url),
            "message": "Local LLM daemon (Ollama) is not running or unreachable on configured port.",
        }
    except Exception as e:
        return {
            "status": STATUS_NOT_CONFIGURED,
            "provider": "ollama",
            "configured_model": model_name,
            "error": str(e),
        }


def check_clamav() -> Dict[str, Any]:
    """
    ClamAV antivirus operational probe.
    Properly reports DISABLED when disabled by configuration.
    """
    try:
        from app.services.security.antivirus import clamav_scanner
        av_health = clamav_scanner.health()
        return av_health
    except Exception:
        return {
            "status": STATUS_DISABLED,
            "enabled": False,
            "required": False,
        }


def check_identity_provider() -> Dict[str, Any]:
    """
    Identity provider operational probe.
    Reports local JWT or LDAP provider state.
    """
    try:
        from app.services.identity import get_identity_provider
        id_prov = get_identity_provider()
        health = id_prov.health()
        raw_status = health.get("status", "UP")
        status_map = {"UP": STATUS_HEALTHY, "DEGRADED": STATUS_DEGRADED, "ERROR": STATUS_UNAVAILABLE}
        return {
            "status": status_map.get(raw_status, STATUS_HEALTHY),
            "provider_type": id_prov.name,
            "details": health,
        }
    except Exception as e:
        return {
            "status": STATUS_UNAVAILABLE,
            "provider_type": "unknown",
            "error": str(e),
        }


def check_enterprise_adapters() -> Dict[str, Any]:
    """
    Enterprise system adapter postures probe.
    Sanitizes credentials and returns safe telemetry.
    """
    try:
        from app.services.adapters import get_system_manager
        adapters_mgr = get_system_manager()
        return adapters_mgr.get_all_health()
    except Exception as e:
        return {"error": str(e)}
