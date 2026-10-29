import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from collections.abc import Callable

from src.find.site import KakuyomuSearch, NaroSearch, SyosetuSearch
from .ai_client import GeminiAIClient
from .executor import SearchExecutor
from .agent import SearchAgent
from .ranker import CandidateRanker
from .utils import PrintIo, normalize_url

class NovelRecommender:
    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        model: str = "gemini-3.1-flash-lite",
        user_data: dict = {"list": {"없음": {"src": "None"}}},
        log: Callable = None
    ):
        self.ai = GeminiAIClient(api_key=gemini_api_key, model=model)
        self.executor = SearchExecutor()
        self.user_data = user_data
        if user_data == {'list': {}}:
            self.user_data = {"list": {"없음": {"src": "None"}}}
        self.log = log or (lambda *args, **kwargs: None)

        self.site_meta = {
            'kakuyomu': {'cls': KakuyomuSearch, 'name': '카쿠요무'},
            'naro': {'cls': NaroSearch, 'name': '소설가가 되자'},
            'hameln': {'cls': SyosetuSearch, 'name': '하멜른'}
        }
        self.site_success_counts = {'kakuyomu': 0, 'naro': 0, 'hameln': 0}

        self.agent = SearchAgent(
            ai_client=self.ai,
            executor=self.executor,
            site_meta=self.site_meta,
            site_success_counts=self.site_success_counts,
            log_callback=self.log
        )
        self.ranker = CandidateRanker(ai_client=self.ai)

    def get_read_history(self) -> Dict[str, Any]:
        self.log("info", "사용자 작품 목록 로드 중...")
        PrintIo("[행동] 사용자 감상 목록 로드")
        user_data = self.user_data

        raw_list = user_data.get("list", {})
        history_items = []
        read_urls = set()

        for title, info in raw_list.items():
            if not isinstance(info, dict):
                continue
            src = info.get("src", "")
            norm_url = normalize_url(src)
            if norm_url:
                read_urls.add(norm_url)

            site_key = "unknown"
            if "kakuyomu.jp" in src:
                site_key = "kakuyomu"
            elif "syosetu.org" in src:
                site_key = "hameln"
            elif "syosetu.com" in src:
                site_key = "naro"

            set_data = {
                "title": title,
                "url": src
            }
            try:
                site_cls = {"kakuyomu": KakuyomuSearch, "naro": NaroSearch, "hameln": SyosetuSearch}[site_key]
                set_data["story"], set_data["keywords"] = self.executor.get_description(site_key, site_cls, src)
            except Exception:
                pass

            history_items.append(set_data)

        PrintIo(f"[기록] 감상 작품 수: {len(history_items)}개, 등록된 URL: {len(read_urls)}개")
        return {"items": history_items, "read_urls": read_urls}

    def run_recommendation(
        self,
        top_k: int = 5,
        user_custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = datetime.now()
        PrintIo("=== 추천 파이프라인 가동 ===")
        if user_custom_prompt:
            PrintIo(f"[사용자 특별 요청 반영]: \"{user_custom_prompt}\"")

        try:
            history = self.get_read_history()
            history_items = history["items"]
            read_urls = history["read_urls"]

            if not history_items:
                msg = "읽은 작품 기록이 없습니다."
                PrintIo(msg)
                return {"error": msg, "recommended_works": []}

            self.log("info", "Ai를 시작하는 중...")

            candidates = self.agent.run_search_loop(
                history_items=history_items,
                read_urls=read_urls,
                user_custom_prompt=user_custom_prompt,
                top_k=top_k
            )

            PrintIo(f"\n[최종 탐색 결산] 중복 제외 총 {len(candidates)}개의 고유 신작 후보 확보")
            PrintIo(f"[플랫폼별 검색 성공 횟수]: {self.site_success_counts}")

            self.log("info", f"검색 종료. {len(candidates)}개의 작품 중 {top_k}개 선별")

            final_result = self.ranker.rerank_and_synthesize(
                history_items=history_items,
                user_custom_prompt=user_custom_prompt,
                candidates=candidates,
                top_k=top_k
            )
            final_result["user_custom_prompt"] = user_custom_prompt

            duration = (datetime.now() - start_time).total_seconds()
            PrintIo(f"=== 추천 파이프라인 완료 (소요시간: {duration:.2f}초) ===")
            PrintIo(f"=== {final_result.get('curator_note', '')} ===")
            return final_result

        except Exception as e:
            PrintIo(f"[치명적 오류 발생]: {e}\n{traceback.format_exc()}")
            return {"error": str(e), "recommended_works": []}