_K = "+---+\n"
_J = "gemini-3.5-flash"
_I = '[\\\\/:*?"<>|]'
_H = "OUTFOLDER"
_G = "+---+"
_F = False
_E = "None"
_D = None
_C = True
_B = "\n"
_A = "utf-8"

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
    client = genai.Client(api_key=API)
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

client = genai.Client(api_key=API)
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
            "キス(?:하는|した)?",
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
            re.compile(pattern, re.IGNORECASE) for pattern in self.rules
        ]

    def normalize(self, text):
        text = unicodedata.normalize("NFKC", text)
        return re.sub("[\\u200B-\\u200D\\uFEFF]", "", text)

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
    result = _sanitizer.sanitize(text)
    return result

def split_text_by_lines(text, max_chars=5000):
    lines = text.splitlines(keepends=_C)
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
    
    jp_chars = len(re.findall("[\\u3040-\\u309f\\u30a0-\\u30ff]", clean_text))
    return jp_chars / len(clean_text) * 100

def get_korean_ratio(text):
    if not text:
        return 0.0

    clean_text = re.sub(r"[^\w]|[\d_]", "", text)
    
    if not clean_text:
        return 0.0

   
    ko_chars = len(re.findall(r"[\uac00-\ud7a3\u3131-\u318e]", clean_text))
    return (ko_chars / len(clean_text)) * 100

