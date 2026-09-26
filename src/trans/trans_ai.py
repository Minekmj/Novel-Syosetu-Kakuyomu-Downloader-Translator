import asyncio
import json
import os
import re
import time

from google import genai
from google.genai import types

import src.down.down as down
from src.system.config import DATA_FILE
from src.trans.prom import *
from src.trans.prompt_sanitizer import (
    assemble_final_text,
    prepare_for_ratio_check,
    x_making,
    get_safety_settings,
    make_statrt_stain,
    check_statrt_stain
)

from src.trans.trans_ai_utils import *

API = ''
MODEL_NAME = 'gemini-3.5-flash-lite'
CUSTOM_AI_PROMPT = ''

USE_ADVANCED_CENSOR = False  
CENSOR_SHUFFLE = True  
CENSOR_EXTRACT_MODE = "word"  
CENSOR_PAPAGO = False

IMG_TAG_PATTERN = re.compile(r'-img-:[^\s\r\n]+')


class ForceStopException(Exception):
    pass


def set_api_key(api_key):
    global API, client
    API = api_key.strip() or ''
    client = genai.Client(api_key=API if API != '' else "None")
    glossary_text.client = client
    data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
    data['api'] = API
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def rest():
    global API, client
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                API = json.load(f).get('api', '')
            client = genai.Client(api_key=API)
            glossary_text.client = client
        except Exception:
            pass


client = genai.Client(api_key=API if API != '' else "None")
glossary_text.client = client
rest()


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
    def __init__(self, model_name, rpm, max_concurrent, temperature, br_start=0, isno_x=False, thinking_budget=None):
        self.model_name = str(model_name).strip()
        self.rpm = max(1, int(rpm))
        self.max_concurrent = max(1, int(max_concurrent))
        self.temperature = float(temperature)
        self.br_start = max(0, int(br_start))
        self.isno_x = bool(isno_x)
        self.thinking_budget = thinking_budget
        self.rate_limiter = AsyncRateLimiter(self.rpm)

    def __repr__(self):
        return f"ModelWorker(model={self.model_name},rpm={self.rpm},concurrent={self.max_concurrent},temperature={self.temperature},br_start={self.br_start},isno_x={self.isno_x},thinking={self.thinking_budget})"


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


def _create_model_workers(model_name, rpm, max_concurrent, temperature, br_start=0, isno_x=False, thinking_budget=None):
    models = _parse_models(model_name)
    rpms = _normalize_model_values(rpm, len(models), 'RPM')
    concurrencies = _normalize_model_values(max_concurrent, len(models), '동시 작업수')
    temperatures = _normalize_model_values(temperature, len(models), 'Temperature')
    br_starts = _normalize_model_values(br_start, len(models), '분할 시작')
    isno_xs = _normalize_model_values(isno_x, len(models), '검열 건너뛰기')
    thinking_budgets = _normalize_model_values(thinking_budget, len(models), '추론')
    workers = []
    for i, model in enumerate(models):
        workers.append(ModelWorker(
            model, rpms[i], concurrencies[i], temperatures[i], br_starts[i], isno_xs[i], thinking_budgets[i]
        ))
    return workers


