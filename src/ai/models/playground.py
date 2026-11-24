import asyncio
import atexit
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.ai.registry import register_ai
from src.ai.targets import AiTarget
from .base import BaseAiModel, AiResponse
from src.system.config import DATA_FOLDER

from playground_on_python import PlayGround
try:
    from playground_on_python import PlayGroundPool
except ImportError:
    PlayGroundPool = None
    
import shutil


def _strip_playground_prefix(model_name: str) -> str:
    name = (model_name or "").strip()
    for prefix in ("playground/", "playground:", "playground-", "pg/", "pg:"):
        if name.lower().startswith(prefix):
            return name[len(prefix):].strip()
    return name


def build_playground_thinking(thinking_val: Any) -> Optional[str]:
    if thinking_val is None:
        return None
    val = str(thinking_val).strip().upper()
    if val in ("기본값", "NONE", "", "DEFAULT"):
        return None
    level_map = {"MINIMAL": "Minimal", "LOW": "Low", "MEDIUM": "Medium", "HIGH": "High", "XHIGH": "XHigh"}
    for candidate in ("XHIGH", "MINIMAL", "LOW", "MEDIUM", "HIGH"):
        if candidate in val:
            return level_map[candidate]
    digits = re.findall(r"-?\d+", val)
    if digits:
        num = int(digits[0])
        if num <= 0:
            return "Minimal"
        if num <= 1024:
            return "Low"
        if num <= 2048:
            return "Medium"
        return "High"
    return None


