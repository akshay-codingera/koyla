from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "CIL/CMPDI Reporting Intelligence"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "supersecretkey_for_local_prototype_only"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/koyla"
    STORAGE_DIR: str = "storage/documents"
    # Configurable cross-document reconciliation policy threshold (relative variance, e.g. 0.01 = 1%).
    # NOTE: This is a configurable prototype system policy rule, NOT an asserted or official CIL/CMPDI institutional standard.
    RECONCILIATION_VARIANCE_THRESHOLD: float = 0.01

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

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

