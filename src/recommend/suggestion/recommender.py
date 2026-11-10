import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from collections.abc import Callable

from src.ai import AiRoute
from src.system.data import load_data
from src.find.site import KakuyomuSearch, NaroSearch, SyosetuSearch
from .ai_client import SuggestionAIClient
from .executor import SearchExecutor
from .agent import SearchAgent
from .ranker import CandidateRanker
from .utils import PrintIo, normalize_url

class NovelRecommender:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        user_data: dict = {"list": {"없음": {"src": "None"}}},
        log: Callable = None,
        ai_target: Optional[int] = None,
        ai_route: Optional[AiRoute] = None
    ):
        chosen_model = model or AiRoute.DEFAULT_MODEL
        chosen_target = ai_target if ai_target is not None else AiRoute.detect_target(chosen_model)

        self.ai = SuggestionAIClient(
            api_key=api_key,
            model=chosen_model,
            ai_target=chosen_target,
            ai_route=ai_route
        )
        self.executor = SearchExecutor()
        self.user_data = user_data if user_data != {'list': {}} else {"list": {"없음": {"src": "None"}}}
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
        self.log("info", "사용자 감상 이력 데이터베이스 로드 중...")
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

        return {"items": history_items, "read_urls": read_urls}

    def run_recommendation(
        self,
        top_k: int = 5,
        user_custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = datetime.now()
        PrintIo("=== 신규 파이프라인 가동 ===")

        try:
            history = self.get_read_history()
            history_items = history["items"]
            read_urls = history["read_urls"]

            if not history_items:
                msg = "읽은 작품 기록이 없습니다."
                return {"error": msg, "recommended_works": []}

            system_data = load_data()
            excluded_dict = system_data.get("recommend_excluded", {})
            excluded_urls = set()
            excluded_titles = set()

            for k, info in excluded_dict.items():
                if k.startswith("http"):
                    excluded_urls.add(normalize_url(k))
                if isinstance(info, dict):
                    u = info.get("url")
                    if u:
                        excluded_urls.add(normalize_url(u))
                    for t_field in ["title", "title_ko"]:
                        t_val = info.get(t_field)
                        if t_val:
                            excluded_titles.add(t_val.strip().lower().replace(" ", ""))
                elif isinstance(info, str) and info.strip():
                    excluded_titles.add(info.strip().lower().replace(" ", ""))

            candidates, history_analysis, main_request = self.agent.run_search_loop(
                history_items=history_items,
                read_urls=read_urls,
                user_custom_prompt=user_custom_prompt,
                top_k=top_k,
                excluded_urls=excluded_urls,
                excluded_titles=excluded_titles
            )

            PrintIo(f"\n[최종 탐색 결산] 총 {len(candidates)}개 후보 확보")
            self.log(
                "info",
                f"누적 확보된 {len(candidates)}작품 중 최상위 {top_k}작품 선별 진행..."
            )

            final_result = self.ranker.rerank_and_synthesize(
                history_analysis=history_analysis,
                main_request=main_request,
                candidates=candidates,
                top_k=top_k
            )
            final_result["user_custom_prompt"] = user_custom_prompt
            final_result["main_request"] = main_request

            duration = (datetime.now() - start_time).total_seconds()
            PrintIo(f"=== 추천 파이프라인 완료 ({duration:.2f}초 소요) ===")
            return final_result

        except Exception as e:
            PrintIo(f"[치명적 오류]: {e}\n{traceback.format_exc()}")
            return {"error": str(e), "recommended_works": []}