def _is_stopped(check, check_i=None):
    if check_i:
        try:
            if check_i():
                raise ForceStopException()
        except ForceStopException:
            raise
        except Exception:
            pass

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
    check_i=None,
    br_start=0,
    isno_x=False,
    thinking_budget=None
):
    if dicts is None:
        dicts = {}

    lines = chunk.splitlines(keepends=True)
    if not lines:
        return '', 0, False

    if _is_stopped(check, check_i):
        if log_callback and not (check_i and check_i()):
            log_callback(f'[{chunk_idx} - {model_name}] [{depth}] 중지: 번역 시작 전 작업 중지')
        return None, 0, True

    force_split = br_start > 0

    if not force_split and get_japanese_ratio(chunk) < 0.03:
        if log_callback and not (check_i and check_i()):
            log_callback(f'[{chunk_idx} - {model_name}] [{depth}] [시도 0] 원문의 일본어 비율이 너무 낮아 번역 생략')
        return chunk, len(lines), False

    img_tags = IMG_TAG_PATTERN.findall(chunk)
    expected_img_count = len(img_tags)
    masked_chunk = IMG_TAG_PATTERN.sub(IMG_PLACEHOLDER, chunk)

    current_chunk = masked_chunk
    is_censored = False
    censor_data = None

    if raw:
        expected_delimiter_count = len(re.findall(r'^={4,}$', masked_chunk, re.MULTILINE))
    else:
        expected_delimiter_count = masked_chunk.count('+---+')

    attempt = 1
    censor_attempt = 0
    max_censor_attempts = 3
    cur_thinking_budget = thinking_budget

    while not force_split:
        if _is_stopped(check, check_i):
            if log_callback and not (check_i and check_i()):
                log_callback(f'[{chunk_idx} - {model_name}] [{depth}] 중지: 다음 API 요청을 실행하지 않습니다.')
            return None, 0, True

        if is_censored and USE_ADVANCED_CENSOR:
            if censor_attempt >= max_censor_attempts:
                if log_callback and not (check_i and check_i()):
                    log_callback(f'[{chunk_idx} - {model_name}] [{depth}] 세분화 검열 {max_censor_attempts}회 재시도 모두 실패 -> 분할 처리로 전환')
                break
            censor_attempt += 1
            prefix_log = f'[{chunk_idx} - {model_name} - 세분화검열] [{depth}] [검열 시도 {censor_attempt}/{max_censor_attempts}]'
        else:
            if attempt > max_retries:
                break
            censored_label = '검열' if is_censored else ''
            prefix_log = f'[{chunk_idx} - {model_name}{(" - " + censored_label) if censored_label else ""}] [{depth}] [시도 {attempt}/{max_retries}]'

        await rate_limiter.wait()

        if _is_stopped(check, check_i):
            if log_callback and not (check_i and check_i()):
                log_callback(f'{prefix_log} 중지: API 호출 직전 작업 중지')
            return None, 0, True

        if log_callback and not (check_i and check_i()):
            log_callback(f'{prefix_log} 번역 시작: (라인 수: {len(lines)})')

        try:
            if raw:
                system_prompt = SYSTEM_PROMPT_RAW
            else:
                system_prompt = SYSTEM_PROMPT if '+---+' in current_chunk else SYSTEM_PROMPT_NO_SPLIT

            if expected_img_count > 0:
                system_prompt += f"\n{IMG_PROMPT_RULE}\n"

            if is_censored and USE_ADVANCED_CENSOR:
                system_prompt += f"\n{CENSOR_PROMPT_RULE}\n"

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
                    if log_callback and not (check_i and check_i()):
                        log_callback(f'{prefix_log} 용어집 사용: {glossary_log}')

            config_params = {
                "system_instruction": system_prompt,
                "temperature": temperature,
                "top_p": 0.8,
                "safety_settings": safety_settings
            }
            thinking_cfg = build_thinking_config(cur_thinking_budget, model_name=model_name)
            if thinking_cfg is not None:
                config_params["thinking_config"] = thinking_cfg

            try:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=f'번역:\n{current_chunk}',
                    config=types.GenerateContentConfig(**config_params)
                )
            except asyncio.CancelledError:
                raise ForceStopException()
            except Exception as api_err:
                _is_stopped(check, check_i)
                err_str = str(api_err).lower()
                if thinking_cfg is not None and any(kw in err_str for kw in ("thinking", "unsupported", "invalid argument")):
                    if log_callback and not (check_i and check_i()):
                        log_callback(f'{prefix_log} 알림: 모델이 해당 추론 설정을 미지원하여 제외 후 일반 모드로 재시도합니다.')
                    cur_thinking_budget = None
                    config_params.pop("thinking_config", None)
                    response = await client.aio.models.generate_content(
                        model=model_name,
                        contents=f'번역:\n{current_chunk}',
                        config=types.GenerateContentConfig(**config_params)
                    )
                else:
                    raise api_err

            _is_stopped(check, check_i)

            if response and response.text:
                res_text = response.text.strip()
                res_text = res_text.replace('「', '“').replace('」', '”').replace('｢', '“').replace('｣', '”')

                if is_censored and USE_ADVANCED_CENSOR and censor_data:
                    valid, err_msg = check_statrt_stain(censor_data, res_text)
                    if not valid:
                        if log_callback and not (check_i and check_i()):
                            log_callback(f"{prefix_log} 경고: 세분화 검열 무결성 검증 실패: {err_msg} ->{' 순서 재셔플 후' if CENSOR_SHUFFLE else ''} 재시도")
                        censor_data, current_chunk = make_statrt_stain(
                            masked_chunk,
                            shuffle=CENSOR_SHUFFLE,
                            extract_mode=CENSOR_EXTRACT_MODE,
                            papago=CENSOR_PAPAGO
                        )
                        continue

                    check_text = prepare_for_ratio_check(res_text, censor_data)
                else:
                    check_text = res_text

                if expected_img_count > 0:
                    actual_img_count = res_text.count(IMG_PLACEHOLDER)
                    if actual_img_count != expected_img_count:
                        if log_callback and not (check_i and check_i()):
                            log_callback(
                                f"{prefix_log} 경고: '-+++-' 이미지 태그 개수 불일치 "
                                f'(기대: {expected_img_count}, 결과: {actual_img_count}) -> 재시도'
                            )
                        if is_censored and USE_ADVANCED_CENSOR:
                            censor_data, current_chunk = make_statrt_stain(masked_chunk, shuffle=CENSOR_SHUFFLE, extract_mode=CENSOR_EXTRACT_MODE, papago=CENSOR_PAPAGO)
                        else:
                            current_chunk = masked_chunk
                            is_censored = False
                            attempt += 1
                        continue

                if not raw and '+---+' in masked_chunk:
                    actual_delimiter_count = res_text.count('+---+')
                    if actual_delimiter_count != expected_delimiter_count:
                        if log_callback and not (check_i and check_i()):
                            log_callback(
                                f"{prefix_log} 경고: '+---+' 개수 불일치 "
                                f'(기대: {expected_delimiter_count}, 결과: {actual_delimiter_count}) -> 재시도'
                            )
                        if is_censored and USE_ADVANCED_CENSOR:
                            censor_data, current_chunk = make_statrt_stain(masked_chunk, shuffle=CENSOR_SHUFFLE, extract_mode=CENSOR_EXTRACT_MODE, papago=CENSOR_PAPAGO)
                        else:
                            current_chunk = masked_chunk
                            is_censored = False
                            attempt += 1
                        continue

                if raw and '====' in masked_chunk:
                    actual_delimiter_count = len(re.findall(r'^={4,}$', res_text, re.MULTILINE))
                    if actual_delimiter_count != expected_delimiter_count:
                        if log_callback and not (check_i and check_i()):
                            log_callback(
                                f"{prefix_log} 경고: '====...' 라인 개수 불일치 "
                                f'(기대: {expected_delimiter_count}, 결과: {actual_delimiter_count}) -> 재시도'
                            )
                        if is_censored and USE_ADVANCED_CENSOR:
                            censor_data, current_chunk = make_statrt_stain(masked_chunk, shuffle=CENSOR_SHUFFLE, extract_mode=CENSOR_EXTRACT_MODE, papago=CENSOR_PAPAGO)
                        else:
                            current_chunk = masked_chunk
                            is_censored = False
                            attempt += 1
                        continue

                jp_ratio = get_japanese_ratio(check_text)
                ko_ratio = get_korean_ratio(check_text)
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
                    line_ratio = get_linebreak_preservation_ratio(masked_chunk, check_text)
                    success = jp_ratio < max_jp_ratio and ko_ratio >= min_ko_ratio and line_ratio >= min_line_ratio
                else:
                    line_ratio = 100.0
                    success = jp_ratio < max_jp_ratio and ko_ratio >= min_ko_ratio

                if success:
                    _is_stopped(check, check_i)
                    if is_censored and USE_ADVANCED_CENSOR and censor_data:
                        res_text = assemble_final_text(res_text, censor_data, use_translated=CENSOR_PAPAGO)

                    if expected_img_count > 0:
                        res_text = restore_img_placeholders(res_text, img_tags)

                    _is_stopped(check, check_i)
                    if log_callback and not (check_i and check_i()):
                        if raw:
                            log_callback(f'{prefix_log} -> 성공: (줄바꿈 보존율: {line_ratio:.2f}%)')
                        else:
                            log_callback(f'{prefix_log} -> 성공: 완료')
                    return res_text, len(lines), False

                if log_callback and not (check_i and check_i()):
                    log_callback(
                        f'{prefix_log} 경고: 번역 조건 미달 '
                        f'(한글: {ko_ratio:.2f}% [기준 {min_ko_ratio}%], 일어: {jp_ratio:.2f}% [기준 <{max_jp_ratio}%]) -> 재시도'
                    )

                if is_censored and USE_ADVANCED_CENSOR:
                    censor_data, current_chunk = make_statrt_stain(masked_chunk, shuffle=CENSOR_SHUFFLE, extract_mode=CENSOR_EXTRACT_MODE, papago=CENSOR_PAPAGO)
                else:
                    current_chunk = masked_chunk
                    is_censored = False
                    attempt += 1

            else:
                if isno_x:
                    if log_callback and not (check_i and check_i()):
                        log_callback(f'{prefix_log} 경고: API 응답이 비어있음 -> 검열 우회 설정으로 즉시 분할 실행')
                    break

                if is_censored:
                    if USE_ADVANCED_CENSOR:
                        if log_callback and not (check_i and check_i()):
                            log_callback(f'{prefix_log} 경고: 세분화 검열 중에도 응답 비어있음 -> 청크 분할')
                        break
                    else:
                        attempt += 1
                        break

                if USE_ADVANCED_CENSOR:
                    if log_callback and not (check_i and check_i()):
                        log_callback(f'{prefix_log} 경고: API 응답 비어있음 -> 세분화 검열 모드 진입 (최대 {max_censor_attempts}회 시도)')
                    is_censored = True
                    censor_attempt = 0
                    censor_data, current_chunk = make_statrt_stain(masked_chunk, shuffle=CENSOR_SHUFFLE, extract_mode=CENSOR_EXTRACT_MODE, papago=CENSOR_PAPAGO)
                    continue
                else:
                    if log_callback and not (check_i and check_i()):
                        log_callback(f'{prefix_log} 경고: API 응답 비어있음 -> 기본 검열 실행')
                    current_chunk = x_making(masked_chunk)
                    is_censored = True
                    attempt += 1

        except (ForceStopException, asyncio.CancelledError):
            raise ForceStopException()
        except Exception as e:
            if _is_stopped(check, check_i):
                if log_callback and not (check_i and check_i()):
                    log_callback(f'{prefix_log} 중지: 현재 API 요청 종료 후 중지')
                return None, 0, True

            if log_callback and not (check_i and check_i()):
                log_callback(f'{prefix_log} 오류: API 호출 중 예외 발생: {e} -> 재시도 (3배 대기)')

            await rate_limiter.wait()
            await rate_limiter.wait()

            if is_censored and USE_ADVANCED_CENSOR:
                censor_data, current_chunk = make_statrt_stain(masked_chunk, shuffle=CENSOR_SHUFFLE, extract_mode=CENSOR_EXTRACT_MODE, papago=CENSOR_PAPAGO)
            else:
                is_censored = False
                attempt += 1

    if _is_stopped(check, check_i):
        if log_callback and not (check_i and check_i()):
            log_callback(f'[{chunk_idx} - {model_name}] [{depth}] 중지: 분할 작업을 실행하지 않습니다.')
        return None, 0, True

    if len(lines) <= 2 or depth >= 4:
        if log_callback and not (check_i and check_i()):
            log_callback(f'[{chunk_idx} - {model_name}] [{depth}] 오류: [최대초과] 분할 한계 도달 -> 원문 유지')
        return chunk, len(lines), False

    mid = len(lines) // 2

    if log_callback and not (check_i and check_i()):
        split_type = f"[강제분할: 남은단계 {br_start}]" if force_split else "[검열실패/최대초과: 분할]"
        log_callback(
            f'[{chunk_idx} - {model_name}] [{depth}] {split_type} '
            f'청크 분할 처리 (전반부 {mid}줄, 후반부 {len(lines)-mid}줄)'
        )

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
        check_i=check_i,
        br_start=max(0, br_start - 1),
        isno_x=isno_x,
        thinking_budget=cur_thinking_budget
    )

    if part1_ignore:
        return part1_text, part1_len, True

    if part1_text is None:
        return None, 0, True

    if _is_stopped(check, check_i):
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
        check_i=check_i,
        br_start=max(0, br_start - 1),
        isno_x=isno_x,
        thinking_budget=cur_thinking_budget
    )

    if part2_ignore:
        return part1_text, len(lines[:mid]), True

    if part2_text is None:
        return part1_text, len(lines[:mid]), True

    return part1_text.rstrip('\n') + '\n' + part2_text.lstrip('\n'), len(lines), False


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
    check_i=None,
    br_start=0,
    isno_x=False,
    thinking_budget=None
):
    if API == '':
        if log_callback:
            log_callback('에러: API 키가 설정되지 않았습니다.')
        return 'error'

    try:
        workers = _create_model_workers(
            model_name, rpm, max_concurrent, temperature, br_start, isno_x, thinking_budget
        )
    except Exception as e:
        if log_callback:
            log_callback(f'에러: 모델 설정 오류: {e}')
        return 'error'

    chunks = split_text_by_lines(text, max_chars=max_chars)
    translated_parts = [None] * len(chunks)
    out = down.downin.base_data.OUTFOLDER + '/'
    os.makedirs(f'{out}trs', exist_ok=True)
    os.makedirs(f'{out}epub', exist_ok=True)
    os.makedirs(f'{out}epub\\raw_txt', exist_ok=True)
    safe = re.sub('[\\\\/:*?"<>|]', '_', title).strip()
    ai_dir = f'{out}trs\\ai_down_{safe}_{max_chars}'
    os.makedirs(ai_dir, exist_ok=True)

    model_info = ', '.join(
        f'{worker.model_name}(RPM={worker.rpm},동시={worker.max_concurrent},온도={worker.temperature},분할={worker.br_start},검열건너뜀={worker.isno_x},추론={worker.thinking_budget})'
        for worker in workers
    )
    msg = f'총 {len(chunks)}개 청크 분할 완료 (청크 크기: {max_chars}). 사용 모델: {model_info}, RAW: {raw}'
    print(msg)
    if log_callback and not (check_i and check_i()):
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
        if _is_stopped(check, check_i):
            if log_callback and not (check_i and check_i()):
                log_callback(f'[{idx}/{len(chunks)}] [{worker.model_name}] 중지: 대기 중인 청크 건너뜀')
            return

        file_path = f'{ai_dir}/{idx}.txt'

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    saved_text = f.read()
                if saved_text and not saved_text.startswith('[번역 실패'):
                    skip_msg = f'[{idx}/{len(chunks)}] [{worker.model_name}] 이미 저장된 파일 존재 → 건너뜀'
                    if log_callback and not (check_i and check_i()):
                        log_callback(skip_msg)
                    async with lock:
                        translated_parts[idx - 1] = saved_text
                        completed_count += 1
                        if progress_callback and not (check_i and check_i()):
                            progress_callback(completed_count, len(chunks), f'{completed_count}/{len(chunks)} 청크 완료')
                    return
            except Exception:
                pass

        result_ignore_back = False
        try:
            if _is_stopped(check, check_i):
                if log_callback and not (check_i and check_i()):
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
                check_i=check_i,
                br_start=worker.br_start,
                isno_x=worker.isno_x,
                thinking_budget=worker.thinking_budget
            )

            _is_stopped(check, check_i)

            if result_text is not None and not result_ignore:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(result_text)
                    async with lock:
                        translated_parts[idx - 1] = result_text
                except Exception as save_err:
                    if log_callback and not (check_i and check_i()):
                        log_callback(f'[{idx}번 청크] 임시 파일 저장 실패: {save_err}')

            if result_ignore or result_text is None or _is_stopped(check, check_i):
                result_ignore_back = True
                async with lock:
                    ignored = True
                return

            if log_callback and not (check_i and check_i()):
                log_callback(f'[{idx}/{len(chunks)}] [{worker.model_name}] 청크 번역 완료: 성공')

        except (ForceStopException, asyncio.CancelledError):
            result_ignore_back = True
            raise ForceStopException()
        except Exception as e:
            if log_callback and not (check_i and check_i()):
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
                with open(error_path, 'w', encoding='utf-8') as f:
                    f.write(chunk)
            except Exception:
                pass

        finally:
            if check_i and check_i():
                result_ignore_back = True

            if not result_ignore_back and not (check_i and check_i()):
                async with lock:
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, len(chunks), f'{completed_count}/{len(chunks)} 청크 완료')

    async def model_worker(worker, worker_number):
        while True:
            if _is_stopped(check, check_i):
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

    async def force_stop_watcher():
        while True:
            if check_i and check_i():
                for t in worker_tasks:
                    if not t.done():
                        t.cancel()
                return
            await asyncio.sleep(0.05)

    watcher_task = asyncio.create_task(force_stop_watcher())

    try:
        await asyncio.gather(*worker_tasks)
    except asyncio.CancelledError:
        raise ForceStopException()
    finally:
        watcher_task.cancel()

    _is_stopped(check, check_i)

    json_path = f'{out}trs\\save_{safe} _ {max_chars}.json'
    try:
        first_br = workers[0].br_start if workers else 0
        first_tb = workers[0].thinking_budget if workers else None
        save_translation_json(
            translated_parts, chunks, max_chars, title, json_path, raw=raw, br_start=first_br, thinking_budget=first_tb
        )
    except Exception as e:
        if log_callback and not (check_i and check_i()):
            log_callback(f'JSON 저장 실패: {e}')

    if ignored or _is_stopped(check, check_i):
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
{'+---+\n'}{book_title} | {author}

