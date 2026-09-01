_K = "+---+\n"
_J = "gemini-3.5-flash"
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
from google import genai
from google.genai import types
import down

from config import DATA_FILE

API = _E
MODEL_NAME = "gemini-3.5-flash-lite"


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
        self.compiled = [re.compile(pattern, re.IGNORECASE) for pattern in self.rules]

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
    jp_chars = len(re.findall(r"[\u3040-\u309f\u30a0-\u30ff]", clean_text))
    return jp_chars / len(clean_text) * 100


def get_korean_ratio(text):
    if not text:
        return 0.0
    clean_text = re.sub(r"[^\w]|[\d_]", "", text)
    if not clean_text:
        return 0.0
    ko_chars = len(re.findall(r"[\uac00-\ud7a3\u3131-\u318e]", clean_text))
    return ko_chars / len(clean_text) * 100


def get_linebreak_preservation_ratio(original, translated):
    original_breaks = original.count("\n")
    translated_breaks = translated.count("\n")
    if original_breaks == 0:
        return 100.0 if translated_breaks == 0 else 0.0
    difference = abs(original_breaks - translated_breaks)
    return max(0.0, (1.0 - difference / original_breaks) * 100.0)


def get_safety_settings():
    return [
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=types.HarmBlockThreshold.BLOCK_NONE),
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
):
    lines = chunk.splitlines(keepends=True)
    if not lines:
        return "", 0

    if get_japanese_ratio(chunk) < 0.03:
        if log_callback:
            log_callback(f"[{chunk_idx} - ] [{depth}] [시도 0] 원문의 일본어 비율이 너무 낮아 번역 생략")
        return chunk, len(lines)

    current_chunk = chunk
    is_censored = False
    if raw:
        expected_delimiter_count = len(re.findall(r'^={4,}$', chunk, re.MULTILINE))
    else:
        expected_delimiter_count = chunk.count(_G)

    attempt = 1
    while attempt <= max_retries:
        censored_label = "검열" if is_censored else ""
        prefix_log = f"[{chunk_idx} - {censored_label}] [{depth}] [시도 {attempt}/{max_retries}]"

        if log_callback:
            log_callback(f"{prefix_log} 번역 시도: (라인 수: {len(lines)}, temperature: {temperature})")

        await rate_limiter.wait()

        try:
            if raw:
                system_prompt = SYSTEM_PROMPT_RAW
            else:
                system_prompt = SYSTEM_PROMPT if _G in chunk else SYSTEM_PROMPT_NO_SPLIT

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
                    res_text.replace("「", "“")
                    .replace("」", "”")
                    .replace("｢", "“")
                    .replace("｣", "”")
                )

                if not raw and _G in chunk:
                    actual_delimiter_count = res_text.count(_G)
                    if actual_delimiter_count != expected_delimiter_count:
                        if log_callback:
                            log_callback(f"{prefix_log} 경고: '+---+' 개수 불일치 (기대: {expected_delimiter_count}, 결과: {actual_delimiter_count}) -> 재시도")
                        current_chunk = chunk
                        attempt += 1
                        is_censored = False
                        continue
                    
                if raw and "====" in chunk:
                    # 한 줄 전체가 '=' 4개 이상으로 이루어진 라인 개수 카운트
                    actual_delimiter_count = len(re.findall(r'^={4,}$', res_text, re.MULTILINE))
                    if actual_delimiter_count != expected_delimiter_count:
                        if log_callback:
                            log_callback(f"{prefix_log} 경고: '====...' 라인 개수 불일치 (기대: {expected_delimiter_count}, 결과: {actual_delimiter_count}) -> 재시도")
                        current_chunk = chunk
                        attempt += 1
                        is_censored = False
                        continue

                jp_ratio = get_japanese_ratio(res_text)
                ko_ratio = get_korean_ratio(res_text)

                # 1. chunk 길이에 따른 가변 기준 설정
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

                # 2. 번역 검증 로직
                if raw:
                    line_ratio = get_linebreak_preservation_ratio(chunk, res_text)

                    if jp_ratio < max_jp_ratio and ko_ratio >= min_ko_ratio and line_ratio >= min_line_ratio:
                        if log_callback:
                            log_callback(f"{prefix_log} -> 성공: (줄바꿈 보존율: {line_ratio:.2f}%)")
                        return res_text, len(lines)

                    if log_callback:
                        log_callback(
                            f"{prefix_log} 경고: 번역 조건 미달 "
                            f"(한글: {ko_ratio:.2f}% [기준 {min_ko_ratio}%], "
                            f"일어: {jp_ratio:.2f}% [기준 <{max_jp_ratio}%], "
                            f"줄바꿈: {line_ratio:.2f}% [기준 {min_line_ratio}%]) -> 재시도"
                        )
                else:
                    if jp_ratio < max_jp_ratio and ko_ratio >= min_ko_ratio:
                        if log_callback:
                            log_callback(f"{prefix_log} -> 성공: 완료")
                        return res_text, len(lines)

                    if log_callback:
                        log_callback(
                            f"{prefix_log} 경고: 번역 조건 미달 "
                            f"(한글: {ko_ratio:.2f}% [기준 {min_ko_ratio}%], "
                            f"일어: {jp_ratio:.2f}% [기준 <{max_jp_ratio}%]) -> 재시도"
                        )

                current_chunk = chunk
                is_censored = False
                attempt += 1
            else:
                if log_callback:
                    log_callback(f"{prefix_log} 경고: API 응답이 비어있음 -> 검열 실행")
                current_chunk = x_making(chunk)
                if is_censored:
                    attempt += 1
                    break
                is_censored = True
                attempt += 1
                continue

        except Exception as e:
            if log_callback:
                log_callback(f"{prefix_log} 오류: API 호출 중 예외 발생: {e} -> 재시도")
            is_censored = False
            attempt += 1

    if len(lines) <= 2 or depth >= 4:
        if log_callback:
            log_callback(f"[{chunk_idx} - ] [{depth}] 오류: [최대초과] 최대 재시도 초과 및 분할 한계 도달 -> 원문 유지")
        return chunk, len(lines)

    mid = len(lines) // 2

    if log_callback:
        log_callback(f"[{chunk_idx} - ] [{depth}] 경고: [분할] 청크 분할 처리 (전반부 {mid}줄, 후반부 {len(lines)-mid}줄)")

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
    )

    return part1_text.rstrip(_B) + _B + part2_text.lstrip(_B), len(lines)


