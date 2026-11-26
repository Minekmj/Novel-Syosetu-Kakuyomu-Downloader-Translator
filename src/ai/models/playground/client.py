import asyncio
import atexit
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from playground_on_python import PlayGround, PlayGroundConfig, PlayGroundOptions
try:
    from playground_on_python import PlayGroundPool
except ImportError:
    PlayGroundPool = None

from src.ai.registry import register_ai
from src.ai.targets import AiTarget
from ..base import AiResponse, BaseAiModel
from .options import (
    build_config,
    build_send_kwargs,
    resolve_model_kind,
    resolve_verbose,
    supports_param,
)
from .process_guard import (
    close_obj,
    collect_pids_from_obj,
    is_pid_alive,
    kill_pid,
    kill_processes_by_markers,
)
from .storage import (
    cleanup_legacy_profiles,
    cleanup_runtime_profiles,
    cleanup_stale_temp_profiles,
    clone_profile_json,
    ensure_profile_exists,
    get_key_path,
    get_save_dir,
    next_runtime_profile,
)


@register_ai(
    target=AiTarget.PLAYGROUND,
    name="Playground",
    default_model="gemini-4-hydrogen",
    popular_models=[
        "gemini-4-hydrogen",
        "gemini-3.5-flash-lite",
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
    _locks: Dict[str, threading.RLock] = {}
    _pool_lock = threading.Lock()
    _verified_profiles: Set[str] = set()
    _scope_pids: Dict[str, Set[int]] = {}
    _scope_profiles: Dict[str, Set[str]] = {}
    _stopped_sessions: Set[str] = set()
    _atexit_registered = False
    _stale_cleaned = False

    def __init__(self, api_key: str = ""):
        super().__init__(api_key)
        with PlaygroundModel._pool_lock:
            if not PlaygroundModel._atexit_registered:
                atexit.register(PlaygroundModel.force_stop_all)
                PlaygroundModel._atexit_registered = True
            if not PlaygroundModel._stale_cleaned:
                PlaygroundModel._stale_cleaned = True
                cleanup_legacy_profiles()
                threading.Thread(target=cleanup_stale_temp_profiles, daemon=True).start()

    @classmethod
    def _get_save_dir_cls(cls) -> Path:
        return get_save_dir()

    def _get_save_dir(self) -> Path:
        return get_save_dir()

    @classmethod
    def _close_all_shared(cls, force: bool = False) -> None:
        with cls._pool_lock:
            clients = list(cls._client_pool.values())
            pools = [e.get("pool") for e in cls._pg_pools.values()]
            all_pids: Set[int] = set()
            for pset in cls._scope_pids.values():
                all_pids.update(pset)
            all_profiles: Set[str] = set()
            for mset in cls._scope_profiles.values():
                all_profiles.update(mset)
            cls._client_pool.clear()
            cls._pg_pools.clear()
            cls._scope_pids.clear()
            cls._scope_profiles.clear()

        for obj in clients + pools:
            all_pids.update(collect_pids_from_obj(obj))
            close_obj(obj, force=force)

        if force:
            for pid in all_pids:
                kill_pid(pid)
            kill_processes_by_markers(all_profiles)
        else:
            for pid in all_pids:
                if is_pid_alive(pid):
                    kill_pid(pid)
            kill_processes_by_markers(all_profiles)

        try:
            cleanup_runtime_profiles(get_save_dir(), all_profiles)
        except Exception:
            pass

    @classmethod
    def force_stop_all(cls) -> None:
        cls._close_all_shared(force=True)

    @classmethod
    def force_stop_session(cls, session_id: Optional[str]) -> None:
        if not session_id:
            cls.force_stop_all()
            return
        sid = str(session_id).strip()
        suffix = f"::{sid}"
        with cls._pool_lock:
            cls._stopped_sessions.add(sid)
            matching_keys = set()
            for d in (cls._client_pool, cls._pg_pools, cls._scope_pids, cls._scope_profiles):
                for k in d.keys():
                    if k.endswith(suffix):
                        matching_keys.add(k)
            objs = []
            pids: Set[int] = set()
            profiles: Set[str] = set()
            for k in matching_keys:
                c = cls._client_pool.pop(k, None)
                if c is not None:
                    objs.append(c)
                p = cls._pg_pools.pop(k, None)
                if p is not None and p.get("pool") is not None:
                    objs.append(p.get("pool"))
                pids.update(cls._scope_pids.pop(k, set()))
                profiles.update(cls._scope_profiles.pop(k, set()))

        for obj in objs:
            pids.update(collect_pids_from_obj(obj))
            close_obj(obj, force=True)
        for pid in pids:
            kill_pid(pid)
        kill_processes_by_markers(profiles)
        try:
            cleanup_runtime_profiles(get_save_dir(), profiles)
        except Exception:
            pass

    @classmethod
    def close_session(cls, session_id: Optional[str]) -> None:
        if not session_id:
            return
        sid = str(session_id).strip()
        suffix = f"::{sid}"
        with cls._pool_lock:
            cls._stopped_sessions.discard(sid)
            matching_keys = set()
            for d in (cls._client_pool, cls._pg_pools, cls._scope_pids, cls._scope_profiles):
                for k in d.keys():
                    if k.endswith(suffix):
                        matching_keys.add(k)
            objs = []
            pids: Set[int] = set()
            profiles: Set[str] = set()
            for k in matching_keys:
                c = cls._client_pool.pop(k, None)
                if c is not None:
                    objs.append(c)
                p = cls._pg_pools.pop(k, None)
                if p is not None and p.get("pool") is not None:
                    objs.append(p.get("pool"))
                pids.update(cls._scope_pids.pop(k, set()))
                profiles.update(cls._scope_profiles.pop(k, set()))

        for obj in objs:
            pids.update(collect_pids_from_obj(obj))
            close_obj(obj, force=False)
        for pid in pids:
            if is_pid_alive(pid):
                kill_pid(pid)
        kill_processes_by_markers(profiles)
        try:
            cleanup_runtime_profiles(get_save_dir(), profiles)
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

    @staticmethod
    def _get_scope_key(profile_key: str, session_id: Optional[str] = None) -> str:
        sid = (str(session_id).strip() if session_id else "") or "shared"
        return f"{profile_key}::{sid}"

    def _get_profile_lock(self, scope_key: str) -> threading.RLock:
        with PlaygroundModel._pool_lock:
            if scope_key not in PlaygroundModel._locks:
                PlaygroundModel._locks[scope_key] = threading.RLock()
            return PlaygroundModel._locks[scope_key]

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
                "loginmode",
                "setting(",
            )
        )

    def _drop_scope(self, scope_key: str, failed_obj: Any = None, force: bool = False) -> None:
        with PlaygroundModel._pool_lock:
            cur_pg = PlaygroundModel._client_pool.get(scope_key)
            cur_pool_entry = PlaygroundModel._pg_pools.get(scope_key)
            cur_pool = cur_pool_entry.get("pool") if cur_pool_entry else None
            if failed_obj is not None and cur_pg is not failed_obj and cur_pool is not failed_obj:
                return
            dead_pg = PlaygroundModel._client_pool.pop(scope_key, None)
            dead_pool = PlaygroundModel._pg_pools.pop(scope_key, None)
            pids = PlaygroundModel._scope_pids.pop(scope_key, set())
            profiles = PlaygroundModel._scope_profiles.pop(scope_key, set())

        close_obj(dead_pg, force=force, extra_pids=pids, markers=profiles)
        if dead_pool is not None:
            close_obj(dead_pool.get("pool"), force=force, extra_pids=pids, markers=profiles)
        cleanup_runtime_profiles(get_save_dir(), profiles)

    def _drop_client(self, profile_key: str, session_id: Optional[str] = None) -> None:
        if session_id is not None:
            self._drop_scope(self._get_scope_key(profile_key, session_id))
            return
        prefix = f"{profile_key}::"
        with PlaygroundModel._pool_lock:
            keys = [
                k for k in set(PlaygroundModel._client_pool.keys()) | set(PlaygroundModel._pg_pools.keys())
                if k.startswith(prefix)
            ]
        for k in keys:
            self._drop_scope(k)

    def _check_session_stopped(self, session_id: Optional[str]) -> None:
        if session_id:
            with PlaygroundModel._pool_lock:
                if str(session_id).strip() in PlaygroundModel._stopped_sessions:
                    raise RuntimeError("Playground 작업이 강제 중지되었습니다.")

    def _build_pg_init_kwargs(
        self,
        profile_name: str,
        save_dir: Path,
        verbose: Any = False,
        default_config: Optional[PlayGroundConfig] = None,
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "profile_name": profile_name,
            "base_dir": save_dir,
            "encrypt": True,
            "verbose": resolve_verbose(verbose),
        }
        if supports_param(PlayGround.__init__, "key_path"):
            kwargs["key_path"] = get_key_path()
        if supports_param(PlayGround.__init__, "wipe_runtime_profile"):
            kwargs["wipe_runtime_profile"] = True
        if default_config is not None and supports_param(PlayGround.__init__, "default_config"):
            kwargs["default_config"] = default_config
        return kwargs

    def get_client(
        self,
        api_key: Optional[str] = None,
        session_id: Optional[str] = None,
        verbose: Any = False,
        default_config: Optional[PlayGroundConfig] = None,
    ) -> Any:
        self._check_session_stopped(session_id)
        profile_key = self._get_profile_key(api_key)
        scope_key = self._get_scope_key(profile_key, session_id)
        with PlaygroundModel._pool_lock:
            pg = PlaygroundModel._client_pool.get(scope_key)
        if pg is not None:
            try:
                if hasattr(pg, "driver") and pg.driver:
                    _ = pg.driver.current_url
                    return pg
            except Exception:
                self._drop_scope(scope_key, failed_obj=pg)

        lock = self._get_profile_lock(scope_key)
        with lock:
            self._check_session_stopped(session_id)
            with PlaygroundModel._pool_lock:
                pg = PlaygroundModel._client_pool.get(scope_key)
                if pg is not None:
                    try:
                        if hasattr(pg, "driver") and pg.driver:
                            _ = pg.driver.current_url
                            return pg
                    except Exception:
                        dead_pg = PlaygroundModel._client_pool.pop(scope_key, None)
                        pids = PlaygroundModel._scope_pids.pop(scope_key, set())
                        profiles = PlaygroundModel._scope_profiles.pop(scope_key, set())
                    else:
                        dead_pg = None
                        pids = set()
                        profiles = set()
                else:
                    dead_pg = None
                    pids = set()
                    profiles = set()
                dead_pool = PlaygroundModel._pg_pools.pop(scope_key, None)
            if dead_pg is not None:
                close_obj(dead_pg, extra_pids=pids, markers=profiles)
                cleanup_runtime_profiles(get_save_dir(), profiles)
            if dead_pool is not None:
                close_obj(dead_pool.get("pool"))

            save_dir = get_save_dir()
            ensure_profile_exists(save_dir, profile_key)

            runtime_profile = next_runtime_profile(profile_key)
            clone_profile_json(save_dir, profile_key, runtime_profile)

            with PlaygroundModel._pool_lock:
                PlaygroundModel._scope_profiles.setdefault(scope_key, set()).add(runtime_profile)

            pg_kwargs = self._build_pg_init_kwargs(
                runtime_profile,
                save_dir,
                verbose=verbose,
                default_config=default_config,
            )
            pg = PlayGround(**pg_kwargs)

            connect_kwargs: Dict[str, Any] = {
                "backup": True,
                "headless": True,
            }
            if supports_param(pg.connect, "auto_login"):
                connect_kwargs["auto_login"] = False

            try:
                pg.connect(**connect_kwargs)
            except Exception as err:
                close_obj(pg, force=True, markers={runtime_profile})
                cleanup_runtime_profiles(save_dir, {runtime_profile})
                if self._is_login_error(err):
                    raise RuntimeError(
                        "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                    ) from err
                raise

            self._check_session_stopped(session_id)
            pids = collect_pids_from_obj(pg)
            with PlaygroundModel._pool_lock:
                PlaygroundModel._client_pool[scope_key] = pg
                PlaygroundModel._scope_pids.setdefault(scope_key, set()).update(pids)
            return pg

    def _get_pg_pool(
        self,
        profile_key: str,
        count: int,
        session_id: Optional[str] = None,
        verbose: Any = False,
        default_config: Optional[PlayGroundConfig] = None,
    ) -> Any:
        self._check_session_stopped(session_id)
        if PlayGroundPool is None:
            raise RuntimeError("PlayGroundPool을 사용할 수 없습니다. playground_on_python 버전을 확인하세요.")
        target_count = max(1, int(count))
        scope_key = self._get_scope_key(profile_key, session_id)
        with PlaygroundModel._pool_lock:
            existing = PlaygroundModel._pg_pools.get(scope_key)
            if existing is not None and existing.get("count") == target_count:
                return existing["pool"]

        lock = self._get_profile_lock(scope_key)
        with lock:
            self._check_session_stopped(session_id)
            with PlaygroundModel._pool_lock:
                existing = PlaygroundModel._pg_pools.get(scope_key)
                if existing is not None and existing.get("count") == target_count:
                    return existing["pool"]
                if existing is not None:
                    PlaygroundModel._pg_pools.pop(scope_key, None)
                dead_single = PlaygroundModel._client_pool.pop(scope_key, None)
                old_pids = PlaygroundModel._scope_pids.pop(scope_key, set())
                old_profiles = PlaygroundModel._scope_profiles.pop(scope_key, set())
            if existing is not None:
                close_obj(existing.get("pool"), extra_pids=old_pids, markers=old_profiles)
            if dead_single is not None:
                close_obj(dead_single, extra_pids=old_pids, markers=old_profiles)
            if old_profiles:
                cleanup_runtime_profiles(get_save_dir(), old_profiles)

            save_dir = get_save_dir()
            ensure_profile_exists(save_dir, profile_key)

            runtime_base = next_runtime_profile(profile_key)
            clone_profile_json(save_dir, profile_key, runtime_base)

            with PlaygroundModel._pool_lock:
                PlaygroundModel._scope_profiles.setdefault(scope_key, set()).add(runtime_base)

            pool_kwargs: Dict[str, Any] = {
                "count": target_count,
                "base_profile": runtime_base,
                "base_dir": save_dir,
                "encrypt": True,
                "verbose": resolve_verbose(verbose),
            }
            if supports_param(PlayGroundPool.__init__, "key_path"):
                pool_kwargs["key_path"] = get_key_path()
            if supports_param(PlayGroundPool.__init__, "wipe_runtime_profile"):
                pool_kwargs["wipe_runtime_profile"] = True
            if default_config is not None and supports_param(PlayGroundPool.__init__, "default_config"):
                pool_kwargs["default_config"] = default_config
            if supports_param(PlayGroundPool.__init__, "headless"):
                pool_kwargs["headless"] = True
            if supports_param(PlayGroundPool.__init__, "backup"):
                pool_kwargs["backup"] = True
            if supports_param(PlayGroundPool.__init__, "auto_login"):
                pool_kwargs["auto_login"] = False

            pool = PlayGroundPool(**pool_kwargs)
            try:
                if hasattr(pool, "start"):
                    start_kwargs: Dict[str, Any] = {}
                    if supports_param(pool.start, "parallel"):
                        start_kwargs["parallel"] = True
                    if supports_param(pool.start, "new_chat"):
                        start_kwargs["new_chat"] = True
                    pool.start(**start_kwargs)
            except Exception as err:
                close_obj(pool, force=True, markers={runtime_base})
                cleanup_runtime_profiles(save_dir, {runtime_base})
                if self._is_login_error(err):
                    raise RuntimeError(
                        "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                    ) from err
                raise

            self._check_session_stopped(session_id)
            pids = collect_pids_from_obj(pool)
            with PlaygroundModel._pool_lock:
                PlaygroundModel._pg_pools[scope_key] = {"count": target_count, "pool": pool}
                PlaygroundModel._scope_pids.setdefault(scope_key, set()).update(pids)
            return pool

    def refresh_client(self, api_key: Optional[str] = None, session_id: Optional[str] = None) -> Any:
        profile_key = self._get_profile_key(api_key)
        self._drop_client(profile_key, session_id=session_id)
        return self.get_client(api_key, session_id=session_id)

    def close(self, api_key: Optional[str] = None, session_id: Optional[str] = None) -> None:
        if api_key is None and session_id is None:
            self._close_all_shared()
            return
        if api_key is None and session_id is not None:
            self.close_session(session_id)
            return
        self._drop_client(self._get_profile_key(api_key), session_id=session_id)

    def get_raw_client(self, api_key: Optional[str] = None, session_id: Optional[str] = None) -> Any:
        return self.get_client(api_key, session_id=session_id)

    def SetLogin(self, api_key: Optional[str] = None, force: bool = False, verbose: Any = True) -> bool:
        profile_key = self._get_profile_key(api_key)
        lock = self._get_profile_lock(f"{profile_key}::__login__")
        with lock:
            self._drop_client(profile_key)
            PlaygroundModel._verified_profiles.discard(profile_key)
            cleanup_legacy_profiles()

            save_dir = get_save_dir()
            runtime_dir = save_dir / f"{profile_key}_runtime"
            if runtime_dir.exists():
                shutil.rmtree(runtime_dir, ignore_errors=True)

            pg = PlayGround(**self._build_pg_init_kwargs(profile_key, save_dir, verbose=verbose))
            login_mode = PlayGroundOptions.LoginMode.FORCE_NEW if force else PlayGroundOptions.LoginMode.AUTO
            try:
                pg.setting(first=login_mode, backup=True)
            finally:
                close_obj(pg)

            PlaygroundModel._verified_profiles.add(profile_key)
            return True

    async def set_login_async(self, api_key: Optional[str] = None, force: bool = False, verbose: Any = True) -> bool:
        return await asyncio.to_thread(self.SetLogin, api_key=api_key, force=force, verbose=verbose)

    def check_login(self, api_key: Optional[str] = None, verify: bool = False) -> bool:
        profile_key = self._get_profile_key(api_key)
        save_dir = get_save_dir()
        if not verify:
            prefix = f"{profile_key}::"
            with PlaygroundModel._pool_lock:
                if any(k.startswith(prefix) for k in PlaygroundModel._client_pool) or any(k.startswith(prefix) for k in PlaygroundModel._pg_pools):
                    return True
            if profile_key in PlaygroundModel._verified_profiles:
                return True
            pg = PlayGround(**self._build_pg_init_kwargs(profile_key, save_dir, verbose=False))
            try:
                if hasattr(pg, "storage") and hasattr(pg.storage, "has_any_saved_session"):
                    return bool(pg.storage.has_any_saved_session())
            except Exception:
                pass
            return (save_dir / f"{profile_key}.json").is_file()

        lock = self._get_profile_lock(f"{profile_key}::__login__")
        with lock:
            if not (save_dir / f"{profile_key}.json").is_file():
                PlaygroundModel._verified_profiles.discard(profile_key)
                return False
            pg = PlayGround(**self._build_pg_init_kwargs(profile_key, save_dir, verbose=False))
            try:
                if hasattr(pg, "is_logged_in"):
                    ok = bool(pg.is_logged_in(backup=True))
                else:
                    connect_kwargs: Dict[str, Any] = {"backup": True, "headless": True}
                    if supports_param(pg.connect, "auto_login"):
                        connect_kwargs["auto_login"] = False
                    pg.connect(**connect_kwargs)
                    ok = True
                if ok:
                    PlaygroundModel._verified_profiles.add(profile_key)
                else:
                    PlaygroundModel._verified_profiles.discard(profile_key)
                return ok
            except Exception:
                PlaygroundModel._verified_profiles.discard(profile_key)
                return False
            finally:
                close_obj(pg)

    def list_models_detail(
        self,
        api_key: Optional[str] = None,
        kind: Optional[Any] = None,
        paid: Optional[bool] = False,
    ) -> List[Dict[str, Any]]:
        profile_key = self._get_profile_key(api_key)
        scope_key = self._get_scope_key(profile_key, "shared")
        kwargs: Dict[str, Any] = {}
        resolved_kind = resolve_model_kind(kind)
        if resolved_kind is not None:
            kwargs["kind"] = resolved_kind
        if paid is not None:
            kwargs["paid"] = paid

        with PlaygroundModel._pool_lock:
            pool_entry = PlaygroundModel._pg_pools.get(scope_key)
            active_pool = pool_entry.get("pool") if pool_entry else None

        if active_pool is not None:
            with active_pool.acquire() as pg:
                raw_models = pg.list_models(**kwargs)
        else:
            pg = self.get_client(api_key, session_id="shared")
            try:
                raw_models = pg.list_models(**kwargs)
            except Exception as err:
                if self._is_login_error(err):
                    self._drop_scope(scope_key, failed_obj=pg)
                    raise RuntimeError(
                        "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                    ) from err
                if self.is_connection_error(err):
                    self._drop_scope(scope_key, failed_obj=pg)
                    raw_models = self.get_client(api_key, session_id="shared").list_models(**kwargs)
                else:
                    raise

        return [item if isinstance(item, dict) else {"id": str(item)} for item in (raw_models or [])]

    def list_models(
        self,
        api_key: Optional[str] = None,
        kind: Optional[Any] = PlayGroundOptions.ModelKind.TEXT,
        paid: Optional[bool] = False,
    ) -> List[str]:
        raw_items = self.list_models_detail(api_key=api_key, kind=kind, paid=paid)
        exclude_keywords = ("imagen", "veo", "lyria", "tts", "audio", "embedding", "robotics", "decision", "transcribe")
        model_names: List[str] = []
        is_text_kind = str(kind).strip().lower() in ("text", str(PlayGroundOptions.ModelKind.TEXT).lower())
        for item in raw_items:
            mid = str(item.get("id") or item.get("name") or "").strip()
            if not mid:
                continue
            item_kind = str(item.get("kind") or item.get("type") or "").strip().lower()
            if is_text_kind:
                if item_kind and item_kind not in ("text", "chat", "llm"):
                    continue
                if any(k in mid.lower() for k in exclude_keywords):
                    continue
            model_names.append(mid)
        return sorted(set(model_names))

    async def send_text(self, message: str, setting: Optional[Dict[str, Any]] = None) -> AiResponse:
        setting = setting or {}
        cur_used_key = setting.get("api_key", self.api_key)
        session_id = setting.get("session_id")
        self._check_session_stopped(session_id)
        profile_key = self._get_profile_key(cur_used_key)
        scope_key = self._get_scope_key(profile_key, session_id)
        verbose = setting.get("verbose", False)
        try:
            concurrency = max(1, int(setting.get("concurrency", 1)))
        except (TypeError, ValueError):
            concurrency = 1

        send_kwargs = build_send_kwargs(message, setting)

        def _call() -> Any:
            self._check_session_stopped(session_id)
            if concurrency > 1 and PlayGroundPool is not None:
                pool = self._get_pg_pool(profile_key, concurrency, session_id=session_id, verbose=verbose)
                try:
                    with pool.acquire() as pg:
                        with PlaygroundModel._pool_lock:
                            PlaygroundModel._scope_pids.setdefault(scope_key, set()).update(collect_pids_from_obj(pg))
                        return pg.send(**send_kwargs)
                except Exception as err:
                    self._check_session_stopped(session_id)
                    if self._is_login_error(err):
                        self._drop_scope(scope_key, failed_obj=pool)
                        raise RuntimeError(
                            "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                        ) from err
                    if self.is_connection_error(err):
                        self._drop_scope(scope_key, failed_obj=pool)
                        pool = self._get_pg_pool(profile_key, concurrency, session_id=session_id, verbose=verbose)
                        with pool.acquire() as pg:
                            with PlaygroundModel._pool_lock:
                                PlaygroundModel._scope_pids.setdefault(scope_key, set()).update(collect_pids_from_obj(pg))
                            return pg.send(**send_kwargs)
                    raise

            lock = self._get_profile_lock(scope_key)
            with lock:
                self._check_session_stopped(session_id)
                pg = self.get_client(cur_used_key, session_id=session_id, verbose=verbose)
                try:
                    return pg.send(**send_kwargs)
                except Exception as err:
                    self._check_session_stopped(session_id)
                    if self._is_login_error(err):
                        self._drop_scope(scope_key, failed_obj=pg)
                        raise RuntimeError(
                            "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                        ) from err
                    if self.is_connection_error(err):
                        self._drop_scope(scope_key, failed_obj=pg)
                        pg2 = self.get_client(cur_used_key, session_id=session_id, verbose=verbose)
                        return pg2.send(**send_kwargs)
                    raise

        raw_reply = await asyncio.to_thread(_call)
        if isinstance(raw_reply, str):
            res_text = raw_reply
        elif isinstance(raw_reply, dict):
            res_text = str(raw_reply.get("text") or raw_reply.get("response") or "")
        else:
            res_text = str(getattr(raw_reply, "text", None) or raw_reply or "")
        return AiResponse(text=res_text, raw_response=raw_reply)

    async def send_batch(self, tasks: List[Dict[str, Any]], setting: Optional[Dict[str, Any]] = None) -> List[Any]:
        setting = setting or {}
        cur_used_key = setting.get("api_key", self.api_key)
        session_id = setting.get("session_id")
        self._check_session_stopped(session_id)
        profile_key = self._get_profile_key(cur_used_key)
        scope_key = self._get_scope_key(profile_key, session_id)
        verbose = setting.get("verbose", False)
        try:
            concurrency = max(1, int(setting.get("concurrency", 3)))
        except (TypeError, ValueError):
            concurrency = 3
        default_cfg = build_config(setting)

        def _call() -> List[Any]:
            self._check_session_stopped(session_id)
            pool = self._get_pg_pool(
                profile_key,
                concurrency,
                session_id=session_id,
                verbose=verbose,
                default_config=default_cfg,
            )
            try:
                return pool.send_batch(tasks)
            except Exception as err:
                self._check_session_stopped(session_id)
                if self._is_login_error(err):
                    self._drop_scope(scope_key, failed_obj=pool)
                    raise RuntimeError(
                        "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                    ) from err
                raise

        return await asyncio.to_thread(_call)

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
