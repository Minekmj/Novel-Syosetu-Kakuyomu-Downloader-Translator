import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections.abc import Callable
from .ai_client import SuggestionAIClient
from .utils import PrintIo, RecommendationCancelled, check_cancelled, extract_json_from_response
from .prompts import RANKER_SYSTEM, RANKER_PROMPT


class CandidateRanker:
    def __init__(
        self,
        ai_client: SuggestionAIClient,
        check_callback: Optional[Callable[[], bool]] = None
    ):
        self.ai = ai_client
        self.check = check_callback or (lambda: False)

    def _check_cancelled(self):
        check_cancelled(self.check)

    def _format_conversation_history(self, conversation_history: Optional[List[Dict[str, str]]]) -> str:
        if not conversation_history:
            return "이전 탐색 내역 없음"
        filtered = [
            entry for entry in conversation_history
            if entry.get("stage") != "최종 추천 완료"
        ][-12:]
        if not filtered:
            return "이전 탐색 내역 없음"
        lines = []
        for idx, entry in enumerate(filtered, 1):
            lines.append(f"{idx}. [{entry.get('stage', '기록')}] {entry.get('content', '')}")
        return "\n".join(lines)

    def _attach_candidate_metadata(self, rec: Dict[str, Any], orig: Dict[str, Any]) -> Dict[str, Any]:
        rec["stars"] = orig.get("stars", 0)
        rec["status_episodes"] = orig.get("status_episodes", "")
        rec["updated_at"] = orig.get("updated_at", "")
        rec["story"] = orig.get("story", "")
        rec["keywords"] = orig.get("keywords", [])
        rec["url"] = orig.get("url", "")
        rec["site"] = orig.get("site_type", "")
        rec["title_ja"] = orig.get("title", "")
        return rec

    def _build_triage_fallback(self, eval_candidates: List[Dict[str, Any]], top_k: int) -> Dict[str, Any]:
        selected = eval_candidates[:top_k]
        fallback_works = []
        for idx, orig in enumerate(selected):
            score = int(orig.get("triage_score", 50) or 50)
            reason = str(orig.get("triage_reason", "")).strip()
            rec = {
                "candidate_id": idx,
                "match_score": score,
                "score_rationale": reason or "요청 조건과 분위기 부합도를 기준으로 선별했습니다.",
                "connection_with_past_reads": "요청 조건 및 취향과 전반적으로 이어지는 작품입니다.",
                "cons_and_warnings": ["세부 비평 생성이 지연되어 작품 개요 기준 순위로 대체되었습니다."],
                "curator_one_liner": reason or "요청 조건에 맞춰 선별된 작품입니다."
            }
            self._attach_candidate_metadata(rec, orig)
            fallback_works.append(rec)

        return {
            "curator_note": "최종 비평 정리 과정에 일시적인 오류가 발생해 사전 검토 순위대로 작품을 선별했습니다.",
            "recommended_works": fallback_works
        }

    def rerank_and_synthesize(
        self,
        history_analysis: List[Dict[str, Any]],
        main_request: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
        user_profile: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        known_excluded_titles: Optional[List[str]] = None,
        check_callback: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        if check_callback is not None:
            self.check = check_callback
        self._check_cancelled()

        PrintIo(f"[평가] {len(candidates)}개 후보 대상 최종 심층 리랭킹")

        if not candidates:
            return {"curator_note": "요청 조건에 부합하는 소설을 발굴하지 못했습니다.", "recommended_works": []}

        eval_candidates = sorted(
            candidates,
            key=lambda x: int(x.get("triage_score", 0) or 0),
            reverse=True
        )[:35]

        if user_profile is None:
            user_list = {}
            for h in history_analysis:
                t = h.get("title", "")
                if t:
                    user_list[t] = {
                        "제목": t,
                        "내용 ai 중심 요약": h.get("story_summary", ""),
                        "태그들": h.get("core_keywords", [])
                    }
            user_profile = {
                "user": main_request.get("user_request", "없음"),
                "ai": main_request,
                "user_list": user_list
            }

        ai_section = user_profile.get("ai", {})
        hard_constraints = ai_section.get("hard_constraints", [])
        taste_profile = ai_section.get("taste_profile", {})
        excluded_list = list(known_excluded_titles or [])
        if not excluded_list and isinstance(user_profile.get("user_list"), dict):
            excluded_list = [k for k in user_profile["user_list"].keys() if k and k != "없음"]

        simplified_candidates = []
        for idx, c in enumerate(eval_candidates):
            simplified_candidates.append({
                "candidate_id": idx,
                "title": c.get("title", ""),
                "site": c.get("site_type", ""),
                "url": c.get("url", ""),
                "stars": c.get("stars", 0),
                "episodes": c.get("status_episodes", ""),
                "serial_status": c.get("serial_status", ""),
                "updated_at": c.get("updated_at", ""),
                "story": (c.get("story", "") or "")[:900],
                "keywords": c.get("keywords", [])
            })

        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt = RANKER_SYSTEM.format(top_k=top_k)
        prompt = RANKER_PROMPT.format(
            current_date=current_date,
            hard_constraints_json=json.dumps(hard_constraints, ensure_ascii=False),
            taste_profile_json=json.dumps(taste_profile, ensure_ascii=False, indent=2),
            user_profile_json=json.dumps(user_profile, ensure_ascii=False, indent=2),
            excluded_titles_json=json.dumps(excluded_list, ensure_ascii=False),
            conversation_history_text=self._format_conversation_history(conversation_history),
            candidates_count=len(simplified_candidates),
            candidates_json=json.dumps(simplified_candidates, ensure_ascii=False, indent=2),
            top_k=top_k
        )

        final_output = None
        valid_recs: List[Dict[str, Any]] = []

        for _ in range(3):
            self._check_cancelled()
            raw_res = self.ai.generate(prompt, system_prompt)
            self._check_cancelled()
            if not raw_res and self.ai.last_error:
                break
            try:
                parsed = extract_json_from_response(raw_res)
                if not isinstance(parsed, dict) or not isinstance(parsed.get("recommended_works"), list):
                    continue

                seen_cids = set()
                temp_recs = []
                for rec in parsed.get("recommended_works", []):
                    if not isinstance(rec, dict):
                        continue
                    try:
                        cid = int(rec.get("candidate_id"))
                    except (ValueError, TypeError):
                        continue
                    if 0 <= cid < len(eval_candidates) and cid not in seen_cids:
                        seen_cids.add(cid)
                        rec["candidate_id"] = cid
                        try:
                            score_val = int(rec.get("match_score", 68))
                        except (ValueError, TypeError):
                            score_val = 68
                        rec["match_score"] = max(0, min(100, score_val))
                        self._attach_candidate_metadata(rec, eval_candidates[cid])
                        temp_recs.append(rec)

                if temp_recs:
                    final_output = parsed
                    valid_recs = temp_recs[:top_k]
                    break
            except RecommendationCancelled:
                raise
            except Exception:
                continue

        self._check_cancelled()

        if not valid_recs or not isinstance(final_output, dict):
            return self._build_triage_fallback(eval_candidates, top_k)

        final_output["recommended_works"] = valid_recs
        return final_output