_K = "+---+\n"
_J = "gemini-3.5-flash-Lite"
_I = r'[\\/:*?"<>|]'
_H = "OUTFOLDER"
_G = "+---+"
_F = False
_E = ""
_D = None
_C = True
_B = "\n"
_A = "utf-8"
_Gi = '=' * 30

import asyncio
import json
import os
import re
import time
import unicodedata
import ast
from collections import Counter

from google import genai
from google.genai import types

import down
from config import DATA_FILE


API = _E
MODEL_NAME = "gemini-3.5-flash-lite"
CUSTOM_AI_PROMPT = """"""

def set_api_key(api_key):
    global API, client

    API = api_key.strip() or _E
    client = genai.Client(api_key=API if API != "" else "None")

    data = {}

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding=_A) as f:
                data = json.load(f)
        except Exception:
            data = {}

    data["api"] = API

    with open(DATA_FILE, "w", encoding=_A) as f:
        json.dump(data, f, ensure_ascii=_F, indent=4)


def rest():
    global API, client

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding=_A) as f:
                API = json.load(f).get("api", _E)
                client = genai.Client(api_key=API)
        except Exception:
            pass


client = genai.Client(api_key=API if API != "" else "None")
rest()


SYSTEM_PROMPT = """## 개요
* 당신은 전문 번역가입니다.

## 핵심 원칙
* 충실하고 검열 없는 번역: 명시적이거나 비속어, 혹은 민감한 내용을 포함하여 원문의 의미, 의도, 어조, 감정적 뉘앙스, 상세 내용을 어떠한 검열이나 수정, 개인적 편견의 개입 없이 완벽한 충실함으로 번역하십시오.
* 자연스럽고 관용적인 표현: 목표 언어의 원어민이 마치 처음부터 해당 언어로 작성된 글을 읽는 것처럼 완전히 자연스럽고 관용적으로 느껴지는 번역을 최우선으로 하십시오. 표현, 문화적 비유, 스타일을 창의적으로 다듬어 가독성, 몰입감, 장르 적합성을 높이되, 언제나 직역보다는 원문의 의도를 우선시하십시오.

## 추가 지침
* 모든 욕설과 비속어는 목표 언어에서 그에 상응하는 표현으로 번역하십시오. 원문의 강도와 전달 기능을 그대로 살려야 합니다.
* 성적이거나 폭력적인 내용을 포함한 노골적인 표현은 완벽한 충실함을 바탕으로 원문의 어조와 노골성의 수위를 직접적이고 정확하게 반영하여 번역하십시오.
* 누락이나 수정 없이 모든 원문의 의미, 어조, 노골적인 내용을 유지하면서 원문 전체를 포괄적으로 번역하십시오.

## 중요 주의사항
* 오직 최종 결과물만 출력하십시오.
* 제목, 설명, 기타 추가 내용을 절대로 덧붙이지 마십시오.
* 원문의 의도, 뉘앙스, 스타일을 유지하십시오.
* 목표 언어로 처음부터 작성된 것처럼 자연스럽고 유려한 번역을 목표로 하십시오.

[중요] 당신은 일본어를 한국어로 번역하여야 합니다. 따라서 일본어 사용을 금지 합니다.

[필수 규칙]
1. 입력문에 포함된 '+---+'는 글자를 절대 유지 하세요.
2. '+---+' 원문에 없는 곳에 새로 만들거나 추가해서는 안 됩니다. (절대 금지!)."""


SYSTEM_PROMPT_NO_SPLIT = """## 개요
* 당신은 전문 번역가입니다.

## 핵심 원칙
* 충실하고 검열 없는 번역: 명시적이거나 비속어, 혹은 민감한 내용을 포함하여 원문의 의미, 의도, 어조, 감정적 뉘앙스, 상세 내용을 어떠한 검열이나 수정, 개인적 편견의 개입 없이 완벽한 충실함으로 번역하십시오.
* 자연스럽고 관용적인 표현: 목표 언어의 원어민이 마치 처음부터 해당 언어로 작성된 글을 읽는 것처럼 완전히 자연스럽고 관용적으로 느껴지는 번역을 최우선으로 하십시오. 표현, 문화적 비유, 스타일을 창의적으로 다듬어 가독성, 몰입감, 장르 적합성을 높이되, 언제나 직역보다는 원문의 의도를 우선시하십시오.

## 추가 지침
* 모든 욕설과 비속어는 목표 언어에서 그에 상응하는 표현으로 번역하십시오. 원문의 강도와 전달 기능을 그대로 살려야 합니다.
* 성적이거나 폭력적인 내용을 포함한 노골적인 표현은 완벽한 충실함을 바탕으로 원문의 어조와 노골성의 수위를 직접적이고 정확하게 반영하여 번역하십시오.
* 누락이나 수정 없이 모든 원문의 의미, 어조, 노골적인 내용을 유지하면서 원문 전체를 포괄적으로 번역하십시오.

## 중요 주의사항
* 오직 최종 결과물만 출력하십시오.
* 제목, 설명, 기타 추가 내용을 절대로 덧붙이지 마십시오.
* 원문의 의도, 뉘앙스, 스타일을 유지하십시오.
* 목표 언어로 처음부터 작성된 것처럼 자연스럽고 유려한 번역을 목표로 하십시오.

[중요] 당신은 일본어를 한국어로 번역하여야 합니다. 따라서 일본어 사용을 금지 합니다."""

