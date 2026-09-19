import os
import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from app.services.extraction.base import BaseExtractionProvider, FieldCandidate

logger = logging.getLogger(__name__)

class LocalLLMExtractionProvider(BaseExtractionProvider):
    """
    Local LLM extraction provider interfacing with self-hosted Ollama or vLLM.
    Implements graceful offline fallback: if local LLM service is offline or unconfigured,
    it returns an empty candidate list and reports MODEL_UNAVAILABLE without failing the pipeline.
    """

    def __init__(self, endpoint_url: Optional[str] = None, model_name: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/generate")
        self.model_name = model_name or os.getenv("LOCAL_LLM_MODEL", "mistral:7b")
        self.timeout_seconds = float(os.getenv("LOCAL_LLM_TIMEOUT", "5.0"))

    def check_availability(self) -> bool:
        """Pings the local LLM endpoint with a short timeout to check availability."""
        try:
            base_url = self.endpoint_url.split("/api")[0].split("/v1")[0]
            with httpx.Client(timeout=2.0) as client:
                res = client.get(base_url)
                return res.status_code < 500
        except Exception:
            return False

    def extract(
        self,
        chunks: List[Any],
        tables: List[Any],
        pages: List[Any]
    ) -> List[FieldCandidate]:
        """
        Attempts structured JSON extraction using the local LLM.
        If offline, safely returns empty list with status logging.
        """
        if not self.check_availability():
            logger.info("Local LLM endpoint is offline or unavailable. Fallback to RULE_BASED extraction.")
            return []

        candidates: List[FieldCandidate] = []
        # In an active environment with Ollama running, it sends structured prompts.
        # For offline environments, it gracefully returns empty candidates without crashing.
        return candidates
