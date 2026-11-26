import os
import re
import shutil
import threading
from pathlib import Path
from typing import Set

from src.system.config import DATA_FOLDER
from .process_guard import is_pid_alive

_seq_lock = threading.Lock()
_runtime_seq = 0


def get_save_dir() -> Path:
    save_dir = (Path(str(DATA_FOLDER)) / "playground").resolve()
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir


def get_key_path() -> Path:
    return get_save_dir() / "key.bmp"


def next_runtime_profile(profile_key: str) -> str:
    global _runtime_seq
    with _seq_lock:
        _runtime_seq += 1
        seq = _runtime_seq
    return f"{profile_key}_r{os.getpid()}_{seq}"


def clone_profile_json(save_dir: Path, source_profile: str, target_profile: str) -> None:
    if not source_profile or not target_profile or source_profile == target_profile:
        return
    src_json = save_dir / f"{source_profile}.json"
    dst_json = save_dir / f"{target_profile}.json"
    if src_json.is_file():
        try:
            shutil.copy2(src_json, dst_json)
        except Exception:
            pass


def cleanup_runtime_profiles(save_dir: Path, runtime_profiles: Set[str]) -> None:
    for rp in list(runtime_profiles):
        if not rp:
            continue
        for target_dir in [
            save_dir / rp,
            save_dir / f"{rp}_runtime",
            *save_dir.glob(f"{rp}_worker_*"),
        ]:
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
        for target_file in [save_dir / f"{rp}.json", *save_dir.glob(f"{rp}*.json")]:
            if target_file.is_file():
                try:
                    target_file.unlink()
                except Exception:
                    pass


def cleanup_legacy_profiles() -> None:
    try:
        save_dir = get_save_dir()
        for enc_file in list(save_dir.rglob("*.enc")):
            try:
                enc_file.unlink()
            except Exception:
                pass
        for item in list(save_dir.iterdir()):
            if item.is_dir() and not item.name.endswith("_runtime"):
                shutil.rmtree(item, ignore_errors=True)
    except Exception:
        pass


def cleanup_stale_temp_profiles() -> None:
    cleanup_legacy_profiles()
    try:
        save_dir = get_save_dir()
        cur_pid = os.getpid()
        pattern = re.compile(r"^.+_r(\d+)_\d+(?:_runtime|_worker_\d+)?$")
        for item in list(save_dir.iterdir()):
            name = item.stem if item.is_file() else item.name
            m = pattern.match(name)
            if not m:
                continue
            owner_pid = int(m.group(1))
            if owner_pid != cur_pid and not is_pid_alive(owner_pid):
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    try:
                        item.unlink()
                    except Exception:
                        pass
    except Exception:
        pass


def ensure_profile_exists(save_dir: Path, profile_key: str) -> None:
    if (save_dir / f"{profile_key}.json").is_file():
        return
    raise RuntimeError(
        "Playground 로그인이 필요하거나 세션이 만료되었습니다. [API 설정 -> Playground]에서 로그인해 주세요."
    )