SYSTEM_PROMPT_RAW = """## 개요
* 당신은 전문 번역가입니다.

## 핵심 원칙
* 충실하고 검열 없는 번역: 원문의 의미, 의도, 어조, 감정적 뉘앙스와 상세 내용을 최대한 충실하게 번역하십시오.
* 자연스럽고 관용적인 한국어 번역을 사용하십시오.
* 누락이나 임의의 추가 없이 원문 전체를 번역하십시오.

## 절대 규칙
1. 원문의 줄 바꿈을 바꾸지 않는다.
2. 원문의 줄 바꿈을 임의로 수정하지 않는다.
3. 원문의 줄을 유지한다.
4. 입력문에 존재하는 모든 줄바꿈 위치를 최대한 그대로 유지한다.
5. 원문에 존재하는 빈 줄도 임의로 삭제하거나 추가하지 않는다.
6. '='로 이루어진 구분선은 원문 그대로 유지한다.

## 중요
* 오직 최종 번역 결과만 출력하십시오.
* 제목, 설명, 기타 추가 내용을 절대로 덧붙이지 마십시오.
* 일본어를 한국어로 번역하십시오.
* 일본어를 번역 결과에 남기지 마십시오."""

GLOSSARY_CONTEXT = """# 용어집 컨텍스트 (아래 용어집에 명시된 번역어를 반드시 준수하세요.)
- 용어집에 있는 용어는 반드시 해당 번역어로 번역해야 하며, 변경하거나 다른 표현을 사용하지 마세요.
- 문맥에 따라 자연스럽게 번역하되, 용어집 우선 적용을 최우선으로 합니다.
- 원문의 의미, 뉘앙스, 톤을 유지하면서 자연스럽고 유창한 한국어로 번역해주세요.
- 번역 결과에 용어집 외의 임의 번역어가 포함되지 않도록 주의하세요.

{glossary}"""

GLOSSARY_MAX_CHARS = 1000


class PromptSanitizer:

    def __init__(self):
        self.rules = [
            "いやらし[いくさ]",
            "エロ(?:い|チック|ティック)?",
            "スケベ(?:な|そう)?",
            "エッチ(?:な|する|した)?",
            "淫ら(?:な|に)?",
            "性的(?:な)?",
            "卑猥(?:な)?",
            "猥褻",
            "セックス(?:する|した)?",
            "本番",
            "3P",
            "起た(?:ない|なくて|つ|ち)",
            "大きくな(?:る|った|って)",
            "ゴム",
            "バイ〇グラ",
            "バイアグラ",
            "イチャイチャ",
            "一線越え(?:る|た)?",
            "浮気",
            "二股",
            "NTR",
            "押し倒(?:す|した|して|され)",
            "抱きしめ(?:る|た|て|返した)",
            "抱きつ(?:く|いた|いて|かれ)",
            "体を重ね(?:る|た|て)",
            "触(?:る|った|れて|れた)",
            "撫で(?:る|た|て)",
            "キス(?:した)?",
            "股間",
            "アレ",
            "胸元",
            "太もも",
            "裸体",
            "裸(?:の|で)?",
            "下半身",
            "ほっぺ",
            "高校(?:の|生)?",
            "理事長(?:室)?",
            "生徒",
            "制服",
            "無理やり",
            "強引(?:に|な)?",
            "襲(?:う|った|われ)",
            "奪(?:い返しても|った|い)",
            "騙(?:してる|して|す)",
            "告げ口",
            "脅迫",
            "自傷",
            "自殺",
            "リスカ",
            "首吊(?:り|る)",
            "殺(?:す|した|せ|そう)",
            "死ね",
        ]

        self.compiled = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.rules
        ]

    def normalize(self, text):
        text = unicodedata.normalize("NFKC", text)
        return re.sub(r"[\u200B-\u200D\uFEFF]", "", text)

    def censor_match(self, match):
        word = match.group()

        if len(word) <= 2:
            return "〇" * len(word)

        return word[0] + "〇" * (len(word) - 1)

    def sanitize(self, text):
        text = self.normalize(text)

        for pattern in self.compiled:
            text = pattern.sub(self.censor_match, text)

        return text


_sanitizer = PromptSanitizer()


def x_making(text):
    return _sanitizer.sanitize(text)


def split_text_by_lines(text, max_chars=5000):
    lines = text.splitlines(keepends=True)

    chunks = []
    current_chunk = []
    current_length = 0

    for line in lines:
        if current_length + len(line) > max_chars and current_chunk:
            chunks.append("".join(current_chunk))
            current_chunk = [line]
            current_length = len(line)
        else:
            current_chunk.append(line)
            current_length += len(line)

    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks


def get_japanese_ratio(text):
    if not text:
        return 0.0

    clean_text = re.sub(r"[^\w]|[\d_]", "", text)

    if not clean_text:
        return 0.0

    jp_chars = len(
        re.findall(
            r"[\u3040-\u309f\u30a0-\u30ff]",
            clean_text
        )
    )

    return jp_chars / len(clean_text) * 100


def get_korean_ratio(text):
    if not text:
        return 0.0

    clean_text = re.sub(r"[^\w]|[\d_]", "", text)

    if not clean_text:
        return 0.0

    ko_chars = len(
        re.findall(
            r"[\uac00-\ud7a3\u3131-\u318e]",
            clean_text
        )
    )

    return ko_chars / len(clean_text) * 100


