import json
import time
import logging
from typing import Dict, Any, Optional
import urllib.request
import urllib.error

from app.core.config import settings
from app.services.llm.base import (
    LLMProvider,
    LLMResponse,
    ProviderHealth,
    ProviderModelInfo,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleLocalProvider(LLMProvider):
    """
    Local OpenAI-compatible adapter for self-hosted vLLM, LMDeploy, or llama.cpp server.
    Ensures zero cloud leakage by strictly pointing to on-premise local endpoints.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.base_url = (base_url or settings.OPENAI_COMPATIBLE_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.OPENAI_COMPATIBLE_MODEL
        self.timeout = timeout or settings.LLM_TIMEOUT_SECONDS

    def health(self) -> ProviderHealth:
        url = f"{self.base_url}/models"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KOYLA-RAG/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("id") for m in data.get("data", [])]
                    is_healthy = bool(models)
                    return ProviderHealth(
                        is_healthy=is_healthy,
                        provider="openai_compatible",
                        model_name=self.model_name,
                        endpoint=self.base_url,
                        error_message=None if is_healthy else "No models reported by local endpoint"
                    )
                else:
                    return ProviderHealth(
                        is_healthy=False,
                        provider="openai_compatible",
                        model_name=self.model_name,
                        endpoint=self.base_url,
                        error_message=f"HTTP {resp.status}"
                    )
        except Exception as e:
            return ProviderHealth(
                is_healthy=False,
                provider="openai_compatible",
                model_name=self.model_name,
                endpoint=self.base_url,
                error_message=f"Connection refused at {self.base_url}: {str(e)}"
            )

    def model_info(self) -> ProviderModelInfo:
        return ProviderModelInfo(
            provider="openai_compatible",
            model_name=self.model_name,
            is_local=True,
            context_window=8192,
            supports_structured=True
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        **kwargs
    ) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        start_t = time.perf_counter()
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "KOYLA-RAG/1.0"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                latency_ms = (time.perf_counter() - start_t) * 1000.0
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    choices = res_json.get("choices", [])
                    if not choices:
                        raise ValueError("No choices returned from local LLM endpoint")
                    choice = choices[0]
                    content = choice.get("message", {}).get("content", "").strip()
                    usage = res_json.get("usage", {})

                    return LLMResponse(
                        content=content,
                        model_name=self.model_name,
                        provider="openai_compatible",
                        finish_reason=choice.get("finish_reason", "stop"),
                        prompt_tokens=usage.get("prompt_tokens"),
                        completion_tokens=usage.get("completion_tokens"),
                        total_tokens=usage.get("total_tokens"),
                        latency_ms=latency_ms,
                        raw_response=res_json
                    )
                else:
                    raise LLMUnavailableError(f"HTTP {resp.status} from local LLM endpoint")
        except urllib.error.URLError as e:
            raise LLMUnavailableError(f"Local LLM service offline at {self.base_url}: {str(e)}")
        except Exception as e:
            raise LLMUnavailableError(f"Local LLM generation failed: {str(e)}")

    def structured_generate(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        messages = []
        sys_p = system_prompt or "You are an accurate structured extraction engine. Respond ONLY in valid JSON conforming to the requested schema."
        messages.append({"role": "system", "content": sys_p})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "stream": False
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "KOYLA-RAG/1.0"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    content = res_json.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                    return json.loads(content)
                else:
                    raise LLMUnavailableError(f"HTTP {resp.status} from local LLM endpoint")
        except urllib.error.URLError as e:
            raise LLMUnavailableError(f"Local LLM offline: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Local LLM produced invalid JSON: {str(e)}")
