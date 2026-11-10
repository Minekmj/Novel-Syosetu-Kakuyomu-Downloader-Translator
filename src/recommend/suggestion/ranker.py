import json
from typing import List, Dict, Any, Optional
from .ai_client import SuggestionAIClient
from .utils import PrintIo, extract_json_from_response
from .prompts import RANKER_SYSTEM, RANKER_PROMPT

class CandidateRanker:
    def __init__(self, ai_client: SuggestionAIClient):
        self.ai = ai_client

    def rerank_and_synthesize(
        self,
        history_analysis: List[Dict[str, Any]],
        main_request: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> Dict[str, Any]:
        PrintIo(f"[평가] {len(candidates)}개 후보 대상 최종 심층 리랭킹")

        if not candidates:
            return {"curator_note": "요청 조건에 부합하는 소설을 발굴하지 못했습니다.", "recommended_works": []}

        simplified_candidates = []
        for idx, c in enumerate(candidates):
            simplified_candidates.append({
                "candidate_id": idx,
                "title": c.get("title", ""),
                "site": c.get("site_type", ""),
                "url": c.get("url", ""),
                "stars": c.get("stars", 0),
                "episodes": c.get("status_episodes", ""),
                "updated_at": c.get("updated_at", ""),
                "story": (c.get("story", "") or "")[:900],
                "keywords": c.get("keywords", [])
            })

        prompt = RANKER_PROMPT.format(
            main_request_json=json.dumps(main_request, ensure_ascii=False, indent=2),
            history_analysis_json=json.dumps(history_analysis, ensure_ascii=False, indent=2),
            candidates_count=len(simplified_candidates),
            candidates_json=json.dumps(simplified_candidates, ensure_ascii=False, indent=2),
            top_k=top_k
        )

        final_output = None
        for _ in range(3):
            raw_res = self.ai.generate(prompt, RANKER_SYSTEM)
            try:
                final_output = extract_json_from_response(raw_res)
                if isinstance(final_output, dict) and "recommended_works" in final_output:
                    break
            except Exception:
                continue

        if not isinstance(final_output, dict):
            final_output = {"curator_note": "추천 결과를 생성했습니다.", "recommended_works": []}

        recs = final_output.get("recommended_works", [])
        if isinstance(recs, list):
            for rec in recs:
                if not isinstance(rec, dict):
                    continue
                cid = rec.get("candidate_id")
                if cid is not None and isinstance(cid, int) and 0 <= cid < len(candidates):
                    orig = candidates[cid]
                    rec["stars"] = orig.get("stars", 0)
                    rec["status_episodes"] = orig.get("status_episodes", "")
                    rec["updated_at"] = orig.get("updated_at", "")
                    rec["story"] = orig.get("story", "")
                    rec["keywords"] = orig.get("keywords", [])
                    rec["url"] = orig.get("url", "")
                    rec["site"] = orig.get("site_type", "")
                    rec["title_ja"] = orig.get("title", "")

        return final_output