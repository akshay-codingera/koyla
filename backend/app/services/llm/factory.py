import logging
from typing import Optional
from app.core.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.ollama import OllamaProvider
from app.services.llm.openai_compatible import OpenAICompatibleLocalProvider

from app.services.llm.local_transformers import LocalTransformersLLMProvider

logger = logging.getLogger(__name__)

_provider_instance: Optional[LLMProvider] = None


def get_llm_provider(force_provider: Optional[str] = None) -> LLMProvider:
    """
    Factory function returning the configured Local LLM Provider.
    In accordance with AGENTS.md, all LLM endpoints must be strictly local.
    """
    global _provider_instance
    provider_type = (force_provider or settings.LLM_PROVIDER).lower()

    if _provider_instance is not None and force_provider is None:
        return _provider_instance

    if provider_type in ["local_transformers", "transformers", "local", "in_process"]:
        provider = LocalTransformersLLMProvider(
            model_path=getattr(settings, "LOCAL_MODEL_PATH", None),
            model_name=getattr(settings, "LOCAL_MODEL_NAME", "SmolLM2-135M-Instruct"),
            timeout=settings.LLM_TIMEOUT_SECONDS
        )
    elif provider_type == "ollama":
        provider = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model_name=settings.OLLAMA_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS
        )
    elif provider_type in ["openai_compatible", "vllm", "local_openai"]:
        provider = OpenAICompatibleLocalProvider(
            base_url=settings.OPENAI_COMPATIBLE_BASE_URL,
            model_name=settings.OPENAI_COMPATIBLE_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS
        )
    else:
        logger.warning(f"Unknown LLM provider '{provider_type}'. Defaulting to Ollama.")
        provider = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model_name=settings.OLLAMA_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS
        )

    # If the network provider is offline but local transformer weights are available, auto-promote local provider
    if not provider.health().is_healthy and provider_type in ["ollama", "openai_compatible"]:
        local_candidate = LocalTransformersLLMProvider(
            model_path=getattr(settings, "LOCAL_MODEL_PATH", None),
            model_name=getattr(settings, "LOCAL_MODEL_NAME", "SmolLM2-135M-Instruct")
        )
        if local_candidate.health().is_healthy:
            logger.info("External local endpoint unavailable. Auto-selecting in-process LocalTransformersLLMProvider.")
            provider = local_candidate

    if force_provider is None:
        _provider_instance = provider
    return provider



def set_llm_provider(provider: LLMProvider) -> None:
    """Explicitly set provider instance (used in tests or dynamic switching)."""
    global _provider_instance
    _provider_instance = provider