def get_safety_settings():
    return [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
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
):
    lines = chunk.splitlines(keepends=_C)
    if not lines:
        return "", 0
    if get_japanese_ratio(chunk) < 0.03:
        if log_callback:
            log_callback(
                f"[{chunk_idx} - ] [{depth}] [시도 0] 원문의 일본어 비율이 너무 낮아 번역 생략"
            )
        return chunk, len(lines)

    current_chunk = chunk
    is_censored = False
    expected_delimiter_count = chunk.count(_G)

    attempt = 1
    while attempt <= max_retries:
        censored_label = "검열" if is_censored else ""
        prefix_log = f"[{chunk_idx} - {censored_label}] [{depth}] [시도 {attempt}/{max_retries}]"

        if log_callback:
            log_callback(
                f"{prefix_log} 번역 시도 (라인 수: {len(lines)}, temperature: {temperature})"
            )

        await rate_limiter.wait()
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=f"번역:\n{current_chunk}",
                config=types.GenerateContentConfig(
                    system_instruction=(
                        SYSTEM_PROMPT if _G in chunk else SYSTEM_PROMPT_NO_SPLIT
                    ),
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

               
                if _G in chunk:
                    actual_delimiter_count = res_text.count(_G)
                    if actual_delimiter_count != expected_delimiter_count:
                        if log_callback:
                            log_callback(
                                f"{prefix_log} 경고: '+---+' 개수 불일치 (기대: {expected_delimiter_count}, 결과: {actual_delimiter_count}) -> 재시도"
                            )
                        current_chunk = chunk
                        attempt += 1
                        is_censored = False
                        continue

               
                jp_ratio = get_japanese_ratio(res_text)
                ko_ratio = get_korean_ratio(res_text)

                if jp_ratio < 0.5 and ko_ratio >= 80.0:
                    if log_callback:
                        log_callback(f"{prefix_log} -> 성공")
                    return res_text, len(lines)
                else:
                    if log_callback:
                        log_callback(
                            f"{prefix_log} 경고: 번역 조건 미달 (한글 비율: {ko_ratio:.2f}% [기준 80%], 일어 비율: {jp_ratio:.2f}%) -> 재시도"
                        )
                    current_chunk = chunk
                    is_censored = False
                    attempt += 1
            else:
                if log_callback:
                    log_callback(
                        f"{prefix_log} 경고: API 응답이 비어있음 (안전 문제 가능성) -> 검열 실행"
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
                log_callback(f"{prefix_log} 오류: API 호출 중 예외 발생: {e} -> 재시도")
            is_censored = False
            attempt += 1

   
    if len(lines) <= 2 or depth >= 3:
        if log_callback:
            log_callback(
                f"[{chunk_idx} - ] [{depth}] 오류: [최대초과] 최대 재시도 초과 및 분할 한계 도달 -> 원문 유지"
            )
        return (
            chunk,
            len(lines),
        )

    mid = len(lines) // 2
    if log_callback:
        log_callback(
            f"[{chunk_idx} - ] [{depth}] 경고: [분할] 청크 분할 처리 (전반부 {mid}줄, 후반부 {len(lines)-mid}줄)"
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
    )

    return part1_text.rstrip(_B) + _B + part2_text.lstrip(_B), len(lines)

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
):
    if API == _E:
        if log_callback:
            log_callback("API 키가 설정되지 않았습니다.")
        return "error"

    chunks = split_text_by_lines(text, max_chars=max_chars)
    translated_parts = [None] * len(chunks)
    translated_parts_raw = [None] * len(chunks)

    out = getattr(down.downin, _H, "./out") + "/"
    os.makedirs(f"{out}trs", exist_ok=_C)
    safe = re.sub(_I, "_", title).strip()

    ai_dir = f"{out}trs\\ai_down_{safe}_{max_chars}"
    os.makedirs(ai_dir, exist_ok=_C)

    msg = f"총 {len(chunks)}개 청크 분할 완료 (청크 크기: {max_chars}). 사용 모델: {model_name}, 동시 작업수: {max_concurrent}"
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
                saved_text = f.read().strip()
            if saved_text and not saved_text.startswith("[번역 실패"):
                skip_msg = f"[{idx}/{len(chunks)}] 이미 저장된 파일 존재 → 건너뜀"
                print(skip_msg)
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
                            f"{completed_count}/{len(chunks)} 청크 완료",
                        )
                return

        async with semaphore:
            start_msg = f"[{idx}/{len(chunks)}] 청크 번역 시작... ({len(chunk)}자)"
            print(start_msg)
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
                )
                with open(file_path, "w", encoding=_A) as f:
                    f.write(result_text)
                async with lock:
                    translated_parts[idx - 1] = result_text
                    translated_parts_raw[idx - 1] = result_text
                success_msg = f"[{idx}/{len(chunks)}] 청크 번역 완료"
                if log_callback:
                    log_callback(success_msg)
            except Exception as e:
                err_msg = f" └ [{idx}번 청크] 번역 최종 실패: {e}"
                print(err_msg)
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
                    progress_callback(
                        completed_count,
                        len(chunks),
                        f"{completed_count}/{len(chunks)} 청크 완료",
                    )

    tasks = [process_chunk(idx, chunk) for idx, chunk in enumerate(chunks, 1)]
    await asyncio.gather(*tasks)

    json_path = f"{out}trs\\save_{safe}_{max_chars}.json"
    save_translation_json(translated_parts_raw, max_chars, title, json_path)
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
    A = "_번역\n"
    if _G in txt:
        split_pos = txt.find(_G)
        f = txt[: split_pos - 1]
        g = txt[split_pos + 6 :]
    else:
        f = "제목 미정"
        g = txt
    first_newline = f.find(_B)
    if first_newline == -1:
        t = f
    else:
        t = f[:first_newline] + "_" + f[first_newline + 1 :]

    if log_callback:
        log_callback(
            f"TransAi_All 시작: 제목 '{t}', 청크 크기: {max_chars}, 동시 작업수: {max_concurrent}"
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
    )
    title_end = f.find(_B)
    if title_end == -1:
        epub_text = f + A + translated_result
    else:
        epub_text = (
            f[:title_end] + A + f[title_end + 1 :] + _B + translated_result
        )
    down.create_epub_from_merged_txt(txt_value=epub_text)
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
        msg = f"JSON 파일을 찾을 수 없습니다: {json_path}"
        print(msg)
        if log_callback:
            log_callback(msg)
        return "error"

    with open(json_path, "r", encoding=_A) as f:
        data = json.load(f)

    title = data.get("name", "restored")
    max_chars = data.get("chunk", 5000)
    out = getattr(down.downin, _H, "./out") + "/"
    os.makedirs(f"{out}trs", exist_ok=_C)
    safe = re.sub(_I, "_", title).strip()

    ai_dir = f"{out}trs\\ai_down_{safe}_{max_chars}"
    os.makedirs(ai_dir, exist_ok=_C)

    safety_settings = get_safety_settings()
    chunk_keys = sorted([k for k in data.keys() if k.isdigit()], key=int)

    msg = f"[{title}] JSON 로드 완료 (청크 크기: {max_chars}, 총 {len(chunk_keys)}개 청크 비동기 복원) / 사용 모델: {model_name}"
    print(msg)
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
            re_msg = (
                f"[{idx}/{len(chunk_keys)}] 재번역 필요 (일본어 비율: {jp_ratio:.4f}%)"
            )
            print(re_msg)
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
                    )
                except Exception as e:
                    err_msg = f" └ [{idx}번 청크] 재번역 실패: {e}"
                    print(err_msg)
                    if log_callback:
                        log_callback(err_msg)
                    result_text = chunk_text
        else:
            pass_msg = (
                f"[{idx}/{len(chunk_keys)}] 청크 통과 (일본어 비율: {jp_ratio:.4f}%)"
            )
            if log_callback:
                log_callback(pass_msg)
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
                    f"{completed_count}/{len(chunk_keys)} 청크 완료",
                )

    tasks = [
        process_json_chunk(pos, key) for pos, key in enumerate(chunk_keys, 1)
    ]
    await asyncio.gather(*tasks)

    final_result = "\n\n".join([p for p in translated_parts if p])
    save_path = f"{out}trs\\save_{safe}_{max_chars}_복원.json"
    save_translation_json(
        translated_parts_raw, max_chars, f"{title}_복원", save_path
    )
    down.create_epub_from_merged_txt(
        txt_value=title + "_복원_번역\n" + _K + final_result
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

def save_translation_json(translated_parts_raw, max_chars, title, file_path):
    data = {}
    for i, text in enumerate(translated_parts_raw):
        data[str(i)] = text
    data["chunk"] = max_chars
    data["name"] = title
    with open(file_path, "w", encoding=_A) as f:
        json.dump(data, f, ensure_ascii=_F, indent=4)