def get_linebreak_preservation_ratio(original, translated):
    original_breaks = original.count("\n")
    translated_breaks = translated.count("\n")

    if original_breaks == 0:
        return 100.0 if translated_breaks == 0 else 0.0

    difference = abs(original_breaks - translated_breaks)

    return max(
        0.0,
        (1.0 - difference / original_breaks) * 100.0
    )


def get_safety_settings():
    return [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
            threshold=types.HarmBlockThreshold.BLOCK_NONE
        ),
    ]


class AsyncRateLimiter:

    def __init__(self, rpm: int):
        self.interval = 60.0 / max(1, rpm) + 0.1
        self.lock = asyncio.Lock()
        self.last_call = 0.0

    async def wait(self):
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_call

            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)

            self.last_call = time.time()


def build_dynamic_glossary(
    chunk,
    dictionary,
    max_chars=GLOSSARY_MAX_CHARS
):
    if not dictionary:
        return ""

    matched = []

    for source, target in dictionary.items():
        source = str(source).strip()
        target = str(target).strip()

        if not source or not target:
            continue

        count = chunk.count(source)

        if count >= 1:
            matched.append((count, source, target))

    if not matched:
        return ""

    matched.sort(key=lambda x: x[0], reverse=True)

    selected = []
    current_length = 0

    for count, source, target in matched:
        line = f"{source} → {target}"
        line_length = len(line) + (1 if selected else 0)

        if current_length + line_length > max_chars:
            break

        selected.append(line)
        current_length += line_length

    if not selected:
        return ""

    return "\n".join(selected)


