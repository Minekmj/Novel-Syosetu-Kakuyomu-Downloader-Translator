import inspect
import re
from typing import Any, Dict, Optional

from playground_on_python import PlayGroundConfig, PlayGroundOptions


def supports_param(fn: Any, param_name: str) -> bool:
    try:
        sig = inspect.signature(fn)
        return param_name in sig.parameters
    except Exception:
        return False


def strip_playground_prefix(model_name: str) -> str:
    name = (model_name or "").strip()
    for prefix in ("playground/", "playground:", "playground-", "pg/", "pg:"):
        if name.lower().startswith(prefix):
            return name[len(prefix):].strip()
    return name


def build_playground_thinking(thinking_val: Any) -> Optional[Any]:
    if thinking_val is None:
        return None
    val = str(thinking_val).strip().upper()
    if val in ("기본값", "NONE", "", "DEFAULT"):
        return None
    level_map = {
        "EXTRAHIGH": PlayGroundOptions.Thinking.EXTRAHIGH,
        "XHIGH": PlayGroundOptions.Thinking.EXTRAHIGH,
        "MINIMAL": PlayGroundOptions.Thinking.MINIMAL,
        "LOW": PlayGroundOptions.Thinking.LOW,
        "MEDIUM": PlayGroundOptions.Thinking.MEDIUM,
        "HIGH": PlayGroundOptions.Thinking.HIGH,
        "ON": PlayGroundOptions.Thinking.ON,
        "OFF": PlayGroundOptions.Thinking.OFF,
    }
    for candidate in ("EXTRAHIGH", "XHIGH", "MINIMAL", "LOW", "MEDIUM", "HIGH", "ON", "OFF"):
        if candidate in val:
            return level_map[candidate]
    digits = re.findall(r"-?\d+", val)
    if digits:
        num = int(digits[0])
        if num <= 0:
            return PlayGroundOptions.Thinking.MINIMAL
        if num <= 1024:
            return PlayGroundOptions.Thinking.LOW
        if num <= 2048:
            return PlayGroundOptions.Thinking.MEDIUM
        return PlayGroundOptions.Thinking.HIGH
    return None


def resolve_model_kind(kind: Any) -> Any:
    if kind is None:
        return None
    k = str(kind).strip().lower()
    kind_map = {
        "all": PlayGroundOptions.ModelKind.ALL,
        "text": PlayGroundOptions.ModelKind.TEXT,
        "image": PlayGroundOptions.ModelKind.IMAGE,
        "video": PlayGroundOptions.ModelKind.VIDEO,
        "audio": PlayGroundOptions.ModelKind.AUDIO,
    }
    return kind_map.get(k, kind)


def resolve_verbose(verbose: Any) -> Any:
    if isinstance(verbose, bool):
        return PlayGroundOptions.Verbose.BASIC if verbose else PlayGroundOptions.Verbose.OFF
    if isinstance(verbose, int):
        if verbose <= 0:
            return PlayGroundOptions.Verbose.OFF
        if verbose == 1:
            return PlayGroundOptions.Verbose.BASIC
        return PlayGroundOptions.Verbose.DEBUG
    return verbose


def build_config(setting: Optional[Dict[str, Any]] = None) -> PlayGroundConfig:
    setting = setting or {}
    model_name = strip_playground_prefix(setting.get("model_name", "gemini-4-hydrogen")) or "gemini-4-hydrogen"
    thinking_level = build_playground_thinking(setting.get("thinking_budget"))
    cfg_kwargs: Dict[str, Any] = {
        "model": model_name,
        "allow_paid": bool(setting.get("allow_paid", False)),
        "new_chat": bool(setting.get("new_chat", True)),
        "raw_mode": bool(setting.get("raw_mode", True)),
    }
    if setting.get("system_instruction"):
        cfg_kwargs["system_input"] = setting["system_instruction"]
    if thinking_level is not None:
        cfg_kwargs["thinnk"] = thinking_level
    if "temperature" in setting:
        cfg_kwargs["temp"] = float(setting["temperature"])
    for opt_key in (
        "google_search",
        "url_context",
        "code_execution",
        "media_resolution",
        "max_output_tokens",
        "stop_sequences",
        "safety_settings",
        "include_thoughts",
    ):
        if opt_key in setting:
            cfg_kwargs[opt_key] = setting[opt_key]
    return PlayGroundConfig(**cfg_kwargs)


def build_send_kwargs(message: str, setting: Dict[str, Any]) -> Dict[str, Any]:
    model_name = strip_playground_prefix(setting.get("model_name", "gemini-4-hydrogen")) or "gemini-4-hydrogen"
    thinking_level = build_playground_thinking(setting.get("thinking_budget"))
    send_kwargs: Dict[str, Any] = {
        "text": message,
        "model": model_name,
        "new_chat": bool(setting.get("new_chat", True)),
        "raw_mode": bool(setting.get("raw_mode", True)),
        "allow_paid": bool(setting.get("allow_paid", False)),
    }
    if setting.get("system_instruction"):
        send_kwargs["system_input"] = setting["system_instruction"]
    if thinking_level is not None:
        send_kwargs["thinnk"] = thinking_level
    if "temperature" in setting:
        send_kwargs["temp"] = float(setting["temperature"])
    for opt_key in (
        "google_search",
        "url_context",
        "code_execution",
        "media_resolution",
        "max_output_tokens",
        "stop_sequences",
        "safety_settings",
        "include_thoughts",
        "media",
    ):
        if opt_key in setting:
            send_kwargs[opt_key] = setting[opt_key]
    return send_kwargs
