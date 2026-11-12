import asyncio
import re
import time
import weakref

from src.ai import AiRoute, AiTarget
from src.system.load_save import load_data, save_data
from src.trans.trans_ai_utils import glossary_text, extract_glossary

API = ''
API_KEYS = []
API_INDEX = 0

AI_TARGET = AiRoute.DEFAULT_TARGET
MODEL_NAME = AiRoute.DEFAULT_MODEL
CUSTOM_AI_PROMPT = ''

USE_ADVANCED_CENSOR = False
CENSOR_SHUFFLE = True
CENSOR_EXTRACT_MODE = "word"
CENSOR_PAPAGO = False

IMG_TAG_PATTERN = re.compile(r'-img-:[^\s\r\n]+')

_LOOP_LOCKS = weakref.WeakKeyDictionary()
_cooldown_until = 0.0
_switches_in_cycle = 0
_last_switch_time = 0.0

ai_route = AiRoute(ai_target=AI_TARGET, api=API)


class ForceStopException(Exception):
    pass


def _reset_switch_state():
    global _cooldown_until, _switches_in_cycle, _last_switch_time
    _cooldown_until = 0.0
    _switches_in_cycle = 0
    _last_switch_time = 0.0


def set_cooldown(seconds: float):
    global _cooldown_until
    _cooldown_until = max(_cooldown_until, time.time() + float(seconds))


def get_cooldown_remaining() -> float:
    global _cooldown_until
    return max(0.0, _cooldown_until - time.time())


async def wait_cooldown():
    while True:
        rem = get_cooldown_remaining()
        if rem <= 0:
            break
        await asyncio.sleep(min(rem, 0.5))


def _get_switch_lock():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.Lock()

    if loop not in _LOOP_LOCKS:
        _LOOP_LOCKS[loop] = asyncio.Lock()
    return _LOOP_LOCKS[loop]


def get_client(api_key: str = None):
    return ai_route.get_raw_client(api_key)


def refresh_client(api_key: str = None):
    return ai_route.refresh_client(api_key)


class _ClientProxy:
    def __getattr__(self, name):
        return getattr(get_client(), name)


client = _ClientProxy()
glossary_text.client = client


def set_ai_target(target: int):
    global AI_TARGET
    AI_TARGET = target
    ai_route.set_target(target)


def set_api_key(api_key):
    global API, API_KEYS, API_INDEX
    API = api_key.strip() or ''
    ai_route.set_api(API)
    if API:
        if not API_KEYS:
            API_KEYS = [API]
            API_INDEX = 0
        elif 0 <= API_INDEX < len(API_KEYS):
            API_KEYS[API_INDEX] = API
        else:
            API_KEYS.append(API)
            API_INDEX = len(API_KEYS) - 1
    _reset_switch_state()
    data = load_data()
    data['api'] = API
    data['api_keys'] = API_KEYS
    data['api_index'] = API_INDEX
    save_data(data)


def set_api_keys(keys, active_index=0):
    global API, API_KEYS, API_INDEX
    API_KEYS = [str(k).strip() for k in keys if str(k).strip()]
    if not API_KEYS:
        API_INDEX = 0
        API = ''
    else:
        API_INDEX = max(0, min(int(active_index), len(API_KEYS) - 1))
        API = API_KEYS[API_INDEX]
    ai_route.set_api(API)
    _reset_switch_state()
    data = load_data()
    data['api'] = API
    data['api_keys'] = API_KEYS
    data['api_index'] = API_INDEX
    save_data(data)


def set_api_index(index):
    global API, API_KEYS, API_INDEX
    if not API_KEYS:
        return False
    API_INDEX = max(0, min(int(index), len(API_KEYS) - 1))
    API = API_KEYS[API_INDEX]
    ai_route.set_api(API)
    _reset_switch_state()
    data = load_data()
    data['api'] = API
    data['api_keys'] = API_KEYS
    data['api_index'] = API_INDEX
    save_data(data)
    return True


async def switch_api_key_safe(failed_key: str, wait_seconds: float = 0, log_callback=None):
    global API, API_KEYS, API_INDEX, _switches_in_cycle, _last_switch_time
    lock = _get_switch_lock()
    async with lock:
        unique_keys = set(API_KEYS)
        if len(unique_keys) <= 1:
            return False, API_INDEX, False, False

        if get_cooldown_remaining() > 0:
            return True, API_INDEX, False, True

        if API == failed_key:
            now = time.time()
            cooldown_sec = float(wait_seconds) if wait_seconds and float(wait_seconds) > 0 else 5.0
            if _last_switch_time > 0 and (now - _last_switch_time) > max(cooldown_sec, 60.0):
                _switches_in_cycle = 0
            _last_switch_time = now

            next_index = API_INDEX
            for _ in range(len(API_KEYS)):
                next_index = (next_index + 1) % len(API_KEYS)
                if API_KEYS[next_index] != failed_key:
                    break

            _switches_in_cycle += 1
            wrapped = _switches_in_cycle >= len(unique_keys)
            if wrapped:
                _switches_in_cycle = 0
                set_cooldown(cooldown_sec)

            API_INDEX = next_index
            API = API_KEYS[API_INDEX]
            ai_route.set_api(API)
            data = load_data()
            data['api'] = API
            data['api_keys'] = API_KEYS
            data['api_index'] = API_INDEX
            save_data(data)

            return True, API_INDEX, True, wrapped
        else:
            return True, API_INDEX, False, False


def switch_to_next_api_key():
    global API, API_KEYS, API_INDEX
    if len(API_KEYS) <= 1:
        return False
    API_INDEX = (API_INDEX + 1) % len(API_KEYS)
    API = API_KEYS[API_INDEX]
    ai_route.set_api(API)
    _reset_switch_state()
    data = load_data()
    data['api'] = API
    data['api_keys'] = API_KEYS
    data['api_index'] = API_INDEX
    save_data(data)
    return True


def rest():
    global API, API_KEYS, API_INDEX
    data = load_data()
    raw_keys = data.get('api_keys', [])
    if isinstance(raw_keys, list):
        API_KEYS = [str(k).strip() for k in raw_keys if str(k).strip()]
    else:
        API_KEYS = []

    single_api = str(data.get('api', '')).strip()
    if not API_KEYS and single_api:
        API_KEYS = [single_api]

    idx = data.get('api_index', 0)
    try:
        API_INDEX = int(idx)
    except (ValueError, TypeError):
        API_INDEX = 0

    if API_KEYS:
        if API_INDEX < 0 or API_INDEX >= len(API_KEYS):
            API_INDEX = 0
        API = API_KEYS[API_INDEX]
    else:
        API_INDEX = 0
        API = single_api

    ai_route.set_api(API)
    _reset_switch_state()


rest()