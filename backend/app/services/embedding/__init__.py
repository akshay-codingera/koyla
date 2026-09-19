import logging
from app.core.config import settings
from app.services.embedding.base import EmbeddingProvider
from app.services.embedding.deterministic import DeterministicLocalEmbeddingProvider
from app.services.embedding.sentence_transformer import LocalSentenceTransformerProvider

logger = logging.getLogger(__name__)

_embedding_provider_instance: EmbeddingProvider = None

def get_embedding_provider() -> EmbeddingProvider:
    """
    Factory function returning the configured local embedding provider.
    Singleton pattern ensures single initialization per worker.
    """
    global _embedding_provider_instance
    if _embedding_provider_instance is not None:
        return _embedding_provider_instance

    provider_type = getattr(settings, "EMBEDDING_PROVIDER", "deterministic").lower()

    if provider_type in ["sentence_transformers", "sentence-transformers", "local_hf"]:
        st_provider = LocalSentenceTransformerProvider(
            model_name=getattr(settings, "NEURAL_MODEL_NAME", "BAAI/bge-small-en-v1.5"),
            model_path=getattr(settings, "NEURAL_MODEL_PATH", None),
            dimension=settings.EMBEDDING_DIMENSION,
            version=settings.EMBEDDING_VERSION
        )
        health = st_provider.health()
        if health.get("available"):
            _embedding_provider_instance = st_provider
            return _embedding_provider_instance
        else:
            logger.warning(
                f"Sentence-transformers provider unavailable ({health.get('detail')}). "
                "Falling back to DeterministicLocalEmbeddingProvider."
            )
            _embedding_provider_instance = DeterministicLocalEmbeddingProvider(
                model_name=getattr(settings, "DETERMINISTIC_MODEL_NAME", "koyla-deterministic-hash-384"),
                dimension=settings.EMBEDDING_DIMENSION,
                version=settings.EMBEDDING_VERSION
            )
            return _embedding_provider_instance

    # Default: Deterministic local provider
    _embedding_provider_instance = DeterministicLocalEmbeddingProvider(
        model_name=getattr(settings, "DETERMINISTIC_MODEL_NAME", "koyla-deterministic-hash-384"),
        dimension=settings.EMBEDDING_DIMENSION,
        version=settings.EMBEDDING_VERSION
    )
    return _embedding_provider_instance

__all__ = [
    "EmbeddingProvider",
    "DeterministicLocalEmbeddingProvider",
    "LocalSentenceTransformerProvider",
    "get_embedding_provider",
]
