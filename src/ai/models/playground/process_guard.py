import os
import signal
import subprocess
import threading
from typing import Any, Optional, Set


def is_pid_alive(pid: int) -> bool:
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


def collect_pids_from_obj(obj: Any, visited: Optional[Set[int]] = None) -> Set[int]:
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
            pids.update(collect_pids_from_obj(item, visited))
        return pids

    if isinstance(obj, dict):
        for item in list(obj.values()):
            pids.update(collect_pids_from_obj(item, visited))
        return pids

    for col_attr in ("workers", "_workers", "clients", "_clients", "instances", "_instances", "pool", "_pool", "items", "_items"):
        col = getattr(obj, col_attr, None)
        if col is not None:
            pids.update(collect_pids_from_obj(col, visited))

    for q_attr in ("_queue", "queue"):
        q_obj = getattr(obj, q_attr, None)
        if q_obj is not None and hasattr(q_obj, "queue"):
            try:
                pids.update(collect_pids_from_obj(list(q_obj.queue), visited))
            except Exception:
                pass

    return pids


def kill_pid(pid: int) -> None:
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


def kill_processes_by_markers(markers: Set[str]) -> None:
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
                    kill_pid(int(proc.info["pid"]))
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
                    kill_pid(int(line))
        except Exception:
            pass


def close_obj(
    obj: Any,
    force: bool = False,
    extra_pids: Optional[Set[int]] = None,
    markers: Optional[Set[str]] = None,
) -> None:
    pids: Set[int] = set(extra_pids or ())
    if obj is not None:
        pids.update(collect_pids_from_obj(obj))

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
            kill_pid(pid)
        if markers:
            kill_processes_by_markers(markers)
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
        if is_pid_alive(pid):
            kill_pid(pid)
    if markers:
        kill_processes_by_markers(markers)
