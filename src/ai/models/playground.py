import asyncio
import atexit
import inspect
import os
import re
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.ai.registry import register_ai
from src.ai.targets import AiTarget
from .base import BaseAiModel, AiResponse
from src.system.config import DATA_FOLDER

from playground_on_python import PlayGround
try:
    from playground_on_python import PlayGroundPool
except ImportError:
    PlayGroundPool = None


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
        "gemini-3.5-flash-lite"
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
    _runtime_seq: int = 0
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
                threading.Thread(target=PlaygroundModel._cleanup_stale_temp_profiles, daemon=True).start()

    @staticmethod
    def _supports_param(fn: Any, param_name: str) -> bool:
        try:
            sig = inspect.signature(fn)
            return param_name in sig.parameters
        except Exception:
            return False

    @classmethod
    def _get_save_dir_cls(cls) -> Path:
        save_dir = (Path(str(DATA_FOLDER)) / "playground").resolve()
        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir

    @staticmethod
    def _is_pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        if os.name == "nt":
            try:
                import ctypes
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                STILL_ACTIVE = 259
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
                if not handle:
                    return False
                try:
                    exit_code = ctypes.c_ulong()
                    if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                        return exit_code.value == STILL_ACTIVE
                    return False
                finally:
                    ctypes.windll.kernel32.CloseHandle(handle)
            except Exception:
                return False
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False

    @classmethod
    def _cleanup_stale_temp_profiles(cls) -> None:
        try:
            save_dir = cls._get_save_dir_cls()
            cur_pid = os.getpid()
            pattern = re.compile(r"^.+_r(\d+)_\d+(?:_worker_\d+)?$")
            for item in list(save_dir.iterdir()):
                name = item.stem if item.is_file() else item.name
                m = pattern.match(name)
                if not m:
                    continue
                owner_pid = int(m.group(1))
                if owner_pid != cur_pid and not cls._is_pid_alive(owner_pid):
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        try:
                            item.unlink()
                        except Exception:
                            pass
        except Exception:
            pass

    @classmethod
    def _next_runtime_profile(cls, profile_key: str) -> str:
        with cls._pool_lock:
            cls._runtime_seq += 1
            seq = cls._runtime_seq
        return f"{profile_key}_r{os.getpid()}_{seq}"

    @staticmethod
    def _clean_lock_files(profile_dir: Path) -> None:
        for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket", "Lockfile"):
            lock_file = profile_dir / lock_name
            if lock_file.exists():
                try:
                    lock_file.unlink()
                except Exception:
                    pass

    @classmethod
    def _clone_profile_storage(cls, save_dir: Path, source_profile: str, target_profile: str) -> None:
        if not source_profile or not target_profile or source_profile == target_profile:
            return
        src_dir = save_dir / source_profile
        dst_dir = save_dir / target_profile
        ignore_fn = shutil.ignore_patterns(
            "Singleton*",
            "Lockfile",
            "Crashpad",
            "Cache",
            "Code Cache",
            "GPUCache",
            "GrShaderCache",
            "ShaderCache",
            "*.lock",
            "*.tmp",
        )
        if src_dir.is_dir():
            try:
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True, ignore=ignore_fn)
            except Exception:
                pass
        dst_dir.mkdir(parents=True, exist_ok=True)
        cls._clean_lock_files(dst_dir)

        for enc_file in list(save_dir.glob("*.enc")):
            stem = enc_file.stem
            if stem == source_profile or stem.startswith(f"{source_profile}_"):
                suffix = stem[len(source_profile):]
                target_enc = save_dir / f"{target_profile}{suffix}.enc"
                try:
                    shutil.copy2(enc_file, target_enc)
                except Exception:
                    pass

        if dst_dir.is_dir():
            for enc_file in list(dst_dir.glob("*.enc")):
                stem = enc_file.stem
                if stem == source_profile or stem.startswith(f"{source_profile}_"):
                    suffix = stem[len(source_profile):]
                    target_enc = dst_dir / f"{target_profile}{suffix}.enc"
                    try:
                        shutil.copy2(enc_file, target_enc)
                    except Exception:
                        pass

    @classmethod
    def _cleanup_runtime_profiles(cls, save_dir: Path, runtime_profiles: Set[str]) -> None:
        for rp in list(runtime_profiles):
            if not rp:
                continue
            for target_dir in [save_dir / rp, *save_dir.glob(f"{rp}_worker_*")]:
                if target_dir.exists():
                    shutil.rmtree(target_dir, ignore_errors=True)
            for enc_file in list(save_dir.glob(f"{rp}*.enc")):
                try:
                    enc_file.unlink()
                except Exception:
                    pass

    @classmethod
    def _collect_pids_from_obj(cls, obj: Any, visited: Optional[Set[int]] = None) -> Set[int]:
        pids: Set[int] = set()
        if obj is None:
            return pids
        if visited is None:
            visited = set()
        obj_id = id(obj)
        if obj_id in visited:
            return pids
        visited.add(obj_id)

        for attr in ("pid", "browser_pid", "driver_pid", "chrome_pid"):
            val = getattr(obj, attr, None)
            if isinstance(val, int) and val > 0:
                pids.add(val)

        for proc_attr in ("process", "_process"):
            proc = getattr(obj, proc_attr, None)
            if proc is not None:
                p_pid = getattr(proc, "pid", None)
                if isinstance(p_pid, int) and p_pid > 0:
                    pids.add(p_pid)

        driver = getattr(obj, "driver", None)
        if driver is not None:
            b_pid = getattr(driver, "browser_pid", None)
            if isinstance(b_pid, int) and b_pid > 0:
                pids.add(b_pid)
            service = getattr(driver, "service", None)
            if service is not None:
                s_proc = getattr(service, "process", None)
                if s_proc is not None:
                    s_pid = getattr(s_proc, "pid", None)
                    if isinstance(s_pid, int) and s_pid > 0:
                        pids.add(s_pid)

        if isinstance(obj, (list, tuple, set)):
            for item in list(obj):
                pids.update(cls._collect_pids_from_obj(item, visited))
            return pids

        if isinstance(obj, dict):
            for item in list(obj.values()):
                pids.update(cls._collect_pids_from_obj(item, visited))
            return pids

        for col_attr in ("workers", "_workers", "clients", "_clients", "instances", "_instances", "pool", "_pool", "items", "_items"):
            col = getattr(obj, col_attr, None)
            if col is not None:
                pids.update(cls._collect_pids_from_obj(col, visited))

        for q_attr in ("_queue", "queue"):
            q_obj = getattr(obj, q_attr, None)
            if q_obj is not None and hasattr(q_obj, "queue"):
                try:
                    pids.update(cls._collect_pids_from_obj(list(q_obj.queue), visited))
                except Exception:
                    pass

        return pids

    @staticmethod
    def _kill_pid(pid: int) -> None:
        if not pid or pid <= 0:
            return
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
                    timeout=5,
                )
            else:
                os.kill(pid, signal.SIGKILL)
        except Exception:
            pass

    @classmethod
    def _kill_processes_by_markers(cls, markers: Set[str]) -> None:
        valid_markers = [m for m in markers if m and len(m) >= 4]
        if not valid_markers:
            return
        try:
            import psutil
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    if "chrome" not in name:
                        continue
                    cmdline = " ".join(proc.info.get("cmdline") or [])
                    if any(m in cmdline for m in valid_markers):
                        cls._kill_pid(int(proc.info["pid"]))
                except Exception:
                    pass
            return
        except ImportError:
            pass

        if os.name == "nt":
            try:
                escaped = [m.replace("'", "''") for m in valid_markers]
                cond = " -or ".join(f"$_.CommandLine -like '*{m}*'" for m in escaped)
                ps_cmd = (
                    f"Get-CimInstance Win32_Process | Where-Object {{ "
                    f"($_.Name -like '*chrome*') -and ({cond}) }} | "
                    f"ForEach-Object {{ $_.ProcessId }}"
                )
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
                    timeout=5,
                )
                for line in (res.stdout or "").splitlines():
                    line = line.strip()
                    if line.isdigit():
                        cls._kill_pid(int(line))
            except Exception:
                pass

    @classmethod
    def _close_obj(
        cls,
        obj: Any,
        force: bool = False,
        extra_pids: Optional[Set[int]] = None,
        markers: Optional[Set[str]] = None,
    ) -> None:
        pids: Set[int] = set(extra_pids or ())
        if obj is not None:
            pids.update(cls._collect_pids_from_obj(obj))

        def _graceful():
            if obj is None:
                return
            try:
                if hasattr(obj, "close"):
                    obj.close()
                elif hasattr(obj, "quit"):
                    obj.quit()
            except Exception:
                pass
            try:
                if hasattr(obj, "driver") and obj.driver:
                    obj.driver.quit()
            except Exception:
                pass

        if force:
            for pid in pids:
                cls._kill_pid(pid)
            if markers:
                cls._kill_processes_by_markers(markers)
            if obj is not None:
                t = threading.Thread(target=_graceful, daemon=True)
                t.start()
                t.join(timeout=0.3)
            return

        if obj is not None:
            t = threading.Thread(target=_graceful, daemon=True)
            t.start()
            t.join(timeout=2.5)

        for pid in pids:
            if cls._is_pid_alive(pid):
                cls._kill_pid(pid)
        if markers:
            cls._kill_processes_by_markers(markers)

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
            all_pids.update(cls._collect_pids_from_obj(obj))
            cls._close_obj(obj, force=force)

        if force:
            for pid in all_pids:
                cls._kill_pid(pid)
            cls._kill_processes_by_markers(all_profiles)
        else:
            for pid in all_pids:
                if cls._is_pid_alive(pid):
                    cls._kill_pid(pid)
            cls._kill_processes_by_markers(all_profiles)

        try:
            cls._cleanup_runtime_profiles(cls._get_save_dir_cls(), all_profiles)
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
            pids.update(cls._collect_pids_from_obj(obj))
            cls._close_obj(obj, force=True)
        for pid in pids:
            cls._kill_pid(pid)
        cls._kill_processes_by_markers(profiles)
        try:
            cls._cleanup_runtime_profiles(cls._get_save_dir_cls(), profiles)
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
            pids.update(cls._collect_pids_from_obj(obj))
            cls._close_obj(obj, force=False)
        for pid in pids:
            if cls._is_pid_alive(pid):
                cls._kill_pid(pid)
        cls._kill_processes_by_markers(profiles)
        try:
            cls._cleanup_runtime_profiles(cls._get_save_dir_cls(), profiles)
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

    def _get_save_dir(self) -> Path:
        return self._get_save_dir_cls()

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
                "setting(first=true",
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

        self._close_obj(dead_pg, force=force, extra_pids=pids, markers=profiles)
        if dead_pool is not None:
            self._close_obj(dead_pool.get("pool"), force=force, extra_pids=pids, markers=profiles)
        self._cleanup_runtime_profiles(self._get_save_dir(), profiles)

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

    def get_client(self, api_key: Optional[str] = None, session_id: Optional[str] = None, verbose: bool = False) -> Any:
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
                self._close_obj(dead_pg, extra_pids=pids, markers=profiles)
                self._cleanup_runtime_profiles(self._get_save_dir(), profiles)
            if dead_pool is not None:
                self._close_obj(dead_pool.get("pool"))

            save_dir = self._get_save_dir()
            runtime_profile = self._next_runtime_profile(profile_key)
            self._clone_profile_storage(save_dir, profile_key, runtime_profile)

            with PlaygroundModel._pool_lock:
                PlaygroundModel._scope_profiles.setdefault(scope_key, set()).add(runtime_profile)

            pg_kwargs: Dict[str, Any] = {
                "profile_name": runtime_profile,
                "base_dir": save_dir,
                "encrypt": False,
                "verbose": verbose,
            }
            if self._supports_param(PlayGround.__init__, "clone_from"):
                pg_kwargs["clone_from"] = profile_key

            pg = PlayGround(**pg_kwargs)
            pg.logger.level = 2

            connect_kwargs: Dict[str, Any] = {
                "backup": True,
                "headless": True,
                "auto_login": False,
            }
            if self._supports_param(pg.connect, "clone_from"):
                connect_kwargs["clone_from"] = profile_key

            try:
                pg.connect(**connect_kwargs)
            except Exception as err:
                self._close_obj(pg, force=True, markers={runtime_profile})
                self._cleanup_runtime_profiles(save_dir, {runtime_profile})
                if self._is_login_error(err):
                    raise RuntimeError(
                        "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                    ) from err
                raise

            self._check_session_stopped(session_id)
            pids = self._collect_pids_from_obj(pg)
            with PlaygroundModel._pool_lock:
                PlaygroundModel._client_pool[scope_key] = pg
                PlaygroundModel._scope_pids.setdefault(scope_key, set()).update(pids)
            return pg

    def _get_pg_pool(
        self,
        profile_key: str,
        count: int,
        session_id: Optional[str] = None,
        verbose: bool = False,
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
                self._close_obj(existing.get("pool"), extra_pids=old_pids, markers=old_profiles)
            if dead_single is not None:
                self._close_obj(dead_single, extra_pids=old_pids, markers=old_profiles)
            if old_profiles:
                self._cleanup_runtime_profiles(self._get_save_dir(), old_profiles)

            save_dir = self._get_save_dir()
            runtime_base = self._next_runtime_profile(profile_key)
            self._clone_profile_storage(save_dir, profile_key, runtime_base)

            with PlaygroundModel._pool_lock:
                PlaygroundModel._scope_profiles.setdefault(scope_key, set()).add(runtime_base)

            pool_kwargs: Dict[str, Any] = {
                "count": target_count,
                "base_profile": runtime_base,
                "base_dir": save_dir,
                "headless": True,
                "backup": True,
                "auto_login": False,
                "encrypt": False,
                "verbose": verbose,
            }
            if self._supports_param(PlayGroundPool.__init__, "clone_from"):
                pool_kwargs["clone_from"] = profile_key

            pool = PlayGroundPool(**pool_kwargs)
            try:
                pool.start(parallel=True, new_chat=True)
            except Exception as err:
                self._close_obj(pool, force=True, markers={runtime_base})
                self._cleanup_runtime_profiles(save_dir, {runtime_base})
                if self._is_login_error(err):
                    raise RuntimeError(
                        "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
                    ) from err
                raise

            self._check_session_stopped(session_id)
            pids = self._collect_pids_from_obj(pool)
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

    def SetLogin(self, api_key: Optional[str] = None, force: bool = False, verbose: bool = True) -> bool:
        profile_key = self._get_profile_key(api_key)
        lock = self._get_profile_lock(f"{profile_key}::__login__")
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
            pg.logger.level = 2
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
            prefix = f"{profile_key}::"
            with PlaygroundModel._pool_lock:
                if any(k.startswith(prefix) for k in PlaygroundModel._client_pool) or any(k.startswith(prefix) for k in PlaygroundModel._pg_pools):
                    return True
            if profile_key in PlaygroundModel._verified_profiles:
                return True
            pg = PlayGround(
                profile_name=profile_key,
                base_dir=self._get_save_dir(),
                encrypt=False,
                verbose=False,
            )
            pg.logger.level = 2
            return bool(pg.storage.has_any_saved_session())

        lock = self._get_profile_lock(f"{profile_key}::__login__")
        with lock:
            pg = PlayGround(
                profile_name=profile_key,
                base_dir=self._get_save_dir(),
                encrypt=False,
                verbose=False,
            )
            pg.logger.level = 2
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
        scope_key = self._get_scope_key(profile_key, "shared")
        kwargs: Dict[str, Any] = {}
        if kind is not None:
            kwargs["kind"] = kind
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
        session_id = setting.get("session_id")
        self._check_session_stopped(session_id)
        profile_key = self._get_profile_key(cur_used_key)
        scope_key = self._get_scope_key(profile_key, session_id)
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
            self._check_session_stopped(session_id)
            if concurrency > 1 and PlayGroundPool is not None:
                pool = self._get_pg_pool(profile_key, concurrency, session_id=session_id, verbose=verbose)
                try:
                    with pool.acquire() as pg:
                        with PlaygroundModel._pool_lock:
                            PlaygroundModel._scope_pids.setdefault(scope_key, set()).update(self._collect_pids_from_obj(pg))
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
                                PlaygroundModel._scope_pids.setdefault(scope_key, set()).update(self._collect_pids_from_obj(pg))
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