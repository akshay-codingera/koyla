from abc import ABC, abstractmethod
from typing import List, Dict, Any

class EmbeddingProvider(ABC):
    """
    Abstract Base Class for KOYLA local embedding providers.
    Enforces consistent vector dimensions, batch processing, model metadata,
    and explicit failure reporting without depending on external cloud APIs.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the embedding model (e.g. 'all-MiniLM-L6-v2')."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality (e.g. 384)."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version identifier of the embedding configuration."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate a single unit-normalized embedding vector for text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate unit-normalized embedding vectors for a batch of texts."""
        pass

    @abstractmethod
    def model_info(self) -> Dict[str, Any]:
        """Return model metadata dictionary."""
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Return health and availability status."""
        pass