async def translate_chunk_safe_async(
    chunk,
    model_name,
    safety_settings,
    rate_limiter,
    temperature=0.2,
    max_retries=3,
    depth=0,
    log_callback=_D,
    chunk_idx=0,
    raw=False,
    dicts={}
):
    lines = chunk.splitlines(keepends=True)

    if not lines:
        return "", 0

    if get_japanese_ratio(chunk) < 0.03:
        if log_callback:
            log_callback(
                f"[{chunk_idx} - ] [{depth}] [시도 0] "
                f"원문의 일본어 비율이 너무 낮아 번역 생략"
            )

        return chunk, len(lines)

    current_chunk = chunk
    is_censored = False

    if raw:
        expected_delimiter_count = len(
            re.findall(r'^={4,}$', chunk, re.MULTILINE)
        )
    else:
        expected_delimiter_count = chunk.count(_G)

    attempt = 1

    while attempt <= max_retries:
        censored_label = "검열" if is_censored else ""

        prefix_log = (
            f"[{chunk_idx} - {censored_label}] "
            f"[{depth}] [시도 {attempt}/{max_retries}]"
        )

        if log_callback:
            log_callback(
                f"{prefix_log} 번역 시도: "
                f"(라인 수: {len(lines)}, temperature: {temperature})"
            )

        await rate_limiter.wait()

        try:
            if raw:
                system_prompt = SYSTEM_PROMPT_RAW
            else:
                system_prompt = (
                    SYSTEM_PROMPT
                    if _G in chunk
                    else SYSTEM_PROMPT_NO_SPLIT
                )
                
            if CUSTOM_AI_PROMPT != "":
                system_prompt += f"""\n\n[사용자 지정 추가 지침]
{CUSTOM_AI_PROMPT}\n\n"""

            if len(dicts) > 0:
                glossary_text = build_dynamic_glossary(
                    chunk,
                    dicts
                )

                if glossary_text != "":
                    system_prompt += (
                        "\n\n"
                        + GLOSSARY_CONTEXT.format(
                            glossary=glossary_text
                        )
                    )

                    glossary_log = ", ".join(
                        glossary_text.splitlines()
                    )

                    if len(glossary_log) > 40:
                        glossary_log = glossary_log[:40] + "..."

                    if log_callback:
                        log_callback(
                            f"{prefix_log} 용어집 사용: "
                            f"{glossary_log}"
                        )

            response = await client.aio.models.generate_content(
                model=model_name,
                contents=f"번역:\n{current_chunk}",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    top_p=0.8,
                    safety_settings=safety_settings,
                ),
            )

            if response and response.text:
                res_text = response.text.strip()

                res_text = (
                    res_text
                    .replace("「", "“")
                    .replace("」", "”")
                    .replace("｢", "“")
                    .replace("｣", "”")
                )

                if not raw and _G in chunk:
                    actual_delimiter_count = res_text.count(_G)

                    if actual_delimiter_count != expected_delimiter_count:
                        if log_callback:
                            log_callback(
                                f"{prefix_log} 경고: '+---+' 개수 불일치 "
                                f"(기대: {expected_delimiter_count}, "
                                f"결과: {actual_delimiter_count}) -> 재시도"
                            )

                        current_chunk = chunk
                        attempt += 1
                        is_censored = False
                        continue

                if raw and "====" in chunk:
                    actual_delimiter_count = len(
                        re.findall(
                            r'^={4,}$',
                            res_text,
                            re.MULTILINE
                        )
                    )

                    if actual_delimiter_count != expected_delimiter_count:
                        if log_callback:
                            log_callback(
                                f"{prefix_log} 경고: '====...' 라인 개수 불일치 "
                                f"(기대: {expected_delimiter_count}, "
                                f"결과: {actual_delimiter_count}) -> 재시도"
                            )

                        current_chunk = chunk
                        attempt += 1
                        is_censored = False
                        continue

                jp_ratio = get_japanese_ratio(res_text)
                ko_ratio = get_korean_ratio(res_text)

                text_len = len(chunk.strip())

                if text_len < 100:
                    min_ko_ratio = 60.0
                    max_jp_ratio = 5.0
                    min_line_ratio = 30.0
                elif text_len < 600:
                    min_ko_ratio = 70.0
                    max_jp_ratio = 2.0
                    min_line_ratio = 70.0
                elif text_len < 1500:
                    min_ko_ratio = 75.0
                    max_jp_ratio = 1.0
                    min_line_ratio = 75.0
                else:
                    min_ko_ratio = 80.0
                    max_jp_ratio = 0.5
                    min_line_ratio = 90.0

                if raw:
                    line_ratio = get_linebreak_preservation_ratio(
                        chunk,
                        res_text
                    )

                    if (
                        jp_ratio < max_jp_ratio
                        and ko_ratio >= min_ko_ratio
                        and line_ratio >= min_line_ratio
                    ):
                        if log_callback:
                            log_callback(
                                f"{prefix_log} -> 성공: "
                                f"(줄바꿈 보존율: {line_ratio:.2f}%)"
                            )

                        return res_text, len(lines)

                    if log_callback:
                        log_callback(
                            f"{prefix_log} 경고: 번역 조건 미달 "
                            f"(한글: {ko_ratio:.2f}% "
                            f"[기준 {min_ko_ratio}%], "
                            f"일어: {jp_ratio:.2f}% "
                            f"[기준 <{max_jp_ratio}%], "
                            f"줄바꿈: {line_ratio:.2f}% "
                            f"[기준 {min_line_ratio}%]) -> 재시도"
                        )
                else:
                    if (
                        jp_ratio < max_jp_ratio
                        and ko_ratio >= min_ko_ratio
                    ):
                        if log_callback:
                            log_callback(
                                f"{prefix_log} -> 성공: 완료"
                            )

                        return res_text, len(lines)

                    if log_callback:
                        log_callback(
                            f"{prefix_log} 경고: 번역 조건 미달 "
                            f"(한글: {ko_ratio:.2f}% "
                            f"[기준 {min_ko_ratio}%], "
                            f"일어: {jp_ratio:.2f}% "
                            f"[기준 <{max_jp_ratio}%]) -> 재시도"
                        )

                current_chunk = chunk
                is_censored = False
                attempt += 1

            else:
                if log_callback:
                    log_callback(
                        f"{prefix_log} 경고: API 응답이 비어있음 "
                        f"-> 검열 실행"
                    )

                current_chunk = x_making(chunk)

                if is_censored:
                    attempt += 1
                    break

                is_censored = True
                attempt += 1
                continue

        except Exception as e:
            if log_callback:
                log_callback(
                    f"{prefix_log} 오류: API 호출 중 예외 발생: "
                    f"{e} -> 재시도"
                )

            is_censored = False
            attempt += 1

    if len(lines) <= 2 or depth >= 4:
        if log_callback:
            log_callback(
                f"[{chunk_idx} - ] [{depth}] 오류: "
                f"[최대초과] 최대 재시도 초과 및 분할 한계 도달 "
                f"-> 원문 유지"
            )

        return chunk, len(lines)

    mid = len(lines) // 2

    if log_callback:
        log_callback(
            f"[{chunk_idx} - ] [{depth}] 경고: [분할] "
            f"청크 분할 처리 "
            f"(전반부 {mid}줄, 후반부 {len(lines) - mid}줄)"
        )

    part1_text, _ = await translate_chunk_safe_async(
        "".join(lines[:mid]),
        model_name,
        safety_settings,
        rate_limiter,
        temperature,
        max_retries,
        depth + 1,
        log_callback,
        chunk_idx,
        raw,
        dicts
    )

    part2_text, _ = await translate_chunk_safe_async(
        "".join(lines[mid:]),
        model_name,
        safety_settings,
        rate_limiter,
        temperature,
        max_retries,
        depth + 1,
        log_callback,
        chunk_idx,
        raw,
        dicts
    )

    return (
        part1_text.rstrip(_B)
        + _B
        + part2_text.lstrip(_B),
        len(lines)
    )


def detect_raw_text(text):
    lines = text.splitlines()

    return (
        len(lines) >= 3
        and lines[2].strip().lower() == "(raw)"
    )


def prepare_raw_text(text):
    lines = text.splitlines(keepends=True)

    if len(lines) < 3 or lines[2].strip().lower() != "(raw)":
        return text, "제목 미정"

    book_title = lines[0].strip()
    author = lines[1].strip()

    title = book_title + "_" + author

    delimiter_index = None

    for i, line in enumerate(lines):
        if line.strip() == _Gi:
            delimiter_index = i
            break

    if delimiter_index is not None:
        body_start = delimiter_index
    else:
        body_start = 5

    raw_body = "".join(lines[body_start:])

    return raw_body, title


