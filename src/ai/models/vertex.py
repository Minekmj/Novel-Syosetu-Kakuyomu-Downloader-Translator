import asyncio
import json
import os
import weakref
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types
from google.oauth2 import service_account

from src.ai.registry import AiRegistry, register_ai
from src.ai.targets import AiTarget
from .base import BaseAiModel, AiResponse
from .gemini import build_thinking_config

VERTEX_SCOPES = [
    "https://www.googleapis.com/auth/generative-language",
    "https://www.googleapis.com/auth/cloud-platform",
]


def parse_vertex_credentials(target_key: str) -> Tuple[Optional[Any], Optional[str], Optional[str]]:
    raw = (target_key or "").strip().strip("'\"")
    credentials = None
    project_id = None
    direct_api_key = None

    if raw.startswith("{") and raw.endswith("}"):
        try:
            info = json.loads(raw)
            if isinstance(info, dict):
                project_id = info.get("project_id")
                credentials = service_account.Credentials.from_service_account_info(
                    info, scopes=VERTEX_SCOPES
                )
                return credentials, project_id, None
        except Exception:
            pass

    if raw and os.path.isfile(raw):
        try:
            with open(raw, "r", encoding="utf-8") as f:
                info = json.load(f)
            if isinstance(info, dict):
                project_id = info.get("project_id")
            credentials = service_account.Credentials.from_service_account_file(
                raw, scopes=VERTEX_SCOPES
            )
            return credentials, project_id, None
        except Exception:
            pass

    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip().strip("'\"")
    if env_path and os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                info = json.load(f)
            if isinstance(info, dict):
                project_id = info.get("project_id")
            credentials = service_account.Credentials.from_service_account_file(
                env_path, scopes=VERTEX_SCOPES
            )
            return credentials, project_id, None
        except Exception:
            pass

    if raw.startswith("AIza"):
        direct_api_key = raw
    elif raw and not raw.endswith(".json") and " " not in raw:
        project_id = raw

    if not project_id:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")

    return credentials, project_id, direct_api_key


@register_ai(
    target=AiTarget.VERTEX,
    name="Vertex AI",
    default_model="gemini-3.5-flash-lite",
    popular_models=[
        "gemini-3.5-flash-lite",
    ],
    patterns=["vertex/", "vertex-", "vertex:"],
    matcher=lambda m: "vertex" in m.lower(),
    default_config={
        "rpm": 30,
        "temperature": 0.1,
        "concurrency": 4,
        "br_start": 0,
        "isno_x": False,
        "thinking_budget": "기본값",
        "location": "us-central1"
    }
)
class VertexModel(BaseAiModel):
    def __init__(self, api_key: str = ""):
        super().__init__(api_key)
        self._loop_client_pools = weakref.WeakKeyDictionary()
        self._sync_client_pool = {}

    def _get_target_key(self, api_key: Optional[str] = None) -> str:
        key = (api_key if api_key is not None else self.api_key).strip()
        return key or "None"

    def _create_client(
        self,
        api_key: Optional[str] = None,
        location: Optional[str] = None,
        project: Optional[str] = None
    ) -> genai.Client:
        target_key = self._get_target_key(api_key)
        credentials, parsed_project, direct_key = parse_vertex_credentials(target_key)

        loc = location or os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1"
        proj = project or parsed_project

        kwargs: Dict[str, Any] = {
            "vertexai": True,
            "location": loc,
        }
        if proj:
            kwargs["project"] = proj
        if credentials:
            kwargs["credentials"] = credentials
        if direct_key:
            kwargs["api_key"] = direct_key

        return genai.Client(**kwargs)

    def get_client(
        self,
        api_key: Optional[str] = None,
        location: Optional[str] = None,
        project: Optional[str] = None
    ) -> genai.Client:
        target_key = self._get_target_key(api_key)
        loc = location or os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1"
        cache_key = (target_key, loc, project or "")

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            if loop not in self._loop_client_pools:
                self._loop_client_pools[loop] = {}
            pool = self._loop_client_pools[loop]
            if cache_key not in pool:
                pool[cache_key] = self._create_client(api_key, location=loc, project=project)
            return pool[cache_key]
        else:
            if cache_key not in self._sync_client_pool:
                self._sync_client_pool[cache_key] = self._create_client(api_key, location=loc, project=project)
            return self._sync_client_pool[cache_key]

    def refresh_client(
        self,
        api_key: Optional[str] = None,
        location: Optional[str] = None,
        project: Optional[str] = None
    ) -> genai.Client:
        target_key = self._get_target_key(api_key)
        loc = location or os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1"
        cache_key = (target_key, loc, project or "")

        new_client = self._create_client(api_key, location=loc, project=project)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            if loop not in self._loop_client_pools:
                self._loop_client_pools[loop] = {}
            self._loop_client_pools[loop][cache_key] = new_client
        else:
            self._sync_client_pool[cache_key] = new_client
        return new_client

    def get_raw_client(self, api_key: Optional[str] = None) -> Any:
        return self.get_client(api_key)

    def list_models(self, api_key: Optional[str] = None) -> List[str]:
        try:
            client = self.get_client(api_key)
            models = client.models.list()
            model_names = []
            for model in models:
                name = getattr(model, "name", "")
                if not name:
                    continue
                if name.startswith("publishers/google/models/"):
                    name = name.replace("publishers/google/models/", "", 1)
                elif name.startswith("models/"):
                    name = name.replace("models/", "", 1)

                m = name.lower()
                if not (m.startswith("gemini") or m.startswith("gemma")):
                    continue
                exclude_keywords = [
                    "embedding", "robotics", "tts", "audio", "image",
                    "omni", "computer-use", "customtools", "live", "transcribe", "nano"
                ]
                if any(keyword in m for keyword in exclude_keywords):
                    continue
                model_names.append(name)

            if model_names:
                return sorted(set(model_names))
        except Exception:
            pass

        info = AiRegistry.get(AiTarget.VERTEX)
        return list(info.popular_models) if info else ["gemini-3.5-flash-lite"]

    async def send_text(self, message: str, setting: Optional[Dict[str, Any]] = None) -> AiResponse:
        setting = setting or {}
        cur_used_key = setting.get("api_key", self.api_key)
        location = setting.get("location")
        project = setting.get("project") or setting.get("project_id")

        client = self.get_client(api_key=cur_used_key, location=location, project=project)

        model_name = setting.get("model_name", "gemini-2.5-flash")
        for prefix in ("vertex/", "vertex:", "vertex-"):
            if model_name.lower().startswith(prefix):
                model_name = model_name[len(prefix):]
                break

        system_instruction = setting.get("system_instruction")
        temperature = setting.get("temperature", 0.1)
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