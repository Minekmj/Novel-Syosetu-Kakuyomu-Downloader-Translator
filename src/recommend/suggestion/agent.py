import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections.abc import Callable

from .executor import SearchExecutor
from .specs import PLATFORM_SPEC_TEXT, build_search_params
from .utils import PrintIo, RecommendationCancelled, check_cancelled, normalize_url, extract_json_from_response, site_delay_all
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
        log_callback: Optional[Callable] = None,
        check_callback: Optional[Callable[[], bool]] = None
    ):
        self.ai = ai_client
        self.executor = executor
        self.site_meta = site_meta
        self.site_success_counts = site_success_counts
        self.log = log_callback or (lambda *args, **kwargs: None)
        self.check = check_callback or (lambda: False)
        self.back_decision = ""
        self.round_search_logs: Dict[str, List[Dict[str, Any]]] = {}
        self.conversation_history: List[Dict[str, str]] = []

    def _check_cancelled(self):
        check_cancelled(self.check)

    def _append_conversation(self, stage: str, content: str):
        text = str(content or "").strip()
        if not text:
            return
        self.conversation_history.append({
            "stage": stage,
            "content": text
        })

    def _format_conversation_history(self, limit: int = 16) -> str:
        if not self.conversation_history:
            return "이전 대화 및 추론 내역 없음"
        recent = self.conversation_history[-limit:]
        lines = []
        for idx, entry in enumerate(recent, 1):
            lines.append(f"{idx}. [{entry.get('stage', '기록')}] {entry.get('content', '')}")
        return "\n".join(lines)

    def _normalize_story_text(self, text: str) -> str:
        return re.sub(r'[\s\W_]+', '', str(text or ""))

    def _is_duplicate_story(self, story_text: str, signatures: List[str]) -> bool:
        if not story_text or not signatures:
            return False
        norm = self._normalize_story_text(story_text)
        if len(norm) < 40:
            return False
        for sig in signatures:
            if len(sig) < 40:
                continue
            if sig[:45] in norm or norm[:45] in sig:
                return True
        return False

    def analyze_user_context(
        self,
        history_items: List[Dict[str, Any]],
        user_custom_prompt: Optional[str]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
        self._check_cancelled()
        raw_user_request = user_custom_prompt if (user_custom_prompt and str(user_custom_prompt).strip()) else "없음"
        current_date = datetime.now().strftime("%Y-%m-%d")

        raw_list = [
            {
                "title": h.get("title", ""),
                "story": (h.get("story", "") or "")[:800],
                "keywords": h.get("keywords", [])
            }
            for h in history_items
        ]
        prompt = ANALYZE_PROFILE_PROMPT.format(
            current_date=current_date,
            user_custom_prompt=raw_user_request,
            history_raw_json=json.dumps(raw_list, ensure_ascii=False, indent=2),
            conversation_history_text=self._format_conversation_history(limit=10)
        )
        system_prompt = ANALYZE_PROFILE_SYSTEM.format(current_date=current_date)

        parsed = {}
        for _ in range(3):
            self._check_cancelled()
            raw = self.ai.generate(prompt, system_prompt)
            self._check_cancelled()
            if not raw and self.ai.last_error:
                break
            candidate_parsed = extract_json_from_response(raw)
            if isinstance(candidate_parsed, dict) and (
                "ai" in candidate_parsed or "main_request" in candidate_parsed
            ):
                parsed = candidate_parsed
                break

        raw_ai = parsed.get("ai")
        if not isinstance(raw_ai, dict):
            raw_ai = parsed.get("main_request")
        if not isinstance(raw_ai, dict):
            raw_ai = {}

        hard_constraints = raw_ai.get("hard_constraints") if isinstance(raw_ai.get("hard_constraints"), list) else []
        if not hard_constraints and raw_user_request != "없음":
            hard_constraints = [raw_user_request]

        raw_tp = raw_ai.get("taste_profile")
        if not isinstance(raw_tp, dict):
            raw_tp = {}

        taste_profile = {
            "dominant_genres": raw_tp.get("dominant_genres") if isinstance(raw_tp.get("dominant_genres"), list) else [],
            "protagonist_archetype": raw_tp.get("protagonist_archetype") or "감상 이력 기반 주인공 성향",
            "story_drive_and_catharsis": raw_tp.get("story_drive_and_catharsis") or (raw_ai.get("core_appeal") or "흥미로운 전개와 캐릭터 매력"),
            "preferred_tone_and_pacing": raw_tp.get("preferred_tone_and_pacing") or "감상 이력 중심의 자연스러운 톤과 템포",
            "relationship_and_romance_stance": raw_tp.get("relationship_and_romance_stance") or "감상 이력 작품들의 연애·인간관계 비중 유지",
            "common_keywords_pattern": raw_tp.get("common_keywords_pattern") if isinstance(raw_tp.get("common_keywords_pattern"), list) else [],
            "taste_mismatch_warnings": raw_tp.get("taste_mismatch_warnings") if isinstance(raw_tp.get("taste_mismatch_warnings"), list) else []
        }

        ai_analysis = {
            "user_intent": raw_ai.get("user_intent") or (raw_user_request if raw_user_request != "없음" else "감상 이력 취향 기반 추천"),
            "taste_profile": taste_profile,
            "hidden_preferences": raw_ai.get("hidden_preferences") or "자연스러운 전개 및 이야기 완성도",
            "hard_constraints": hard_constraints,
            "taboos": raw_ai.get("taboos") if isinstance(raw_ai.get("taboos"), list) else [],
            "core_appeal": raw_ai.get("core_appeal") or taste_profile["story_drive_and_catharsis"],
            "target_japanese_tags": raw_ai.get("target_japanese_tags") if isinstance(raw_ai.get("target_japanese_tags"), list) else [],
            "search_direction": raw_ai.get("search_direction") or "감상 이력 핵심 장르와 태그 중심의 다중 플랫폼 탐색"
        }

        raw_user_list = parsed.get("user_list")
        parsed_by_title: Dict[str, Dict[str, Any]] = {}
        if isinstance(raw_user_list, dict):
            for k, v in raw_user_list.items():
                if isinstance(v, dict):
                    t_key = str(v.get("제목") or k).strip()
                    parsed_by_title[t_key] = v
        elif isinstance(parsed.get("history_analysis"), list):
            for v in parsed.get("history_analysis", []):
                if isinstance(v, dict) and v.get("title"):
                    parsed_by_title[str(v.get("title")).strip()] = {
                        "제목": v.get("title", ""),
                        "내용 ai 중심 요약": v.get("story_summary", ""),
                        "태그들": v.get("core_keywords", [])
                    }

        user_list: Dict[str, Dict[str, Any]] = {}
        history_analysis: List[Dict[str, Any]] = []

        for h in history_items:
            title = str(h.get("title", "")).strip()
            if not title:
                continue
            matched = parsed_by_title.get(title, {})
            summary = str(matched.get("내용 ai 중심 요약") or matched.get("story_summary") or (h.get("story", "") or "")[:150]).strip()
            genre_mood = str(matched.get("장르_및_분위기") or "").strip()
            protagonist = str(matched.get("주인공_유형") or "").strip()
            core_fun = str(matched.get("핵심_재미_요소") or "").strip()
            tags = matched.get("태그들") or matched.get("core_keywords") or list(h.get("keywords", []))[:5]
            if not isinstance(tags, list):
                tags = []

            user_list[title] = {
                "제목": title,
                "내용 ai 중심 요약": summary,
                "장르_및_분위기": genre_mood,
                "주인공_유형": protagonist,
                "핵심_재미_요소": core_fun,
                "태그들": tags
            }
            history_analysis.append({
                "title": title,
                "story_summary": summary,
                "genre_and_mood": genre_mood,
                "protagonist_type": protagonist,
                "core_fun": core_fun,
                "core_keywords": tags
            })

        user_profile = {
            "user": raw_user_request,
            "ai": ai_analysis,
            "user_list": user_list
        }

        main_request = dict(ai_analysis)
        main_request["user_request"] = raw_user_request

        dominant_str = ", ".join(str(x) for x in taste_profile.get("dominant_genres", [])) or "미정"
        self._append_conversation(
            "프로필 분석",
            f"요청 원문: {raw_user_request} | 주류 취향 장르: {dominant_str} | "
            f"주인공 성향: {taste_profile['protagonist_archetype']} | 연애 비중: {taste_profile['relationship_and_romance_stance']} | "
            f"필수 조건: {', '.join(ai_analysis['hard_constraints']) or '없음'} | 탐색 방향: {ai_analysis['search_direction']}"
        )

        return history_analysis, main_request, user_profile

    def decide_searches(
        self,
        round_num: int,
        user_profile: Dict[str, Any],
        collected_summary: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        self._check_cancelled()
        platform_counts = {'kakuyomu': 0, 'naro': 0, 'hameln': 0}
        for c in collected_summary:
            st = c.get('site_type')
            if st in platform_counts:
                platform_counts[st] += 1

        recent_round_keys = list(self.round_search_logs.keys())[-6:]
        recent_round_logs = {k: self.round_search_logs[k] for k in recent_round_keys}

        prompt = SEARCH_DECISION_PROMPT.format(
            current_date=datetime.now().strftime("%Y-%m-%d"),
            platform_spec_text=PLATFORM_SPEC_TEXT,
            user_profile_json=json.dumps(user_profile, ensure_ascii=False, indent=2),
            conversation_history_text=self._format_conversation_history(limit=16),
            round_num=round_num,
            candidates_count=len(collected_summary),
            platform_counts_json=json.dumps(platform_counts, ensure_ascii=False),
            round_search_log_json=json.dumps(recent_round_logs, ensure_ascii=False, indent=2) if recent_round_logs else "이전 검색 기록 없음 (초기 탐색)"
        )

        for _ in range(3):
            self._check_cancelled()
            raw_res = self.ai.generate(prompt, SEARCH_DECISION_SYSTEM)
            self._check_cancelled()
            if not raw_res and self.ai.last_error:
                break
            parsed = extract_json_from_response(raw_res)
            if isinstance(parsed, dict) and ("actions" in parsed or "decision" in parsed):
                return parsed
        return {"ai_thought": "탐색 전략 응답을 받지 못해 현재까지 모은 작품으로 정리합니다.", "decision": "FINISH", "actions": []}

    def triage_candidates(
        self,
        items_to_triage: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        known_excluded_titles: List[str]
    ) -> Dict[int, Dict[str, Any]]:
        self._check_cancelled()
        if not items_to_triage:
            return {}

        current_date = datetime.now().strftime("%Y-%m-%d")
        ai_section = user_profile.get("ai", {})
        hard_constraints = ai_section.get("hard_constraints", [])
        taste_profile = ai_section.get("taste_profile", {})
        simplified_list = []
        for idx, it in enumerate(items_to_triage):
            simplified_list.append({
                "id": idx,
                "title": it.get("title", ""),
                "updated_at": it.get("updated_at", ""),
                "serial_status": it.get("serial_status", ""),
                "episodes": it.get("status_episodes", ""),
                "keywords": it.get("keywords", []),
                "story_preview": (it.get("story", "") or "")[:250]
            })

        prompt = TRIAGE_PROMPT.format(
            current_date=current_date,
            hard_constraints_json=json.dumps(hard_constraints, ensure_ascii=False),
            taste_profile_json=json.dumps(taste_profile, ensure_ascii=False, indent=2),
            user_profile_json=json.dumps(user_profile, ensure_ascii=False, indent=2),
            excluded_titles_json=json.dumps(known_excluded_titles, ensure_ascii=False),
            conversation_history_text=self._format_conversation_history(limit=12),
            items_count=len(simplified_list),
            items_json=json.dumps(simplified_list, ensure_ascii=False, indent=2)
        )

        system_prompt = TRIAGE_SYSTEM.format(current_date=current_date)

        try:
            parsed = {}
            for _ in range(3):
                self._check_cancelled()
                raw_res = self.ai.generate(prompt, system_prompt)
                self._check_cancelled()
                if not raw_res and self.ai.last_error:
                    break
                candidate_parsed = extract_json_from_response(raw_res)
                if isinstance(candidate_parsed, dict) and "triage_results" in candidate_parsed:
                    parsed = candidate_parsed
                    break
            results = parsed.get("triage_results", [])

            status_map: Dict[int, Dict[str, Any]] = {}
            for r in results:
                if not isinstance(r, dict) or "id" not in r:
                    continue
                try:
                    item_id = int(r["id"])
                except (ValueError, TypeError):
                    continue

                constraint_ok = r.get("constraint_ok", True)
                status = str(r.get("status", "의심")).strip()
                raw_score = r.get("score")
                try:
                    score = int(raw_score)
                except (ValueError, TypeError):
                    if any(x in status for x in ["버려", "삭제", "제외", "탈락"]):
                        score = 20
                    elif "줄거리" in status:
                        score = 72
                    else:
                        score = 52
                score = max(0, min(100, score))
                reason = str(r.get("reason", "")).strip()

                if constraint_ok is False or str(constraint_ok).lower() == "false":
                    status = "버려"
                    score = 0

                status_map[item_id] = {
                    "status": status,
                    "score": score,
                    "reason": reason
                }

            for idx in range(len(items_to_triage)):
                if idx not in status_map:
                    status_map[idx] = {"status": "의심", "score": 50, "reason": "세부 내용 확인 필요"}

            return status_map
        except RecommendationCancelled:
            raise
        except Exception:
            return {
                idx: {"status": "의심", "score": 50, "reason": "세부 내용 확인 필요"}
                for idx in range(len(items_to_triage))
            }

    def run_search_loop(
        self,
        history_items: List[Dict[str, Any]],
        read_urls: set,
        user_custom_prompt: Optional[str],
        top_k: int = 5,
        excluded_urls: Optional[set] = None,
        excluded_titles: Optional[set] = None,
        excluded_titles_raw: Optional[List[str]] = None,
        initial_conversation_history: Optional[List[Dict[str, str]]] = None,
        check_callback: Optional[Callable[[], bool]] = None
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any], Dict[str, Any], List[Dict[str, str]]]:
        if check_callback is not None:
            self.check = check_callback
        self._check_cancelled()

        self.conversation_history = list(initial_conversation_history) if initial_conversation_history else []
        self.round_search_logs = {}
        self.back_decision = ""

        self.log("info", "감상 이력 및 요청 조건 분석 진행 중...")
        history_analysis, main_request, user_profile = self.analyze_user_context(history_items, user_custom_prompt)
        self._check_cancelled()

        read_titles = {
            h.get("title", "").strip().lower().replace(" ", "")
            for h in history_items
            if h.get("title") and h.get("title") != "없음"
        }

        read_story_signatures: List[str] = []
        for h in history_items:
            norm_s = self._normalize_story_text(h.get("story", ""))
            if len(norm_s) >= 40:
                read_story_signatures.append(norm_s[:80])

        known_excluded_titles: List[str] = []
        seen_known = set()
        for h in history_items:
            t = str(h.get("title", "")).strip()
            if t and t != "없음" and t not in seen_known:
                seen_known.add(t)
                known_excluded_titles.append(t)
        for t in (excluded_titles_raw or []):
            t_str = str(t).strip()
            if t_str and t_str != "없음" and t_str not in seen_known:
                seen_known.add(t_str)
                known_excluded_titles.append(t_str)

        ex_urls = excluded_urls or set()
        ex_titles = excluded_titles or set()

        all_candidates: Dict[str, Dict[str, Any]] = {}
        all_evaluated_items: Dict[str, Dict[str, Any]] = {}
        discarded_urls: set = set()

        max_agent_rounds = 7
        round_idx = 0
        round_all = 0
        round_miss = 0

        while round_idx < max_agent_rounds:
            self._check_cancelled()
            round_idx += 1
            round_all += 1

            if self.back_decision == "FINISH":
                break

            if sum(self.site_success_counts.values()) >= 20:
                break

            PrintIo(f"\n[라운드 {round_idx}/{max_agent_rounds}] 쿼리 전략 수립")
            plan = self.decide_searches(
                round_num=round_all,
                user_profile=user_profile,
                collected_summary=list(all_candidates.values())
            )
            self._check_cancelled()

            ai_thought = str(plan.get("ai_thought", "")).strip()
            decision = str(plan.get("decision", "CONTINUE")).upper()
            actions = plan.get("actions", [])
            if not isinstance(actions, list):
                actions = []

            PrintIo(f"[AI 분석 보고]: {ai_thought}")
            if ai_thought:
                self.log("ai", ai_thought)
            self.back_decision = decision

            action_reasons = [
                f"{a.get('site', '')}: {a.get('reason', '')}"
                for a in actions
                if isinstance(a, dict) and a.get("reason")
            ]
            self._append_conversation(
                f"{round_all}라운드 전략({decision})",
                f"{ai_thought} | 세부 근거: {' / '.join(action_reasons) if action_reasons else '없음'}"
            )

            if len(actions) == 0:
                if self.back_decision == "FINISH":
                    break

            round_key = f"{round_all}라운드"
            self.round_search_logs[round_key] = []

            round_pending_items: List[Dict[str, Any]] = []
            action_meta_list: List[Dict[str, Any]] = []

            for act in actions:
                self._check_cancelled()
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

                other_options = {
                    "page": page,
                    "genre": params.get("genre_name") if site == "kakuyomu" else params.get("genre_val"),
                    "order": params.get("order"),
                    "serial_status": params.get("serial_status"),
                    "last_published": params.get("last_published"),
                    "min_pt": params.get("min_start", 0) if site == "kakuyomu" else params.get("min_pt", 0),
                    "min_chars": params.get("min_chars", 0),
                    "exclude_words": params.get("exclude_words", []),
                    "inclusion_flags": params.get("inclusion_flag") if site == "kakuyomu" else params.get("inclusion_flags", []),
                    "exclusion_flags": params.get("exclusion_flag") if site == "kakuyomu" else params.get("exclusion_flags", []),
                    "origin": params.get("origin", "")
                }

                PrintIo(f"[{site_name}] 검색 호출: p.{page}, Q:'{params.get('query')}'")

                action_idx = len(action_meta_list)

                try:
                    result = self.executor.run_search_with_retry(site, site_cls, params)
                    self._check_cancelled()
                    site_delay_all(site, self.check)
                    self._check_cancelled()
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

                        if self._is_duplicate_story(it.get("story", ""), read_story_signatures):
                            continue

                        if u and u not in read_urls and u not in all_candidates and u not in discarded_urls:
                            if any(normalize_url(x.get("url", "")) == u for x in round_pending_items):
                                continue
                            it["site_type"] = site
                            it["_site_cls"] = site_cls
                            it["_action_idx"] = action_idx
                            round_pending_items.append(it)
                            valid_action_items.append(it)

                    self.log("info", f"[{site_name}] {len(valid_action_items)}작품")

                    action_meta_list.append({
                        "action_idx": action_idx,
                        "site": site,
                        "site_label": f"{site_name} ({site})",
                        "query": params.get("query", ""),
                        "options": other_options,
                        "status": "SUCCESS" if raw_items else "EMPTY",
                        "raw_count": len(raw_items),
                        "valid_count": len(valid_action_items)
                    })

                except RecommendationCancelled:
                    raise
                except Exception as e:
                    self._check_cancelled()
                    PrintIo(f"   => [검색 실패]: {e}")
                    self.log("info", f"[{site_name}] 연결 지연 발생")
                    action_meta_list.append({
                        "action_idx": action_idx,
                        "site": site,
                        "site_label": f"{site_name} ({site})",
                        "query": params.get("query", ""),
                        "options": other_options,
                        "status": f"FAILED: {e}",
                        "raw_count": 0,
                        "valid_count": 0
                    })

            if not round_pending_items:
                for act_meta in action_meta_list:
                    self.round_search_logs[round_key].append({
                        "사이트 이름": act_meta["site_label"],
                        "검색 결과 나온 작품 수": act_meta["raw_count"],
                        "최종 통과 작품 수": 0,
                        "검색 쿼리": act_meta["query"],
                        "그외 검색 옵션들": act_meta["options"],
                        "상태": act_meta["status"],
                        "통과 작품 요약": []
                    })
                self._append_conversation(
                    f"{round_all}라운드 결과",
                    "신규 작품 0건. 필수 조건과 기간은 유지하고 taste_profile 기반의 검색어, 정렬, 하한 기준만 조정할 필요가 있음."
                )
                if round_miss < 3:
                    round_idx -= 1
                    round_miss += 1
                continue

            round_miss = 0

            self._check_cancelled()
            self.log("info", f"신규 {len(round_pending_items)}작품 분리 진행...")
            triage_map = self.triage_candidates(round_pending_items, user_profile, known_excluded_titles)
            self._check_cancelled()

            triage_stats = {"통과": 0, "버려": 0}
            passed_by_action: Dict[int, List[Dict[str, Any]]] = {}

            for idx, it in enumerate(round_pending_items):
                self._check_cancelled()
                u = normalize_url(it.get("url", ""))
                site = it.get("site_type", "kakuyomu")
                site_cls = it.get("_site_cls")
                a_idx = it.get("_action_idx", -1)

                decision_info = triage_map.get(idx, {"status": "의심", "score": 50, "reason": ""})
                raw_status = str(decision_info.get("status", "의심")).strip()
                triage_score = int(decision_info.get("score", 50))
                triage_reason = str(decision_info.get("reason", "")).strip()

                it["triage_status"] = raw_status
                it["triage_score"] = triage_score
                it["triage_reason"] = triage_reason

                if any(x in raw_status for x in ["버려", "삭제", "제외", "탈락"]):
                    discarded_urls.add(u)
                    if triage_score > 0:
                        all_evaluated_items[u] = it
                    triage_stats["버려"] += 1
                    continue

                try:
                    enriched_story = self.executor.enrich_description(site, site_cls, it)
                    self._check_cancelled()
                    if self._is_duplicate_story(enriched_story, read_story_signatures):
                        discarded_urls.add(u)
                        triage_stats["버려"] += 1
                        continue
                    it["story"] = enriched_story
                except RecommendationCancelled:
                    raise
                except Exception:
                    self._check_cancelled()

                triage_stats["통과"] += 1
                all_evaluated_items[u] = it
                all_candidates[u] = it
                passed_by_action.setdefault(a_idx, []).append(it)

            self.log(
                "info",
                f"{len(round_pending_items)}작품 중 {triage_stats['통과']}작품 통과 (누적 후보: {len(all_candidates)}작품)"
            )

            round_summary_parts = []
            for act_meta in action_meta_list:
                a_idx = act_meta["action_idx"]
                passed_items = passed_by_action.get(a_idx, [])
                summarized_works = []
                for it in passed_items:
                    summarized_works.append({
                        "title": it.get("title", ""),
                        "keywords": list(it.get("keywords", []))[:6],
                        "updated_at": it.get("updated_at", ""),
                        "story_summary": (it.get("story", "") or "")[:180],
                        "episodes": it.get("status_episodes", ""),
                        "serial_status": it.get("serial_status", "")
                    })

                self.round_search_logs[round_key].append({
                    "사이트 이름": act_meta["site_label"],
                    "검색 결과 나온 작품 수": act_meta["raw_count"],
                    "최종 통과 작품 수": len(passed_items),
                    "검색 쿼리": act_meta["query"],
                    "그외 검색 옵션들": act_meta["options"],
                    "상태": act_meta["status"],
                    "통과 작품 요약": summarized_works
                })
                round_summary_parts.append(
                    f"{act_meta['site_label']}(쿼리:'{act_meta['query']}', 결과:{act_meta['raw_count']}건, 통과:{len(passed_items)}건)"
                )

            self._append_conversation(
                f"{round_all}라운드 결과",
                f"심사 {len(round_pending_items)}건 중 {triage_stats['통과']}건 통과, {triage_stats['버려']}건 제외 | "
                f"세부: {', '.join(round_summary_parts)}"
            )

        self._check_cancelled()

        if not all_candidates and all_evaluated_items:
            self.log("info", "통과 작품이 없어 차점 순으로 대체 후보 구성...")
            fallback_pool = sorted(
                all_evaluated_items.values(),
                key=lambda x: int(x.get("triage_score", 0) or 0),
                reverse=True
            )[:max(top_k * 2, 10)]

            for it in fallback_pool:
                self._check_cancelled()
                u = normalize_url(it.get("url", ""))
                site = it.get("site_type", "kakuyomu")
                site_cls = it.get("_site_cls")
                try:
                    enriched_story = self.executor.enrich_description(site, site_cls, it)
                    self._check_cancelled()
                    if self._is_duplicate_story(enriched_story, read_story_signatures):
                        continue
                    it["story"] = enriched_story
                except RecommendationCancelled:
                    raise
                except Exception:
                    self._check_cancelled()
                all_candidates[u] = it

            self._append_conversation(
                "대체 후보 복원",
                f"통과 작품 0건으로 차점 상위 {len(all_candidates)}작품을 대체 후보로 복원함"
            )

        self._check_cancelled()

        sorted_candidates = sorted(
            all_candidates.values(),
            key=lambda x: int(x.get("triage_score", 0) or 0),
            reverse=True
        )

        return sorted_candidates, history_analysis, main_request, user_profile, self.conversation_history