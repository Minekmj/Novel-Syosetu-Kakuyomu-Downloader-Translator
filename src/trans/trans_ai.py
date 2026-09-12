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

_K = '+---+\n'
_J = 'gemini-3.5-flash-Lite'
_I = '[\\\\/:*?"<>|]'
_H = 'OUTFOLDER'
_G = '+---+'
_F = False
_E = ''
_D = None
_C = True
_B = '\n'
_A = 'utf-8'
_Gi = '=' * 30

API = _E
MODEL_NAME = 'gemini-3.5-flash-lite'
CUSTOM_AI_PROMPT = ''

IMG_TAG_PATTERN = re.compile(r'-img-:[^\s\r\n]+')
IMG_PLACEHOLDER = '-+++-'
IMG_PROMPT_RULE = """
[이미지 필수 규칙]
1. 입력문에 포함된 '-+++-'는 글자를 절대 유지 하세요.
2. '-+++-' 원문에 없는 곳에 새로 만들거나 추가해서는 안 됩니다. (절대 금지!).
"""


def set_api_key(api_key):
    global API, client
    API = api_key.strip() or _E
    client = genai.Client(api_key=API if API != '' else "None")
    glossary_text.client = client
    data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding=_A) as f:
                data = json.load(f)
        except Exception:
            data = {}
    data['api'] = API
    with open(DATA_FILE, 'w', encoding=_A) as f:
        json.dump(data, f, ensure_ascii=_F, indent=4)


def rest():
    global API, client
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding=_A) as f:
                API = json.load(f).get('api', _E)
            client = genai.Client(api_key=API)
            glossary_text.client = client
        except Exception:
            pass


client = genai.Client(api_key=API if API != '' else "None")
glossary_text.client = client
rest()


def split_text_by_lines(text, max_chars=5000):
    lines = text.splitlines(keepends=True)
    chunks = []
    current_chunk = []
    current_length = 0

    for line in lines:
        if current_length + len(line) > max_chars and current_chunk:
            chunks.append(''.join(current_chunk))
            current_chunk = [line]
            current_length = len(line)
        else:
            current_chunk.append(line)
            current_length += len(line)

    if current_chunk:
        chunks.append(''.join(current_chunk))

    return chunks

JP_PATTERN = re.compile(
    r'[\u3040-\u309f\u30a0-\u30ff\u31f0-\u31ff\uff65-\uff9f\u4e00-\u9fff\uf900-\ufaff\u3005\u3006\u3007]'
)

def get_japanese_ratio(text):
    if not text:
        return 0.0

    clean_text = re.sub(r'[^\w]|[\d_]', '', text)
    if not clean_text:
        return 0.0

    jp_chars = len(JP_PATTERN.findall(clean_text))
    return jp_chars / len(clean_text) * 100

def get_korean_ratio(text):
    if not text:
        return 0.0

    clean_text = re.sub(r'[^\w]|[\d_]', '', text)
    if not clean_text:
        return 0.0

    ko_chars = len(re.findall(r'[\uac00-\ud7a3\u3131-\u318e]', clean_text))
    return ko_chars / len(clean_text) * 100


def get_linebreak_preservation_ratio(original, translated):
    original_breaks = original.count('\n')
    translated_breaks = translated.count('\n')

    if original_breaks == 0:
        return 100.0 if translated_breaks == 0 else 0.0

    difference = abs(original_breaks - translated_breaks)
    return max(0.0, (1.0 - difference / original_breaks) * 100.0)


def get_japanese_info(text):
    if not text:
        return 0.0, 0

    clean_text = re.sub(r"[^\w]|[\d_]", "", text)
    if not clean_text:
        return 0.0, 0

    jp_chars = len(JP_PATTERN.findall(clean_text))
    ratio = (jp_chars / len(clean_text)) * 100
    return ratio, jp_chars


def inspect_json_japanese(
    json_path, ratio_threshold=10.0, char_count_threshold=0, encoding="utf-8"
):
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_path}")

    with open(json_path, "r", encoding=encoding) as f:
        data = json.load(f)

    title = data.get("name", os.path.splitext(os.path.basename(json_path))[0])
    chunk_size = data.get("chunk", 5000)
    raw = bool(data.get("raw", False))

    chunk_indices = sorted(
        list(set(int(k) for k in data.keys() if k.isdigit()))
    )

    detected_items = []

    def is_jp_line(line_text):
        jp_ratio, jp_count = get_japanese_info(line_text)
        if char_count_threshold > 0:
            return jp_count >= char_count_threshold
        return jp_ratio >= ratio_threshold

    for chunk_idx in chunk_indices:
        chunk_key = str(chunk_idx)
        text = data.get(chunk_key)
        if not text or not isinstance(text, str):
            continue

        lines = text.splitlines(keepends=True)
        total_lines = len(lines)
        i = 0

        while i < total_lines:
            if is_jp_line(lines[i]):
                start_line = i
                last_jp_line = i
                j = i + 1

                while j < total_lines:
                    if is_jp_line(lines[j]):
                        last_jp_line = j
                        j += 1
                    elif lines[j].strip() == "":
                        k = j + 1
                        while k < total_lines and lines[k].strip() == "":
                            k += 1
                        if k < total_lines and is_jp_line(lines[k]):
                            j += 1
                        else:
                            break
                    else:
                        break

                end_line = last_jp_line + 1
                block_text = "".join(lines[start_line:end_line])

                detected_items.append(
                    {
                        "chunk_key": chunk_key,
                        "chunk_display": chunk_idx + 1,
                        "start_line": start_line,
                        "end_line": end_line,
                        "original_text": block_text,
                    }
                )

                i = end_line
            else:
                i += 1

    return {
        "json_path": json_path,
        "title": title,
        "chunk_size": chunk_size,
        "raw": raw,
        "items": detected_items,
    }


