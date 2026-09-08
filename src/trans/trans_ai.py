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

import src.glossary_fast_py.glossary_text as glossary_text
extract_glossary = glossary_text.extract_glossary

from google import genai
from google.genai import types

import src.down.down as down
from src.system.config import DATA_FILE
from src.trans.prom import *
from src.trans.prompt_sanitizer import x_making, get_safety_settings


API = _E
MODEL_NAME = "gemini-3.5-flash-lite"
CUSTOM_AI_PROMPT = """"""

def set_api_key(api_key):
    global API, client

    API = api_key.strip() or _E
    client = genai.Client(api_key=API if API != "" else "None")
    glossary_text.client = client

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
                glossary_text.client = client
        except Exception:
            pass


client = genai.Client(api_key=API if API != "" else "None")
glossary_text.client = client
rest()

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

def _is_stopped(check):
    try:
        return bool(check and check())
    except Exception:
        return False

async def translate_chunk_safe_async(
    chunk,
    model_name,
    safety_settings,
    rate_limiter,
    temperature=0.2,
    max_retries=3,
    depth=0,
    log_callback=None,
    chunk_idx=0,
    raw=False,
    dicts=None,
    check=None,
    br_start=0
):
    if dicts is None:
        dicts = {}

    lines = chunk.splitlines(keepends=True)

    if not lines:
        return "", 0, False

    if _is_stopped(check):
        if log_callback:
            log_callback(f"[{chunk_idx} - ] [{depth}] 중지: 번역 시작 전 작업 중지")
        return None, 0, True

    force_split = br_start > 0

    if not force_split and get_japanese_ratio(chunk) < 0.03:
        if log_callback:
            log_callback(
                f"[{chunk_idx} - ] [{depth}] [시도 0] "
                f"원문의 일본어 비율이 너무 낮아 번역 생략"
            )
        return chunk, len(lines), False

    current_chunk = chunk
    is_censored = False

    if raw:
        expected_delimiter_count = len(
            re.findall(r'^={4,}$', chunk, re.MULTILINE)
        )
    else:
        expected_delimiter_count = chunk.count(_G)

    attempt = 1

    while not force_split and attempt <= max_retries:
        if _is_stopped(check):
            if log_callback:
                log_callback(
                    f"[{chunk_idx} - ] [{depth}] 중지: "
                    f"다음 API 요청을 실행하지 않습니다."
                )
            return None, 0, True

        censored_label = "검열" if is_censored else ""

        prefix_log = (
            f"[{chunk_idx} - {censored_label}] "
            f"[{depth}] [시도 {attempt}/{max_retries}]"
        )

        await rate_limiter.wait()

        if _is_stopped(check):
            if log_callback:
                log_callback(
                    f"{prefix_log} 중지: "
                    f"API 호출 직전 작업 중지"
                )
            return None, 0, True

        if log_callback:
            log_callback(
                f"{prefix_log} 번역 시작: "
                f"(라인 수: {len(lines)})"
            )

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
                system_prompt += (
                    f"\n\n[사용자 지정 추가 지침]\n"
                    f"{CUSTOM_AI_PROMPT}\n\n"
                )

            if dicts:
                glossary_value = build_dynamic_glossary(
                    chunk,
                    dicts
                )

                if glossary_value:
                    system_prompt += (
                        "\n\n"
                        + GLOSSARY_CONTEXT.format(
                            glossary=glossary_value
                        )
                    )

                    glossary_log = ", ".join(
                        glossary_value.splitlines()
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
                        is_censored = False
                        attempt += 1
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
                                f"{prefix_log} 경고: "
                                f"'====...' 라인 개수 불일치 "
                                f"(기대: {expected_delimiter_count}, "
                                f"결과: {actual_delimiter_count}) -> 재시도"
                            )

                        current_chunk = chunk
                        is_censored = False
                        attempt += 1
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

                    success = (
                        jp_ratio < max_jp_ratio
                        and ko_ratio >= min_ko_ratio
                        and line_ratio >= min_line_ratio
                    )
                else:
                    line_ratio = 100.0

                    success = (
                        jp_ratio < max_jp_ratio
                        and ko_ratio >= min_ko_ratio
                    )

                if success:
                    if log_callback:
                        if raw:
                            log_callback(
                                f"{prefix_log} -> 성공: "
                                f"(줄바꿈 보존율: {line_ratio:.2f}%)"
                            )
                        else:
                            log_callback(
                                f"{prefix_log} -> 성공: 완료"
                            )

                    return res_text, len(lines), False

                if log_callback:
                    if raw:
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

                if is_censored:
                    attempt += 1
                    break

                current_chunk = x_making(chunk)
                is_censored = True
                attempt += 1

        except Exception as e:
            if _is_stopped(check):
                if log_callback:
                    log_callback(
                        f"{prefix_log} 중지: "
                        f"현재 API 요청 종료 후 중지"
                    )
                return None, 0, True

            if log_callback:
                log_callback(
                    f"{prefix_log} 오류: API 호출 중 예외 발생: "
                    f"{e} -> 재시도. 원래 대기 시간에 3배 대기"
                )
                await rate_limiter.wait()
                await rate_limiter.wait()

            is_censored = False
            attempt += 1

    if _is_stopped(check):
        if log_callback:
            log_callback(
                f"[{chunk_idx} - ] [{depth}] 중지: "
                f"분할 작업을 실행하지 않습니다."
            )
        return None, 0, True

    if len(lines) <= 2 or depth >= 4:
        if log_callback:
            log_callback(
                f"[{chunk_idx} - ] [{depth}] 오류: "
                f"[최대초과] 최대 재시도 초과 및 분할 한계 도달 "
                f"-> 원문 유지"
            )
        return chunk, len(lines), False

    mid = len(lines) // 2

    if log_callback and not force_split:
        log_callback(
            f"[{chunk_idx} - ] [{depth}] 경고: [분할] "
            f"청크 분할 처리 "
            f"(전반부 {mid}줄, 후반부 {len(lines) - mid}줄)"
        )

    part1_text, part1_len, part1_ignore = await translate_chunk_safe_async(
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
        dicts,
        check,
        br_start=br_start-1
    )

    if part1_ignore:
        return part1_text, part1_len, True

    if part1_text is None:
        return None, 0, True

    if _is_stopped(check):
        return part1_text, len(lines[:mid]), True

    part2_text, part2_len, part2_ignore = await translate_chunk_safe_async(
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
        dicts,
        check,
        br_start=br_start-1
    )

    if part2_ignore:
        return part1_text, len(lines[:mid]), True

    if part2_text is None:
        return part1_text, len(lines[:mid]), True

    return (
        part1_text.rstrip(_B)
        + _B
        + part2_text.lstrip(_B),
        len(lines),
        False
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
    dicts={},
    check=None,
    br_start=0
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

    out = down.downin.base_data.OUTFOLDER + "/"

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
    ignored = False
    lock = asyncio.Lock()

    async def process_chunk(idx, chunk):
        nonlocal completed_count, ignored

        if _is_stopped(check):
            if log_callback:
                log_callback(
                    f"[{idx}/{len(chunks)}] 중지: "
                    f"대기 중인 청크 건너뜀"
                )
            return

        file_path = f"{ai_dir}/{idx}.txt"

        if os.path.exists(file_path):
            with open(file_path, "r", encoding=_A) as f:
                saved_text = f.read()

            if saved_text and not saved_text.startswith("[번역 실패"):
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
                            f"{completed_count}/{len(chunks)} 청크 완료"
                        )

                return

        async with semaphore:
            if _is_stopped(check):
                if log_callback:
                    log_callback(
                        f"[{idx}/{len(chunks)}] 중지: "
                        f"실행 대기 중 청크 건너뜀"
                    )
                return
            result_ignore_back = False
            try:
                result_text, result_lines, result_ignore = await translate_chunk_safe_async(
                    chunk=chunk,
                    model_name=model_name,
                    safety_settings=safety_settings,
                    rate_limiter=rate_limiter,
                    temperature=temperature,
                    log_callback=log_callback,
                    chunk_idx=idx,
                    raw=raw,
                    dicts=dicts,
                    check=check,
                    br_start=br_start
                )

                if result_ignore:
                    result_ignore_back = result_ignore
                    async with lock:
                        ignored = True
                    return

                with open(file_path, "w", encoding=_A) as f:
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
                if log_callback:
                    log_callback(
                        f" └ [{idx}번 청크] "
                        f"번역 최종 실패: {e}"
                    )

                err_text = (
                    f"\n+---+\n"
                    f"[번역 실패: {idx}번째 청크]\n"
                    f"error+---+\n"
                    f"error 청크 next\n"
                )

                async with lock:
                    translated_parts[idx - 1] = err_text
                    translated_parts_raw[idx - 1] = chunk

                error_path = f"{ai_dir}/{idx}_error.txt"

                with open(error_path, "w", encoding=_A) as f:
                    f.write(chunk)

            finally:
                async with lock:
                    if not result_ignore_back:
                        completed_count += 1

                        if progress_callback:
                            progress_callback(
                                completed_count,
                                len(chunks),
                                f"{completed_count}/{len(chunks)} 청크 완료"
                            )

    tasks = [
        process_chunk(idx, chunk)
        for idx, chunk in enumerate(chunks, 1)
    ]

    await asyncio.gather(*tasks)

    if ignored:
        return "ignore"

    json_path = (
        f"{out}trs\\"
        f"save_{safe} _ {max_chars}.json"
    )
    if not check():
        save_translation_json(
            translated_parts_raw,
            max_chars,
            title,
            json_path,
            raw=raw,
            br_start=br_start
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
        if not check():
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
    dicts={},
    check=None,
    br_start=0
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
            dicts,
            check,
            br_start
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
    dicts={},
    check=None,
    br_start=0
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
            dicts=dicts,
            check=check,
            br_start=br_start
        )

        if translated_result == "ignore":
            return "ignore"

        epub_text = (
            f"{book_title}\n"
            f"{author}\n"
            f"(raw)\n"
            f"{_K}"
            f"{translated_result}"
        )
        if not check():
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
        dicts=dicts,
        check=check,
        br_start=br_start
    )

    if translated_result == "ignore":
        return "ignore"

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
    if not check():
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
    dicts,
    check=None,
    br_start=0
):

    if _is_stopped(check):
        if log_callback:
            log_callback("JSON 복원 중지: 작업 시작 전 중지되었습니다.")
        return "ignore"

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

    out = down.downin.base_data.OUTFOLDER + "/"

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
    ignored = False
    lock = asyncio.Lock()

    async def process_json_chunk(
        pos,
        key,
        dicts
    ):
        nonlocal completed_count, ignored

        result_ignore_back = False

        try:
            if _is_stopped(check):
                result_ignore_back = True

                async with lock:
                    ignored = True

                if log_callback:
                    log_callback(
                        f"[{pos}/{len(chunk_keys)}] "
                        f"JSON 복원 중지 → 청크 건너뜀"
                    )

                return

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
                        (
                            result_text,
                            result_lines,
                            result_ignore
                        ) = await translate_chunk_safe_async(
                            chunk=chunk_text,
                            model_name=model_name,
                            safety_settings=safety_settings,
                            rate_limiter=rate_limiter,
                            temperature=temperature,
                            log_callback=log_callback,
                            chunk_idx=idx,
                            raw=raw,
                            dicts=dicts,
                            check=check,
                            br_start=br_start
                        )

                        if result_ignore:
                            result_ignore_back = True

                            async with lock:
                                ignored = True

                            if log_callback:
                                log_callback(
                                    f" └ [{idx}번 청크] "
                                    f"JSON 복원 무시 → "
                                    f"청크 완료 처리하지 않습니다."
                                )

                            return

                        if result_text is None:
                            result_ignore_back = True

                            async with lock:
                                ignored = True

                            if log_callback:
                                log_callback(
                                    f" └ [{idx}번 청크] "
                                    f"번역 결과 없음 → "
                                    f"청크 완료 처리하지 않습니다."
                                )

                            return

                    except Exception as e:
                        if _is_stopped(check):
                            result_ignore_back = True

                            async with lock:
                                ignored = True

                            if log_callback:
                                log_callback(
                                    f" └ [{idx}번 청크] "
                                    f"JSON 복원 중지됨 → 저장하지 않습니다."
                                )

                            return

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

            if _is_stopped(check):
                result_ignore_back = True

                async with lock:
                    ignored = True

                if log_callback:
                    log_callback(
                        f" └ [{idx}번 청크] "
                        f"저장 직전 중지됨 → 저장하지 않습니다."
                    )

                return

            with open(
                file_path,
                "w",
                encoding=_A
            ) as f_out:
                f_out.write(result_text)

            async with lock:
                translated_parts_raw[pos - 1] = result_text
                translated_parts[pos - 1] = result_text

        except Exception as e:

            if _is_stopped(check):
                result_ignore_back = True

                async with lock:
                    ignored = True

                if log_callback:
                    log_callback(
                        f" └ [{pos}번 청크] "
                        f"JSON 복원 중지됨 → 저장하지 않습니다."
                    )

                return

            if log_callback:
                log_callback(
                    f" └ [{pos}번 청크] "
                    f"JSON 복원 처리 실패: {e}"
                )

        finally:

            if result_ignore_back:
                return

            async with lock:
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

    await asyncio.gather(
        *tasks
    )

    if ignored or _is_stopped(check):
        if log_callback:
            log_callback(
                "JSON 복원 중지됨 → "
                "복원 JSON/TXT 저장 및 EPUB 변환을 실행하지 않습니다."
            )
        return "ignore"

    final_result = "\n\n".join(
        p
        for p in translated_parts
        if p
    )

    os.makedirs(
        f"{out}trs",
        exist_ok=_C
    )

    save_path = (
        f"{out}trs\\"
        f"save_{safe}_{max_chars}_복원.json"
    )

    if not _is_stopped(check):
        save_translation_json(
            translated_parts_raw,
            max_chars,
            f"{title}_복원",
            save_path,
            raw=raw,
            br_start=br_start,
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

        if not _is_stopped(check):
            save_translation_txt(
                translated_parts_raw,
                r_title,
                txt_path
            )

    if raw:

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

    if not _is_stopped(check):
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
    dicts={},
    check=None,
    br_start=0
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
            dicts,
            check,
            br_start
        )
    )


def save_translation_json(
    translated_parts_raw,
    max_chars,
    title,
    file_path,
    raw=False,
    br_start=0,
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

    data["br_start"] = br_start

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


glossary_text.get_safety_settings = get_safety_settings