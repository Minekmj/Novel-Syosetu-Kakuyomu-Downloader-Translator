import json
from typing import List, Dict, Any, Optional
from collections.abc import Callable

from .executor import SearchExecutor
from .specs import PLATFORM_SPEC_TEXT, build_search_params
from .utils import PrintIo, normalize_url, extract_json_from_response, site_delay_all
from .ai_client import SuggestionAIClient
from .prompts import (
    ANALYZE_PROFILE_SYSTEM,
    ANALYZE_PROFILE_PROMPT,
    SEARCH_DECISION_SYSTEM,
    SEARCH_DECISION_PROMPT,
    TRIAGE_SYSTEM,
    TRIAGE_PROMPT
)

class SearchAgent:
    def __init__(
        self,
        ai_client: SuggestionAIClient,
        executor: SearchExecutor,
        site_meta: Dict[str, Any],
        site_success_counts: Dict[str, int],
        log_callback: Optional[Callable] = None
    ):
        self.ai = ai_client
        self.executor = executor
        self.site_meta = site_meta
        self.site_success_counts = site_success_counts
        self.log = log_callback or (lambda *args, **kwargs: None)
        self.back_decision = ""
        self.search_memory: List[Dict[str, Any]] = []

    def analyze_user_context(
        self,
        history_items: List[Dict[str, Any]],
        user_custom_prompt: Optional[str]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        raw_list = [
            {
                h.get("title", ""): {
                    "story": h.get("story", ""),
                    "keywords": h.get("keywords", [])
                }
            }
            for h in history_items
        ]
        prompt = ANALYZE_PROFILE_PROMPT.format(
            user_custom_prompt=user_custom_prompt or "없음",
            history_raw_json=json.dumps(raw_list, ensure_ascii=False, indent=2)
        )

        parsed = {}
        for _ in range(3):
            raw = self.ai.generate(prompt, ANALYZE_PROFILE_SYSTEM)
            parsed = extract_json_from_response(raw)
            if isinstance(parsed, dict) and "main_request" in parsed:
                break

        history_analysis = parsed.get("history_analysis", [])
        if not history_analysis:
            history_analysis = [
                {
                    "title": h.get("title", ""),
                    "story_summary": (h.get("story", "") or "")[:150],
                    "core_keywords": h.get("keywords", [])[:5]
                }
                for h in history_items
            ]

        main_request = parsed.get("main_request", {
            "user_intent": user_custom_prompt or "취향 기반 추천",
            "hidden_preferences": "자연스러운 전개 및 완성도",
            "taboos": [],
            "core_appeal": "흥미로운 서사 구조",
            "target_japanese_tags": []
        })

        return history_analysis, main_request

    def decide_searches(
        self,
        round_num: int,
        main_request: Dict[str, Any],
        history_analysis: List[Dict[str, Any]],
        collected_summary: List[Dict[str, Any]],
        top_k: int = 5
    ) -> Dict[str, Any]:
        platform_counts = {'kakuyomu': 0, 'naro': 0, 'hameln': 0}
        for c in collected_summary:
            st = c.get('site_type')
            if st in platform_counts:
                platform_counts[st] += 1

        recent_memory = self.search_memory[-8:]
        prompt = SEARCH_DECISION_PROMPT.format(
            platform_spec_text=PLATFORM_SPEC_TEXT,
            main_request_json=json.dumps(main_request, ensure_ascii=False, indent=2),
            history_analysis_json=json.dumps(history_analysis, ensure_ascii=False, indent=2),
            round_num=round_num,
            candidates_count=len(collected_summary),
            platform_counts_json=json.dumps(platform_counts, ensure_ascii=False),
            search_memory_json=json.dumps(recent_memory, ensure_ascii=False, indent=2) if recent_memory else "이전 검색 기록 없음 (초기 탐색)"
        )

        raw_res = self.ai.generate(prompt, SEARCH_DECISION_SYSTEM)
        return extract_json_from_response(raw_res)

    def triage_candidates(
        self,
        items_to_triage: List[Dict[str, Any]],
        main_request: Dict[str, Any],
        history_analysis: List[Dict[str, Any]]
    ) -> Dict[int, Dict[str, str]]:
        if not items_to_triage:
            return {}

        simplified_list = []
        for idx, it in enumerate(items_to_triage):
            simplified_list.append({
                "id": idx,
                "title": it.get("title", ""),
                "keywords": it.get("keywords", []),
                "story_preview": (it.get("story", "") or "")[:250]
            })

        prompt = TRIAGE_PROMPT.format(
            main_request_json=json.dumps(main_request, ensure_ascii=False, indent=2),
            history_analysis_json=json.dumps(history_analysis, ensure_ascii=False, indent=2),
            items_count=len(simplified_list),
            items_json=json.dumps(simplified_list, ensure_ascii=False, indent=2)
        )

        try:
            parsed = {}
            for _ in range(3):
                raw_res = self.ai.generate(prompt, TRIAGE_SYSTEM)
                parsed = extract_json_from_response(raw_res)
                if parsed != {}:
                    break
            results = parsed.get("triage_results", [])

            status_map = {}
            for r in results:
                if isinstance(r, dict) and "id" in r:
                    status_map[r["id"]] = {"status": r.get("status", "의심")}

            for idx in range(len(items_to_triage)):
                if idx not in status_map:
                    status_map[idx] = {"status": "의심"}

            return status_map
        except Exception:
            return {idx: {"status": "의심"} for idx in range(len(items_to_triage))}

    def run_search_loop(
        self,
        history_items: List[Dict[str, Any]],
        read_urls: set,
        user_custom_prompt: Optional[str],
        top_k: int = 5,
        excluded_urls: Optional[set] = None,
        excluded_titles: Optional[set] = None
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        self.log("info", "감상 이력 및 요청 조건 분석 진행 중...")
        history_analysis, main_request = self.analyze_user_context(history_items, user_custom_prompt)

        read_titles = {
            h.get("title", "").strip().lower().replace(" ", "")
            for h in history_items
            if h.get("title")
        }

        ex_urls = excluded_urls or set()
        ex_titles = excluded_titles or set()

        all_candidates: Dict[str, Dict[str, Any]] = {}
        discarded_urls: set = set()
        self.search_memory = []

        max_agent_rounds = 7
        round_idx = 0
        round_all = 0
        round_miss = 0

        while round_idx < max_agent_rounds:
            round_idx += 1
            round_all += 1

            if self.back_decision == "FINISH":
                break

            if sum(self.site_success_counts.values()) >= 20:
                break

            PrintIo(f"\n[라운드 {round_idx}/{max_agent_rounds}] 쿼리 전략 수립")
            plan = self.decide_searches(
                round_num=round_all,
                main_request=main_request,
                history_analysis=history_analysis,
                collected_summary=list(all_candidates.values()),
                top_k=top_k
            )

            ai_thought = plan.get("ai_thought", "")
            decision = str(plan.get("decision", "CONTINUE")).upper()
            actions = plan.get("actions", [])
            if not isinstance(actions, list):
                actions = []

            PrintIo(f"[AI 분석 보고]: {ai_thought}")
            if ai_thought:
                self.log("ai", ai_thought)
            self.back_decision = decision

            if len(actions) == 0:
                if self.back_decision == "FINISH" and len(all_candidates) >= top_k:
                    break

            round_pending_items: List[Dict[str, Any]] = []
            action_meta_list: List[Dict[str, Any]] = []

            for act in actions:
                if not isinstance(act, dict):
                    continue
                site = act.get("site", "kakuyomu")
                if site not in self.site_meta:
                    continue

                site_name = self.site_meta[site].get("name", site)

                try:
                    page = int(act.get("page", 1) or 1)
                except (ValueError, TypeError):
                    page = 1

                site_cls = self.site_meta[site]['cls']
                params = build_search_params(site, act, page=page)

                PrintIo(f"▶ [{site_name}] 검색 호출: p.{page}, Q:'{params.get('query')}'")

                try:
                    result = self.executor.run_search_with_retry(site, site_cls, params)
                    site_delay_all(site)
                    raw_items = result.get("items", []) if isinstance(result, dict) else []
                    self.site_success_counts[site] += 1

                    valid_action_items = []
                    for it in raw_items:
                        if not isinstance(it, dict):
                            continue
                        u = normalize_url(it.get("url", ""))
                        title_clean = it.get("title", "").strip().lower().replace(" ", "")

                        if title_clean in read_titles or title_clean in ex_titles:
                            continue

                        if u in ex_urls:
                            continue

                        if u and u not in read_urls and u not in all_candidates and u not in discarded_urls:
                            if any(normalize_url(x.get("url", "")) == u for x in round_pending_items):
                                continue
                            it["site_type"] = site
                            it["_site_cls"] = site_cls
                            it["_action_idx"] = len(action_meta_list)
                            round_pending_items.append(it)
                            valid_action_items.append(it)

                    self.log("info", f"[{site_name}] {len(valid_action_items)}작품")

                    action_meta_list.append({
                        "search_params": {
                            "site": site,
                            "page": page,
                            "genre": params.get("genre_name") or params.get("genre_val"),
                            "order": params.get("order"),
                            "min_pt": params.get("min_pt") or params.get("min_start", 0),
                            "exclude_words": params.get("exclude_words", [])
                        },
                        "status": "SUCCESS" if raw_items else "EMPTY",
                        "raw_count": len(raw_items),
                        "items_captured": valid_action_items
                    })

                except Exception as e:
                    PrintIo(f"   => [검색 실패]: {e}")
                    self.log("info", f"[{site_name}] 연결 지연 발생")
                    self.search_memory.append({
                        "search_params": {
                            "site": site,
                            "page": page
                        },
                        "status": f"FAILED: {e}",
                        "results": []
                    })

            if not round_pending_items:
                for act_meta in action_meta_list:
                    self.search_memory.append({
                        "search_params": act_meta["search_params"],
                        "status": act_meta["status"],
                        "results": []
                    })
                if round_miss < 3:
                    round_idx -= 1
                    round_miss += 1
                continue

            round_miss = 0

            self.log("info", f"신규 {len(round_pending_items)}작품 분리 진행...")
            triage_map = self.triage_candidates(round_pending_items, main_request, history_analysis)

            triage_stats = {"통과": 0, "버려": 0}

            for idx, it in enumerate(round_pending_items):
                u = normalize_url(it.get("url", ""))
                site = it.get("site_type", "kakuyomu")
                site_cls = it.get("_site_cls")

                decision_info = triage_map.get(idx, {"status": "의심"})
                raw_status = str(decision_info.get("status", "의심")).strip()

                if any(x in raw_status for x in ["버려", "삭제", "제외", "탈락"]):
                    discarded_urls.add(u)
                    triage_stats["버려"] += 1
                    continue

                triage_stats["통과"] += 1
                try:
                    it["story"] = self.executor.enrich_description(site, site_cls, it)
                except Exception:
                    pass

                all_candidates[u] = it

            self.log(
                "info",
                f"{len(round_pending_items)}작품 중 {triage_stats['통과']}작품 통과 (누적 후보: {len(all_candidates)}작품)"
            )

            for act_meta in action_meta_list:
                summarized_works = []
                for it in act_meta["items_captured"]:
                    summarized_works.append({
                        "title": it.get("title", ""),
                        "keywords": list(it.get("keywords", []))[:6],
                        "updated_at": it.get("updated_at", ""),
                        "story_summary": (it.get("story", "") or "")[:180],
                        "episodes": it.get("status_episodes", ""),
                        "serial_status": it.get("serial_status", "")
                    })

                self.search_memory.append({
                    "search_params": act_meta["search_params"],
                    "status": act_meta["status"],
                    "raw_count": act_meta["raw_count"],
                    "passed_count": len(summarized_works),
                    "results": summarized_works
                })

        return list(all_candidates.values()), history_analysis, main_request