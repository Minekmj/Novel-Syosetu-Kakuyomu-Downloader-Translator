import time
import traceback
from typing import Optional
from google import genai
from google.genai import types
from src.trans.trans_ai_utils import build_thinking_config
from .utils import PrintIo

class GeminiAIClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.1-flash-lite"):
        self.api_key = api_key
        self.model = model

        if not self.api_key:
            err_msg = "GEMINI_API_KEY 환경변수가 설정되지 않았습니다."
            PrintIo(err_msg)
            raise ValueError(err_msg)

        PrintIo(f"[Gemini] 모델 초기화: {self.model}")
        self.client = genai.Client(api_key=self.api_key)

    def generate(self, prompt: str, system_instruction: str = "", max_retries: int = 5) -> str:
        PrintIo(f"[Gemini 요청] 본문 길이: {len(prompt)}자")

        config = types.GenerateContentConfig(
            system_instruction=system_instruction if system_instruction else None,
            temperature=1.0,
            response_mime_type="application/json",
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            thinking_config=build_thinking_config("HIGH", self.model)
        )

        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config
                )
                return response.text or ""
            except Exception as e:
                err_str = str(e)
                is_transient = any(k in err_str.upper() for k in ["503", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "429", "OVERLOADED"])
                if is_transient and attempt < max_retries:
                    print(f"[Gemini 서버 과부하 감지] 3초 대기 후 재시도... ({attempt}/{max_retries})")
                    time.sleep(3)
                    continue
                print(f"[Gemini API 최종 에러]: {e}\n{traceback.format_exc()}")
                return ""