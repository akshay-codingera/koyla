from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    content: str
    model_name: str
    provider: str
    finish_reason: str = "stop"
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: float = 0.0
    raw_response: Optional[Dict[str, Any]] = None


class ProviderHealth(BaseModel):
    is_healthy: bool
    provider: str
    model_name: str
    endpoint: str
    error_message: Optional[str] = None
    checked_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ProviderModelInfo(BaseModel):
    provider: str
    model_name: str
    is_local: bool = True
    context_window: int = 4096
    supports_structured: bool = True


class LLMUnavailableError(Exception):
    """Raised when the local LLM engine is unreachable or offline."""
    pass


class LLMProvider(ABC):
    """
    Abstract Base Class for Local LLM Providers in KOYLA.
    In accordance with AGENTS.md, all LLM inference must be local/on-premise.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        **kwargs
    ) -> LLMResponse:
        """Execute text generation against local model."""
        pass

    @abstractmethod
    def structured_generate(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute schema-constrained structured generation."""
        pass

    @abstractmethod
    def health(self) -> ProviderHealth:
        """Verify provider availability and endpoint connectivity."""
        pass

    @abstractmethod
    def model_info(self) -> ProviderModelInfo:
        """Return provider and model metadata."""
        pass
