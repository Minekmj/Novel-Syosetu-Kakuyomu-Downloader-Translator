import json
from typing import List, Dict, Any, Optional, Set
from collections.abc import Callable

from .ai_client import GeminiAIClient
from .executor import SearchExecutor
from .specs import PLATFORM_SPEC_TEXT, build_search_params
from .utils import PrintIo, normalize_url, extract_json_from_response, site_delay_all

class SearchAgent:
    def __init__(
        self,
        ai_client: GeminiAIClient,
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

    def decide_searches(
        self,
        round_num: int,
        history_items: List[Dict[str, Any]],
        user_custom_prompt: Optional[str],
        collected_summary: List[Dict[str, Any]],
        search_history_logs: List[Dict[str, Any]],
        top_k: int = 5
    ) -> Dict[str, Any]:
        platform_counts = {'kakuyomu': 0, 'naro': 0, 'hameln': 0}
        for c in collected_summary:
            st = c.get('site_type')
            if st in platform_counts:
                platform_counts[st] += 1

        platform_plus = {'kakuyomu': 15, 'naro': 15, 'hameln': 6}
        successful_queries = []
        for log in search_history_logs:
            if log.get("new_added", 0) >= platform_plus[log['site']]:
                successful_queries.append(
                    f"★ 성공 대박 조건: [{log['site']}] p.{log['page']} Q:'{log.get('query')}' -> 유효 신규작 {log.get('new_added')}개 발굴! (다음 페이지 page: {log['page'] + 1} 연속 탐색 추천)"
                )
            elif log.get("returned", 0) == 0 and "FAILED" not in log.get("status", ""):
                successful_queries.append(
                    f"⚠ 결과 0건 실패: [{log['site']}] Q:'{log.get('query')}' (조건이 너무 빡빡하거나 태그가 많음. 태그 수를 1개로 줄이거나 min_pt 완화 필요)"
                )
        success_tips = "\n".join(successful_queries[-8:]) if successful_queries else "아직 성공/실패 패턴 기록 없음"

        user_req_text = f"## ★ [사용자 특별 요청 조건 (최우선 절대 원칙)][매우중요]:\n\"{user_custom_prompt}\"\n[end 사용자 조건]\n" if user_custom_prompt else "★ [사용자 특별 요청 조건]: 없음"
        system_instruction = (
            "당신은 일본 3대 웹소설 플랫폼(카쿠요무, 소설가가되자, 하멜른)을 통달한 최고 실력의 수석 데이터 큐레이터입니다.\n"
            "목표: [사용자 특별 요청 조건]과 독자의 기존 취향을 철저히 분석하여, 방황 없이 가장 정밀한 검색 쿼리와 파라미터를 발주하는 것입니다.\n\n"
            "★ 핵심 지침:\n"
            "1. [검색어(query) 규칙]: 일본어 웹소설 태그를 넣으세요.\n"
            "2. [지뢰 및 금기 배제]: 사용자가 싫어하는 요소는 exclude_words, exclusion_flags를 통해 검색 단계부터 원천 차단하세요.\n"
            "3. [성공 쿼리 심층 페이징]: 이전 라운드에서 유효작이 많이 나온 조건은 반드시 동일 조건에 page만 +1 하여 심층 탐색하세요.\n"
            "4. [플랫폼 집중]: 장르 특성에 맞는 사이트에 집중하세요.\n"
            "5. [종료 판단]: 고품질 후보가 충분히 확보 되었고 요청 조건에 완벽히 부합하면 'FINISH', 부족하면 'CONTINUE'를 선언하세요."
        )

        result_list = [
            {
                h.get("title", ""): {
                    "story": h.get("story", ""),
                    "keywords": h.get("keywords", [])
                }
            }
            for h in history_items
        ]
        json_result = json.dumps(result_list, ensure_ascii=False, indent=2)

        prompt = f"""
{PLATFORM_SPEC_TEXT}

{user_req_text}

[독자의 기존 감상 작품 이력]
{json_result}

[현재 탐색 상태]
- 라운드: {round_num}차 루프
- 누적 확보 고유 후보: 총 {len(collected_summary)}개 (카쿠요무 {platform_counts['kakuyomu']}개, 나로우 {platform_counts['naro']}개, 하멜른 {platform_counts['hameln']}개)
- 최근 확보된 후보 표본: {[c['title'] for c in collected_summary[-5:]]}

[최근 검색 시도 분석 및 피드백]
{success_tips}

[최근 5회 원본 검색 로그]
{json.dumps(search_history_logs[-5:], ensure_ascii=False, indent=2) if search_history_logs else "첫 번째 탐색 라운드입니다."}

위 정보를 바탕으로 아래 JSON 규격으로만 응답하세요:
{{
  "ai_thought": "현재 후보군 상태, 사용자 요청 조건 및 금기 사항 분석, 이번 라운드에 발주할 검색 전략",
  "decision": "CONTINUE",  // 후보가 충분히 검증되었으면 "FINISH", 더 필요하면 "CONTINUE"
  "actions": [
    {{
      "site": "kakuyomu",  // "kakuyomu", "naro", "hameln"
      "reason": "구체적인 전략적 선정 사유", //다만 조건들을 나열하는 것이 아니라 자연스럽게 설명하는 것이며 일본어 태그를 말할 시 한국어로 말 해준다. "decision"의 상태를 직접적으로 말하는 것이아니라 '속행', '끝' 이런식으로 일반 사용자가 들을 수 있도록 한다.
      "page": 1,
      "query": [],  // 핵심 일본어 태그 0~2개. 매우 상세히 알고 싶으면 3개 이상(이 때는 대중적인 태그를 사용하여야 함.)
      "genre": "romance",
      "order": "popular",
      "serial_status": "running",
      "last_published": "1months",
      "min_pt": 50,
      "min_chars": 10000,
      "exclude_words": [],
      "inclusion_flags": [],
      "exclusion_flags": [],
      "origin": "原作：オリジナル",  // 하멜른 전용
    }}
  ]
}}
* CONTINUE일 때는 반드시 1~3개의 action을 지시하세요.
* action은 보통 사이트를 골고루 넣지만 같은 사이트를 여러번하여도 좋습니다.
* 70개 이상 많은 작품이 있을 시 더이상 검색을 하지 말고 "FINISH"를 무조건 사용해야 합니다. [매우중요]
* 무조건 70개 이상일 때만 멈추는 것이 아니라 70개 보다 작은 수의 작품이라도 이정도면 충분하다고 판단되면 "FINISH" 해도 좋습니다.
"""
        raw_res = self.ai.generate(prompt, system_instruction)
        return extract_json_from_response(raw_res)

    def triage_candidates(
        self,
        items_to_triage: List[Dict[str, Any]],
        user_custom_prompt: Optional[str],
        history_items: List[Dict[str, Any]]
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

        user_req_text = f"★ [사용자 특별 요청 조건 (최우선 절대 원칙)]:\n\"{user_custom_prompt}\"\n" if user_custom_prompt else "★ [사용자 특별 요청 조건]: 없음"

        system_instruction = (
            "당신은 일본 웹소설 1차 사전 스크리닝 심사관입니다.\n"
            "목표1: 제목, 키워드(태그), 간이 줄거리를 보고 사용자의 특별 요청 조건과 독자 취향에 맞는지 냉철하게 판정하는 것입니다.\n"
            "목표2: 작품 후보를 줄이는 역할을 하며 25개 이상의 매우 많은 작품일 경우 최대 20개의 작품만 '줄거리'로 판정 할 수 있고, 5개만 '의심' 판정 할 수 있습니다. 그리고 남은 작품은 전부 '버려'로 지정합니다. 이 때 최선의 선택을 하여야 합니다.\n\n"
            "★ 판정 상태 (정확히 다음 3가지 중 하나로 판정):\n"
            "1. '버려': 사용자의 금기 조건이 확인되거나, 질적으로 부적합한 경우. 또는 사용자가 싫어할 것으로 예상이 되거나 절대 선택될 일이 없는 작품 -> 상세 조회 없이 즉시 폐기.\n"
            "2. '줄거리': 요청 조건과 취향에 부합하는 명백한 핵심 키워드가 확인되어 정밀 검토할 가치가 매우 높은 경우.\n"
            "3. '의심': 제목이나 미리보기만으로는 적합성을 단정하기 어려워 상세 줄거리를 확인할 필요가 있는 경우.\n"
        )

        result_list = [
            {
                h.get("title", ""): {
                    "story": h.get("story", ""),
                    "keywords": h.get("keywords", [])
                }
            }
            for h in history_items
        ]
        json_result = json.dumps(result_list, ensure_ascii=False, indent=2)

        prompt = f"""
{user_req_text}

[독자의 기존 감상 작품 이력]
{json_result}

[1차 심사 대상 작품 목록 ({len(simplified_list)}개)]
{json.dumps(simplified_list, ensure_ascii=False, indent=2)}

각 id에 대해 아래 JSON 규격으로 응답하세요:
{{
  "triage_results": [
    {{
      "id": 0,
      "status": "줄거리",  // "줄거리", "의심", "버려" 중 하나
    }}
  ]
}}
* 모든 id가 포함되어야 합니다.
"""
        try:
            parsed = {}
            for _ in range(3):
                raw_res = self.ai.generate(prompt, system_instruction)
                parsed = extract_json_from_response(raw_res)
                if parsed != {}:
                    break
            results = parsed.get("triage_results", [])

            status_map = {}
            for r in results:
                if isinstance(r, dict) and "id" in r:
                    status_map[r["id"]] = {
                        "status": r.get("status", "의심")
                    }

            for idx in range(len(items_to_triage)):
                if idx not in status_map:
                    status_map[idx] = {"status": "의심"}
                    PrintIo(f"[경고] 결과에 {idx}가 없어 '의심'으로 지정")

            return status_map

        except Exception as e:
            PrintIo(f"[1차 스크리닝 AI 오류]: {e} -> 전원 '의심'으로 처리합니다.")
            return {idx: {"status": "의심"} for idx in range(len(items_to_triage))}

    def run_search_loop(
        self,
        history_items: List[Dict[str, Any]],
        read_urls: Set[str],
        user_custom_prompt: Optional[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        PrintIo("=== AI 자율 에이전트 다회차 탐색 가동 ===")

        all_candidates: Dict[str, Dict[str, Any]] = {}
        discarded_urls: Set[str] = set()
        search_history_logs: List[Dict[str, Any]] = []

        max_agent_rounds = 7
        round_idx = 0
        round_all = 0
        round_miss = 0

        while round_idx < max_agent_rounds:
            round_idx += 1
            round_all += 1

            if self.back_decision == "FINISH":
                PrintIo(f"[AI 자율 판단] 후보군({len(all_candidates)}개) 확보 완료로 탐색을 자율 종료합니다.")
                break

            total_searches = sum(self.site_success_counts.values())
            if total_searches >= 20:
                PrintIo("[안내] 총 검색 실행 횟수 상한에 도달하여 탐색을 마칩니다.")
                break

            PrintIo(f"\n[라운드 {round_idx}/{max_agent_rounds}] 전략 수립 및 파라미터 계획 수립")

            plan = self.decide_searches(
                round_num=round_all,
                history_items=history_items,
                user_custom_prompt=user_custom_prompt,
                collected_summary=list(all_candidates.values()),
                search_history_logs=search_history_logs,
                top_k=top_k
            )

            ai_thought = plan.get("ai_thought", "")
            decision = str(plan.get("decision", "CONTINUE")).upper()
            actions = plan.get("actions", [])
            if not isinstance(actions, list):
                actions = []

            PrintIo(f"[AI 사고 과정]: {ai_thought}")
            self.log("ai", ai_thought)
            PrintIo(f"[AI 결정]: {decision} (실행할 액션: {len(actions)}건)")

            self.back_decision = decision
            if len(actions) == 0:
                if self.back_decision == "FINISH":
                    if len(all_candidates) < top_k:
                        PrintIo(f"[안내] 목표({top_k}작품) 대비 후보군({len(all_candidates)}개)이 부족하여 추가 탐색합니다.")
                    else:
                        PrintIo(f"[AI 자율 판단] 후보군({len(all_candidates)}개) 확보 완료로 탐색을 자율 종료합니다.")
                        break

            round_pending_items: List[Dict[str, Any]] = []
            action_results_meta: List[Dict[str, Any]] = []

            for act in actions:
                if not isinstance(act, dict):
                    continue
                site = act.get("site", "kakuyomu")
                if site not in self.site_meta:
                    continue

                try:
                    page = int(act.get("page", 1) or 1)
                except (ValueError, TypeError):
                    page = 1

                site_cls = self.site_meta[site]['cls']
                params = build_search_params(site, act, page=page)

                pt_disp = params.get('min_pt') if 'min_pt' in params else params.get('min_start', 0)
                exc_disp = params.get('exclude_words', []) + params.get('exclusion_flag', []) + params.get('exlusion_flags', [])

                PrintIo(
                    f"▶ [{site}] 실행 (누적 {self.site_success_counts[site]}회) - p.{page}, Q:'{params.get('query')}', 장르:'{params.get('genre_name') or params.get('genre_val')}', 정렬:'{params.get('order')}', PT:{pt_disp}, 제외:{exc_disp}"
                )
                self.log("info", f"{site} 검색 실행")

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
                        if u and u not in read_urls and u not in all_candidates and u not in discarded_urls:
                            if any(normalize_url(x.get("url", "")) == u for x in round_pending_items):
                                continue
                            it["site_type"] = site
                            it["_site_cls"] = site_cls
                            it["_action_idx"] = len(action_results_meta)
                            round_pending_items.append(it)
                            valid_action_items.append(it)

                    action_results_meta.append({
                        "site": site,
                        "page": page,
                        "query": params.get("query"),
                        "raw_count": len(raw_items),
                        "pending_count": len(valid_action_items),
                        "new_added": 0,
                        "status": "SUCCESS"
                    })

                except Exception as e:
                    PrintIo(f"   => [검색 실패]: {e}")
                    search_history_logs.append({
                        "site": site,
                        "page": page,
                        "query": params.get("query"),
                        "returned": 0,
                        "new_added": 0,
                        "status": f"FAILED: {e}"
                    })

            if not round_pending_items:
                PrintIo("   => 이번 라운드 신규 발견 작품이 없습니다.")
                for meta in action_results_meta:
                    search_history_logs.append({
                        "site": meta["site"],
                        "page": meta["page"],
                        "query": meta["query"],
                        "returned": meta["raw_count"],
                        "new_added": 0,
                        "status": meta["status"]
                    })
                if round_miss < 3:
                    round_idx -= 1
                    round_miss += 1
                continue
            
            round_miss = 0

            PrintIo(f"[1차 스크리닝] 신규 발굴 {len(round_pending_items)}작품 대상 적합성 사전 심사")
            self.log("info", f"총 {len(round_pending_items)}개의 찾은 작품 정리 중...")
            triage_map = self.triage_candidates(
                round_pending_items,
                user_custom_prompt=user_custom_prompt,
                history_items=history_items
            )

            triage_stats = {"통과": 0, "의심": 0, "버려": 0}

            for idx, it in enumerate(round_pending_items):
                u = normalize_url(it.get("url", ""))
                site = it.get("site_type", "kakuyomu")
                site_cls = it.get("_site_cls")
                act_idx = it.get("_action_idx", 0)
                title = it.get("title", "")

                decision_info = triage_map.get(idx, {"status": "의심"})
                raw_status = str(decision_info.get("status", "의심")).strip()

                if "버려" in raw_status or "삭제" in raw_status or "제외" in raw_status or "탈락" in raw_status:
                    norm_status = "버려"
                elif "줄거리" in raw_status or "적합" in raw_status:
                    norm_status = "통과"
                else:
                    norm_status = "의심"

                triage_stats[norm_status] += 1

                if norm_status == "버려":
                    PrintIo(f"   ✖ [1차 탈락] {title} ({site})")
                    discarded_urls.add(u)
                    continue

                PrintIo(f"   ✔ [1차 통과/{norm_status}] {title} ({site}) - OK")
                try:
                    it["story"] = self.executor.enrich_description(site, site_cls, it)
                except Exception as e:
                    PrintIo(f"상세 정보 수집 중 에러 ({u}): {e}")

                all_candidates[u] = it

                if 0 <= act_idx < len(action_results_meta):
                    action_results_meta[act_idx]["new_added"] += 1

            PrintIo(
                f"[1차 스크리닝 결산] 신규 {len(round_pending_items)}개 중 [통과: {triage_stats['통과'] + triage_stats['의심']}개], [버려: {triage_stats['버려']}개 제외] (누적 고유 후보: {len(all_candidates)}개)"
            )
            self.log("info", f"{len(round_pending_items)}개의 결과 중 {triage_stats['통과'] + triage_stats['의심']}개 통과")

            for meta in action_results_meta:
                search_history_logs.append({
                    "site": meta["site"],
                    "page": meta["page"],
                    "query": meta["query"],
                    "returned": meta["raw_count"],
                    "new_added": meta["new_added"],
                    "status": meta["status"]
                })

        return list(all_candidates.values())