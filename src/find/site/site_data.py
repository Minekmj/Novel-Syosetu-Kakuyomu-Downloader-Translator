
import os
import json
import tempfile
import threading
import src.find.state as sf

COOKIES = {}
BASE_HEADERS = {}
COOKIES_H = {}
BASE_HEADERS_H = {}

_LOCK = threading.RLock()
_INITIALIZED = False


def load_headers(data):
    if isinstance(data, dict) and isinstance(data.get("headers"), dict):
        data = data["headers"]
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, (str, bytes, int, float))}


def load_cookies(data):
    if isinstance(data, dict) and isinstance(data.get("cookies"), dict):
        data = data["cookies"]
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, (str, bytes, int, float))}


def _serialize(data):
    return json.dumps(data, ensure_ascii=False)


def _sync_to_env_locked():
    os.environ["minedown_APP_COOKIES"] = _serialize(COOKIES)
    os.environ["minedown_APP_BASE_HEADERS"] = _serialize(BASE_HEADERS)


def sync_to_env():
    with _LOCK:
        _sync_to_env_locked()


def _get_env(key):
    try:
        value = json.loads(os.environ.get(key, "{}"))
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def get_env_cookies():
    with _LOCK:
        return _get_env("minedown_APP_COOKIES")


def get_env_headers():
    with _LOCK:
        return _get_env("minedown_APP_BASE_HEADERS")


def get_cookies():
    with _LOCK:
        return COOKIES.copy()


def get_headers():
    with _LOCK:
        return BASE_HEADERS.copy()


def _save_locked():
    if not sf.SRC:
        return False

    directory = os.path.dirname(os.path.abspath(sf.SRC))
    os.makedirs(directory, exist_ok=True)

    data = {
        "headers": BASE_HEADERS,
        "cookies": COOKIES
    }

    temp_path = None

    try:
        fd, temp_path = tempfile.mkstemp(prefix=".cookies_", suffix=".tmp", dir=directory)
        with os.fdopen(fd, "w", encoding="UTF-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, sf.SRC)
        temp_path = None
        return True

    except Exception as e:
        print(f"[!] 쿠키 저장 실패: {e}")
        return False

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def save():
    with _LOCK:
        result = _save_locked()
        _sync_to_env_locked()
        return result


def update(cookies=None, headers=None, save_file=True):
    global COOKIES, BASE_HEADERS

    with _LOCK:
        if cookies is not None:
            if not isinstance(cookies, dict):
                raise TypeError("cookies는 dict여야 합니다.")
            COOKIES.update(load_cookies(cookies))

        if headers is not None:
            if not isinstance(headers, dict):
                raise TypeError("headers는 dict여야 합니다.")
            BASE_HEADERS.update(load_headers(headers))

        _sync_to_env_locked()

        if save_file:
            return _save_locked()

        return True


def replace(cookies=None, headers=None, save_file=True):
    global COOKIES, BASE_HEADERS

    with _LOCK:
        if cookies is not None:
            COOKIES = load_cookies(cookies)

        if headers is not None:
            BASE_HEADERS = load_headers(headers)

        _sync_to_env_locked()

        if save_file:
            return _save_locked()

        return True


def _load_locked():
    global COOKIES, BASE_HEADERS

    if not sf.SRC or not os.path.exists(sf.SRC):
        COOKIES = {}
        BASE_HEADERS = {}
        _sync_to_env_locked()
        return False

    try:
        with open(sf.SRC, "r", encoding="UTF-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("쿠키 파일 형식이 올바르지 않습니다.")

        BASE_HEADERS = load_headers(data)

        if isinstance(data.get("cf_clearance"), dict):
            value = data["cf_clearance"].get("value", "")
            COOKIES = {"cf_clearance": str(value)} if value else {}
        else:
            COOKIES = load_cookies(data)

        _sync_to_env_locked()
        return True

    except Exception as e:
        print(f"[!] 쿠키 로드 실패: {e}")
        return False


def reset(b=False):
    global _INITIALIZED

    if b:
        sf.find_cf()

    with _LOCK:
        result = _load_locked()
        _INITIALIZED = True
        return result


def reset_b():
    return reset(False)


def refresh_env():
    with _LOCK:
        _sync_to_env_locked()


def clear(save_file=True):
    global COOKIES, BASE_HEADERS

    with _LOCK:
        COOKIES = {}
        BASE_HEADERS = {}
        _sync_to_env_locked()

        if save_file:
            return _save_locked()

        return True


# 초기 로드
reset(False)
