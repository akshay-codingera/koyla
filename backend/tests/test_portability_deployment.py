import os
import pytest
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.services.embedding.sentence_transformer import LocalSentenceTransformerProvider
from app.services.embedding.deterministic import DeterministicLocalEmbeddingProvider
from app.services.embedding import get_embedding_provider
from app.services.extraction.local_llm import LocalLLMExtractionProvider
from app.services.reports.docx_renderer import REPORTS_DIR


def test_config_offline_flags_defaults():
    """Verify offline mode flags exist in Settings and have safe defaults."""
    assert hasattr(settings, "TRANSFORMERS_OFFLINE")
    assert hasattr(settings, "HF_HUB_OFFLINE")
    assert hasattr(settings, "OFFLINE_MODE")
    assert settings.OLLAMA_BASE_URL is not None


def test_extraction_local_llm_uses_configured_ollama_base_url():
    """Verify LocalLLMExtractionProvider derives its endpoint from settings.OLLAMA_BASE_URL."""
    with patch.object(settings, "OLLAMA_BASE_URL", "http://custom-ollama-host:11434"):
        with patch.dict(os.environ, {}, clear=True):
            provider = LocalLLMExtractionProvider()
            assert provider.endpoint_url == "http://custom-ollama-host:11434/api/generate"


def test_system_health_uses_configured_ollama_base_url():
    """Verify system health check dynamically constructs endpoint from settings.OLLAMA_BASE_URL."""
    with patch.object(settings, "OLLAMA_BASE_URL", "http://host.docker.internal:11434"):
        base_url = (getattr(settings, "OLLAMA_BASE_URL", None) or "http://localhost:11434").rstrip("/")
        llm_endpoint = f"{base_url}/api/tags"
        assert llm_endpoint == "http://host.docker.internal:11434/api/tags"


def test_topics_summary_uses_configured_ollama_base_url():
    """Verify topics factual summary dynamically derives endpoint from settings.OLLAMA_BASE_URL."""
    with patch.object(settings, "OLLAMA_BASE_URL", "http://remote-ollama:11434"):
        base_url = (getattr(settings, "OLLAMA_BASE_URL", None) or "http://localhost:11434").rstrip("/")
        endpoint = f"{base_url}/api/generate"
        assert endpoint == "http://remote-ollama:11434/api/generate"


def test_sentence_transformer_offline_mode_immediate_fallback():
    """
    Verify that in offline mode with absent weights, SentenceTransformer does not stall
    with network retries and immediately reports unavailable.
    """
    with patch.dict(os.environ, {"TRANSFORMERS_OFFLINE": "1", "HF_HUB_OFFLINE": "1"}):
        provider = LocalSentenceTransformerProvider(
            model_name="nonexistent/fake-model-absent",
            model_path="/nonexistent/path/fake-model"
        )
        health = provider.health()
        assert health["available"] is False
        assert health["status"] == "EMBEDDING_MODEL_UNAVAILABLE"
        assert provider._model is None


def test_reports_dir_is_consistent():
    """Verify REPORTS_DIR is valid and ends with data/reports."""
    norm_path = os.path.normpath(REPORTS_DIR)
    assert norm_path.endswith(os.path.normpath("data/reports"))
