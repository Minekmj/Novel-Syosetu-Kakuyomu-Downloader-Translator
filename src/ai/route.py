import asyncio
from typing import Any, Dict, List, Optional, Tuple

from .registry import AiRegistry, register_ai
from .targets import AiTarget
from .models.base import BaseAiModel, AiResponse
from . import models


class _AiRouteMeta(type):
    @property
    def DEFAULT_TARGET(cls) -> int:
        return AiRegistry.get_default_target()

    @property
    def DEFAULT_MODEL(cls) -> str:
        info = AiRegistry.get(cls.DEFAULT_TARGET)
        return info.default_model if info else "gemini-3.5-flash-lite"

    @property
    def TARGET_NAMES(cls) -> Dict[int, str]:
        return {t: info.name for t, info in AiRegistry.get_all().items()}

    @property
    def POPULAR_MODELS_BY_TARGET(cls) -> Dict[int, List[str]]:
        return {t: info.popular_models for t, info in AiRegistry.get_all().items()}

    @property
    def DEFAULT_CONFIGS_BY_TARGET(cls) -> Dict[int, Dict[str, Any]]:
        return {t: info.default_config for t, info in AiRegistry.get_all().items()}


class AiRoute(metaclass=_AiRouteMeta):

    @classmethod
    def fetch_models(cls, api_key: str = "", target: Optional[int] = None) -> List[str]:
        t = cls.DEFAULT_TARGET if target is None else int(target)
        route = cls(ai_target=t, api=api_key)
        adapter = route.get_model(t)
        if hasattr(adapter, "list_models"):
            try:
                models_list = adapter.list_models(api_key)
                if models_list:
                    return models_list
            except Exception:
                pass
        return cls.get_popular_models(t)

    @classmethod
    def get_storage_keys(cls, target: int) -> Tuple[str, str, str]:
        t = int(target)
        if t == cls.DEFAULT_TARGET:
            return "api", "api_keys", "api_index"
        name = cls.get_target_name(t).lower()
        return f"api_{name}", f"api_keys_{name}", f"api_index_{name}"

    @classmethod
    def detect_target(cls, model_name: str) -> int:
        return AiRegistry.detect_target(model_name)

    @classmethod
    def get_target_name(cls, target: int) -> str:
        info = AiRegistry.get(target)
        return info.name if info else "AI"

    @classmethod
    def get_default_model(cls, target: Optional[int] = None) -> str:
        t = cls.DEFAULT_TARGET if target is None else int(target)
        info = AiRegistry.get(t)
        return info.default_model if info else cls.DEFAULT_MODEL

    @classmethod
    def get_default_config(cls, target: Optional[int] = None) -> dict:
        t = cls.DEFAULT_TARGET if target is None else int(target)
        info = AiRegistry.get(t)
        if info and info.default_config:
            return dict(info.default_config)
        return {
            "rpm": 15,
            "temperature": 0.1,
            "concurrency": 4,
            "br_start": 0,
            "isno_x": False,
            "thinking_budget": "기본값"
        }

    @classmethod
    def get_popular_models(cls, target: Optional[int] = None) -> List[str]:
        if target is not None:
            info = AiRegistry.get(int(target))
            return list(info.popular_models) if info else []

        merged = []
        for info in AiRegistry.get_all().values():
            for m in info.popular_models:
                if m not in merged:
                    merged.append(m)
        return merged

    def __init__(self, ai_target: Optional[int] = None, api: str = ""):
        self.ai_target = self.DEFAULT_TARGET if ai_target is None else int(ai_target)
        self.api = api.strip() if api else ""
        self._models: Dict[int, BaseAiModel] = {}
        self._init_target(self.ai_target)

    def _init_target(self, target: int):
        target = int(target)
        if target not in self._models:
            info = AiRegistry.get(target)
            if info:
                self._models[target] = info.model_class(api_key=self.api)
            else:
                def_info = AiRegistry.get(self.DEFAULT_TARGET)
                if def_info:
                    self._models[self.DEFAULT_TARGET] = def_info.model_class(api_key=self.api)

    def set_target(self, ai_target: int):
        self.ai_target = int(ai_target)
        self._init_target(self.ai_target)
        if self.api and self.ai_target in self._models:
            self._models[self.ai_target].set_api(self.api)

    def set_api(self, api: str):
        self.api = api.strip() if api else ""
        for model in self._models.values():
            model.set_api(self.api)

    def get_model(self, target: Optional[int] = None) -> BaseAiModel:
        t = self.ai_target if target is None else int(target)
        self._init_target(t)
        return self._models[t]

    def refresh_client(self, api_key: Optional[str] = None):
        return self.get_model().refresh_client(api_key)

    def get_raw_client(self, api_key: Optional[str] = None) -> Any:
        return self.get_model().get_raw_client(api_key)

    async def send_text(self, message: str, setting: Optional[Dict[str, Any]] = None) -> AiResponse:
        setting = setting or {}
        model_name = setting.get("model_name", self.get_default_model(self.ai_target))
        target = setting.get("ai_target")
        if target is None:
            target = self.detect_target(model_name)

        model = self.get_model(target)
        return await model.send_text(message, setting)

    def send_text_sync(self, message: str, setting: Optional[Dict[str, Any]] = None) -> AiResponse:
        return asyncio.run(self.send_text(message, setting))

    def is_rate_limit_error(self, err: Exception) -> bool:
        return self.get_model().is_rate_limit_error(err)

    def extract_retry_delay(self, err: Exception) -> float:
        return self.get_model().extract_retry_delay(err)

    def is_connection_error(self, err: Exception) -> bool:
        return self.get_model().is_connection_error(err)