async def _translate_light_novel_async(
    text,
    max_chars,
    model_name,
    rpm,
    temperature,
    max_concurrent,
    title,
    progress_callback,
    log_callback,
    raw=False,
    dicts={}
):
    if API == _E:
        if log_callback:
            log_callback(
                "에러: API 키가 설정되지 않았습니다."
            )

        return "error"

    chunks = split_text_by_lines(
        text,
        max_chars=max_chars
    )

    translated_parts = [None] * len(chunks)
    translated_parts_raw = [None] * len(chunks)

    out = getattr(
        down.downin,
        _H,
        "./out"
    ) + "/"

    os.makedirs(
        f"{out}trs",
        exist_ok=_C
    )

    os.makedirs(
        f"{out}epub",
        exist_ok=_C
    )

    os.makedirs(
        f"{out}epub\\raw_txt",
        exist_ok=_C
    )

    safe = re.sub(
        _I,
        "_",
        title
    ).strip()

    ai_dir = (
        f"{out}trs\\"
        f"ai_down_{safe}_{max_chars}"
    )

    os.makedirs(
        ai_dir,
        exist_ok=_C
    )

    msg = (
        f"총 {len(chunks)}개 청크 분할 완료 "
        f"(청크 크기: {max_chars}). "
        f"사용 모델: {model_name}, "
        f"동시 작업수: {max_concurrent}, "
        f"RAW: {raw}"
    )

    print(msg)

    if log_callback:
        log_callback(msg)

    safety_settings = get_safety_settings()
    rate_limiter = AsyncRateLimiter(rpm)

    concurrency_limit = max(
        1,
        min(15, max_concurrent)
    )

    semaphore = asyncio.Semaphore(
        concurrency_limit
    )

    completed_count = 0
    lock = asyncio.Lock()

    async def process_chunk(idx, chunk):
        nonlocal completed_count

        file_path = f"{ai_dir}/{idx}.txt"

        if os.path.exists(file_path):
            with open(
                file_path,
                "r",
                encoding=_A
            ) as f:
                saved_text = f.read()

            if (
                saved_text
                and not saved_text.startswith("[번역 실패")
            ):
                skip_msg = (
                    f"[{idx}/{len(chunks)}] "
                    f"이미 저장된 파일 존재 → 건너뜀"
                )

                if log_callback:
                    log_callback(skip_msg)

                async with lock:
                    translated_parts[idx - 1] = saved_text
                    translated_parts_raw[idx - 1] = saved_text
                    completed_count += 1

                    if progress_callback:
                        progress_callback(
                            completed_count,
                            len(chunks),
                            f"{completed_count}/{len(chunks)} "
                            f"청크 완료"
                        )

                return

        async with semaphore:
            start_msg = (
                f"[{idx}/{len(chunks)}] "
                f"청크 번역 시작: "
                f"{len(chunk)}자 | "
                f"{len(chunk.splitlines())}줄"
            )

            if log_callback:
                log_callback(start_msg)

            try:
                result_text, _ = await translate_chunk_safe_async(
                    chunk=chunk,
                    model_name=model_name,
                    safety_settings=safety_settings,
                    rate_limiter=rate_limiter,
                    temperature=temperature,
                    log_callback=log_callback,
                    chunk_idx=idx,
                    raw=raw,
                    dicts=dicts
                )

                with open(
                    file_path,
                    "w",
                    encoding=_A
                ) as f:
                    f.write(result_text)

                async with lock:
                    translated_parts[idx - 1] = result_text
                    translated_parts_raw[idx - 1] = result_text

                if log_callback:
                    log_callback(
                        f"[{idx}/{len(chunks)}] "
                        f"청크 번역 완료: 성공"
                    )

            except Exception as e:
                err_msg = (
                    f" └ [{idx}번 청크] "
                    f"번역 최종 실패: {e}"
                )

                if log_callback:
                    log_callback(err_msg)

                err_text = (
                    f"\n+---+\n"
                    f"[번역 실패: {idx}번째 청크]\n"
                    f"error+---+\n"
                    f"error 청크 next\n"
                )

                async with lock:
                    translated_parts[idx - 1] = err_text
                    translated_parts_raw[idx - 1] = chunk

                error_path = (
                    f"{ai_dir}/{idx}_error.txt"
                )

                with open(
                    error_path,
                    "w",
                    encoding=_A
                ) as f:
                    f.write(chunk)

            async with lock:
                completed_count += 1

                if progress_callback:
                    progress_callback(
                        completed_count,
                        len(chunks),
                        f"{completed_count}/{len(chunks)} "
                        f"청크 완료"
                    )

    tasks = [
        process_chunk(idx, chunk)
        for idx, chunk in enumerate(chunks, 1)
    ]

    await asyncio.gather(*tasks)

    json_path = (
        f"{out}trs\\"
        f"save_{safe} _ {max_chars}.json"
    )

    save_translation_json(
        translated_parts_raw,
        max_chars,
        title,
        json_path,
        raw=raw
    )

    if raw:
        txt_path = (
            f"{out}epub\\raw_txt\\"
            f"{safe}.txt"
        )

        if "_" in title:
            book_title, author = title.rsplit("_", 1)
        else:
            book_title = title
            author = ""

        r_title = (
            f"{book_title}\n"
            f"{author}\n"
            f"(raw)\n"
            f"{_K}"
            f"{book_title} | {author}\n\n"
        )

        save_translation_txt(
            translated_parts_raw,
            r_title,
            txt_path
        )

    return "\n\n".join(
        p for p in translated_parts if p
    )


def translate_light_novel(
    text,
    max_chars=5000,
    model_name=MODEL_NAME,
    rpm=15,
    temperature=0.5,
    max_concurrent=4,
    title="save",
    progress_callback=_D,
    log_callback=_D,
    raw=False,
    dicts={}
):
    return asyncio.run(
        _translate_light_novel_async(
            text,
            max_chars,
            model_name,
            rpm,
            temperature,
            max_concurrent,
            title,
            progress_callback,
            log_callback,
            raw,
            dicts
        )
    )


