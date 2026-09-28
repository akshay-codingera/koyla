import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from app.core.config import settings
from app.core.logging.timing import timed_operation

logger = logging.getLogger(__name__)

class Reranker(ABC):
    """Abstract base class for local rerankers."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 10
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Rerank candidate chunks for a query.
        Returns (reranked_candidates, status_code).
        Status code is 'ACTIVE', 'DISABLED', or 'RERANKER_UNAVAILABLE'.
        """
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        pass


class LocalCrossEncoderReranker(Reranker):
    """
    Local Cross-Encoder Reranker using sentence-transformers CrossEncoder.
    If unavailable or disabled, safely falls back and preserves original RRF ranking
    without fabricating scores.
    """

    def __init__(self, model_name: str = None, enabled: bool = None):
        self.model_name = model_name or getattr(settings, "RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.enabled = enabled if enabled is not None else getattr(settings, "ENABLE_RERANKER", True)
        self._model = None
        self._load_attempted = False
        self._load_error: Optional[str] = None

    def _load_model(self):
        if self._load_attempted or not self.enabled:
            return
        self._load_attempted = True
        try:
            import os
            from sentence_transformers import CrossEncoder
            from app.core.config import settings

            is_offline = (
                os.environ.get("TRANSFORMERS_OFFLINE") in ("1", "true", "True") or
                os.environ.get("HF_HUB_OFFLINE") in ("1", "true", "True") or
                bool(getattr(settings, "TRANSFORMERS_OFFLINE", False)) or
                bool(getattr(settings, "HF_HUB_OFFLINE", False)) or
                bool(getattr(settings, "OFFLINE_MODE", False))
            )

            if is_offline:
                self._model = CrossEncoder(self.model_name, local_files_only=True)
            else:
                try:
                    self._model = CrossEncoder(self.model_name, local_files_only=True)
                except Exception:
                    self._model = CrossEncoder(self.model_name)
            logger.info(f"Loaded local CrossEncoder reranker: {self.model_name}")
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"Local CrossEncoder '{self.model_name}' unavailable: {e}")

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 10
    ) -> Tuple[List[Dict[str, Any]], str]:
        with timed_operation(
            logger,
            "cross_encoder_rerank",
            extra={
                "candidate_count": len(candidates),
                "top_k": top_k,
                "model_name": self.model_name,
                "enabled": self.enabled,
            }
        ) as metrics:
            if not candidates:
                metrics["status"] = "EMPTY"
                return [], "EMPTY"

            if not self.enabled:
                # Reranker explicitly disabled: preserve fused ranking
                for c in candidates:
                    c["reranker_score"] = None
                metrics["status"] = "DISABLED"
                return candidates[:top_k], "DISABLED"

            self._load_model()
            if self._model is None:
                # Model unavailable: preserve fused ranking, do NOT fabricate scores
                for c in candidates:
                    c["reranker_score"] = None
                metrics["status"] = "RERANKER_UNAVAILABLE"
                return candidates[:top_k], "RERANKER_UNAVAILABLE"

            try:
                pairs = [(query, c.get("content", "")) for c in candidates]
                scores = self._model.predict(pairs)

                for c, score in zip(candidates, scores):
                    c["reranker_score"] = round(float(score), 4)

                # Re-sort candidates by reranker score descending
                reranked = sorted(candidates, key=lambda x: x["reranker_score"] if x["reranker_score"] is not None else -999.0, reverse=True)
                metrics["status"] = "ACTIVE"
                metrics["reranked_count"] = len(reranked[:top_k])
                return reranked[:top_k], "ACTIVE"
            except Exception as e:
                logger.error(f"Error during cross-encoder reranking: {e}")
                for c in candidates:
                    c["reranker_score"] = None
                metrics["status"] = "RERANKER_UNAVAILABLE"
                metrics["error"] = str(e)
                return candidates[:top_k], "RERANKER_UNAVAILABLE"

    def health(self) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "status": "DISABLED",
                "model_name": self.model_name,
                "available": False
            }
        self._load_model()
        if self._model is not None:
            return {
                "status": "UP",
                "model_name": self.model_name,
                "available": True
            }
        return {
            "status": "RERANKER_UNAVAILABLE",
            "model_name": self.model_name,
            "available": False,
            "detail": self._load_error
        }

local_reranker = LocalCrossEncoderReranker()
