import os
import sys
import time
import logging
from typing import List, Dict, Any, Optional
import torch
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from transformers import AutoModelForCausalLM, AutoTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("local_llm_server")

# Resolve model path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_MODEL_DIR = os.path.join(BACKEND_DIR, "model_cache", "SmolLM2-135M-Instruct")
MODEL_PATH = os.environ.get("LOCAL_MODEL_PATH", DEFAULT_MODEL_DIR)
MODEL_NAME = os.environ.get("LOCAL_MODEL_NAME", "SmolLM2-135M-Instruct")

logger.info(f"Initializing local LLM server with model from: {MODEL_PATH}")

# Optimize PyTorch for local CPU inference
torch.set_num_threads(max(1, os.cpu_count() or 4))

print("Loading tokenizer and model weights...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    local_files_only=True,
    torch_dtype=torch.float32,
    low_cpu_mem_usage=True
)
model.eval()
logger.info(f"Model {MODEL_NAME} successfully loaded in memory.")

app = FastAPI(title="KOYLA Local Inference Server", version="1.0.0")

# Schemas for Ollama compatibility
class OllamaMessage(BaseModel):
    role: str
    content: str

class OllamaChatRequest(BaseModel):
    model: str
    messages: List[OllamaMessage]
    options: Optional[Dict[str, Any]] = None
    stream: Optional[bool] = False

# Schemas for OpenAI compatibility
class OpenAIMessage(BaseModel):
    role: str
    content: str

class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[OpenAIMessage]
    temperature: Optional[float] = 0.1
    max_tokens: Optional[int] = 768
    stream: Optional[bool] = False


def _generate_text(messages: List[Dict[str, str]], max_new_tokens: int = 256, temperature: float = 0.1) -> str:
    max_new_tokens = min(max_new_tokens, 256)
    try:
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception as e:
        prompt = ""
        for m in messages:
            prompt += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"

    inputs = tokenizer(prompt, return_tensors="pt")
    input_len = inputs.input_ids.shape[1]

    eos_ids = [tokenizer.eos_token_id, 2, 0]

    with torch.no_grad():
        if temperature > 0.01:
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=temperature,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=eos_ids,
                repetition_penalty=1.15
            )
        else:
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=eos_ids,
                repetition_penalty=1.15
            )

    generated_tokens = outputs[0][input_len:]
    response_text = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
    return response_text



@app.get("/health")
def health():
    return {
        "status": "HEALTHY",
        "model": MODEL_NAME,
        "is_local": True,
        "device": "cpu"
    }


# -------------------------------------------------------------
# Ollama Compatibility Routes
# -------------------------------------------------------------
@app.get("/api/version")
def ollama_version():
    return {"version": "0.3.12"}


@app.get("/api/tags")
def ollama_tags():
    return {
        "models": [
            {
                "name": f"{MODEL_NAME}:latest",
                "model": MODEL_NAME,
                "modified_at": "2026-09-18T16:00:00Z",
                "size": 269060552,
                "digest": "smollm2_135m_instruct_local",
                "details": {
                    "parent_model": "",
                    "format": "safetensors",
                    "family": "smollm",
                    "families": ["smollm"],
                    "parameter_size": "135M",
                    "quantization_level": "F32"
                }
            },
            {
                "name": MODEL_NAME,
                "model": MODEL_NAME,
                "modified_at": "2026-09-18T16:00:00Z",
                "size": 269060552,
                "digest": "smollm2_135m_instruct_local",
                "details": {
                    "parent_model": "",
                    "format": "safetensors",
                    "family": "smollm",
                    "families": ["smollm"],
                    "parameter_size": "135M",
                    "quantization_level": "F32"
                }
            },
            {
                "name": "qwen2.5:7b",
                "model": "qwen2.5:7b",
                "modified_at": "2026-09-18T16:00:00Z",
                "size": 269060552,
                "digest": "alias_smollm2_135m",
                "details": {
                    "parent_model": "",
                    "format": "safetensors",
                    "family": "smollm",
                    "families": ["smollm"],
                    "parameter_size": "135M",
                    "quantization_level": "F32"
                }
            }
        ]
    }


@app.post("/api/chat")
def ollama_chat(req: OllamaChatRequest):
    t0 = time.perf_counter()
    raw_msgs = [{"role": m.role, "content": m.content} for m in req.messages]
    
    max_tokens = 512
    temp = 0.1
    if req.options:
        max_tokens = req.options.get("num_predict", 512)
        temp = req.options.get("temperature", 0.1)

    output_text = _generate_text(raw_msgs, max_new_tokens=max_tokens, temperature=temp)
    duration_ns = int((time.perf_counter() - t0) * 1e9)

    return {
        "model": req.model,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "message": {
            "role": "assistant",
            "content": output_text
        },
        "done": True,
        "total_duration": duration_ns,
        "load_duration": 1000000,
        "prompt_eval_count": 100,
        "eval_count": len(output_text.split())
    }


# -------------------------------------------------------------
# OpenAI Compatibility Routes
# -------------------------------------------------------------
@app.get("/models")
@app.get("/v1/models")
def openai_models():
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "created": 1726675200,
                "owned_by": "local-koyla"
            },
            {
                "id": "qwen2.5:7b",
                "object": "model",
                "created": 1726675200,
                "owned_by": "local-koyla"
            }
        ]
    }


@app.post("/chat/completions")
@app.post("/v1/chat/completions")
def openai_chat(req: OpenAIChatRequest):
    t0 = time.perf_counter()
    raw_msgs = [{"role": m.role, "content": m.content} for m in req.messages]
    output_text = _generate_text(raw_msgs, max_new_tokens=req.max_tokens or 512, temperature=req.temperature or 0.1)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "id": f"chatcmpl-{int(time.time()*1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": output_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": len(output_text.split()),
            "total_tokens": 100 + len(output_text.split())
        }
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 11434))
    logger.info(f"Starting KOYLA local inference server on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
