from typing import List, Any, Optional, Dict
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

    # Phase 5: Identity Provider & LDAP/AD Abstraction Settings
    IDENTITY_PROVIDER: str = "local"  # "local" (default) or "ldap"
    LDAP_SERVER_URL: Optional[str] = None
    LDAP_BASE_DN: Optional[str] = None
    LDAP_BIND_DN: Optional[str] = None
    LDAP_BIND_PASSWORD: Optional[str] = None
    LDAP_USER_SEARCH_BASE: Optional[str] = None
    LDAP_USER_SEARCH_FILTER: str = "(&(objectClass=person)(sAMAccountName={username}))"
    LDAP_GROUP_SEARCH_BASE: Optional[str] = None
    LDAP_GROUP_SEARCH_FILTER: str = "(&(objectClass=group)(member={user_dn}))"
    LDAP_USE_TLS: bool = True
    LDAP_VERIFY_CERT: bool = True
    LDAP_CA_CERT_PATH: Optional[str] = None
    LDAP_TIMEOUT_SECONDS: float = 5.0
    LDAP_GROUP_ROLE_MAPPING: Any = {}
    LDAP_DEFAULT_ORGANIZATION_ID: Optional[str] = None

    # Phase 6: Enterprise System Integration Adapters (SAP, CoalNet, DMS)
    # Default is disabled and unconfigured, maintaining air-gapped / local-first deployment.
    # Never claim live connectivity unless actual tested enterprise connectors are configured.
    EXTERNAL_SYSTEM_MOCK_ENABLED: bool = False
    EXTERNAL_SYSTEM_DEFAULT_TIMEOUT: float = 5.0

    # SAP ERP Adapter Settings
    SAP_ENABLED: bool = False
    SAP_ENDPOINT: Optional[str] = None
    SAP_CLIENT_ID: Optional[str] = None
    SAP_CLIENT_SECRET: Optional[str] = None
    SAP_AUTH_MODE: str = "oauth2"  # "oauth2", "basic", "api_key"
    SAP_TIMEOUT_SECONDS: float = 5.0
    SAP_VERIFY_TLS: bool = True

    # CoalNet Dispatch & Logistics Adapter Settings
    COALNET_ENABLED: bool = False
    COALNET_ENDPOINT: Optional[str] = None
    COALNET_API_KEY: Optional[str] = None
    COALNET_TIMEOUT_SECONDS: float = 5.0
    COALNET_VERIFY_TLS: bool = True

    # Enterprise Document Management System (DMS) Adapter Settings
    DMS_ENABLED: bool = False
    DMS_ENDPOINT: Optional[str] = None
    DMS_AUTH_TOKEN: Optional[str] = None
    DMS_TIMEOUT_SECONDS: float = 5.0
    DMS_VERIFY_TLS: bool = True

    # Phase 9: Backup, Restore & Disaster Recovery Settings
    BACKUP_DIR: str = "data/backups"
    BACKUP_RETENTION_COUNT: int = 5
    REPORTS_DIR: str = "data/reports"
    BACKUP_INCLUDE_DOCUMENTS: bool = True
    BACKUP_INCLUDE_REPORTS: bool = True
    BACKUP_INCLUDE_DATABASE: bool = True

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

    @property
    def parsed_ldap_group_role_mapping(self) -> dict:
        if isinstance(self.LDAP_GROUP_ROLE_MAPPING, str):
            import json
            try:
                parsed = json.loads(self.LDAP_GROUP_ROLE_MAPPING)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        if isinstance(self.LDAP_GROUP_ROLE_MAPPING, dict):
            return self.LDAP_GROUP_ROLE_MAPPING
        return {}

    def validate_security(self):
        """
        Validates security settings against production environment requirements.
        Fails fast if production environment is detected with default/insecure secret,
        or if an invalid identity provider is specified.
        """
        provider = self.IDENTITY_PROVIDER.lower().strip()
        if provider not in ("local", "ldap"):
            raise ValueError(
                f"Invalid IDENTITY_PROVIDER '{self.IDENTITY_PROVIDER}'. Supported identity providers: 'local', 'ldap'."
            )
        if provider == "ldap":
            if not self.LDAP_SERVER_URL or not self.LDAP_BASE_DN:
                raise ValueError(
                    "Invalid LDAP configuration: LDAP_SERVER_URL and LDAP_BASE_DN are required when IDENTITY_PROVIDER=ldap."
                )

        # Phase 7: Visual classifier selection validation
        valid_classifiers = ("heuristic", "domain_cv")
        if self.VISUAL_CLASSIFIER.lower().strip() not in valid_classifiers:
            raise ValueError(
                f"Invalid VISUAL_CLASSIFIER '{self.VISUAL_CLASSIFIER}'. "
                f"Supported classifiers: {', '.join(valid_classifiers)}."
            )

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

            # Phase 6: Enterprise integration adapter security validation
            for sys_name, enabled, endpoint, verify_tls in [
                ("SAP", self.SAP_ENABLED, self.SAP_ENDPOINT, self.SAP_VERIFY_TLS),
                ("CoalNet", self.COALNET_ENABLED, self.COALNET_ENDPOINT, self.COALNET_VERIFY_TLS),
                ("DMS", self.DMS_ENABLED, self.DMS_ENDPOINT, self.DMS_VERIFY_TLS),
            ]:
                if enabled:
                    if not endpoint:
                        raise ValueError(f"CRITICAL SECURITY CONFIGURATION ERROR: {sys_name}_ENABLED is True but {sys_name}_ENDPOINT is not configured.")
                    if not endpoint.lower().startswith("https://"):
                        raise ValueError(f"CRITICAL SECURITY CONFIGURATION ERROR: {sys_name}_ENDPOINT must use HTTPS in production.")
                    if not verify_tls:
                        raise ValueError(f"CRITICAL SECURITY CONFIGURATION ERROR: {sys_name}_VERIFY_TLS cannot be disabled in production.")
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

    # Phase 9: Visual & Figure Intelligence & Phase 7 Visual Classifier Hardening
    # NOTE: Confidence thresholds are configurable operational thresholds,
    # NOT guarantees of semantic accuracy.
    VISUAL_CLASSIFIER: str = "heuristic"  # "heuristic", "domain_cv"
    VISUAL_HIGH_CONFIDENCE_THRESHOLD: float = 0.70
    VISUAL_LOW_CONFIDENCE_THRESHOLD: float = 0.40
    VISUAL_DOMAIN_MODEL_PATH: Optional[str] = None
    VISUAL_MAX_IMAGE_PIXELS: int = 50_000_000
    VISUAL_OCR_CONFIDENCE_MIN: float = 0.70
    VISUAL_DETECTION_DPI: int = 150
    VISUAL_MIN_IMAGE_SIZE: int = 50   # pixels; skip decorative images smaller than this
    VISUAL_CLASSIFICATION_CONFIDENCE_MIN: float = 0.5

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

