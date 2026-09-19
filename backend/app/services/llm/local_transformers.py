import os
import time
import logging
from typing import Dict, Any, Optional
import torch
from app.core.config import settings
from app.services.llm.base import (
    LLMProvider,
    LLMResponse,
    ProviderHealth,
    ProviderModelInfo,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)

class LocalTransformersLLMProvider(LLMProvider):
    """
    In-process local transformer inference provider using local weights.
    Provides direct, zero-network-overhead generation completely on CPU/GPU.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.model_name = model_name or getattr(settings, "LOCAL_MODEL_NAME", "SmolLM2-135M-Instruct")
        
        # Determine model path: try container path first, then relative path
        candidate_paths = [
            model_path,
            getattr(settings, "LOCAL_MODEL_PATH", None),
            "/app/model_cache/SmolLM2-135M-Instruct",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "model_cache", "SmolLM2-135M-Instruct")
        ]
        
        self.resolved_path = None
        for p in candidate_paths:
            if p and os.path.exists(p) and os.path.exists(os.path.join(p, "model.safetensors")):
                self.resolved_path = p
                break

        self.tokenizer = None
        self.model = None
        self._init_error = None
        
        if self.resolved_path:
            try:
                from transformers import AutoModelForCausalLM, AutoTokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(self.resolved_path, local_files_only=True)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.resolved_path,
                    local_files_only=True,
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True
                )
                self.model.eval()
                logger.info(f"LocalTransformersLLMProvider: Loaded {self.model_name} from {self.resolved_path}")
            except Exception as e:
                self._init_error = str(e)
                logger.error(f"Failed to load local transformers model: {e}")
        else:
            self._init_error = "Model weights not found in candidate paths"

    def health(self) -> ProviderHealth:
        is_healthy = bool(self.model is not None and self.tokenizer is not None)
        return ProviderHealth(
            is_healthy=is_healthy,
            provider="local_transformers",
            model_name=self.model_name,
            endpoint=self.resolved_path or "unresolved",
            error_message=self._init_error if not is_healthy else None
        )

    def model_info(self) -> ProviderModelInfo:
        return ProviderModelInfo(
            provider="local_transformers",
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
        max_tokens: int = 768,
        **kwargs
    ) -> LLMResponse:
        if not self.model or not self.tokenizer:
            raise LLMUnavailableError(f"Local transformers model not available: {self._init_error}")

        start_t = time.perf_counter()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            formatted_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        except Exception:
            formatted_prompt = ""
            for m in messages:
                formatted_prompt += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
            formatted_prompt += "<|im_start|>assistant\n"

        inputs = self.tokenizer(formatted_prompt, return_tensors="pt")
        input_len = inputs.input_ids.shape[1]

        with torch.no_grad():
            if temperature > 0.01:
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=True,
                    temperature=temperature,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            else:
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id
                )

        generated_tokens = outputs[0][input_len:]
        content = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
        latency_ms = (time.perf_counter() - start_t) * 1000.0

        return LLMResponse(
            content=content,
            model_name=self.model_name,
            provider="local_transformers",
            finish_reason="stop",
            prompt_tokens=input_len,
            completion_tokens=len(generated_tokens),
            total_tokens=input_len + len(generated_tokens),
            latency_ms=latency_ms
        )

    def structured_generate(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        import json
        sys_p = system_prompt or "You are an accurate structured extraction engine. Respond ONLY in valid JSON conforming to the requested schema."
        resp = self.generate(prompt=prompt, system_prompt=sys_p, temperature=0.0, max_tokens=512)
        try:
            return json.loads(resp.content)
        except Exception:
            import re
            m = re.search(r'\{.*\}', resp.content, re.DOTALL)
            if m:
                return json.loads(m.group(0))
            raise ValueError(f"Failed to parse JSON from generation: {resp.content}")
