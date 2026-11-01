import time
import traceback
from typing import Optional
from src.ai import AiRoute, AiTarget
from .utils import PrintIo


class SuggestionAIClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        ai_target: Optional[int] = None,
        ai_route: Optional[AiRoute] = None
    ):
        self.model = model or AiRoute.DEFAULT_MODEL
        self.ai_target = int(ai_target) if ai_target is not None else AiRoute.detect_target(self.model)
        self.target_name = AiRoute.get_target_name(self.ai_target)

        self.api_key = (api_key or "").strip()
        if not self.api_key:
            from src.system.load_save import load_data
            data = load_data()
            single_k, list_k, _ = AiRoute.get_storage_keys(self.ai_target)
            self.api_key = str(data.get(single_k) or "").strip()
            if not self.api_key:
                keys = data.get(list_k, [])
                if isinstance(keys, list) and keys:
                    self.api_key = str(keys[0]).strip()

        PrintIo(f"[{self.target_name}] 추천 클라이언트 가동 (모델: {self.model})")
        self.route = ai_route if ai_route is not None else AiRoute(ai_target=self.ai_target, api=self.api_key)

    def generate(self, prompt: str, system_instruction: str = "", max_retries: int = 5) -> str:
        PrintIo(f"[{self.target_name}] 프롬프트 요청: {len(prompt)}자 (모델: {self.model})")

        setting = {
            "model_name": self.model,
            "ai_target": self.ai_target,
            "api_key": self.api_key,
            "system_instruction": system_instruction if system_instruction else None,
            "temperature": 1.0,
            "thinking_budget": "HIGH",
        }

        for attempt in range(1, max_retries + 1):
            try:
                response = self.route.send_text_sync(prompt, setting=setting)
                res_text = response.text if response else ""
                if res_text:
                    return res_text
            except Exception as e:
                is_rate = self.route.is_rate_limit_error(e)
                is_conn = self.route.is_connection_error(e)
                is_transient = is_rate or is_conn or any(
                    k in str(e).upper() for k in ["503", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "429", "OVERLOADED", "TIMEOUT"]
                )

                if is_conn:
                    self.route.refresh_client(self.api_key)

                if is_transient and attempt < max_retries:
                    delay = self.route.extract_retry_delay(e) if is_rate else 3.0
                    delay = min(max(delay, 2.0), 30.0)
                    print(f"[{self.target_name} 일시 오류] {int(delay)}초 대기 후 재시도... ({attempt}/{max_retries})")
                    time.sleep(delay)
                    continue

                print(f"[{self.target_name} 에러]: {e}\n{traceback.format_exc()}")
                return ""

        return ""