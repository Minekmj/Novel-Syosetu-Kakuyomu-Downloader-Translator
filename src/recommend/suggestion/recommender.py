import re
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from collections.abc import Callable

from src.ai import AiRoute
from src.system.data import load_data
from src.find.site import KakuyomuSearch, NaroSearch, SyosetuSearch
from .ai_client import SuggestionAIClient
from .executor import SearchExecutor
from .agent import SearchAgent
from .ranker import CandidateRanker
from .utils import PrintIo, RecommendationCancelled, check_cancelled, normalize_url


class NovelRecommender:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        user_data: dict = {"list": {"없음": {"src": "None"}}},
        log: Callable = None,
        ai_target: Optional[int] = None,
        ai_route: Optional[AiRoute] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        check: Optional[Callable[[], bool]] = None
    ):
        chosen_model = model or AiRoute.DEFAULT_MODEL
        chosen_target = ai_target if ai_target is not None else AiRoute.detect_target(chosen_model)

        self.log = log or (lambda *args, **kwargs: None)
        self.check = check or (lambda: False)
        self.ai = SuggestionAIClient(
            api_key=api_key,
            model=chosen_model,
            ai_target=chosen_target,
            ai_route=ai_route,
            log_callback=self.log,
            check_callback=self.check
        )
        self.executor = SearchExecutor(check_callback=self.check)
        self.user_data = user_data if user_data != {'list': {}} else {"list": {"없음": {"src": "None"}}}
        self.conversation_history: List[Dict[str, str]] = list(conversation_history) if conversation_history else []

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
            log_callback=self.log,
            check_callback=self.check
        )
        self.ranker = CandidateRanker(ai_client=self.ai, check_callback=self.check)

    def _apply_check_callback(self, active_check: Callable[[], bool]):
        self.ai.check = active_check
        self.executor.check = active_check
        self.agent.check = active_check
        self.ranker.check = active_check

    def _check_cancelled(self, active_check: Callable[[], bool]):
        check_cancelled(active_check)

    def _extract_error_code(self, e: Exception) -> str:
        for attr in ("code", "status_code", "status"):
            val = getattr(e, attr, None)
            if val is not None and str(val).strip():
                return str(val).strip()
        msg = str(e)
        m = re.search(
            r'\b([45]\d{2}|RESOURCE_EXHAUSTED|UNAVAILABLE|INVALID_ARGUMENT|PERMISSION_DENIED|UNAUTHENTICATED|DEADLINE_EXCEEDED|NOT_FOUND)\b',
            msg
        )
        if m:
            return m.group(1)
        return type(e).__name__

    def get_read_history(self, check_callback: Optional[Callable[[], bool]] = None) -> Dict[str, Any]:
        active_check = check_callback if check_callback is not None else self.check
        self._check_cancelled(active_check)

        self.log("info", "사용자 감상 이력 데이터베이스 로드 중...")
        PrintIo("[행동] 사용자 감상 목록 로드")
        user_data = self.user_data

        raw_list = user_data.get("list", {})
        history_items = []
        read_urls = set()

        for title, info in raw_list.items():
            self._check_cancelled(active_check)
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
                self._check_cancelled(active_check)
            except RecommendationCancelled:
                raise
            except Exception:
                self._check_cancelled(active_check)

            history_items.append(set_data)

        return {"items": history_items, "read_urls": read_urls}

    def run_recommendation(
        self,
        top_k: int = 5,
        user_custom_prompt: Optional[str] = None,
        previous_history: Optional[List[Dict[str, str]]] = None,
        check: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        start_time = datetime.now()
        PrintIo("=== 신규 파이프라인 가동 ===")
        active_check = check if check is not None else self.check
        self._apply_check_callback(active_check)

        try:
            self._check_cancelled(active_check)

            self.site_success_counts['kakuyomu'] = 0
            self.site_success_counts['naro'] = 0
            self.site_success_counts['hameln'] = 0

            history = self.get_read_history(check_callback=active_check)
            self._check_cancelled(active_check)
            history_items = history["items"]
            read_urls = history["read_urls"]

            if not history_items:
                msg = "읽은 작품 기록이 없습니다."
                return {"error": msg, "recommended_works": []}

            system_data = load_data()
            excluded_dict = system_data.get("recommend_excluded", {})
            excluded_urls = set()
            excluded_titles = set()
            excluded_titles_raw: List[str] = []

            for k, info in excluded_dict.items():
                if k.startswith("http"):
                    excluded_urls.add(normalize_url(k))
                if isinstance(info, dict):
                    u = info.get("url")
                    if u:
                        excluded_urls.add(normalize_url(u))
                    for t_field in ["title", "title_ko"]:
                        t_val = info.get(t_field)
                        if t_val and str(t_val).strip():
                            excluded_titles.add(str(t_val).strip().lower().replace(" ", ""))
                            excluded_titles_raw.append(str(t_val).strip())
                elif isinstance(info, str) and info.strip():
                    excluded_titles.add(info.strip().lower().replace(" ", ""))
                    excluded_titles_raw.append(info.strip())

            seed_history = previous_history if previous_history is not None else self.conversation_history

            candidates, history_analysis, main_request, user_profile, conv_history = self.agent.run_search_loop(
                history_items=history_items,
                read_urls=read_urls,
                user_custom_prompt=user_custom_prompt,
                top_k=top_k,
                excluded_urls=excluded_urls,
                excluded_titles=excluded_titles,
                excluded_titles_raw=excluded_titles_raw,
                initial_conversation_history=seed_history,
                check_callback=active_check
            )
            self._check_cancelled(active_check)

            all_excluded_for_ranker: List[str] = []
            seen_ex = set()
            for h in history_items:
                t = str(h.get("title", "")).strip()
                if t and t != "없음" and t not in seen_ex:
                    seen_ex.add(t)
                    all_excluded_for_ranker.append(t)
            for t in excluded_titles_raw:
                if t and t != "없음" and t not in seen_ex:
                    seen_ex.add(t)
                    all_excluded_for_ranker.append(t)

            PrintIo(f"\n[최종 탐색 결산] 총 {len(candidates)}개 후보 확보")
            self.log(
                "info",
                f"누적 {len(candidates)}작품 중 상위 {top_k}작품 선별 진행..."
            )

            self._check_cancelled(active_check)

            final_result = self.ranker.rerank_and_synthesize(
                history_analysis=history_analysis,
                main_request=main_request,
                candidates=candidates,
                top_k=top_k,
                user_profile=user_profile,
                conversation_history=conv_history,
                known_excluded_titles=all_excluded_for_ranker,
                check_callback=active_check
            )
            self._check_cancelled(active_check)

            rec_titles = [
                f"{w.get('title_ja', '')}"
                for w in final_result.get("recommended_works", [])
                if isinstance(w, dict)
            ]
            conv_history.append({
                "stage": "최종 추천 완료",
                "content": f"총평: {final_result.get('curator_note', '')} | 선별 작품: {', '.join(rec_titles) if rec_titles else '없음'}"
            })
            self.conversation_history = conv_history

            final_result["user_custom_prompt"] = user_custom_prompt
            final_result["main_request"] = main_request
            final_result["user_profile"] = user_profile
            final_result["conversation_history"] = conv_history

            duration = (datetime.now() - start_time).total_seconds()
            PrintIo(f"=== 추천 파이프라인 완료 ({duration:.2f}초 소요) ===")
            return final_result

        except RecommendationCancelled:
            self.log("info", "추천 작업이 중단되었습니다.")
            PrintIo("=== 추천 작업 중단 ===")
            return {"cancelled": True, "recommended_works": []}
        except Exception as e:
            err_code = self._extract_error_code(e)
            self.log("info", f'AI 호출 에러 "{err_code}"')
            PrintIo(f"[치명적 오류]: {e}\n{traceback.format_exc()}")
            return {"error": str(e), "recommended_works": []}