import os
import logging
from typing import List, Dict, Any, Optional
from app.services.embedding.base import EmbeddingProvider

logger = logging.getLogger(__name__)

class LocalSentenceTransformerProvider(EmbeddingProvider):
    """
    Local Sentence-Transformers neural embedding provider for BAAI/bge-small-en-v1.5.
    Loads local pre-trained weights from local model cache on CPU.
    If the package is not installed or model weights are not found,
    reports EMBEDDING_MODEL_UNAVAILABLE without crashing.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        model_path: Optional[str] = None,
        dimension: int = 384,
        version: str = "1.1.0"
    ):
        self._model_name = model_name
        self._model_path = model_path
        self._dimension = dimension
        self._version = version
        self._model = None
        self._load_attempted = False
        self._load_error: Optional[str] = None
        self._resolved_path: Optional[str] = None

    def _resolve_model_path(self) -> str:
        """Find local model weights path across Docker and host environments."""
        candidates = []
        if self._model_path:
            candidates.append(self._model_path)
        
        env_path = os.environ.get("NEURAL_MODEL_PATH")
        if env_path:
            candidates.append(env_path)

        # Standard container path
        candidates.append(f"/app/model_cache/{self._model_name}")
        
        # Local workspace paths relative to this file
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(curr_dir)))
        model_subpath = os.path.join(*self._model_name.split("/"))
        candidates.append(os.path.join(base_dir, "backend", "model_cache", model_subpath))
        candidates.append(os.path.join(base_dir, "model_cache", model_subpath))
        candidates.append(os.path.join("backend", "model_cache", model_subpath))

        for c in candidates:
            if c and os.path.exists(c):
                st_file = os.path.join(c, "model.safetensors")
                if os.path.exists(st_file) and os.path.getsize(st_file) > 10000000:
                    return os.path.abspath(c)

        # Fallback to model name identifier
        return self._model_name

    def _load_model(self):
        if self._model is not None:
            return
        try:
            import gc
            gc.collect()
            from sentence_transformers import SentenceTransformer
            from app.core.config import settings

            load_target = self._resolve_model_path()
            self._resolved_path = load_target

            is_offline = (
                os.environ.get("TRANSFORMERS_OFFLINE") in ("1", "true", "True") or
                os.environ.get("HF_HUB_OFFLINE") in ("1", "true", "True") or
                bool(getattr(settings, "TRANSFORMERS_OFFLINE", False)) or
                bool(getattr(settings, "HF_HUB_OFFLINE", False)) or
                bool(getattr(settings, "OFFLINE_MODE", False))
            )

            logger.info(f"Loading SentenceTransformer model target: {load_target} (offline_mode={is_offline})")

            if is_offline:
                # In offline mode, strictly use local files; fail immediately without network retries
                self._model = SentenceTransformer(load_target, local_files_only=True)
            else:
                # In online mode, attempt loading from persistent local cache first to avoid remote HEAD requests
                try:
                    self._model = SentenceTransformer(load_target, local_files_only=True)
                    logger.info(f"Loaded {self._model_name} from local cache without remote check.")
                except Exception:
                    logger.info(f"Model not found in local cache; downloading {self._model_name} from Hugging Face Hub...")
                    self._model = SentenceTransformer(load_target)

            self._load_error = None
            logger.info(f"Successfully loaded neural SentenceTransformer: {self._model_name} from {load_target}")
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"Sentence-transformer model '{self._model_name}' unavailable: {e}")

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def version(self) -> str:
        return self._version

    def embed_text(self, text: str) -> List[float]:
        self._load_model()
        if self._model is None:
            raise RuntimeError(f"EMBEDDING_MODEL_UNAVAILABLE: {self._load_error or 'SentenceTransformer not initialized'}")
        embedding = self._model.encode(text, normalize_embeddings=True)
        return [float(x) for x in embedding]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        if self._model is None:
            raise RuntimeError(f"EMBEDDING_MODEL_UNAVAILABLE: {self._load_error or 'SentenceTransformer not initialized'}")
        embeddings = self._model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [[float(x) for x in emb] for emb in embeddings]

    def model_info(self) -> Dict[str, Any]:
        self._load_model()
        return {
            "provider": "LocalSentenceTransformerProvider",
            "model_name": self._model_name,
            "model_type": "NEURAL_TRANSFORMER",
            "is_neural": True,
            "dimension": self._dimension,
            "version": self._version,
            "is_local": True,
            "loaded": self._model is not None,
            "local_path": self._resolved_path,
            "error": self._load_error,
            "description": "Genuine local neural SentenceTransformer model BAAI/bge-small-en-v1.5 running on PyTorch CPU. 384-d normalized dense embeddings."
        }

    def health(self) -> Dict[str, Any]:
        self._load_model()
        if self._model is not None:
            return {
                "status": "UP",
                "provider": "LocalSentenceTransformerProvider",
                "model_name": self._model_name,
                "model_type": "NEURAL_TRANSFORMER",
                "is_neural": True,
                "dimension": self._dimension,
                "available": True,
                "local_path": self._resolved_path
            }
        return {
            "status": "EMBEDDING_MODEL_UNAVAILABLE",
            "provider": "LocalSentenceTransformerProvider",
            "model_name": self._model_name,
            "model_type": "NEURAL_TRANSFORMER",
            "is_neural": True,
            "dimension": self._dimension,
            "available": False,
            "detail": self._load_error or "Neural model weights unprovisioned or failed to initialize."
        }