def TransAi_All(
    txt,
    max_chars=5000,
    model_name=_J,
    rpm=15,
    temperature=0.1,
    max_concurrent=4,
    progress_callback=_D,
    log_callback=_D,
    dicts={}
):
    raw = detect_raw_text(txt)

    if raw:
        # RAW 원본의 제목/작가를 원본에서 직접 가져온다.
        # 이후 title을 "_" 기준으로 다시 분리하지 않는다.
        lines = txt.splitlines(keepends=True)

        book_title = (
            lines[0].strip()
            if len(lines) > 0
            else "제목 미정"
        )

        author = (
            lines[1].strip()
            if len(lines) > 1
            else ""
        )

        raw_text, raw_title = prepare_raw_text(txt)

        if log_callback:
            log_callback(
                f"RAW 번역 시작: 제목 '{book_title}', "
                f"작가 '{author}', "
                f"청크 크기: {max_chars}, "
                f"동시 작업수: {max_concurrent}"
            )

        translated_result = _K + translate_light_novel(
            raw_text,
            max_chars=max_chars,
            model_name=model_name,
            rpm=rpm,
            temperature=temperature,
            max_concurrent=max_concurrent,
            title=raw_title,
            progress_callback=progress_callback,
            log_callback=log_callback,
            raw=True,
            dicts=dicts
        )

        epub_text = (
            f"{book_title}\n"
            f"{author}\n"
            f"(raw)\n"
            f"{_K}"
            f"{translated_result}"
        )

        down.create_epub_from_merged_txt(
            txt_value=epub_text,
            RAW=True,
        )

        return translated_result

    A = "_번역\n"

    if _G in txt:
        split_pos = txt.find(_G)

        f = txt[:split_pos - 1]
        g = txt[split_pos + 6:]
    else:
        f = "제목 미정"
        g = txt

    first_newline = f.find(_B)

    if first_newline == -1:
        t = f
    else:
        t = (
            f[:first_newline]
            + "_"
            + f[first_newline + 1:]
        )

    if log_callback:
        log_callback(
            f"전체 번역 시작: 제목 '{t}', "
            f"청크 크기: {max_chars}, "
            f"동시 작업수: {max_concurrent}"
        )

    translated_result = _K + translate_light_novel(
        g,
        max_chars=max_chars,
        model_name=model_name,
        rpm=rpm,
        temperature=temperature,
        max_concurrent=max_concurrent,
        title=t,
        progress_callback=progress_callback,
        log_callback=log_callback,
        raw=False,
        dicts=dicts
    )

    title_end = f.find(_B)

    if title_end == -1:
        epub_text = (
            f
            + A
            + translated_result
        )
    else:
        epub_text = (
            f[:title_end]
            + A
            + f[title_end + 1:]
            + _B
            + translated_result
        )

    down.create_epub_from_merged_txt(
        txt_value=epub_text,
        RAW=False
    )

    return translated_result


