import ast
import asyncio
from collections import Counter
import re
from google.genai import types

client = None
get_safety_settings = None

from glossary_fast import extract_glossary_sample as _extract_glossary_sample

def _split_glossary_text(text, chunk):
    if not text:
        return []

    try:
        chunk = int(chunk)
    except (TypeError, ValueError):
        chunk = 5000

    chunk = max(100, chunk)

    lines = text.splitlines(keepends=True)

    chunks = []
    current = []
    current_length = 0

    for line in lines:
        line_length = len(line)

        if (
            current
            and current_length + line_length > chunk
        ):
            chunks.append("".join(current))
            current = []
            current_length = 0

        current.append(line)
        current_length += line_length

        if current_length >= chunk:
            chunks.append("".join(current))
            current = []
            current_length = 0

    if current:
        chunks.append("".join(current))

    return chunks


def _is_japanese_text(text):
    if not text:
        return False

    for char in text:
        code = ord(char)

        if (
            0x3040 <= code <= 0x309F
            or 0x30A0 <= code <= 0x30FF
            or 0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF
        ):
            return True

    return False


def _is_korean_text(text):
    if not text:
        return False

    return any(
        0xAC00 <= ord(char) <= 0xD7A3
        for char in text
    )


def _parse_glossary_response(response_text, log_callback=None):
    result = {}

    if not response_text:
        return result

    text = response_text.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:python|text)?\s*",
            "",
            text,
            flags=re.IGNORECASE
        )
        text = re.sub(
            r"\s*```$",
            "",
            text
        )

    lines = text.splitlines()

    for line_number, line in enumerate(lines, 1):
        original_line = line
        line = line.strip()

        if not line:
            continue

        try:
            value = ast.literal_eval(line)

            if not isinstance(value, tuple):
                raise ValueError("튜플이 아님")

            if len(value) != 2:
                raise ValueError("항목 수가 2개가 아님")

            source, target = value

            if not isinstance(source, str):
                raise ValueError("일본어 항목이 문자열이 아님")

            if not isinstance(target, str):
                raise ValueError("한국어 항목이 문자열이 아님")

            source = source.strip()
            target = target.strip()

            if not source or not target:
                raise ValueError("빈 항목")

            if not _is_japanese_text(source):
                if log_callback:
                    log_callback(
                        f"용어집 파싱: {line_number}번째 줄 무시 -> "
                        f"{original_line} (일본어 문자가 없음)"
                    )
                continue

            if not _is_korean_text(target):
                if log_callback:
                    log_callback(
                        f"용어집 파싱: {line_number}번째 줄 무시 -> "
                        f"{original_line} (한국어 문자가 없음)"
                    )
                continue

            result[source] = target

        except Exception as e:
            if log_callback:
                log_callback(
                    f"용어집 파싱: {line_number}번째 줄 무시 -> "
                    f"{original_line} ({e})"
                )

    return result


GLOSSARY_SEMAPHORE = asyncio.Semaphore(3)