@register_ai(
    target=AiTarget.PLAYGROUND,
    name="Playground",
    default_model="gemini-4-hydrogen",
    popular_models=[
        "gemini-4-hydrogen",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
    ],
    patterns=["playground/", "playground:", "playground-", "pg/", "pg:"],
    matcher=lambda m: (
        m.startswith(("playground/", "playground:", "playground-", "pg/", "pg:"))
        or "playground" in m.lower()
    ),
    default_config={
        "rpm": 10,
        "temperature": 0.1,
        "concurrency": 4,
        "br_start": 0,
        "isno_x": False,
        "thinking_budget": "기본값",
    },
)
class PlaygroundModel(BaseAiModel):
    _client_pool: Dict[str, Any] = {}
    _pg_pools: Dict[str, Dict[str, Any]] = {}
    _locks: Dict[str, threading.Lock] = {}
    _pool_lock = threading.Lock()
    _verified_profiles = set()
    _atexit_registered = False

    def __init__(self, api_key: str = ""):
        super().__init__(api_key)
        with PlaygroundModel._pool_lock:
            if not PlaygroundModel._atexit_registered:
                atexit.register(PlaygroundModel._close_all_shared)
                PlaygroundModel._atexit_registered = True

    @classmethod
    def _close_all_shared(cls) -> None:
        with cls._pool_lock:
            clients = list(cls._client_pool.values())
            pools = [e.get("pool") for e in cls._pg_pools.values()]
            cls._client_pool.clear()
            cls._pg_pools.clear()
        for obj in clients + pools:
            cls._close_obj(obj)

    @staticmethod
    def _close_obj(obj: Any) -> None:
        if obj is None:
            return
        try:
            obj.close()
        except Exception:
            pass

    @staticmethod
    def _is_non_profile_secret(val: str) -> bool:
        if not val:
            return False
        if val.startswith(("AIza", "AQ.", "sk-", "gsk_", "xai-", "http://", "https://")):
            return True
        return len(val) > 40 or any(ch in val for ch in ('/', '\\', ':', '*', '?', '"', '<', '>', '|'))

    def _get_profile_key(self, api_key: Optional[str] = None) -> str:
        key = (api_key if api_key is not None else self.api_key).strip()
        if self._is_non_profile_secret(key):
            fallback = (self.api_key or "").strip()
            key = "" if self._is_non_profile_secret(fallback) else fallback
        return "default" if (not key or key.lower() == "none") else key

    def _get_save_dir(self) -> Path:
        save_dir = (Path(str(DATA_FOLDER)) / "playground").resolve()
        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir

    def _get_profile_lock(self, profile_key: str) -> threading.Lock:
        with PlaygroundModel._pool_lock:
            if profile_key not in PlaygroundModel._locks:
                PlaygroundModel._locks[profile_key] = threading.Lock()
            return PlaygroundModel._locks[profile_key]

    @staticmethod
    def _is_login_error(err: Exception) -> bool:
        msg = str(err).lower()
        return any(
            k in msg
            for k in (
                "login",
                "로그인",
                "accounts.google",
                "세션",
                "만료",
                "expired",
                "not logged in",
                "unauthorized",
                "setting(first=true",
            )
        )

    def _drop_client(self, profile_key: str) -> None:
        with PlaygroundModel._pool_lock:
            dead_pg = PlaygroundModel._client_pool.pop(profile_key, None)
            dead_pool = PlaygroundModel._pg_pools.pop(profile_key, None)
        self._close_obj(dead_pg)
        if dead_pool is not None:
            self._close_obj(dead_pool.get("pool"))

    def get_client(self, api_key: Optional[str] = None, verbose: bool = False) -> Any:
        profile_key = self._get_profile_key(api_key)
        with PlaygroundModel._pool_lock:
            pg = PlaygroundModel._client_pool.get(profile_key)
        if pg is not None:
            return pg

        lock = self._get_profile_lock(profile_key)
        with lock:
            with PlaygroundModel._pool_lock:
                pg = PlaygroundModel._client_pool.get(profile_key)
                if pg is not None:
                    return pg
                dead_pool = PlaygroundModel._pg_pools.pop(profile_key, None)
            if dead_pool is not None:
                self._close_obj(dead_pool.get("pool"))

            pg = PlayGround(
                profile_name=profile_key,
                base_dir=self._get_save_dir(),
                encrypt=False,
                verbose=verbose,
            )
            try:
                pg.connect(backup=True, headless=True, auto_login=False)
            except Exception as err:
                self._close_obj(pg)
                if self._is_login_error(err):
                    raise RuntimeError(
                        "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                    ) from err
                raise
            with PlaygroundModel._pool_lock:
                PlaygroundModel._client_pool[profile_key] = pg
            return pg

    def _get_pg_pool(self, profile_key: str, count: int, verbose: bool = False) -> Any:
        if PlayGroundPool is None:
            raise RuntimeError("PlayGroundPool을 사용할 수 없습니다. playground_on_python 버전을 확인하세요.")
        target_count = max(1, int(count))
        with PlaygroundModel._pool_lock:
            existing = PlaygroundModel._pg_pools.get(profile_key)
            if existing is not None and existing.get("count") == target_count:
                return existing["pool"]

        lock = self._get_profile_lock(profile_key)
        with lock:
            with PlaygroundModel._pool_lock:
                existing = PlaygroundModel._pg_pools.get(profile_key)
                if existing is not None and existing.get("count") == target_count:
                    return existing["pool"]
                if existing is not None:
                    PlaygroundModel._pg_pools.pop(profile_key, None)
                dead_single = PlaygroundModel._client_pool.pop(profile_key, None)
            if existing is not None:
                self._close_obj(existing.get("pool"))
            self._close_obj(dead_single)

            pool = PlayGroundPool(
                count=target_count,
                base_profile=profile_key,
                base_dir=self._get_save_dir(),
                headless=True,
                backup=True,
                auto_login=False,
                encrypt=False,
                verbose=verbose,
            )
            try:
                pool.start(parallel=True, new_chat=True)
            except Exception as err:
                self._close_obj(pool)
                if self._is_login_error(err):
                    raise RuntimeError(
                        "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                    ) from err
                raise
            with PlaygroundModel._pool_lock:
                PlaygroundModel._pg_pools[profile_key] = {"count": target_count, "pool": pool}
            return pool

    def refresh_client(self, api_key: Optional[str] = None) -> Any:
        profile_key = self._get_profile_key(api_key)
        self._drop_client(profile_key)
        return self.get_client(api_key)

    def close(self, api_key: Optional[str] = None) -> None:
        if api_key is None:
            self._close_all_shared()
            return
        self._drop_client(self._get_profile_key(api_key))

    def get_raw_client(self, api_key: Optional[str] = None) -> Any:
        return self.get_client(api_key)
    
    def SetLogin(self, api_key: Optional[str] = None, force: bool = False, verbose: bool = True) -> bool:
        profile_key = self._get_profile_key(api_key)
        lock = self._get_profile_lock(profile_key)
        with lock:
            self._drop_client(profile_key)
            PlaygroundModel._verified_profiles.discard(profile_key)

            save_dir = self._get_save_dir()
            for target_dir in [save_dir / profile_key, *save_dir.glob(f"{profile_key}_worker_*")]:
                if target_dir.exists():
                    shutil.rmtree(target_dir, ignore_errors=True)

            pg = PlayGround(
                profile_name=profile_key,
                base_dir=save_dir,
                encrypt=False,
                verbose=verbose,
            )
            try:
                pg.setting(first=True, backup=True)
            finally:
                self._close_obj(pg)

            PlaygroundModel._verified_profiles.add(profile_key)
            return True
        
    async def set_login_async(self, api_key: Optional[str] = None, force: bool = False, verbose: bool = True) -> bool:
        return await asyncio.to_thread(self.SetLogin, api_key=api_key, force=force, verbose=verbose)

    def check_login(self, api_key: Optional[str] = None, verify: bool = False) -> bool:
        profile_key = self._get_profile_key(api_key)
        if not verify:
            with PlaygroundModel._pool_lock:
                if profile_key in PlaygroundModel._client_pool or profile_key in PlaygroundModel._pg_pools:
                    return True
            if profile_key in PlaygroundModel._verified_profiles:
                return True
            pg = PlayGround(
                profile_name=profile_key,
                base_dir=self._get_save_dir(),
                encrypt=False,
                verbose=False,
            )
            return bool(pg.storage.has_any_saved_session())

        lock = self._get_profile_lock(profile_key)
        with lock:
            pg = PlayGround(
                profile_name=profile_key,
                base_dir=self._get_save_dir(),
                encrypt=False,
                verbose=False,
            )
            try:
                ok = bool(pg.is_logged_in(backup=True))
                if ok:
                    PlaygroundModel._verified_profiles.add(profile_key)
                else:
                    PlaygroundModel._verified_profiles.discard(profile_key)
                return ok
            except Exception:
                PlaygroundModel._verified_profiles.discard(profile_key)
                return False
            finally:
                self._close_obj(pg)

    def list_models_detail(
        self,
        api_key: Optional[str] = None,
        kind: Optional[str] = None,
        paid: Optional[bool] = False,
    ) -> List[Dict[str, Any]]:
        profile_key = self._get_profile_key(api_key)
        kwargs: Dict[str, Any] = {}
        if kind is not None:
            kwargs["kind"] = kind
        if paid is not None:
            kwargs["paid"] = paid

        with PlaygroundModel._pool_lock:
            pool_entry = PlaygroundModel._pg_pools.get(profile_key)
            active_pool = pool_entry.get("pool") if pool_entry else None

        if active_pool is not None:
            with active_pool.acquire() as pg:
                raw_models = pg.list_models(**kwargs)
        else:
            pg = self.get_client(api_key)
            try:
                raw_models = pg.list_models(**kwargs)
            except Exception as err:
                if self._is_login_error(err):
                    self._drop_client(profile_key)
                    raise RuntimeError(
                        "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                    ) from err
                if self.is_connection_error(err):
                    self._drop_client(profile_key)
                    raw_models = self.get_client(api_key).list_models(**kwargs)
                else:
                    raise

        return [item if isinstance(item, dict) else {"id": str(item)} for item in (raw_models or [])]

    def list_models(
        self,
        api_key: Optional[str] = None,
        kind: Optional[str] = "text",
        paid: Optional[bool] = False,
    ) -> List[str]:
        raw_items = self.list_models_detail(api_key=api_key, kind=kind, paid=paid)
        exclude_keywords = ("imagen", "veo", "lyria", "tts", "audio", "embedding", "robotics", "decision", "transcribe")
        model_names: List[str] = []
        for item in raw_items:
            mid = str(item.get("id") or item.get("name") or "").strip()
            if not mid:
                continue
            item_kind = str(item.get("kind") or item.get("type") or "").strip().lower()
            if kind == "text":
                if item_kind and item_kind not in ("text", "chat", "llm"):
                    continue
                if any(k in mid.lower() for k in exclude_keywords):
                    continue
            model_names.append(mid)
        return sorted(set(model_names))

    async def send_text(self, message: str, setting: Optional[Dict[str, Any]] = None) -> AiResponse:
        setting = setting or {}
        cur_used_key = setting.get("api_key", self.api_key)
        profile_key = self._get_profile_key(cur_used_key)
        model_name = _strip_playground_prefix(setting.get("model_name", "gemini-4-hydrogen")) or "gemini-4-hydrogen"
        thinking_level = build_playground_thinking(setting.get("thinking_budget"))
        verbose = bool(setting.get("verbose", False))
        try:
            concurrency = max(1, int(setting.get("concurrency", 1)))
        except (TypeError, ValueError):
            concurrency = 1

        send_kwargs: Dict[str, Any] = {
            "text": message,
            "model": model_name,
            "new_chat": bool(setting.get("new_chat", True)),
        }
        if setting.get("system_instruction"):
            send_kwargs["system_input"] = setting["system_instruction"]
        if thinking_level is not None:
            send_kwargs["thinnk"] = thinking_level
        if "temperature" in setting:
            send_kwargs["temp"] = setting["temperature"]
        for opt_key in ("top_p", "google_search", "media", "allow_paid"):
            if opt_key in setting:
                send_kwargs[opt_key] = setting[opt_key]

        def _call() -> Any:
            if concurrency > 1 and PlayGroundPool is not None:
                pool = self._get_pg_pool(profile_key, concurrency, verbose=verbose)
                try:
                    with pool.acquire() as pg:
                        return pg.send(**send_kwargs)
                except Exception as err:
                    if self._is_login_error(err):
                        self._drop_client(profile_key)
                        raise RuntimeError(
                            "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                        ) from err
                    if self.is_connection_error(err):
                        self._drop_client(profile_key)
                        pool = self._get_pg_pool(profile_key, concurrency, verbose=verbose)
                        with pool.acquire() as pg:
                            return pg.send(**send_kwargs)
                    raise

            lock = self._get_profile_lock(profile_key)
            with lock:
                try:
                    return self.get_client(cur_used_key, verbose=verbose).send(**send_kwargs)
                except Exception as err:
                    if self._is_login_error(err):
                        self._drop_client(profile_key)
                        raise RuntimeError(
                            "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                        ) from err
                    if self.is_connection_error(err):
                        self._drop_client(profile_key)
                        return self.get_client(cur_used_key, verbose=verbose).send(**send_kwargs)
                    raise

        raw_reply = await asyncio.to_thread(_call)
        if isinstance(raw_reply, str):
            res_text = raw_reply
        elif isinstance(raw_reply, dict):
            res_text = str(raw_reply.get("text") or raw_reply.get("response") or "")
        else:
            res_text = str(getattr(raw_reply, "text", None) or raw_reply or "")
        return AiResponse(text=res_text, raw_response=raw_reply)

    def is_rate_limit_error(self, err: Exception) -> bool:
        if super().is_rate_limit_error(err):
            return True
        msg = str(err).lower()
        return any(k in msg for k in ("too many requests", "limit reached"))

    def is_connection_error(self, err: Exception) -> bool:
        if super().is_connection_error(err):
            return True
        msg = str(err).lower()
        return any(
            k in msg
            for k in (
                "invalid session id",
                "disconnected",
                "chrome not reachable",
                "no such window",
                "connection refused",
                "unable to connect",
                "max retries exceeded",
                "not connected to devtools",
                "browser has closed",
                "session not created",
                "chrome failed to start",
            )
        )