def apply_japanese_corrections(json_path, corrections):
    if not os.path.exists(json_path):
        return False, 0, f"JSON 파일을 찾을 수 없습니다: {json_path}"

    try:
        with open(json_path, 'r', encoding=_A) as f:
            data = json.load(f)

        title = data.get('name', 'restored')
        max_chars = data.get('chunk', 5000)
        out = down.downin.base_data.OUTFOLDER + '/'
        safe = re.sub(_I, '_', title).strip()
        ai_dir = f'{out}trs\\ai_down_{safe}_{max_chars}'

        grouped = {}
        for corr in corrections:
            ck = corr['chunk_key']
            if ck not in grouped:
                grouped[ck] = []
            grouped[ck].append(corr)

        modified_count = 0

        for chunk_key, corr_list in grouped.items():
            if chunk_key not in data:
                continue

            text = data[chunk_key]
            lines = text.splitlines(keepends=True)

            corr_list.sort(key=lambda x: x['start_line'], reverse=True)

            for item in corr_list:
                start = item['start_line']
                end = item['end_line']
                new_text = item['new_text']

                new_lines = new_text.splitlines(keepends=True)
                lines[start:end] = new_lines
                modified_count += 1

            updated_chunk_text = ''.join(lines)
            data[chunk_key] = updated_chunk_text

            if os.path.exists(ai_dir):
                try:
                    display_idx = int(chunk_key) + 1
                    chunk_file = f'{ai_dir}/{display_idx}.txt'
                    with open(chunk_file, 'w', encoding=_A) as cf:
                        cf.write(updated_chunk_text)
                except Exception:
                    pass

        with open(json_path, 'w', encoding=_A) as f:
            json.dump(data, f, ensure_ascii=_F, indent=4)

        return True, modified_count, ""

    except Exception as e:
        return False, 0, str(e)


class AsyncRateLimiter:
    def __init__(self, rpm):
        self.rpm = max(1, int(rpm))
        self.interval = 60.0 / self.rpm + 0.1
        self.lock = asyncio.Lock()
        self.last_call = 0.0

    async def wait(self):
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_call

            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)

            self.last_call = time.time()


class ModelWorker:
    def __init__(self, model_name, rpm, max_concurrent, temperature, br_start=0, isno_x=False):
        self.model_name = str(model_name).strip()
        self.rpm = max(1, int(rpm))
        self.max_concurrent = max(1, int(max_concurrent))
        self.temperature = float(temperature)
        self.br_start = max(0, int(br_start))
        self.isno_x = bool(isno_x)
        self.rate_limiter = AsyncRateLimiter(self.rpm)

    def __repr__(self):
        return f"ModelWorker(model={self.model_name},rpm={self.rpm},concurrent={self.max_concurrent},temperature={self.temperature},br_start={self.br_start},isno_x={self.isno_x})"


def _parse_models(model_name):
    if isinstance(model_name, str):
        models = [x.strip() for x in model_name.split(',') if x.strip()]
    else:
        models = [str(x).strip() for x in model_name if str(x).strip()]

    if not models:
        raise ValueError('사용할 모델이 없습니다.')

    return models


def _normalize_model_values(value, count, name):
    if isinstance(value, (tuple, list)):
        values = list(value)
        if len(values) == 1 and count > 1:
            values = values * count
    elif isinstance(value, str) and ',' in value:
        values = [x.strip() for x in value.split(',') if x.strip()]
    else:
        values = [value]

    if len(values) == 1 and count > 1:
        values = values * count

    if len(values) != count:
        raise ValueError(f'{name} 개수 불일치: 모델 {count}개 / {name} {len(values)}개')

    return values


def _create_model_workers(model_name, rpm, max_concurrent, temperature, br_start=0, isno_x=False):
    models = _parse_models(model_name)
    rpms = _normalize_model_values(rpm, len(models), 'RPM')
    concurrencies = _normalize_model_values(max_concurrent, len(models), '동시 작업수')
    temperatures = _normalize_model_values(temperature, len(models), 'Temperature')
    br_starts = _normalize_model_values(br_start, len(models), '분할 시작')
    isno_xs = _normalize_model_values(isno_x, len(models), '검열 건너뛰기')
    workers = []
    for i, model in enumerate(models):
        workers.append(ModelWorker(model, rpms[i], concurrencies[i], temperatures[i], br_starts[i], isno_xs[i]))
    return workers


