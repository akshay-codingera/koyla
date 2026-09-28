from typing import List, Any
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    PROJECT_NAME: str = "CIL/CMPDI Reporting Intelligence"
    API_V1_STR: str = "/api/v1"
    
    # Phase 4: Security Hardening & Secret Management
    ENVIRONMENT: str = "development"  # "development", "testing", or "production"
    SECRET_KEY: str = "supersecretkey_for_local_prototype_only"
    INSECURE_SECRETS: List[str] = [
        "supersecretkey_for_local_prototype_only",
        "secret",
        "changeme",
        "default",
        "password",
        "testsecret",
        "12345678",
    ]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/koyla"
    
    # Phase 4: CORS Configuration (No wildcard in production with credentials)
    CORS_ORIGINS: Any = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Phase 4: Resource & Rate Limiting Settings
    MAX_UPLOAD_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB
    STORAGE_DIR: str = "storage/documents"
    STORAGE_QUARANTINE_DIR: str = "storage/quarantine"
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH_PER_MINUTE: int = 120
    RATE_LIMIT_QA_PER_MINUTE: int = 120
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = 120

    # Phase 4: Antivirus / ClamAV Scanner Settings
    CLAMAV_ENABLED: bool = False  # Disabled by default in air-gapped / local prototype
    CLAMAV_REQUIRED: bool = False  # If True in prod, blocks upload if ClamAV daemon is unreachable
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310
    CLAMAV_TIMEOUT_SECONDS: float = 5.0

    @property
    def parsed_cors_origins(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            import json
            try:
                parsed = json.loads(self.CORS_ORIGINS)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return list(self.CORS_ORIGINS)

    def validate_security(self):
        """
        Validates security settings against production environment requirements.
        Fails fast if production environment is detected with default/insecure secret.
        """
        env = self.ENVIRONMENT.lower().strip()
        if env in ("production", "prod"):
            if not self.SECRET_KEY or self.SECRET_KEY in self.INSECURE_SECRETS or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: In production mode (ENVIRONMENT=production), "
                    "a cryptographically secure SECRET_KEY of at least 32 characters must be provided via environment variables. "
                    "Insecure default/fallback secrets are strictly prohibited."
                )
            if any(origin.strip() == "*" for origin in self.parsed_cors_origins):
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: Wildcard CORS origin ('*') is prohibited in production "
                    "when credentials are enabled. Configure explicit trusted origins."
                )
        elif self.SECRET_KEY in self.INSECURE_SECRETS:
            logger.warning("Running with default/insecure SECRET_KEY in non-production mode.")

    # Configurable cross-document reconciliation policy threshold (relative variance, e.g. 0.01 = 1%).
    # NOTE: This is a configurable prototype system policy rule, NOT an asserted or official CIL/CMPDI institutional standard.
    RECONCILIATION_VARIANCE_THRESHOLD: float = 0.01

    # Phase 1: Persistent Job Processing (Celery & Redis)
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # Phase 5: Embedding & Vector Search Settings
    EMBEDDING_PROVIDER: str = "sentence_transformers"  # "sentence_transformers" (primary neural) or "deterministic" (fallback)
    NEURAL_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    NEURAL_MODEL_PATH: str = "backend/model_cache/BAAI/bge-small-en-v1.5"
    DETERMINISTIC_MODEL_NAME: str = "koyla-deterministic-hash-384"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_VERSION: str = "1.1.0"
    EMBEDDING_BATCH_SIZE: int = 32

    # Offline / Air-Gapped Controls
    TRANSFORMERS_OFFLINE: bool = False
    HF_HUB_OFFLINE: bool = False
    OFFLINE_MODE: bool = False

    # Phase 5: Hybrid Retrieval & RRF Settings
    RRF_K: int = 60
    RRF_KEYWORD_WEIGHT: float = 1.0
    RRF_DENSE_WEIGHT: float = 1.0
    ENABLE_RERANKER: bool = True
    RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    DEFAULT_SEARCH_TOP_K: int = 10

    # Phase 6: Grounded Q&A and Local LLM Settings
    LLM_PROVIDER: str = "ollama"  # "ollama", "openai_compatible", or "local_transformers"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "SmolLM2-135M-Instruct"
    OPENAI_COMPATIBLE_BASE_URL: str = "http://localhost:11434/v1"
    OPENAI_COMPATIBLE_MODEL: str = "SmolLM2-135M-Instruct"
    LOCAL_MODEL_NAME: str = "SmolLM2-135M-Instruct"
    LOCAL_MODEL_PATH: str = "backend/model_cache/SmolLM2-135M-Instruct"
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_TEMPERATURE: float = 0.1
    QA_REFUSAL_THRESHOLD: float = 0.015
    ENABLE_ARITHMETIC_ENGINE: bool = True
    ENABLE_GROUNDING_VERIFICATION: bool = True
    MAX_EVIDENCE_CHUNKS: int = 5

    # Phase 9: Visual & Figure Intelligence
    # NOTE: Confidence thresholds are configurable operational thresholds,
    # NOT guarantees of semantic accuracy.
    VISUAL_OCR_CONFIDENCE_MIN: float = 0.70
    VISUAL_DETECTION_DPI: int = 150
    VISUAL_MIN_IMAGE_SIZE: int = 50   # pixels; skip decorative images smaller than this
    VISUAL_CLASSIFICATION_CONFIDENCE_MIN: float = 0.5

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