def detect_raw_text(text):
    lines = text.splitlines()
    return len(lines) >= 3 and lines[2].strip().lower() == "(raw)"


def prepare_raw_text(text):
    lines = text.splitlines(keepends=True)

    if len(lines) < 3 or lines[2].strip().lower() != "(raw)":
        return text, "제목 미정"

    title = lines[0].strip() + "_" + lines[1].strip()
    
    body_start = None

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

    raw_body_lines = raw_body.splitlines(keepends=True)

    if raw_body_lines:
        raw_body = "".join(raw_body_lines)

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
):
    if API == _E:
        if log_callback:
            log_callback("에러: API 키가 설정되지 않았습니다.")
        return "error"

    chunks = split_text_by_lines(text, max_chars=max_chars)
    translated_parts = [None] * len(chunks)
    translated_parts_raw = [None] * len(chunks)

    out = getattr(down.downin, _H, "./out") + "/"
    os.makedirs(f"{out}trs", exist_ok=_C)
    os.makedirs(f"{out}epub", exist_ok=_C)
    os.makedirs(f"{out}epub\\raw_txt", exist_ok=_C)

    safe = re.sub(_I, "_", title).strip()
    ai_dir = f"{out}trs\\ai_down_{safe}_{max_chars}"
    os.makedirs(ai_dir, exist_ok=_C)

    msg = f"총 {len(chunks)}개 청크 분할 완료 (청크 크기: {max_chars}). 사용 모델: {model_name}, 동시 작업수: {max_concurrent}, RAW: {raw}"
    print(msg)

    if log_callback:
        log_callback(msg)

    safety_settings = get_safety_settings()
    rate_limiter = AsyncRateLimiter(rpm)

    concurrency_limit = max(1, min(15, max_concurrent))
    semaphore = asyncio.Semaphore(concurrency_limit)

    completed_count = 0
    lock = asyncio.Lock()

    async def process_chunk(idx, chunk):
        nonlocal completed_count

        file_path = f"{ai_dir}/{idx}.txt"

        if os.path.exists(file_path):
            with open(file_path, "r", encoding=_A) as f:
                saved_text = f.read()

            if saved_text and not saved_text.startswith("[번역 실패"):
                skip_msg = f"[{idx}/{len(chunks)}] 이미 저장된 파일 존재 → 건너뜀"

                if log_callback:
                    log_callback(skip_msg)

                async with lock:
                    translated_parts[idx - 1] = saved_text
                    translated_parts_raw[idx - 1] = saved_text
                    completed_count += 1

                    if progress_callback:
                        progress_callback(completed_count, len(chunks), f"{completed_count}/{len(chunks)} 청크 완료: 성공")

                return

        async with semaphore:
            start_msg = f"[{idx}/{len(chunks)}] 청크 번역 시작: {len(chunk)}자 | {len(chunk.splitlines())}줄"

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
                )

                with open(file_path, "w", encoding=_A) as f:
                    f.write(result_text)

                async with lock:
                    translated_parts[idx - 1] = result_text
                    translated_parts_raw[idx - 1] = result_text

                if log_callback:
                    log_callback(f"[{idx}/{len(chunks)}] 청크 번역 완료: 성공")

            except Exception as e:
                err_msg = f" └ [{idx}번 청크] 번역 최종 실패: {e}"

                if log_callback:
                    log_callback(err_msg)

                err_text = f"\n+---+\n[번역 실패: {idx}번째 청크]\nerror+---+\nerror 청크 next\n"

                async with lock:
                    translated_parts[idx - 1] = err_text
                    translated_parts_raw[idx - 1] = chunk

                error_path = f"{ai_dir}/{idx}_error.txt"

                with open(error_path, "w", encoding=_A) as f:
                    f.write(chunk)

            async with lock:
                completed_count += 1

                if progress_callback:
                    progress_callback(completed_count, len(chunks), f"{completed_count}/{len(chunks)} 청크 완료: 성공")

    tasks = [process_chunk(idx, chunk) for idx, chunk in enumerate(chunks, 1)]
    await asyncio.gather(*tasks)

    json_path = f"{out}trs\\save_{safe} _ {max_chars}.json"
    save_translation_json(translated_parts_raw, max_chars, title, json_path, raw=raw)
    if raw:
        txt_path = f"{out}epub\\raw_txt\\{safe}.txt"
        r_title = ""
        r_title += title[:str(title).rfind("_")]
        r_title += "\n" + title[str(title).rfind("_") + 1:]
        r_title += "\n(raw)"
        r_title += "\n" + _K
        r_title += title[:str(title).rfind("_")] + " | " + title[str(title).rfind("_") + 1:]
        r_title += "\n\n"
        save_translation_txt(translated_parts_raw, r_title, txt_path)

    return "\n\n".join([p for p in translated_parts if p])


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
):
    raw = detect_raw_text(txt)

    if raw:
        lines = txt.splitlines(keepends=True)
        title = lines[0].strip() if lines else "제목 미정"

        raw_text, raw_title = prepare_raw_text(txt)

        if log_callback:
            log_callback(
                f"RAW 번역 시작: 제목 '{raw_title}', "
                f"청크 크기: {max_chars}, 동시 작업수: {max_concurrent}"
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
        )

        epub_text = f"{title}\n{lines[1].strip() if len(lines) > 1 else ''}\n(raw)\n{_K}{translated_result}"

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
        t = f[:first_newline] + "_" + f[first_newline + 1:]


    if log_callback:
        log_callback(
            f"전체 번역 시작: 제목 '{t}', 청크 크기: {max_chars}, 동시 작업수: {max_concurrent}"
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
    )

    title_end = f.find(_B)

    if title_end == -1:
        epub_text = f + A + translated_result
    else:
        epub_text = f[:title_end] + A + f[title_end + 1:] + _B + translated_result

    down.create_epub_from_merged_txt(txt_value=epub_text, RAW=False)

    return translated_result


