
import asyncio
import json
import requests
from typing import Any, Dict, Optional

from src.ai.registry import register_ai
from src.ai.targets import AiTarget
from .base import BaseAiModel, AiResponse


@register_ai(
    target=AiTarget.OLLAMA,
    name="Ollama",
    default_model="qwen3.5:9b",
    popular_models=[
        "translategemma:4b",
        "translategemma:12b",
        "translategemma:27b",

        "MedAIBase/Tencent-HY-MT1.5:1.8b",
        "MedAIBase/Tencent-HY-MT1.5:7b",
        "MedAIBase/Tencent-HY-MT1.5:1.8b-q4_K_M",
        "MedAIBase/Tencent-HY-MT1.5:7b-q4_K_M",

        "qwen3.5:0.8b",
        "qwen3.5:2b",
        "qwen3.5:4b",
        "qwen3.5:9b",
        "qwen3.5:27b",
        "qwen3.5:35b-a3b",
        "qwen3.5:122b-a10b",

        "qwen3.6:27b",
        "qwen3.6:35b",

        "qwen3:0.6b",
        "qwen3:1.7b",
        "qwen3:4b",
        "qwen3:8b",
        "qwen3:14b",
        "qwen3:30b",
        "qwen3:32b",
        "qwen3:235b",

        "qwen2.5:0.5b",
        "qwen2.5:1.5b",
        "qwen2.5:3b",
        "qwen2.5:7b",
        "qwen2.5:14b",
        "qwen2.5:32b",
        "qwen2.5:72b",

        "exaone3.5:2.4b",
        "exaone3.5:7.8b",
        "exaone3.5:32b",

        "gemma4:e2b",
        "gemma4:e4b",
        "gemma4:12b",
        "gemma4:26b",
        "gemma4:31b",

        "gemma3:1b",
        "gemma3:4b",
        "gemma3:12b",
        "gemma3:27b",
        
        "gemma2:2b",
        "gemma2:9b",
        "gemma2:27b",

        "aya-expanse:8b",
        "aya-expanse:32b",

        "deepseek-r1:1.5b",
        "deepseek-r1:7b",
        "deepseek-r1:8b",
        "deepseek-r1:14b",
        "deepseek-r1:32b",
        "deepseek-r1:70b",
        "deepseek-r1:671b",

        "llama3.2:1b",
        "llama3.2:3b",
        "llama3.1:8b",
        "llama3.1:70b",
        "llama3.3:70b",

        "mistral:7b",
        "mistral-nemo:12b",

        "phi4-mini",
        "phi4",
        "granite3.3:8b",
        "solar:10.7b",
        "command-r:35b",
        "command-r-plus:104b",
    ],
    patterns=[
        "translategemma",
        "hy-mt",
        "tencent",
        "qwen",
        "gemma",
        "exaone",
        "aya",
        "deepseek",
        "llama",
        "mistral",
        "phi",
        "granite",
        "solar",
        "command-r",
        "gpt-oss",
        ":"
    ],
    matcher=lambda m: ":" in m or any(k in m.lower() for k in (
        "qwen", "gemma", "exaone", "aya", "deepseek", "llama",
        "mistral", "phi", "granite", "solar", "command-r",
        "translategemma", "hy-mt", "tencent", "ollama"
    )),
    default_config={
        "rpm": 60,
        "temperature": 0.1,
        "concurrency": 1,
        "br_start": 0,
        "isno_x": False,
        "thinking_budget": "기본값"
    }
)
class OllamaModel(BaseAiModel):
    def __init__(self, api_key: str = "", base_url: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")

    def _get_base_url(self) -> str:
        try:
            from src.system.load_save import load_data
            data = load_data()
            url = str(data.get("ollama_url", "")).strip()
            if url:
                return url.rstrip("/")
        except Exception:
            pass
        return self.base_url

    async def send_text(self, message: str, setting: Optional[Dict[str, Any]] = None) -> AiResponse:
        setting = setting or {}
        model_name = setting.get("model_name", "qwen3.5:9b")
        system_instruction = setting.get("system_instruction", "")
        temperature = setting.get("temperature", 0.1)
        top_p = setting.get("top_p", 0.8)

        url = f"{self._get_base_url()}/api/generate"
        payload = {
            "model": model_name,
            "prompt": message,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p
            }
        }
        if system_instruction:
            payload["system"] = system_instruction

        def _call():
            try:
                resp = requests.post(url, json=payload, timeout=600)
                if resp.status_code != 200:
                    raise RuntimeError(f"Ollama 오류 ({resp.status_code}): {resp.text}")
                return resp.json().get("response", "")
            except requests.exceptions.ConnectionError:
                raise RuntimeError("로컬 Ollama 서버에 연결할 수 없습니다. AI 관리자에서 서버를 실행하세요.")

        text = await asyncio.to_thread(_call)
        return AiResponse(text=text)