def _is_stopped(check):
    try:
        return bool(check and check())
    except Exception:
        return False


def build_dynamic_glossary(chunk, dictionary, max_chars=GLOSSARY_MAX_CHARS):
    if not dictionary:
        return ''

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
        return ''

    matched.sort(key=lambda x: x[0], reverse=True)

    selected = []
    current_length = 0

    for count, source, target in matched:
        line = f'{source} → {target}'
        line_length = len(line) + (1 if selected else 0)

        if current_length + line_length > max_chars:
            break

        selected.append(line)
        current_length += line_length

    if not selected:
        return ''

    return '\n'.join(selected)


def restore_img_placeholders(text, img_tags):
    """번역 결과 내의 '-+++-' 플레이스홀더를 원래 '-img-:*' 태그로 순서대로 복원합니다."""
    for tag in img_tags:
        text = text.replace(IMG_PLACEHOLDER, tag, 1)
    return text


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
    br_start=0,
    isno_x=False
):
    if dicts is None:
        dicts = {}

    lines = chunk.splitlines(keepends=True)
    if not lines:
        return '', 0, False

    if _is_stopped(check):
        if log_callback:
            log_callback(f'[{chunk_idx} - {model_name}] [{depth}] 중지: 번역 시작 전 작업 중지')
        return None, 0, True

    force_split = br_start > 0

    if not force_split and get_japanese_ratio(chunk) < 0.03:
        if log_callback:
            log_callback(f'[{chunk_idx} - {model_name}] [{depth}] [시도 0] 원문의 일본어 비율이 너무 낮아 번역 생략')
        return chunk, len(lines), False

    # 1. 이미지 태그 추출 및 '-+++-'로 임시 마스킹
    img_tags = IMG_TAG_PATTERN.findall(chunk)
    expected_img_count = len(img_tags)
    masked_chunk = IMG_TAG_PATTERN.sub(IMG_PLACEHOLDER, chunk)

    current_chunk = masked_chunk
    is_censored = False

    if raw:
        expected_delimiter_count = len(re.findall(r'^={4,}$', masked_chunk, re.MULTILINE))
    else:
        expected_delimiter_count = masked_chunk.count(_G)

    attempt = 1

    while not force_split and attempt <= max_retries:
        if _is_stopped(check):
            if log_callback:
                log_callback(f'[{chunk_idx} - {model_name}] [{depth}] 중지: 다음 API 요청을 실행하지 않습니다.')
            return None, 0, True

        censored_label = '검열' if is_censored else ''
        prefix_log = f'[{chunk_idx} - {model_name} - {censored_label}] [{depth}] [시도 {attempt}/{max_retries}]'

        await rate_limiter.wait()

        if _is_stopped(check):
            if log_callback:
                log_callback(f'{prefix_log} 중지: API 호출 직전 작업 중지')
            return None, 0, True

        if log_callback:
            log_callback(f'{prefix_log} 번역 시작: (라인 수: {len(lines)})')

        try:
            if raw:
                system_prompt = SYSTEM_PROMPT_RAW
            else:
                system_prompt = SYSTEM_PROMPT if _G in masked_chunk else SYSTEM_PROMPT_NO_SPLIT

            # 이미지가 청크에 포함되어 있으면 프롬프트 추가
            if expected_img_count > 0:
                system_prompt += f"\n{IMG_PROMPT_RULE}\n"

            if CUSTOM_AI_PROMPT != '':
                system_prompt += f"""[사용자 지정 추가 지침]
{CUSTOM_AI_PROMPT}
[end]
"""

            if dicts:
                glossary_value = build_dynamic_glossary(masked_chunk, dicts)
                if glossary_value:
                    system_prompt += '\n\n' + GLOSSARY_CONTEXT.format(glossary=glossary_value)
                    glossary_log = ', '.join(glossary_value.splitlines())
                    if len(glossary_log) > 40:
                        glossary_log = glossary_log[:40] + '...'
                    if log_callback:
                        log_callback(f'{prefix_log} 용어집 사용: {glossary_log}')

            response = await client.aio.models.generate_content(
                model=model_name,
                contents=f'번역:\n{current_chunk}',
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    top_p=0.8,
                    safety_settings=safety_settings
                )
            )

            if response and response.text:
                res_text = response.text.strip()
                res_text = res_text.replace('「', '“').replace('」', '”').replace('｢', '“').replace('｣', '”')

                # 이미지 플레이스홀더 개수 검사
                if expected_img_count > 0:
                    actual_img_count = res_text.count(IMG_PLACEHOLDER)
                    if actual_img_count != expected_img_count:
                        if log_callback:
                            log_callback(
                                f"{prefix_log} 경고: '-+++-' 이미지 태그 개수 불일치 "
                                f'(기대: {expected_img_count}, 결과: {actual_img_count}) -> 재시도'
                            )
                        current_chunk = masked_chunk
                        is_censored = False
                        attempt += 1
                        continue

                if not raw and _G in masked_chunk:
                    actual_delimiter_count = res_text.count(_G)
                    if actual_delimiter_count != expected_delimiter_count:
                        if log_callback:
                            log_callback(
                                f"{prefix_log} 경고: '+---+' 개수 불일치 "
                                f'(기대: {expected_delimiter_count}, 결과: {actual_delimiter_count}) -> 재시도'
                            )
                        current_chunk = masked_chunk
                        is_censored = False
                        attempt += 1
                        continue

                if raw and '====' in masked_chunk:
                    actual_delimiter_count = len(re.findall(r'^={4,}$', res_text, re.MULTILINE))
                    if actual_delimiter_count != expected_delimiter_count:
                        if log_callback:
                            log_callback(
                                f"{prefix_log} 경고: '====...' 라인 개수 불일치 "
                                f'(기대: {expected_delimiter_count}, 결과: {actual_delimiter_count}) -> 재시도'
                            )
                        current_chunk = masked_chunk
                        is_censored = False
                        attempt += 1
                        continue

                jp_ratio = get_japanese_ratio(res_text)
                ko_ratio = get_korean_ratio(res_text)
                text_len = len(masked_chunk.strip())

                if text_len < 100:
                    min_ko_ratio = 60.0
                    max_jp_ratio = 5.0
                    min_line_ratio = 30.0
                elif text_len < 600:
                    min_ko_ratio = 70.0
                    max_jp_ratio = 3.0
                    min_line_ratio = 70.0
                elif text_len < 1500:
                    min_ko_ratio = 75.0
                    max_jp_ratio = 1.5
                    min_line_ratio = 75.0
                elif text_len < 9000:
                    min_ko_ratio = 80.0
                    max_jp_ratio = 1.2
                    min_line_ratio = 90.0
                else:
                    min_ko_ratio = 80.0
                    max_jp_ratio = 1.1
                    min_line_ratio = 90.0

                if raw:
                    line_ratio = get_linebreak_preservation_ratio(masked_chunk, res_text)
                    success = jp_ratio < max_jp_ratio and ko_ratio >= min_ko_ratio and line_ratio >= min_line_ratio
                else:
                    line_ratio = 100.0
                    success = jp_ratio < max_jp_ratio and ko_ratio >= min_ko_ratio

                if success:
                    # 번역 성공 시 '-+++-'를 원래 '-img-:*' 태그로 복원
                    if expected_img_count > 0:
                        res_text = restore_img_placeholders(res_text, img_tags)

                    if log_callback:
                        if raw:
                            log_callback(f'{prefix_log} -> 성공: (줄바꿈 보존율: {line_ratio:.2f}%)')
                        else:
                            log_callback(f'{prefix_log} -> 성공: 완료')
                    return res_text, len(lines), False

                if log_callback:
                    if raw:
                        log_callback(
                            f'{prefix_log} 경고: 번역 조건 미달 '
                            f'(한글: {ko_ratio:.2f}% [기준 {min_ko_ratio}%], '
                            f'일어: {jp_ratio:.2f}% [기준 <{max_jp_ratio}%], '
                            f'줄바꿈: {line_ratio:.2f}% [기준 {min_line_ratio}%]) -> 재시도'
                        )
                    else:
                        log_callback(
                            f'{prefix_log} 경고: 번역 조건 미달 '
                            f'(한글: {ko_ratio:.2f}% [기준 {min_ko_ratio}%], '
                            f'일어: {jp_ratio:.2f}% [기준 <{max_jp_ratio}%]) -> 재시도'
                        )

                current_chunk = masked_chunk
                is_censored = False
                attempt += 1

            else:
                if isno_x:
                    if log_callback:
                        log_callback(f'{prefix_log} 경고: API 응답이 비어있음 -> 검열 우회 설정으로 즉시 분할 실행')
                    break

                if log_callback:
                    log_callback(f'{prefix_log} 경고: API 응답이 비어있음 -> 검열 실행')

                if is_censored:
                    attempt += 1
                    break

                current_chunk = x_making(masked_chunk)
                is_censored = True
                attempt += 1

        except Exception as e:
            if _is_stopped(check):
                if log_callback:
                    log_callback(f'{prefix_log} 중지: 현재 API 요청 종료 후 중지')
                return None, 0, True

            if log_callback:
                log_callback(
                    f'{prefix_log} 오류: API 호출 중 예외 발생: {e} -> 재시도. '
                    '원래 대기 시간에 3배 대기'
                )

            await rate_limiter.wait()
            await rate_limiter.wait()

            is_censored = False
            attempt += 1

    if _is_stopped(check):
        if log_callback:
            log_callback(f'[{chunk_idx} - {model_name}] [{depth}] 중지: 분할 작업을 실행하지 않습니다.')
        return None, 0, True

    if len(lines) <= 2 or depth >= 4:
        if log_callback:
            log_callback(
                f'[{chunk_idx} - {model_name}] [{depth}] 오류: '
                '[최대초과] 최대 재시도 초과 및 분할 한계 도달 -> 원문 유지'
            )
        return chunk, len(lines), False

    mid = len(lines) // 2

    if log_callback:
        split_type = f"[강제분할: 남은단계 {br_start}]" if force_split else "[경고: 분할]"
        log_callback(
            f'[{chunk_idx} - {model_name}] [{depth}] {split_type} '
            f'청크 분할 처리 (전반부 {mid}줄, 후반부 {len(lines)-mid}줄)'
        )

    # 분할 시 원본 청크(이미지 태그 포함)를 기준으로 재귀 호출
    part1_text, part1_len, part1_ignore = await translate_chunk_safe_async(
        chunk=''.join(lines[:mid]),
        model_name=model_name,
        safety_settings=safety_settings,
        rate_limiter=rate_limiter,
        temperature=temperature,
        max_retries=max_retries,
        depth=depth + 1,
        log_callback=log_callback,
        chunk_idx=chunk_idx,
        raw=raw,
        dicts=dicts,
        check=check,
        br_start=max(0, br_start - 1),
        isno_x=isno_x
    )

    if part1_ignore:
        return part1_text, part1_len, True

    if part1_text is None:
        return None, 0, True

    if _is_stopped(check):
        return part1_text, len(lines[:mid]), True

    part2_text, part2_len, part2_ignore = await translate_chunk_safe_async(
        chunk=''.join(lines[mid:]),
        model_name=model_name,
        safety_settings=safety_settings,
        rate_limiter=rate_limiter,
        temperature=temperature,
        max_retries=max_retries,
        depth=depth + 1,
        log_callback=log_callback,
        chunk_idx=chunk_idx,
        raw=raw,
        dicts=dicts,
        check=check,
        br_start=max(0, br_start - 1),
        isno_x=isno_x
    )

    if part2_ignore:
        return part1_text, len(lines[:mid]), True

    if part2_text is None:
        return part1_text, len(lines[:mid]), True

    return part1_text.rstrip(_B) + _B + part2_text.lstrip(_B), len(lines), False


