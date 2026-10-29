import json
from typing import List, Dict, Any, Optional
from .ai_client import GeminiAIClient
from .utils import PrintIo, extract_json_from_response

class CandidateRanker:
    def __init__(self, ai_client: GeminiAIClient):
        self.ai = ai_client

    def rerank_and_synthesize(
        self,
        history_items: List[Dict[str, Any]],
        user_custom_prompt: Optional[str],
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> Dict[str, Any]:
        PrintIo(f"[행동] Gemini 2차: 수집된 {len(candidates)}개 후보 중 최적의 {top_k}작품 심층 리랭킹 및 평가")

        if not candidates:
            return {"curator_note": "조건에 부합하는 신작 소설을 발굴하지 못했습니다.", "recommended_works": []}

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

        user_cond_note = f"""
★ [사용자 특별 요청 조건 (최우선 절대 원칙)]:
"{user_custom_prompt}\n[end 사용자 조건]"
""" if user_custom_prompt else ""

        system_instruction = (
            "당신은 일본 웹소설 업계 최고의 냉혹하고 객관적인 수석 평론가입니다.\n"
            "목표: 방대한 후보작 중에서 사용자의 특별 요청 조건과 과거 감상작 취향을 가장 완벽하게 만족하는 최상위 작품을 엄선하여 리포트를 작성하는 것입니다.\n\n"
            "★ 점수 인플레이션 절대 엄벌 (매우 객관적이고 냉정한 점수 산정 기준):\n"
            "- 평균적인 보통 소설의 점수는 60점대입니다.\n"
            "- 90~100점: 사용자의 특별 요청 조건 100% 충족 + 과거 최고 감상작과 핵심 재미 포인트 완벽 일치 + 문체와 전개의 완성도가 검증된 극소수 명작. 하지만 매우 극소수만 가능하기에 왠만해선 이 점수를 주지 마(1위라도 90점대는 힘듦).\n"
            "- 80~89점: 요청 조건의 핵심을 만족하나 1~2가지 아쉬운 클리셰나 약간의 호불호 요소가 포함된 수작.\n"
            "- 70~79점: 기본 조건은 맞추었으나 과거 취향과 미묘하게 어긋나거나 평이한 양산형 전개가 섞인 경우.  (대다수가 이 점수로)\n"
            "- 60~69점: 조건 중 일부만 일치하거나 매력이 부족한 평작.\n"
            "- 60점 미만: 조건 위배 또는 지뢰 요소 포함.\n"
            "※ 절대 억지로 점수를 80~90점대로 부풀리지 마세요. 아쉬운 점과 지뢰/불호 가능성을 cons_and_warnings에 날카롭게 지적하세요."
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
{user_cond_note}
[독자가 감상했던 대표 작품 목록]
{json_result}

[발굴된 신작 후보군 ({len(simplified_candidates)}개)]
{json.dumps(simplified_candidates, ensure_ascii=False, indent=2)}

위 후보작 중에서 독자의 취향 및 특별 요청 조건에 가장 알맞은 최상위 {top_k}작품을 선별하여 아래 JSON 규격으로 반환하세요:
{{
  "curator_note": "독자에게 전하는 종합 코멘트 (특별 요청 사항 반영 내역 및 엄격한 선별 기준 설명 3문장)", //다만 조건들을 나열하는 것이 아니라 자연스럽게 설명하는 것이며 일본어 태그를 말할 시 한국어로 말 해준다.
  "recommended_works": [
    {{
      "candidate_id": 0,
      "match_score": 78,
      "score_rationale": "냉정한 점수 산출 근거 (요청 조건 만족도 및 감점 사유 명시)",
      "connection_with_past_reads": "과거 읽은 특정 작품의 감상 포인트와 이어지는 이유",
      "cons_and_warnings": ["독자에 따라 거슬릴 수 있는 호불호 요소, 드리프트 가능성, 문체적 주의점"],
      "curator_one_liner": "큐레이터의 날카로운 한 줄 평"
    }}
  ]
}}
반드시 위와 같은 JSON 규격으로 출력하세요.
"""
        final_output = None
        for _ in range(3):
            raw_res = self.ai.generate(prompt, system_instruction)
            try:
                final_output = extract_json_from_response(raw_res)
                if final_output == {}:
                    continue
                break
            except Exception:
                print("error")
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