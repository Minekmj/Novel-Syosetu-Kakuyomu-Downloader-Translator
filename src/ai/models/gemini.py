import asyncio
import re
import weakref
from typing import Any, Dict, Optional, List
from google import genai
from google.genai import types

from src.ai.registry import register_ai
from src.ai.targets import AiTarget
from .base import BaseAiModel, AiResponse


def build_thinking_config(thinking_val, model_name=""):
    if thinking_val is None:
        return None

    val = str(thinking_val).strip().upper()
    if val in ('기본값', 'NONE', '', 'DEFAULT'):
        return None

    level = None
    for candidate in ('MINIMAL', 'LOW', 'MEDIUM', 'HIGH', 'XHIGH'):
        if candidate in val:
            level = candidate
            break

    digits = re.findall(r'-?\d+', val)
    raw_number = int(digits[0]) if digits else None

    m = str(model_name).lower()
    
    if not 'hydrogen' in m:
        target_level = 'HIGH' if level == 'XHIGH' else level
        level = 'HIGH' if level == 'XHIGH' else level

    if 'gemma-4' in m:
        target_level = 'HIGH' if level == 'HIGH' or (raw_number is not None and raw_number > 0) else 'MINIMAL'
        return types.ThinkingConfig(thinking_level=target_level)

    if 'gemini-3' in m or 'gemini-4' in m:
        def _get_level_enum(name):
            try:
                return getattr(types.ThinkingLevel, name)
            except AttributeError:
                return name

        is_pro = 'pro' in m
        if level == 'MINIMAL':
            target_level = 'LOW' if is_pro else 'MINIMAL'
        elif level in ('LOW', 'MEDIUM', 'HIGH'):
            target_level = level
        elif raw_number == 0:
            target_level = 'LOW' if is_pro else 'MINIMAL'
        else:
            target_level = 'LOW'

        return types.ThinkingConfig(thinking_level=_get_level_enum(target_level))

    if 'gemini-2.5' in m:
        budget_map = {'MINIMAL': 0, 'LOW': 1024, 'MEDIUM': 2048, 'HIGH': 4096}
        if level in budget_map:
            return types.ThinkingConfig(thinking_budget=budget_map[level])
        if raw_number is not None:
            return types.ThinkingConfig(thinking_budget=raw_number)
        return types.ThinkingConfig(thinking_budget=1024)

    return None


@register_ai(
    target=AiTarget.GEMINI,
    name="Gemini",
    default_model="gemini-3.5-flash-lite",
    popular_models=[
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
    ],
    patterns=["gemini-", "gemma-"],
    default_config={
        "rpm": 15,
        "temperature": 0.1,
        "concurrency": 4,
        "br_start": 0,
        "isno_x": False,
        "thinking_budget": "기본값"
    },
    is_default=True
)
class GeminiModel(BaseAiModel):
    def __init__(self, api_key: str = ""):
        super().__init__(api_key)
        self._loop_client_pools = weakref.WeakKeyDictionary()
        self._sync_client_pool = {}

    def _get_target_key(self, api_key: Optional[str] = None) -> str:
        key = (api_key if api_key is not None else self.api_key).strip()
        return key or "None"

    def get_client(self, api_key: Optional[str] = None) -> genai.Client:
        target_key = self._get_target_key(api_key)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            if loop not in self._loop_client_pools:
                self._loop_client_pools[loop] = {}
            pool = self._loop_client_pools[loop]
            if target_key not in pool:
                pool[target_key] = genai.Client(api_key=target_key)
            return pool[target_key]
        else:
            if target_key not in self._sync_client_pool:
                self._sync_client_pool[target_key] = genai.Client(api_key=target_key)
            return self._sync_client_pool[target_key]

    def refresh_client(self, api_key: Optional[str] = None) -> genai.Client:
        target_key = self._get_target_key(api_key)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        new_client = genai.Client(api_key=target_key)
        if loop is not None:
            if loop not in self._loop_client_pools:
                self._loop_client_pools[loop] = {}
            self._loop_client_pools[loop][target_key] = new_client
        else:
            self._sync_client_pool[target_key] = new_client
        return new_client

    def get_raw_client(self, api_key: Optional[str] = None) -> Any:
        return self.get_client(api_key)

    def list_models(self, api_key: Optional[str] = None) -> List[str]:
        client = self.get_client(api_key)
        models = client.models.list()
        model_names = []
        for model in models:
            name = model.name
            if not name:
                continue
            if name.startswith("models/"):
                name = name.replace("models/", "", 1)
            m = name.lower()
            if not (m.startswith("gemini") or m.startswith("gemma")):
                continue
            exclude_keywords = [
                "embedding", "robotics", "tts", "audio", "image",
                "omni", "computer-use", "customtools", "live", "transcribe", "nano",
                "3.1-flash-lite-preview", "3-pro-preview", "3.7-flash", "2.5", "decision"
            ]
            if any(keyword in m for keyword in exclude_keywords):
                continue
            supported_methods = getattr(model, "supported_generation_methods", None)
            if supported_methods and "generateContent" not in supported_methods:
                continue
            model_names.append(name)
        try:
            model_names.insert(0, "gemini-3-flash-preview")
            model_names.remove("gemini-3.5-flash")
        except Exception:
            pass
        return sorted(set(model_names))

    async def send_text(self, message: str, setting: Optional[Dict[str, Any]] = None) -> AiResponse:
        setting = setting or {}
        cur_used_key = setting.get("api_key", self.api_key)
        client = self.get_client(cur_used_key)

        model_name = setting.get("model_name", "gemini-3.5-flash-lite")
        system_instruction = setting.get("system_instruction")
        temperature = setting.get("temperature", 0.2)
        top_p = setting.get("top_p", 0.8)
        safety_settings = setting.get("safety_settings")
        thinking_budget = setting.get("thinking_budget")

        config_params = {
            "temperature": temperature,
            "top_p": top_p
        }
        if system_instruction:
            config_params["system_instruction"] = system_instruction
        if safety_settings:
            config_params["safety_settings"] = safety_settings

        if thinking_budget is not None:
            thinking_cfg = build_thinking_config(thinking_budget, model_name=model_name)
            if thinking_cfg is not None:
                config_params["thinking_config"] = thinking_cfg

        config_obj = types.GenerateContentConfig(**config_params)

        response = await client.aio.models.generate_content(
            model=model_name,
            contents=message,
            config=config_obj
        )

        res_text = response.text if response and response.text else ""
        return AiResponse(text=res_text, raw_response=response)