async def _TransAi_From_Json_async(
    json_path,
    model_name,
    rpm,
    temperature,
    max_concurrent,
    progress_callback,
    log_callback,
    dicts
):
    if not os.path.exists(json_path):
        msg = (
            f"에러: JSON 파일을 찾을 수 없습니다 | "
            f"{json_path}"
        )

        if log_callback:
            log_callback(msg)

        return "error"

    with open(
        json_path,
        "r",
        encoding=_A
    ) as f:
        data = json.load(f)

    title = data.get(
        "name",
        "restored"
    )

    max_chars = data.get(
        "chunk",
        5000
    )

    raw = bool(
        data.get(
            "raw",
            False
        )
    )

    out = getattr(
        down.downin,
        _H,
        "./out"
    ) + "/"

    os.makedirs(
        f"{out}trs",
        exist_ok=_C
    )

    safe = re.sub(
        _I,
        "_",
        title
    ).strip()

    ai_dir = (
        f"{out}trs\\"
        f"ai_down_{safe}_{max_chars}"
    )

    os.makedirs(
        ai_dir,
        exist_ok=_C
    )

    safety_settings = get_safety_settings()

    chunk_keys = sorted(
        [
            k for k in data.keys()
            if k.isdigit()
        ],
        key=int
    )

    msg = (
        f"[{title}] JSON 로드 완료 "
        f"(청크 크기: {max_chars}, "
        f"총 {len(chunk_keys)}개 청크 비동기 복원) "
        f"/ 사용 모델: {model_name} "
        f"/ RAW: {raw}"
    )

    if log_callback:
        log_callback(msg)

    translated_parts = [
        None
    ] * len(chunk_keys)

    translated_parts_raw = [
        None
    ] * len(chunk_keys)

    rate_limiter = AsyncRateLimiter(rpm)

    concurrency_limit = max(
        1,
        min(15, max_concurrent)
    )

    semaphore = asyncio.Semaphore(
        concurrency_limit
    )

    completed_count = 0
    lock = asyncio.Lock()

    async def process_json_chunk(
        pos,
        key,
        dicts
    ):
        nonlocal completed_count

        idx = int(key) + 1
        chunk_text = data[key]

        if not isinstance(
            chunk_text,
            str
        ):
            chunk_text = str(chunk_text)

        chunk_text = (
            chunk_text
            .replace("%'%", '"')
            .replace("\\\n", _B)
        )

        file_path = (
            f"{ai_dir}/{idx}.txt"
        )

        jp_ratio = get_japanese_ratio(
            chunk_text
        )

        if jp_ratio >= 0.5:
            re_msg = (
                f"[{idx}/{len(chunk_keys)}] "
                f"재번역 필요: "
                f"일본어 비율 {jp_ratio:.4f}%"
            )

            if log_callback:
                log_callback(re_msg)

            async with semaphore:
                try:
                    result_text, _ = (
                        await translate_chunk_safe_async(
                            chunk=chunk_text,
                            model_name=model_name,
                            safety_settings=safety_settings,
                            rate_limiter=rate_limiter,
                            temperature=temperature,
                            log_callback=log_callback,
                            chunk_idx=idx,
                            raw=raw,
                            dicts=dicts
                        )
                    )

                except Exception as e:
                    if log_callback:
                        log_callback(
                            f" └ [{idx}번 청크] "
                            f"재번역 실패: {e}"
                        )

                    result_text = chunk_text

        else:
            if log_callback:
                log_callback(
                    f"[{idx}/{len(chunk_keys)}] "
                    f"청크 통과: "
                    f"일본어 비율 {jp_ratio:.4f}%"
                )

            result_text = chunk_text

        with open(
            file_path,
            "w",
            encoding=_A
        ) as f_out:
            f_out.write(result_text)

        async with lock:
            translated_parts_raw[pos - 1] = result_text
            translated_parts[pos - 1] = result_text
            completed_count += 1

            if progress_callback:
                progress_callback(
                    completed_count,
                    len(chunk_keys),
                    f"{completed_count}/{len(chunk_keys)} "
                    f"청크 완료"
                )

    tasks = [
        process_json_chunk(
            pos,
            key,
            dicts
        )
        for pos, key in enumerate(
            chunk_keys,
            1
        )
    ]

    await asyncio.gather(*tasks)

    final_result = "\n\n".join(
        p for p in translated_parts if p
    )

    os.makedirs(
        f"{out}trs",
        exist_ok=_C
    )

    save_path = (
        f"{out}trs\\"
        f"save_{safe}_{max_chars}_복원.json"
    )

    save_translation_json(
        translated_parts_raw,
        max_chars,
        f"{title}_복원",
        save_path,
        raw=raw,
    )

    if raw:
        os.makedirs(
            f"{out}epub",
            exist_ok=_C
        )

        os.makedirs(
            f"{out}epub\\raw_txt",
            exist_ok=_C
        )

        txt_path = (
            f"{out}epub\\raw_txt\\"
            f"{safe}_복원.txt"
        )

        # JSON의 title은 기본적으로 "작품명_작가명"
        # 형태이므로 내부 표시용 제목을 생성한다.
        if "_" in title:
            book_title, author = title.rsplit(
                "_",
                1
            )
        else:
            book_title = title
            author = ""

        restored_title = (
            f"{book_title}_복원"
        )

        r_title = (
            f"{restored_title}\n"
            f"{author}\n"
            f"(raw)\n"
            f"{_K}"
            f"{restored_title} | {author}\n\n"
        )

        save_translation_txt(
            translated_parts_raw,
            r_title,
            txt_path
        )

    if raw:
        # RAW 복원에서도 제목 구조를 명확하게 유지
        if "_" in title:
            book_title, author = title.rsplit(
                "_",
                1
            )
        else:
            book_title = title
            author = ""

        epub_text = (
            f"{book_title}_복원\n"
            f"{author}\n"
            f"(raw)\n"
            f"{_K}"
            f"{final_result}"
        )
    else:
        epub_text = (
            f"{title}_복원_번역\n"
            f"{_K}"
            f"{final_result}"
        )

    down.create_epub_from_merged_txt(
        txt_value=epub_text,
        RAW=raw,
    )

    return final_result


def TransAi_From_Json(
    json_path,
    model_name=_J,
    rpm=15,
    temperature=0.1,
    max_concurrent=4,
    progress_callback=_D,
    log_callback=_D,
    dicts={}
):
    return asyncio.run(
        _TransAi_From_Json_async(
            json_path,
            model_name,
            rpm,
            temperature,
            max_concurrent,
            progress_callback,
            log_callback,
            dicts
        )
    )


def save_translation_json(
    translated_parts_raw,
    max_chars,
    title,
    file_path,
    raw=False,
):
    data = {}

    for i, text in enumerate(
        translated_parts_raw
    ):
        data[str(i)] = text

    data["chunk"] = max_chars
    data["name"] = title

    if raw:
        data["raw"] = True

    with open(
        file_path,
        "w",
        encoding=_A
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=_F,
            indent=4
        )


def save_translation_txt(
    translated_parts_raw,
    title,
    file_path
):
    data = {}

    for i, text in enumerate(
        translated_parts_raw
    ):
        data[str(i)] = text

    data["name"] = title

    with open(
        file_path,
        "w",
        encoding=_A
    ) as f:
        f.write(
            title
            + "\n"
            + "".join(translated_parts_raw)
        )


