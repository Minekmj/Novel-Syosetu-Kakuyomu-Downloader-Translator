import json
import re
import time
from typing import Any
from urllib.parse import urlparse, parse_qs

try:
    from PySide6.QtCore import QThread
except Exception:
    QThread = None

PRINT_OK = False


class RecommendationCancelled(Exception):
    pass


def PrintIo(text: str):
    if PRINT_OK:
        print(text)


def is_cancel_triggered(check_fn=None) -> bool:
    if check_fn:
        try:
            if check_fn():
                return True
        except Exception:
            pass
    if QThread is not None:
        try:
            curr = QThread.currentThread()
            if curr is not None and curr.isInterruptionRequested():
                return True
        except Exception:
            pass
    return False


def check_cancelled(check_fn=None):
    if is_cancel_triggered(check_fn):
        raise RecommendationCancelled()


def sleep_with_cancel(seconds: float, check_fn=None):
    remaining = float(seconds)
    while remaining > 0:
        check_cancelled(check_fn)
        step = min(0.25, remaining)
        time.sleep(step)
        remaining -= step
    check_cancelled(check_fn)


def site_delay(site: str, check_fn=None):
    if site == 'kakuyomu':
        sleep_with_cancel(1.0, check_fn)
    elif site == 'hameln':
        sleep_with_cancel(2.0, check_fn)


def site_delay_all(site: str, check_fn=None):
    if site == 'kakuyomu':
        sleep_with_cancel(1.0, check_fn)
    elif site == 'naro':
        sleep_with_cancel(1.0, check_fn)
    elif site == 'hameln':
        sleep_with_cancel(2.0, check_fn)


def normalize_url(url: str) -> str:
    if not url:
        return ""
    raw = url.strip()
    if raw == "None":
        return ""
    parsed = urlparse(raw)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip('/')

    if "kakuyomu.jp" in netloc:
        m = re.search(r'/works/(\d+)', path)
        if m:
            return f"kakuyomu.jp/works/{m.group(1)}"
    elif "syosetu.com" in netloc:
        m_info = re.search(r'/ncode/([a-zA-Z0-9]+)', path)
        if m_info:
            return f"{netloc}/{m_info.group(1).lower()}"
        m = re.match(r'^/([a-zA-Z0-9]+)', path)
        if m:
            return f"{netloc}/{m.group(1).lower()}"
    elif "syosetu.org" in netloc:
        m = re.search(r'/novel/(\d+)', path)
        if m:
            return f"syosetu.org/novel/{m.group(1)}"
        qs = parse_qs(parsed.query)
        if "id" in qs and qs["id"]:
            return f"syosetu.org/novel/{qs['id'][0]}"

    if not netloc:
        return path
    return f"{netloc}{path}"


def extract_json_from_response(text: str) -> Any:
    if not text:
        return {}
    text = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            first_brace = text.find('{')
            last_brace = text.rfind('}')
            if first_brace != -1 and last_brace != -1:
                return json.loads(text[first_brace:last_brace + 1])
            first_bracket = text.find('[')
            last_bracket = text.rfind(']')
            if first_bracket != -1 and last_bracket != -1:
                return json.loads(text[first_bracket:last_bracket + 1])
        except Exception:
            pass
        return {}