async def _TransAi_From_Json_async(
    json_path,
    model_name,
    rpm,
    temperature,
    max_concurrent,
    progress_callback,
    log_callback,
):
    if not os.path.exists(json_path):
        msg = f"에러: JSON 파일을 찾을 수 없습니다 | {json_path}"

        if log_callback:
            log_callback(msg)

        return "error"

    with open(json_path, "r", encoding=_A) as f:
        data = json.load(f)

    title = data.get("name", "restored")
    max_chars = data.get("chunk", 5000)
    raw = bool(data.get("raw", False))

    out = getattr(down.downin, _H, "./out") + "/"
    os.makedirs(f"{out}trs", exist_ok=_C)

    safe = re.sub(_I, "_", title).strip()
    ai_dir = f"{out}trs\\ai_down_{safe}_{max_chars}"
    os.makedirs(ai_dir, exist_ok=_C)

    safety_settings = get_safety_settings()
    chunk_keys = sorted([k for k in data.keys() if k.isdigit()], key=int)

    msg = (
        f"[{title}] JSON 로드 완료 "
        f"(청크 크기: {max_chars}, 총 {len(chunk_keys)}개 청크 비동기 복원) "
        f"/ 사용 모델: {model_name} / RAW: {raw}"
    )

    if log_callback:
        log_callback(msg)

    translated_parts = [None] * len(chunk_keys)
    translated_parts_raw = [None] * len(chunk_keys)
    rate_limiter = AsyncRateLimiter(rpm)

    concurrency_limit = max(1, min(15, max_concurrent))
    semaphore = asyncio.Semaphore(concurrency_limit)

    completed_count = 0
    lock = asyncio.Lock()

    async def process_json_chunk(pos, key):
        nonlocal completed_count

        idx = int(key) + 1
        chunk_text = data[key]

        if not isinstance(chunk_text, str):
            chunk_text = str(chunk_text)

        chunk_text = chunk_text.replace("%'%", '"').replace("\\\n", _B)

        file_path = f"{ai_dir}/{idx}.txt"
        jp_ratio = get_japanese_ratio(chunk_text)

        if jp_ratio >= 0.5:
            re_msg = f"[{idx}/{len(chunk_keys)}] 재번역 필요: 일본어 비율 {jp_ratio:.4f}%"

            if log_callback:
                log_callback(re_msg)

            async with semaphore:
                try:
                    result_text, _ = await translate_chunk_safe_async(
                        chunk=chunk_text,
                        model_name=model_name,
                        safety_settings=safety_settings,
                        rate_limiter=rate_limiter,
                        temperature=temperature,
                        log_callback=log_callback,
                        chunk_idx=idx,
                        raw=raw,
                    )
                except Exception as e:
                    if log_callback:
                        log_callback(f" └ [{idx}번 청크] 재번역 실패: {e}")

                    result_text = chunk_text
        else:
            if log_callback:
                log_callback(f"[{idx}/{len(chunk_keys)}] 청크 통과: 일본어 비율 {jp_ratio:.4f}%")

            result_text = chunk_text

        with open(file_path, "w", encoding=_A) as f_out:
            f_out.write(result_text)

        async with lock:
            translated_parts_raw[pos - 1] = result_text
            translated_parts[pos - 1] = result_text
            completed_count += 1

            if progress_callback:
                progress_callback(
                    completed_count,
                    len(chunk_keys),
                    f"{completed_count}/{len(chunk_keys)} 청크 완료: 성공",
                )

    tasks = [
        process_json_chunk(pos, key)
        for pos, key in enumerate(chunk_keys, 1)
    ]

    await asyncio.gather(*tasks)

    final_result = "\n\n".join([p for p in translated_parts if p])
    os.makedirs(f"{out}trs", exist_ok=_C)
    save_path = f"{out}trs\\save_{safe}_{max_chars}_복원.json"

    save_translation_json(
        translated_parts_raw,
        max_chars,
        f"{title}_복원",
        save_path,
        raw=raw,
    )
    
    if raw:
        os.makedirs(f"{out}epub", exist_ok=_C)
        os.makedirs(f"{out}epub\\raw_txt", exist_ok=_C)
        txt_path = f"{out}epub\\raw_txt\\{safe}_복원.txt"
        r_title = ""
        r_title += title[:str(title).rfind("_")] + "_복원"
        r_title += "\n" + title[str(title).rfind("_") + 1:]
        r_title += "\n(raw)"
        r_title += "\n" + _K
        r_title += title[:str(title).rfind("_")] + "_복원" + " | " + title[str(title).rfind("_") + 1:]
        r_title += "\n\n"
        save_translation_txt(translated_parts_raw, r_title, txt_path)

    if raw:
        epub_text = f"{title}\n\n(raw)\n{_K}{final_result}"
    else:
        epub_text = f"{title}_복원_번역\n{_K}{final_result}"

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

    for i, text in enumerate(translated_parts_raw):
        data[str(i)] = text

    data["chunk"] = max_chars
    data["name"] = title

    if raw:
        data["raw"] = True

    with open(file_path, "w", encoding=_A) as f:
        json.dump(data, f, ensure_ascii=_F, indent=4)
        
def save_translation_txt(
    translated_parts_raw,
    title,
    file_path
):
    
    data = {}

    for i, text in enumerate(translated_parts_raw):
        data[str(i)] = text

    data["name"] = title

    with open(file_path, "w", encoding=_A) as f:
        f.write(title + "\n" + "".join(translated_parts_raw))