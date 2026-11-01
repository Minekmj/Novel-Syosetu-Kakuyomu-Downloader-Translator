from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AiResponse:
    def __init__(self, text: str, raw_response: Any = None):
        self.text = text or ""
        self.raw_response = raw_response

    def __str__(self) -> str:
        return self.text

    def __bool__(self) -> bool:
        return bool(self.text)


class BaseAiModel(ABC):
    def __init__(self, api_key: str = ""):
        self.api_key = api_key.strip() if api_key else ""

    def set_api(self, api_key: str):
        self.api_key = api_key.strip() if api_key else ""

    def refresh_client(self, api_key: Optional[str] = None):
        pass

    def get_raw_client(self, api_key: Optional[str] = None) -> Any:
        return None

    @abstractmethod
    async def send_text(self, message: str, setting: Optional[Dict[str, Any]] = None) -> AiResponse:
        pass

    def is_rate_limit_error(self, err: Exception) -> bool:
        msg = str(err).lower()
        return any(k in msg for k in ("429", "resource_exhausted", "quota", "rate limit", "rate_limit", "exhausted"))

    def extract_retry_delay(self, err: Exception) -> float:
        import re
        err_str = str(err)
        m = re.search(r"retryDelay':\s*'(\d+)s'", err_str)
        if m:
            return float(m.group(1)) + 2.0
        m2 = re.search(r"retry in (\d+(\.\d+)?)s", err_str)
        if m2:
            return float(m2.group(1)) + 2.0
        return 45.0

    def is_connection_error(self, err: Exception) -> bool:
        msg = str(err).lower()
        return "connector is closed" in msg or "clientconnectorerror" in msg or "connection reset" in msg