def _extract_glossary_sample(all_text, paserent):
    """
    전체 텍스트에서 paserent(%)만큼 분석용 텍스트를 추출한다.
    텍스트의 앞부분만 자르지 않고 전체 구간에 골고루 분포하도록 한다.
    """
    if not all_text:
        return ""

    try:
        paserent = float(paserent)
    except (TypeError, ValueError):
        paserent = 10.0

    paserent = max(0.1, min(100.0, paserent))

    if paserent >= 100.0:
        return all_text

    target_length = max(1, int(len(all_text) * paserent / 100.0))

    if target_length >= len(all_text):
        return all_text

    # 전체 텍스트에서 일정 간격으로 여러 구간을 뽑는다.
    # 한 곳에 몰리지 않게 하기 위한 방식.
    segment_count = max(
        1,
        min(20, len(all_text) // max(1, target_length // 4))
    )

    segment_length = max(
        1,
        target_length // segment_count
    )

    if segment_length * segment_count > target_length:
        segment_length = max(
            1,
            target_length // segment_count
        )

    result = []

    max_start = len(all_text) - segment_length

    if segment_count == 1:
        positions = [max_start // 2]
    else:
        positions = [
            int(
                max_start * i / (segment_count - 1)
            )
            for i in range(segment_count)
        ]

    for start in positions:
        part = all_text[
            start:start + segment_length
        ]

        if part:
            result.append(part)

    sample = "\n".join(result)

    # 실제 사용량이 목표보다 약간 달라질 수 있으므로
    # 최종적으로 목표 길이만큼 제한
    return sample[:target_length]


def _split_glossary_text(text, chunk):
    """
    분석 대상 텍스트를 chunk 크기로 분할한다.
    가능한 경우 줄 단위로 자른다.
    """
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

        # 한 줄 자체가 chunk보다 긴 경우
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


async def _extract_glossary_chunk_async(
    chunk_text,
    chunk_idx,
    total_chunks,
    log_callback=None,
    max_retries=3
):
    system_prompt = """당신은 일본어 라이트노벨 전문 용어집 추출기입니다.

입력된 일본어 본문을 분석하여 작품 전체에서 반복적으로 사용되거나 번역 시 일관성이 중요한 고유명사, 인명, 지명, 조직명, 능력명, 아이템명, 직업명, 호칭, 특수 용어 등을 추출하십시오.

중요:
- 일반적인 조사, 동사, 형용사 등은 추출하지 마십시오.
- 문맥상 번역을 통일할 필요가 있는 단어를 우선하십시오.
- 인명과 고유명사는 적극적으로 추출하십시오.
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

    for attempt in range(1, max_retries + 1):
        if log_callback:
            log_callback(
                f"[용어집 {chunk_idx}/{total_chunks}] "
                f"추출 시도 {attempt}/{max_retries}"
            )

        try:
            response = await client.aio.models.generate_content(
                model=MODEL_NAME,
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
                        f"[용어집 {chunk_idx}/{total_chunks}] "
                        f"응답 없음"
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
            if log_callback:
                log_callback(
                    f"[용어집 {chunk_idx}/{total_chunks}] "
                    f"오류: {e}"
                )

            await asyncio.sleep(1.0)

    return {}


async def _extract_glossary_async(
    all_text,
    paserent,
    chunk,
    log_callback=None
):
    if not all_text:
        if log_callback:
            log_callback(
                "용어집 추출 실패: 입력 텍스트가 비어있음"
            )

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
    sample_text = _extract_glossary_sample(
        all_text,
        paserent_value
    )

    if not sample_text:
        if log_callback:
            log_callback(
                "용어집 추출 실패: 분석 대상 텍스트가 없음"
            )

        return {}

    if log_callback:
        log_callback(
            f"분석 대상 생성 완료: "
            f"{len(sample_text)}자 "
            f"({len(sample_text) / len(all_text) * 100:.2f}%)"
        )
    chunks = _split_glossary_text(
        sample_text,
        chunk_value
    )

    if not chunks:
        return {}

    if log_callback:
        log_callback(
            f"용어집 분석 청크 분할 완료: "
            f"{len(chunks)}개"
        )

    tasks = [
        _extract_glossary_chunk_async(
            chunk_text,
            idx,
            len(chunks),
            log_callback
        )
        for idx, chunk_text in enumerate(
            chunks,
            1
        )
    ]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True
    )
    glossary_candidates = {}

    for idx, result in enumerate(
        results,
        1
    ):
        if isinstance(
            result,
            Exception
        ):
            if log_callback:
                log_callback(
                    f"[용어집 {idx}/{len(chunks)}] "
                    f"결과 처리 실패: {result}"
                )

            continue

        if not isinstance(
            result,
            dict
        ):
            continue

        for source, target in result.items():
            source = source.strip()
            target = target.strip()

            if not source or not target:
                continue

            glossary_candidates.setdefault(
                source,
                []
            ).append(target)

    final_glossary = {}

    for source, targets in glossary_candidates.items():
        if not targets:
            continue

        counter = Counter(targets)

        target, count = counter.most_common(1)[0]

        final_glossary[source] = target

        if (
            log_callback
            and len(counter) > 1
        ):
            log_callback(
                f"용어 번역 충돌: "
                f"'{source}' -> "
                f"'{target}' 선택 "
                f"({count}/{len(targets)})"
            )

    if log_callback:
        log_callback(
            f"용어집 추출 완료: "
            f"{len(final_glossary)}개"
        )

    return final_glossary


def extract_glossary(
    all_text,
    paserent=10,
    chunk=5000,
    log_callback=None
):
    return asyncio.run(
        _extract_glossary_async(
            all_text,
            paserent,
            chunk,
            log_callback
        )
    )