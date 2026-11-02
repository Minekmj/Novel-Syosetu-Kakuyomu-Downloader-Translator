
import asyncio
import json
import requests
from typing import Any, Dict, List, Optional
import subprocess

from src.ai.registry import register_ai
from src.ai.targets import AiTarget
from .base import BaseAiModel, AiResponse


@register_ai(
    target=AiTarget.OLLAMA,
    name="Ollama",
    default_model="translategemma:12b",
    popular_models=[
        "translategemma:12b",
        "translategemma:27b",
        
        "gemma4:12b",
        "gemma4:26b",
        "gemma4:31b",
        "gemma4:e4b",
        "gemma4:e2b",
        
        "MedAIBase/Tencent-HY-MT1.5:7b",

        "deepseek-v2:16b",
        "deepseek-r1:14b",
        "deepseek-r1:32b",
        
        "gpt-oss:20b",
        
    ],
    patterns=[
        "translategemma",
        "hy-mt",
        "deepseek",
        "qwen",
        "gemma",
        "exaone",
        "translate",
        ":"
    ],
    matcher=lambda m: ":" in m or any(k in m.lower() for k in (
        "translategemma", "hy-mt", "deepseek", "qwen",
        "gemma", "exaone", "translate", "ollama"
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
    
    def list_models(self, _) -> List[str]:
        try:
            result = subprocess.run(
                ['ollama', 'list'], capture_output=True, text=True, check=True
            )

            lines = result.stdout.strip().split('\n')
            models = []
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    models.append(parts[0])

            return models
        except:
            return []

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
                "top_p": top_p,
                "num_predict": -1
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
                raise RuntimeError("로컬 Ollama 서버에 연결할 수 없습니다. Ollama 서버를 실행하세요.")

        text = await asyncio.to_thread(_call)
        return AiResponse(text=text)