'''
        _is_stopped(check, check_i)
        if not _is_stopped(check, check_i):
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
    progress_callback=None,
    log_callback=None,
    raw=False,
    dicts={},
    check=None,
    check_i=None,
    br_start=0,
    isno_x=False,
    thinking_budget=None
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
            check_i,
            br_start,
            isno_x,
            thinking_budget
        )
    )


def TransAi_All(
    txt: str,
    max_chars=5000,
    model_name='gemini-3.5-flash-Lite',
    rpm=15,
    temperature=0.1,
    max_concurrent=4,
    progress_callback=None,
    log_callback=None,
    dicts={},
    check=None,
    check_i=None,
    br_start=0,
    isno_x=False,
    thinking_budget=None
):
    try:
        raw = detect_raw_text(txt)

        if raw:
            lines = txt.splitlines(keepends=True)
            book_title = lines[0].strip() if len(lines) > 0 else '제목 미정'
            author = lines[1].strip() if len(lines) > 1 else ''

            raw_text, raw_title = prepare_raw_text(txt)

            if log_callback and not (check_i and check_i()):
                log_callback(
                    f"RAW 번역 시작: 제목 '{book_title}', 작가 '{author}', "
                    f'청크 크기: {max_chars}, 동시 작업수: {max_concurrent}, 추론: {thinking_budget}'
                )

            trans_out = translate_light_novel(
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
                check_i=check_i,
                br_start=br_start,
                isno_x=isno_x,
                thinking_budget=thinking_budget
            )

            if trans_out == 'ignore':
                return 'ignore'

            if trans_out == 'error':
                return 'error'

            translated_result = '+---+\n' + trans_out
            epub_text = f'{book_title}\n{author}\n(raw)\n{"+---+\n"}{translated_result}'

            _is_stopped(check, check_i)
            if not _is_stopped(check, check_i):
                down.create_epub_from_merged_txt(
                    txt_value=epub_text,
                    RAW=True
                )

            return translated_result

        A = '_번역\n'

        if '+---+' in txt:
            split_pos = txt.find('+---+')
            f = txt[:split_pos - 1]
            g = txt[split_pos + 6:]
        else:
            f = '제목 미정'
            g = txt

        first_newline = f.find('\n')
        if first_newline == -1:
            t = f
        else:
            t = f[:first_newline] + '_' + f[first_newline + 1:]

        if log_callback and not (check_i and check_i()):
            log_callback(
                f"전체 번역 시작: 제목 '{t}', 청크 크기: {max_chars}, "
                f'동시 작업수: {max_concurrent}, 추론: {thinking_budget}'
            )

        trans_out = translate_light_novel(
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
            check_i=check_i,
            br_start=br_start,
            isno_x=isno_x,
            thinking_budget=thinking_budget
        )

        if trans_out == 'ignore':
            return 'ignore'

        if trans_out == 'error':
            return 'error'

        translated_result = '+---+\n' + trans_out

        title_end = f.find('\n')
        if title_end == -1:
            epub_text = f + A + translated_result
        else:
            epub_text = f[:title_end] + A + f[title_end + 1:] + '\n' + translated_result

        _is_stopped(check, check_i)
        if not _is_stopped(check, check_i):
            down.create_epub_from_merged_txt(
                txt_value=epub_text,
                RAW=False
            )

        return translated_result

    except (ForceStopException, asyncio.CancelledError):
        if log_callback:
            log_callback('번역이 강제로 종료 되었습니다.')
        return 'ignore'


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
    check_i=None,
    br_start=0,
    isno_x=False,
    thinking_budget=None
):
    if _is_stopped(check, check_i):
        if log_callback and not (check_i and check_i()):
            log_callback('JSON 복원 중지: 작업 시작 전 중지되었습니다.')
        return 'ignore'

    if not os.path.exists(json_path):
        msg = f'에러: JSON 파일을 찾을 수 없습니다 | {json_path}'
        if log_callback and not (check_i and check_i()):
            log_callback(msg)
        return 'error'

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    title = data.get('name', 'restored')
    max_chars = data.get('chunk', 5000)
    raw = bool(data.get('raw', False))

    try:
        workers = _create_model_workers(
            model_name, rpm, max_concurrent, temperature, br_start, isno_x, thinking_budget
        )
    except Exception as e:
        if log_callback and not (check_i and check_i()):
            log_callback(f'에러: JSON 모델 설정 오류: {e}')
        return 'error'

    out = down.downin.base_data.OUTFOLDER + '/'
    os.makedirs(f'{out}trs', exist_ok=True)
    safe = re.sub('[\\\\/:*?"<>|]', '_', title).strip()
    ai_dir = f'{out}trs\\ai_down_{safe}_{max_chars}'
    os.makedirs(ai_dir, exist_ok=True)

    safety_settings = get_safety_settings()

    chunk_indices = sorted(list(set(
        int(k[:-2]) if (k.endswith('-j') and k[:-2].isdigit()) else int(k)
        for k in data.keys() if k.isdigit() or (k.endswith('-j') and k[:-2].isdigit())
    )))

    model_info = ', '.join(
        f'{worker.model_name}(RPM={worker.rpm},동시={worker.max_concurrent},온도={worker.temperature},분할={worker.br_start},검열건너뜀={worker.isno_x},추론={worker.thinking_budget})'
        for worker in workers
    )
    msg = f'[{title}] JSON 로드 완료 (청크 크기: {max_chars}, 총 {len(chunk_indices)}개 청크 비동기 복원) / 사용 모델: {model_info} / RAW: {raw}'
    if log_callback and not (check_i and check_i()):
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
            if _is_stopped(check, check_i):
                result_ignore_back = True
                async with lock:
                    ignored = True
                if log_callback and not (check_i and check_i()):
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
                clean_source = str(source_to_use).replace("%'%", '"').replace('\\\n', '\n')
                jp_ratio_orig = get_japanese_ratio(clean_source)

                re_msg = f'[{pos}/{len(chunk_indices)}] [{worker.model_name}] 원문 번역 실행 (인덱스 {chunk_idx}, 원문 일어 비율 {jp_ratio_orig:.2f}%)'
                if log_callback and not (check_i and check_i()):
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
                        check_i=check_i,
                        br_start=worker.br_start,
                        isno_x=worker.isno_x,
                        thinking_budget=worker.thinking_budget
                    )
                    if result_ignore or result_text is None:
                        result_ignore_back = True
                        async with lock:
                            ignored = True
                        if log_callback and not (check_i and check_i()):
                            log_callback(f' └ [{display_idx}번 청크] [{worker.model_name}] 번역 결과 없음/무시됨')
                        return
                except (ForceStopException, asyncio.CancelledError):
                    raise ForceStopException()
                except Exception as e:
                    if log_callback and not (check_i and check_i()):
                        log_callback(f' └ [{display_idx}번 청크] [{worker.model_name}] 재번역 실패: {e}')
                    result_text = clean_source
            else:
                if log_callback and not (check_i and check_i()):
                    log_callback(f'[{pos}/{len(chunk_indices)}] [{worker.model_name}] 기존 번역 청크 통과 (인덱스 {chunk_idx})')
                result_text = str(trans_text).replace("%'%", '"').replace('\\\n', '\n')

            _is_stopped(check, check_i)

            try:
                with open(file_path, 'w', encoding='utf-8') as f_out:
                    f_out.write(result_text)
            except Exception as e:
                if log_callback and not (check_i and check_i()):
                    log_callback(f' └ [{display_idx}번 청크] 파일 저장 오류: {e}')

            async with lock:
                translated_parts[pos - 1] = result_text
                original_chunks[pos - 1] = orig_text if orig_text is not None else result_text

            if _is_stopped(check, check_i):
                result_ignore_back = True
                async with lock:
                    ignored = True
                return

        except (ForceStopException, asyncio.CancelledError):
            result_ignore_back = True
            raise ForceStopException()
        except Exception as e:
            if log_callback and not (check_i and check_i()):
                log_callback(f' └ [{pos}번 청크] [{worker.model_name}] JSON 복원 처리 실패: {e}')
        finally:
            if check_i and check_i():
                result_ignore_back = True

            if not result_ignore_back and not (check_i and check_i()):
                async with lock:
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, len(chunk_indices), f'{completed_count}/{len(chunk_indices)} 청크 완료')

    async def model_worker(worker, worker_number):
        while True:
            if _is_stopped(check, check_i):
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

    async def force_stop_watcher():
        while True:
            if check_i and check_i():
                for t in worker_tasks:
                    if not t.done():
                        t.cancel()
                return
            await asyncio.sleep(0.05)

    watcher_task = asyncio.create_task(force_stop_watcher())

    try:
        await asyncio.gather(*worker_tasks)
    except asyncio.CancelledError:
        raise ForceStopException()
    finally:
        watcher_task.cancel()

    _is_stopped(check, check_i)

    title_lines = [line.strip() for line in title.splitlines() if line.strip()]
    if len(title_lines) >= 3:
        raw_book_title = title_lines[0]
        author = title_lines[1]
        episode = '\n'.join(title_lines[2:])
    elif len(title_lines) == 2:
        if '_' in title_lines[0]:
            raw_book_title, author = title_lines[0].rsplit('_', 1)
        else:
            raw_book_title = title_lines[0]
            author = ''
        episode = title_lines[1]
    elif len(title_lines) == 1:
        if '_' in title_lines[0]:
            raw_book_title, author = title_lines[0].rsplit('_', 1)
        else:
            raw_book_title = title_lines[0]
            author = ''
        episode = ''
    else:
        raw_book_title = 'restored'
        author = ''
        episode = ''

    clean_book_title = re.sub(r'(_번역)+$', '', raw_book_title)
    restored_book_title = f'{clean_book_title}_복원'

    if episode:
        restored_name = f'{restored_book_title}_{author}\n{episode}' if author else f'{restored_book_title}\n{episode}'
    else:
        restored_name = f'{restored_book_title}_{author}' if author else restored_book_title

    os.makedirs(f'{out}trs', exist_ok=True)
    safe_title = re.sub('[\\\\/:*?"<>|]', '_', restored_book_title).strip()
    save_path = f'{out}trs\\save_{safe_title}_{max_chars}_복원.json'
    try:
        first_br = workers[0].br_start if workers else 0
        first_tb = workers[0].thinking_budget if workers else None
        save_translation_json(
            translated_parts, original_chunks, max_chars, restored_name, save_path, raw=raw, br_start=first_br, thinking_budget=first_tb
        )
    except Exception as e:
        if log_callback and not (check_i and check_i()):
            log_callback(f'복원 JSON 파일 저장 실패: {e}')

    if ignored or _is_stopped(check, check_i):
        if log_callback and not (check_i and check_i()):
            log_callback('JSON 복원 중지됨 → EPUB 변환은 생략합니다.')
        return 'ignore'

    final_result = '\n\n'.join(p for p in translated_parts if p)

    if raw:
        os.makedirs(f'{out}epub', exist_ok=True)
        os.makedirs(f'{out}epub\\raw_txt', exist_ok=True)
        txt_path = f'{out}epub\\raw_txt\\{safe_title}.txt'

        r_title = f'''{restored_book_title}
{author}
(raw)
{'+---+\n'}{restored_book_title} | {author}

