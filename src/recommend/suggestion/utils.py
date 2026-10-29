import json
import re
import time
from typing import Any
from urllib.parse import urlparse

PRINT_OK = False

def PrintIo(text: str):
    if PRINT_OK:
        print(text)

def site_delay(site: str):
    if site == 'kakuyomu':
        time.sleep(1)
    elif site == 'hameln':
        time.sleep(2.0)

def site_delay_all(site: str):
    if site == 'kakuyomu':
        time.sleep(1)
    elif site == 'naro':
        time.sleep(1)
    elif site == 'hameln':
        time.sleep(2.0)

def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip('/')
    return f"{parsed.scheme}://{netloc}{path}"

def extract_json_from_response(text: str) -> Any:
    text = text.strip()
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