def detect_raw_text(text):
    lines = text.splitlines()
    return len(lines) >= 3 and lines[2].strip().lower() == '(raw)'


def prepare_raw_text(text):
    lines = text.splitlines(keepends=True)

    if len(lines) < 3 or lines[2].strip().lower() != '(raw)':
        return text, '제목 미정'

    book_title = lines[0].strip()
    author = lines[1].strip()
    title = book_title + '_' + author
    delimiter_index = None

    for i, line in enumerate(lines):
        if line.strip() == _Gi:
            delimiter_index = i
            break

    if delimiter_index is not None:
        body_start = delimiter_index
    else:
        body_start = 5

    raw_body = ''.join(lines[body_start:])
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
    br_start=0,
    isno_x=False
):
    if API == _E:
        if log_callback:
            log_callback('에러: API 키가 설정되지 않았습니다.')
        return 'error'

    try:
        workers = _create_model_workers(model_name, rpm, max_concurrent, temperature, br_start, isno_x)
    except Exception as e:
        if log_callback:
            log_callback(f'에러: 모델 설정 오류: {e}')
        return 'error'

    chunks = split_text_by_lines(text, max_chars=max_chars)
    translated_parts = [None] * len(chunks)
    out = down.downin.base_data.OUTFOLDER + '/'
    os.makedirs(f'{out}trs', exist_ok=_C)
    os.makedirs(f'{out}epub', exist_ok=_C)
    os.makedirs(f'{out}epub\\raw_txt', exist_ok=_C)
    safe = re.sub(_I, '_', title).strip()
    ai_dir = f'{out}trs\\ai_down_{safe}_{max_chars}'
    os.makedirs(ai_dir, exist_ok=_C)

    model_info = ', '.join(
        f'{worker.model_name}(RPM={worker.rpm},동시={worker.max_concurrent},온도={worker.temperature},분할={worker.br_start},검열건너뜀={worker.isno_x})'
        for worker in workers
    )
    msg = f'총 {len(chunks)}개 청크 분할 완료 (청크 크기: {max_chars}). 사용 모델: {model_info}, RAW: {raw}'
    print(msg)
    if log_callback:
        log_callback(msg)

    safety_settings = get_safety_settings()
    queue = asyncio.Queue()
    for idx, chunk in enumerate(chunks, 1):
        await queue.put((idx, chunk))

    completed_count = 0
    ignored = False
    lock = asyncio.Lock()

    async def process_chunk(idx, chunk, worker):
        nonlocal completed_count, ignored
        if _is_stopped(check):
            if log_callback:
                log_callback(f'[{idx}/{len(chunks)}] [{worker.model_name}] 중지: 대기 중인 청크 건너뜀')
            return

        file_path = f'{ai_dir}/{idx}.txt'

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding=_A) as f:
                    saved_text = f.read()
                if saved_text and not saved_text.startswith('[번역 실패'):
                    skip_msg = f'[{idx}/{len(chunks)}] [{worker.model_name}] 이미 저장된 파일 존재 → 건너뜀'
                    if log_callback:
                        log_callback(skip_msg)
                    async with lock:
                        translated_parts[idx - 1] = saved_text
                        completed_count += 1
                        if progress_callback:
                            progress_callback(completed_count, len(chunks), f'{completed_count}/{len(chunks)} 청크 완료')
                    return
            except Exception:
                pass

        result_ignore_back = False
        try:
            if _is_stopped(check):
                if log_callback:
                    log_callback(f'[{idx}/{len(chunks)}] [{worker.model_name}] 실행 대기 중 청크 건너뜀')
                return

            result_text, result_lines, result_ignore = await translate_chunk_safe_async(
                chunk=chunk,
                model_name=worker.model_name,
                safety_settings=safety_settings,
                rate_limiter=worker.rate_limiter,
                temperature=worker.temperature,
                log_callback=log_callback,
                chunk_idx=idx,
                raw=raw,
                dicts=dicts,
                check=check,
                br_start=worker.br_start,
                isno_x=worker.isno_x
            )

            if result_text is not None and not result_ignore:
                try:
                    with open(file_path, 'w', encoding=_A) as f:
                        f.write(result_text)
                    async with lock:
                        translated_parts[idx - 1] = result_text
                except Exception as save_err:
                    if log_callback:
                        log_callback(f'[{idx}번 청크] 임시 파일 저장 실패: {save_err}')

            if result_ignore or result_text is None or _is_stopped(check):
                result_ignore_back = True
                async with lock:
                    ignored = True
                return

            if log_callback:
                log_callback(f'[{idx}/{len(chunks)}] [{worker.model_name}] 청크 번역 완료: 성공')

        except Exception as e:
            if log_callback:
                log_callback(f' └ [{idx}번 청크] [{worker.model_name}] 번역 최종 실패: {e}')

            err_text = f'''
+---+

[번역 실패: {idx}번째 청크]

error+---+

error 청크 next

'''
            async with lock:
                translated_parts[idx - 1] = err_text

            try:
                error_path = f'{ai_dir}/{idx}_error.txt'
                with open(error_path, 'w', encoding=_A) as f:
                    f.write(chunk)
            except Exception:
                pass

        finally:
            if not result_ignore_back:
                async with lock:
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, len(chunks), f'{completed_count}/{len(chunks)} 청크 완료')

    async def model_worker(worker, worker_number):
        while True:
            if _is_stopped(check):
                return
            try:
                idx, chunk = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                await process_chunk(idx, chunk, worker)
            finally:
                queue.task_done()

    worker_tasks = []
    for worker in workers:
        for worker_number in range(worker.max_concurrent):
            worker_tasks.append(asyncio.create_task(model_worker(worker, worker_number + 1)))

    await asyncio.gather(*worker_tasks)

    json_path = f'{out}trs\\save_{safe} _ {max_chars}.json'
    try:
        first_br = workers[0].br_start if workers else 0
        save_translation_json(translated_parts, chunks, max_chars, title, json_path, raw=raw, br_start=first_br)
    except Exception as e:
        if log_callback:
            log_callback(f'JSON 저장 실패: {e}')

    if ignored or _is_stopped(check):
        return 'ignore'

    if raw:
        txt_path = f'{out}epub\\raw_txt\\{safe}.txt'
        if '_' in title:
            book_title, author = title.rsplit('_', 1)
        else:
            book_title = title
            author = ''
        r_title = f'''{book_title}
{author}
(raw)
{_K}{book_title} | {author}

'''
        if not _is_stopped(check):
            save_translation_txt(translated_parts, r_title, txt_path)

    return '\n\n'.join(p for p in translated_parts if p)


