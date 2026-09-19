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


class OllamaProvider(LLMProvider):
    """
    Native Local Ollama client adapter for KOYLA.
    Communicates strictly with on-premise / local Ollama daemon.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.LLM_TIMEOUT_SECONDS

    def health(self) -> ProviderHealth:
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KOYLA-RAG/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", [])]
                    # Check if configured model is installed
                    is_model_present = any(self.model_name in m for m in models)
                    if not is_model_present and models:
                        # Model name might not have tag suffix
                        is_model_present = any(m.startswith(self.model_name.split(":")[0]) for m in models)
                    
                    err = None if is_model_present else f"Model '{self.model_name}' not found in Ollama library. Available: {models}"
                    return ProviderHealth(
                        is_healthy=is_model_present,
                        provider="ollama",
                        model_name=self.model_name,
                        endpoint=self.base_url,
                        error_message=err
                    )
                else:
                    return ProviderHealth(
                        is_healthy=False,
                        provider="ollama",
                        model_name=self.model_name,
                        endpoint=self.base_url,
                        error_message=f"Ollama returned HTTP status {resp.status}"
                    )
        except Exception as e:
            return ProviderHealth(
                is_healthy=False,
                provider="ollama",
                model_name=self.model_name,
                endpoint=self.base_url,
                error_message=f"Connection refused or offline at {self.base_url}: {str(e)}"
            )

    def model_info(self) -> ProviderModelInfo:
        return ProviderModelInfo(
            provider="ollama",
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
        url = f"{self.base_url}/api/chat"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
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
                    message = res_json.get("message", {})
                    content = message.get("content", "").strip()
                    prompt_eval_count = res_json.get("prompt_eval_count")
                    eval_count = res_json.get("eval_count")
                    total_tokens = (prompt_eval_count or 0) + (eval_count or 0) if prompt_eval_count or eval_count else None

                    return LLMResponse(
                        content=content,
                        model_name=self.model_name,
                        provider="ollama",
                        finish_reason=res_json.get("done_reason", "stop"),
                        prompt_tokens=prompt_eval_count,
                        completion_tokens=eval_count,
                        total_tokens=total_tokens,
                        latency_ms=latency_ms,
                        raw_response=res_json
                    )
                else:
                    raise LLMUnavailableError(f"Ollama returned HTTP status {resp.status}")
        except urllib.error.URLError as e:
            raise LLMUnavailableError(f"Local Ollama is offline or unreachable at {self.base_url}: {str(e)}")
        except Exception as e:
            raise LLMUnavailableError(f"Ollama generation failed: {str(e)}")

    def structured_generate(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        messages = []
        sys_p = system_prompt or "You are an accurate structured data extraction model. Respond ONLY in valid JSON matching the requested schema."
        messages.append({"role": "system", "content": sys_p})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.0,
                "num_predict": 1024
            }
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
                    content = res_json.get("message", {}).get("content", "{}")
                    return json.loads(content)
                else:
                    raise LLMUnavailableError(f"Ollama returned HTTP status {resp.status}")
        except urllib.error.URLError as e:
            raise LLMUnavailableError(f"Local Ollama offline: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Ollama produced non-JSON structured output: {str(e)}")