async def _extract_glossary_chunk_async(
    chunk_text,
    chunk_idx,
    total_chunks,
    log_callback=None,
    max_retries=3,
    model='gemini-3.5-flash',
    RPM=5,
    semaphore=None
):
    if semaphore is None:
        semaphore = asyncio.Semaphore(3)

    delay_between_calls = (60.0 / RPM) * 1.1

    system_prompt = """당신은 일본어 라이트노벨 전문 용어집 추출기입니다.

입력된 일본어 본문을 분석하여 작품 전체에서 반복적으로 사용되거나 번역 시 일관성이 중요한 고유명사, 인명, 지명, 조직명, 능력명, 아이템명, 직업명, 호칭, 특수 용어 등을 추출하십시오.

중요:
- 일반적인 조사, 동사, 형용사 등은 추출하지 마십시오.
- 문맥상 번역을 통일할 필요가 있는 단어를 우선하십시오.
- 인명과 고유명사는 적극적으로 추출하십시오.
- 일반 사물이나 물건, 음식 등은 필요 추출하지 마십시오.
- 일반 단어들은 추출하지 마십시오. 
- 일본어 원문을 왼쪽에 작성하십시오.
- 자연스럽고 일관된 한국어 번역을 오른쪽에 작성하십시오.
- 반드시 입력문에 실제로 존재하는 일본어 표현만 추출하십시오.
- 추측하여 존재하지 않는 용어를 만들지 마십시오.
- 동일한 용어가 여러 번 등장하더라도 한 번만 출력하십시오.

출력 형식은 반드시 한 줄에 하나씩 아래 형식만 사용하십시오.

("일본어", "한국어")
("일본어", "한국어")

절대로 설명하지 마십시오.
절대로 번호를 붙이지 마십시오.
절대로 마크다운을 사용하지 마십시오.
절대로 JSON으로 출력하지 마십시오.
"""

    async with semaphore:
        for attempt in range(1, max_retries + 1):
            if log_callback:
                log_callback(
                    f"[용어집 {chunk_idx}/{total_chunks}] "
                    f"추출 시도 {attempt}/{max_retries}"
                )

            try:
                await asyncio.sleep(delay_between_calls)

                response = await client.aio.models.generate_content(
                    model=model,
                    contents=(
                        "다음 일본어 본문에서 용어집을 추출하십시오.\n\n"
                        f"{chunk_text}"
                    ),
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.1,
                        top_p=0.8,
                        safety_settings=get_safety_settings(),
                    ),
                )

                if not response or not response.text:
                    if log_callback:
                        log_callback(
                            f"[용어집 {chunk_idx}/{total_chunks}] 응답 없음"
                        )
                    continue

                parsed = _parse_glossary_response(
                    response.text,
                    log_callback
                )

                if log_callback:
                    log_callback(
                        f"[용어집 {chunk_idx}/{total_chunks}] "
                        f"{len(parsed)}개 후보 추출"
                    )

                return parsed

            except Exception as e:
                backoff_delay = (2 ** attempt) + delay_between_calls
                if log_callback:
                    log_callback(
                        f"[용어집 {chunk_idx}/{total_chunks}] "
                        f"오류: {e} ({backoff_delay:.1f}초 후 재시도)"
                    )

                await asyncio.sleep(backoff_delay)

    return {}

async def _filter_glossary_with_ai_async(
    glossary_dict,
    log_callback=None,
    model='gemini-2.5-flash',
    RPM=5
):
    if not glossary_dict:
        return glossary_dict

    terms_list_str = "\n".join([f"{k}: {v}" for k, v in glossary_dict.items()])

    filter_system_prompt = """당신은 라이트노벨 번역용 용어집 정리 전문가입니다.

전달받은 용어 목록 중에서 **번역 고유성이 필요 없는 일반 명사 및 불필요한 단어**를 찾아내십시오.

[제외 대상]
- 어디서나 의미가 고정된 일반 사물/개념/단어 (예: 피, 돈, 물, 하늘, 손, 칼, 집, 밥 등)
- 중복되어 사용된 단어들 (이 경우는 둘 중 하나를 제외)
- 고유명사나 특정 설정값이 아닌 흔한 일상 어휘
- 번역자가 굳이 통일 관리하지 않아도 자연스럽게 번역되는 단어

[출력 형식]
제외해야 할 **일본어 원문**만 쉼표(,)로 구분하여 한 줄로 출력하십시오.
예시: 血, 金, 空, ご飯, 魔王, 魔物

중요:
- 제외할 단어가 없다면 아무것도 출력하지 마십시오.
- 절대로 설명이나 마크다운, 번호 등을 붙이지 마십시오.
- 오직 일본어 원문 단어만 쉼표로 구분하여 출력하십시오.
"""

    if log_callback:
        log_callback(f"[2차 검증] 총 {len(glossary_dict)}개 용어 중 불필요한 일반 명사 필터링 중...")

    try:
        await asyncio.sleep((60.0 / RPM) * 1.1)

        response = await client.aio.models.generate_content(
            model=model,
            contents=(
                "다음 용어 목록 중 제외할 일반 명사/불필요 단어를 골라내십시오.\n\n"
                f"{terms_list_str}"
            ),
            config=types.GenerateContentConfig(
                system_instruction=filter_system_prompt,
                temperature=0.0,
                top_p=0.8,
                safety_settings=get_safety_settings(),
            ),
        )

        if not response or not response.text:
            if log_callback:
                log_callback("[2차 검증] 응답 없음 (기존 용어집 유지)")
            return glossary_dict

        raw_text = response.text.strip()
        if not raw_text:
            if log_callback:
                log_callback("[2차 검증] 제외할 단어 없음")
            return glossary_dict

        remove_keywords = [
            item.strip() 
            for item in raw_text.replace("\n", ",").split(",") 
            if item.strip()
        ]

        filtered_glossary = dict(glossary_dict)
        removed_count = 0

        for key in remove_keywords:
            if key in filtered_glossary:
                del filtered_glossary[key]
                removed_count += 1

        if log_callback:
            log_callback(f"[2차 검증 완료] 불필요한 단어 {removed_count}개 제외됨 -> 최종 {len(filtered_glossary)}개 확정")

        return filtered_glossary

    except Exception as e:
        if log_callback:
            log_callback(f"[2차 검증 오류] {e} (기존 용어집 유지)")
        return glossary_dict