def translate_light_novel(
    text,
    max_chars=5000,
    model_name=MODEL_NAME,
    rpm=15,
    temperature=0.5,
    max_concurrent=4,
    title='save',
    progress_callback=_D,
    log_callback=_D,
    raw=False,
    dicts={},
    check=None,
    br_start=0,
    isno_x=False
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
            br_start,
            isno_x
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
    br_start=0,
    isno_x=False
):
    raw = detect_raw_text(txt)

    if raw:
        lines = txt.splitlines(keepends=True)
        book_title = lines[0].strip() if len(lines) > 0 else '제목 미정'
        author = lines[1].strip() if len(lines) > 1 else ''

        raw_text, raw_title = prepare_raw_text(txt)

        if log_callback:
            log_callback(
                f"RAW 번역 시작: 제목 '{book_title}', 작가 '{author}', "
                f'청크 크기: {max_chars}, 동시 작업수: {max_concurrent}'
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
            br_start=br_start,
            isno_x=isno_x
        )

        if translated_result == 'ignore':
            return 'ignore'

        if translated_result == 'error':
            return 'error'

        epub_text = f'{book_title}\n{author}\n(raw)\n{_K}{translated_result}'

        if not _is_stopped(check):
            down.create_epub_from_merged_txt(
                txt_value=epub_text,
                RAW=True
            )

        return translated_result

    A = '_번역\n'

    if _G in txt:
        split_pos = txt.find(_G)
        f = txt[:split_pos - 1]
        g = txt[split_pos + 6:]
    else:
        f = '제목 미정'
        g = txt

    first_newline = f.find(_B)
    if first_newline == -1:
        t = f
    else:
        t = f[:first_newline] + '_' + f[first_newline + 1:]

    if log_callback:
        log_callback(
            f"전체 번역 시작: 제목 '{t}', 청크 크기: {max_chars}, "
            f'동시 작업수: {max_concurrent}'
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
        br_start=br_start,
        isno_x=isno_x
    )

    if translated_result == 'ignore':
        return 'ignore'

    if translated_result == 'error':
        return 'error'

    title_end = f.find(_B)
    if title_end == -1:
        epub_text = f + A + translated_result
    else:
        epub_text = f[:title_end] + A + f[title_end + 1:] + _B + translated_result

    if not _is_stopped(check):
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
    br_start=0,
    isno_x=False
):
    if _is_stopped(check):
        if log_callback:
            log_callback('JSON 복원 중지: 작업 시작 전 중지되었습니다.')
        return 'ignore'

    if not os.path.exists(json_path):
        msg = f'에러: JSON 파일을 찾을 수 없습니다 | {json_path}'
        if log_callback:
            log_callback(msg)
        return 'error'

    with open(json_path, 'r', encoding=_A) as f:
        data = json.load(f)

    title = data.get('name', 'restored')
    max_chars = data.get('chunk', 5000)
    raw = bool(data.get('raw', False))

    try:
        workers = _create_model_workers(model_name, rpm, max_concurrent, temperature, br_start, isno_x)
    except Exception as e:
        if log_callback:
            log_callback(f'에러: JSON 모델 설정 오류: {e}')
        return 'error'

    out = down.downin.base_data.OUTFOLDER + '/'
    os.makedirs(f'{out}trs', exist_ok=_C)
    safe = re.sub(_I, '_', title).strip()
    ai_dir = f'{out}trs\\ai_down_{safe}_{max_chars}'
    os.makedirs(ai_dir, exist_ok=_C)

    safety_settings = get_safety_settings()

    chunk_indices = sorted(list(set(
        int(k[:-2]) if (k.endswith('-j') and k[:-2].isdigit()) else int(k)
        for k in data.keys() if k.isdigit() or (k.endswith('-j') and k[:-2].isdigit())
    )))

    model_info = ', '.join(
        f'{worker.model_name}(RPM={worker.rpm},동시={worker.max_concurrent},온도={worker.temperature},분할={worker.br_start},검열건너뜀={worker.isno_x})'
        for worker in workers
    )
    msg = f'[{title}] JSON 로드 완료 (청크 크기: {max_chars}, 총 {len(chunk_indices)}개 청크 비동기 복원) / 사용 모델: {model_info} / RAW: {raw}'
    if log_callback:
        log_callback(msg)

    translated_parts = [None] * len(chunk_indices)
    original_chunks = [None] * len(chunk_indices)
    queue = asyncio.Queue()

    for pos, chunk_idx in enumerate(chunk_indices, 1):
        trans_text = data.get(str(chunk_idx))
        orig_text = data.get(f"{chunk_idx}-j")
        if orig_text is None and trans_text is not None:
            orig_text = trans_text
        await queue.put((pos, chunk_idx, trans_text, orig_text))

    completed_count = 0
    ignored = False
    lock = asyncio.Lock()

    async def process_json_chunk(pos, chunk_idx, trans_text, orig_text, worker):
        nonlocal completed_count, ignored
        result_ignore_back = False
        try:
            if _is_stopped(check):
                result_ignore_back = True
                async with lock:
                    ignored = True
                if log_callback:
                    log_callback(f'[{pos}/{len(chunk_indices)}] [{worker.model_name}] JSON 복원 중지 → 청크 건너뜀')
                return

            display_idx = chunk_idx + 1
            file_path = f'{ai_dir}/{display_idx}.txt'

            need_translate = False
            source_to_use = orig_text if orig_text else trans_text

            if not trans_text or str(trans_text).startswith('[번역 실패'):
                need_translate = True
            else:
                jp_ratio = get_japanese_ratio(str(trans_text))
                if jp_ratio >= 0.1:
                    need_translate = True

            if need_translate:
                if not source_to_use:
                    source_to_use = ''
                clean_source = str(source_to_use).replace("%'%", '"').replace('\\\n', _B)
                jp_ratio_orig = get_japanese_ratio(clean_source)

                re_msg = f'[{pos}/{len(chunk_indices)}] [{worker.model_name}] 원문 번역 실행 (인덱스 {chunk_idx}, 원문 일어 비율 {jp_ratio_orig:.2f}%)'
                if log_callback:
                    log_callback(re_msg)

                try:
                    result_text, result_lines, result_ignore = await translate_chunk_safe_async(
                        chunk=clean_source,
                        model_name=worker.model_name,
                        safety_settings=safety_settings,
                        rate_limiter=worker.rate_limiter,
                        temperature=worker.temperature,
                        log_callback=log_callback,
                        chunk_idx=display_idx,
                        raw=raw,
                        dicts=dicts,
                        check=check,
                        br_start=worker.br_start,
                        isno_x=worker.isno_x
                    )
                    if result_ignore or result_text is None:
                        result_ignore_back = True
                        async with lock:
                            ignored = True
                        if log_callback:
                            log_callback(f' └ [{display_idx}번 청크] [{worker.model_name}] 번역 결과 없음/무시됨')
                        return
                except Exception as e:
                    if log_callback:
                        log_callback(f' └ [{display_idx}번 청크] [{worker.model_name}] 재번역 실패: {e}')
                    result_text = clean_source
            else:
                if log_callback:
                    log_callback(f'[{pos}/{len(chunk_indices)}] [{worker.model_name}] 기존 번역 청크 통과 (인덱스 {chunk_idx})')
                result_text = str(trans_text).replace("%'%", '"').replace('\\\n', _B)

            try:
                with open(file_path, 'w', encoding=_A) as f_out:
                    f_out.write(result_text)
            except Exception as e:
                if log_callback:
                    log_callback(f' └ [{display_idx}번 청크] 파일 저장 오류: {e}')

            async with lock:
                translated_parts[pos - 1] = result_text
                original_chunks[pos - 1] = orig_text if orig_text is not None else result_text

            if _is_stopped(check):
                result_ignore_back = True
                async with lock:
                    ignored = True
                return

        except Exception as e:
            if log_callback:
                log_callback(f' └ [{pos}번 청크] [{worker.model_name}] JSON 복원 처리 실패: {e}')
        finally:
            if not result_ignore_back:
                async with lock:
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, len(chunk_indices), f'{completed_count}/{len(chunk_indices)} 청크 완료')

    async def model_worker(worker, worker_number):
        while True:
            if _is_stopped(check):
                return
            try:
                pos, chunk_idx, trans_text, orig_text = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                await process_json_chunk(pos, chunk_idx, trans_text, orig_text, worker)
            finally:
                queue.task_done()

    worker_tasks = []
    for worker in workers:
        for worker_number in range(worker.max_concurrent):
            worker_tasks.append(asyncio.create_task(model_worker(worker, worker_number + 1)))

    await asyncio.gather(*worker_tasks)

    os.makedirs(f'{out}trs', exist_ok=_C)
    save_path = f'{out}trs\\save_{safe}_{max_chars}_복원.json'
    try:
        first_br = workers[0].br_start if workers else 0
        save_translation_json(translated_parts, original_chunks, max_chars, f'{title}_복원', save_path, raw=raw, br_start=first_br)
    except Exception as e:
        if log_callback:
            log_callback(f'복원 JSON 파일 저장 실패: {e}')

    if ignored or _is_stopped(check):
        if log_callback:
            log_callback('JSON 복원 중지됨 → EPUB 변환은 생략합니다.')
        return 'ignore'

    final_result = '\n\n'.join(p for p in translated_parts if p)

    if raw:
        os.makedirs(f'{out}epub', exist_ok=_C)
        os.makedirs(f'{out}epub\\raw_txt', exist_ok=_C)
        txt_path = f'{out}epub\\raw_txt\\{safe}_복원.txt'
        if '_' in title:
            book_title, author = title.rsplit('_', 1)
        else:
            book_title = title
            author = ''
        restored_title = f'{book_title}_복원'
        r_title = f'''{restored_title}
{author}
(raw)
{_K}{restored_title} | {author}

'''
        if not _is_stopped(check):
            save_translation_txt(translated_parts, r_title, txt_path)

    if raw:
        if '_' in title:
            book_title, author = title.rsplit('_', 1)
        else:
            book_title = title
            author = ''
        epub_text = f'{book_title}_복원\n{author}\n(raw)\n{_K}{final_result}'
    else:
        epub_text = f'{title}_복원_번역\n{_K}{final_result}'

    if not _is_stopped(check):
        down.create_epub_from_merged_txt(txt_value=epub_text, RAW=raw)

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
    br_start=0,
    isno_x=False
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
            br_start,
            isno_x
        )
    )


def save_translation_json(
    translated_parts,
    original_chunks,
    max_chars,
    title,
    file_path,
    raw=False,
    br_start=0
):
    data = {}
    count = max(
        len(translated_parts) if translated_parts else 0,
        len(original_chunks) if original_chunks else 0
    )

    for i in range(count):
        trans = translated_parts[i] if translated_parts and i < len(translated_parts) else None
        orig = original_chunks[i] if original_chunks and i < len(original_chunks) else None

        if trans is not None:
            data[str(i)] = trans
        if orig is not None:
            data[f"{i}-j"] = orig

    data['chunk'] = max_chars
    data['name'] = title
    if raw:
        data['raw'] = True
    data['br_start'] = br_start

    with open(file_path, 'w', encoding=_A) as f:
        json.dump(data, f, ensure_ascii=_F, indent=4)


def save_translation_txt(
    translated_parts,
    title,
    file_path
):
    data = {}
    for i, text in enumerate(translated_parts):
        data[str(i)] = text
    data['name'] = title

    with open(file_path, 'w', encoding=_A) as f:
        f.write(title + '\n' + ''.join(p for p in translated_parts if p))


glossary_text.get_safety_settings = get_safety_settings