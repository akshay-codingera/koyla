import re
import math
import hashlib
from typing import List, Dict, Any
from app.services.embedding.base import EmbeddingProvider

class DeterministicLocalEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic Local Feature-Hashing Embedding Provider.
    Generates unit-normalized 384-dimensional embedding vectors using multi-resolution
    token n-gram hashing and subword projections.
    
    Zero external GPU/cloud dependency. 100% reproducible and compatible with pgvector
    cosine distance `<=>`.
    """

    def __init__(self, model_name: str = "koyla-deterministic-hash-384", dimension: int = 384, version: str = "1.0.0"):
        self._model_name = model_name
        self._dimension = dimension
        self._version = version

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def version(self) -> str:
        return self._version

    def _hash_token(self, token: str, seed: int = 0) -> tuple[int, float]:
        """Hash a token to an index [0, dimension) and sign {-1.0, 1.0}."""
        h = hashlib.sha256(f"{token}_{seed}".encode("utf-8")).digest()
        # Extract index from first 4 bytes
        idx = int.from_bytes(h[:4], "big") % self._dimension
        # Extract sign from 5th byte
        sign = 1.0 if (h[4] % 2 == 0) else -1.0
        return idx, sign

    def embed_text(self, text: str) -> List[float]:
        """Generate a unit-normalized 384-d vector for a text string."""
        if not text or not text.strip():
            # Return zero-like normalized vector with small epsilon or unit point
            vec = [0.0] * self._dimension
            vec[0] = 1.0
            return vec

        cleaned = text.lower().strip()
        tokens = re.findall(r'\b[a-zA-Z0-9_\-]+\b', cleaned)
        if not tokens:
            vec = [0.0] * self._dimension
            vec[0] = 1.0
            return vec

        vec = [0.0] * self._dimension

        # 1. Unigrams
        for tok in tokens:
            idx1, sign1 = self._hash_token(tok, seed=42)
            idx2, sign2 = self._hash_token(tok, seed=1337)
            weight = math.log1p(len(tok))
            vec[idx1] += sign1 * weight
            vec[idx2] += sign2 * (weight * 0.5)

        # 2. Bigrams for local phrase structure
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]}_{tokens[i+1]}"
            idx_bi, sign_bi = self._hash_token(bigram, seed=999)
            vec[idx_bi] += sign_bi * 1.5

        # 3. Subwords / Character 3-grams for technical codes (e.g. FY2024-25, BH-01)
        for tok in tokens:
            if len(tok) >= 3:
                for j in range(len(tok) - 2):
                    trigram = tok[j:j+3]
                    idx_tri, sign_tri = self._hash_token(trigram, seed=777)
                    vec[idx_tri] += sign_tri * 0.4

        # Unit normalize (L2 norm)
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 1e-9:
            vec = [float(v / norm) for v in vec]
        else:
            vec = [0.0] * self._dimension
            vec[0] = 1.0

        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate normalized vectors for a batch of texts."""
        return [self.embed_text(t) for t in texts]

    def model_info(self) -> Dict[str, Any]:
        return {
            "provider": "DeterministicLocalEmbeddingProvider",
            "model_name": self._model_name,
            "model_type": "DETERMINISTIC_FEATURE_HASHING",
            "is_neural": False,
            "dimension": self._dimension,
            "version": self._version,
            "is_local": True,
            "device": "cpu",
            "normalized": True,
            "description": "Deterministic multi-resolution token and n-gram feature hashing into 384-d unit L2 normalized vector space (Air-gapped mathematical fallback; NOT neural sentence-transformers)."
        }

    def health(self) -> Dict[str, Any]:
        return {
            "status": "UP",
            "provider": "DeterministicLocalEmbeddingProvider",
            "model_name": self._model_name,
            "model_type": "DETERMINISTIC_FEATURE_HASHING",
            "is_neural": False,
            "dimension": self._dimension,
            "version": self._version,
            "available": True,
            "detail": "Deterministic local feature hashing active. Neural weights unprovisioned in air-gapped container."
        }