async def _extract_glossary_async(
    all_text,
    paserent,
    chunk,
    log_callback=None,
    model='gemini-2.5-flash',
    RPM=5
):
    if not all_text:
        if log_callback:
            log_callback("용어집 추출 실패: 입력 텍스트가 비어있음")
        return {}

    try:
        paserent_value = float(paserent)
    except (TypeError, ValueError):
        paserent_value = 10.0

    try:
        chunk_value = int(chunk)
    except (TypeError, ValueError):
        chunk_value = 5000

    if log_callback:
        log_callback(
            f"용어집 추출 시작: "
            f"전체 {len(all_text)}자 / "
            f"분석 비율 {paserent_value}% / "
            f"청크 {chunk_value}자"
        )
        
    sample_text = _extract_glossary_sample(all_text, paserent_value)

    if not sample_text:
        if log_callback:
            log_callback("용어집 추출 실패: 분석 대상 텍스트가 없음")
        return {}

    if log_callback:
        log_callback(
            f"분석 대상 생성 완료: "
            f"{len(sample_text)}자 "
            f"({len(sample_text) / len(all_text) * 100:.2f}%)"
        )
        
    chunks = _split_glossary_text(sample_text, chunk_value)

    if not chunks:
        return {}

    if log_callback:
        log_callback(f"용어집 분석 청크 분할 완료: {len(chunks)}개")

    semaphore = asyncio.Semaphore(3)
    
    tasks = [
        _extract_glossary_chunk_async(
            chunk_text,
            idx,
            len(chunks),
            log_callback,
            model=model,
            RPM=RPM,
            semaphore=semaphore
        )
        for idx, chunk_text in enumerate(chunks, 1)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    glossary_candidates = {}

    for idx, result in enumerate(results, 1):
        if isinstance(result, Exception):
            if log_callback:
                log_callback(f"[용어집 {idx}/{len(chunks)}] 결과 처리 실패: {result}")
            continue

        if not isinstance(result, dict):
            continue

        for source, target in result.items():
            source = source.strip()
            target = target.strip()

            if not source or not target:
                continue

            glossary_candidates.setdefault(source, []).append(target)

    candidate_glossary = {}
    for source, targets in glossary_candidates.items():
        if not targets:
            continue

        counter = Counter(targets)
        target, count = counter.most_common(1)[0]
        candidate_glossary[source] = target

        if log_callback and len(counter) > 1:
            log_callback(
                f"용어 번역 충돌: '{source}' -> '{target}' 선택 ({count}/{len(targets)})"
            )

    if log_callback:
        log_callback(f"1차 용어집 추출 완료: {len(candidate_glossary)}개 후보")

    final_glossary = await _filter_glossary_with_ai_async(
        glossary_dict=candidate_glossary,
        log_callback=log_callback,
        model=model,
        RPM=RPM
    )

    if log_callback:
        log_callback(f"최종 용어집 확정: {len(final_glossary)}개")

    return final_glossary


def extract_glossary(
    all_text,
    paserent=10,
    chunk=5000,
    log_callback=None,
    model='gemini-3.5-flash-lite',
    RPM=5
):
    return asyncio.run(
        _extract_glossary_async(
            all_text,
            paserent,
            chunk,
            log_callback,
            model,
            RPM
        )
    )