'''
        _is_stopped(check, check_i)
        if not _is_stopped(check, check_i):
            save_translation_txt(translated_parts, r_title, txt_path)

        raw_header = [restored_book_title, author, '(raw)']
        if episode:
            raw_header.append(episode)
        epub_text = '\n'.join(raw_header) + f'\n{"+---+\n"}{final_result}'

    else:
        normal_header = [f'{restored_book_title}_번역']
        if author:
            normal_header.append(author)
        if episode:
            normal_header.append(episode)
        epub_text = '\n'.join(normal_header) + f'\n{"+---+\n"}{final_result}'

    _is_stopped(check, check_i)
    if not _is_stopped(check, check_i):
        down.create_epub_from_merged_txt(txt_value=epub_text, RAW=raw)

    return final_result


def TransAi_From_Json(
    json_path,
    model_name='gemini-3.5-flash-Lite',
    rpm=15,
    temperature=0.1,
    max_concurrent=4,
    progress_callback=None,
    log_callback=None,
    dicts={},
    check=None,
    check_i=None,
    br_start=0,
    isno_x=False,
    thinking_budget=None
):
    try:
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
                check_i,
                br_start,
                isno_x,
                thinking_budget
            )
        )
    except (ForceStopException, asyncio.CancelledError):
        if log_callback:
            log_callback('번역이 강제로 종료 되었습니다.')
        return 'ignore'