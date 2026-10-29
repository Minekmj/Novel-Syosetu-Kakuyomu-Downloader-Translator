import asyncio
import re
import time
import weakref
from google import genai
from src.system.load_save import load_data, save_data
from src.trans.trans_ai_utils import glossary_text

API = ''
API_KEYS = []
API_INDEX = 0

MODEL_NAME = 'gemini-3.5-flash-lite'
CUSTOM_AI_PROMPT = ''

USE_ADVANCED_CENSOR = False  
CENSOR_SHUFFLE = True  
CENSOR_EXTRACT_MODE = "word"  
CENSOR_PAPAGO = False

IMG_TAG_PATTERN = re.compile(r'-img-:[^\s\r\n]+')

_LOOP_CLIENT_POOLS = weakref.WeakKeyDictionary()
_LOOP_LOCKS = weakref.WeakKeyDictionary()
_SYNC_CLIENT_POOL = {}
_cooldown_until = 0.0


class ForceStopException(Exception):
    pass


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


def get_client(api_key: str = None) -> genai.Client:
    target_key = (api_key if api_key is not None else API).strip() or "None"
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        if loop not in _LOOP_CLIENT_POOLS:
            _LOOP_CLIENT_POOLS[loop] = {}
        pool = _LOOP_CLIENT_POOLS[loop]
        if target_key not in pool:
            pool[target_key] = genai.Client(api_key=target_key)
        return pool[target_key]
    else:
        if target_key not in _SYNC_CLIENT_POOL:
            _SYNC_CLIENT_POOL[target_key] = genai.Client(api_key=target_key)
        return _SYNC_CLIENT_POOL[target_key]


def refresh_client(api_key: str = None) -> genai.Client:
    target_key = (api_key if api_key is not None else API).strip() or "None"
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    new_client = genai.Client(api_key=target_key)
    if loop is not None:
        if loop not in _LOOP_CLIENT_POOLS:
            _LOOP_CLIENT_POOLS[loop] = {}
        _LOOP_CLIENT_POOLS[loop][target_key] = new_client
    else:
        _SYNC_CLIENT_POOL[target_key] = new_client

    return new_client


class _ClientProxy:
    def __getattr__(self, name):
        return getattr(get_client(), name)


client = _ClientProxy()
glossary_text.client = client


def set_api_key(api_key):
    global API, API_KEYS, API_INDEX
    API = api_key.strip() or ''
    if API:
        if not API_KEYS:
            API_KEYS = [API]
            API_INDEX = 0
        elif 0 <= API_INDEX < len(API_KEYS):
            API_KEYS[API_INDEX] = API
        else:
            API_KEYS.append(API)
            API_INDEX = len(API_KEYS) - 1
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
    data = load_data()
    data['api'] = API
    data['api_index'] = API_INDEX
    save_data(data)
    return True


async def switch_api_key_safe(failed_key: str, wait_seconds: float = 0, log_callback=None):
    global API, API_KEYS, API_INDEX
    lock = _get_switch_lock()
    async with lock:
        if len(API_KEYS) <= 1:
            return False, API_INDEX, False, False

        if get_cooldown_remaining() > 0:
            await wait_cooldown()
            return True, API_INDEX, False, True

        if API == failed_key:
            next_index = (API_INDEX + 1) % len(API_KEYS)
            wrapped = (next_index <= API_INDEX)
            API_INDEX = next_index
            API = API_KEYS[API_INDEX]
            data = load_data()
            data['api'] = API
            data['api_keys'] = API_KEYS
            data['api_index'] = API_INDEX
            save_data(data)

            # if wrapped:
                # sleep_sec = max(wait_seconds, 55.0)
                # set_cooldown(sleep_sec)
                # if log_callback:
                #     log_callback(f"[API 쿨다운] 모든 API 키(총 {len(API_KEYS)}개) 소진. 전체 작업을 {int(sleep_sec)}초간 일괄 일시정지 후 [0]번 키부터 재개합니다...")
                # await wait_cooldown()

            return True, API_INDEX, True, wrapped
        else:
            return True, API_INDEX, False, False


def switch_to_next_api_key():
    global API, API_KEYS, API_INDEX
    if len(API_KEYS) <= 1:
        return False
    API_INDEX = (API_INDEX + 1) % len(API_KEYS)
    API = API_KEYS[API_INDEX]
    data = load_data()
    data['api'] = API
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


rest()