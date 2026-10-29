import asyncio
import re
from google.genai import types

from src.trans.prom import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_NO_SPLIT,
    SYSTEM_PROMPT_RAW,
    IMG_PROMPT_RULE,
    CENSOR_PROMPT_RULE,
    GLOSSARY_CONTEXT
)
from src.trans.prompt_sanitizer import (
    assemble_final_text,
    prepare_for_ratio_check,
    x_making,
    make_statrt_stain,
    check_statrt_stain
)
from src.trans.trans_ai_utils import (
    get_japanese_ratio,
    build_dynamic_glossary,
    build_thinking_config,
    restore_img_placeholders,
    IMG_PLACEHOLDER
)
from . import config
from .config import ForceStopException
from .chunk_utils import _is_stopped, adjust_split_mid
from .validator import validate_translation_ratios, reset_or_retry_censor


def _extract_retry_delay(err) -> float:
    err_str = str(err)
    m = re.search(r"retryDelay':\s*'(\d+)s'", err_str)
    if m:
        return float(m.group(1)) + 2.0
    m2 = re.search(r"retry in (\d+(\.\d+)?)s", err_str)
    if m2:
        return float(m2.group(1)) + 2.0
    return 45.0


def _is_rate_limit_error(err):
    msg = str(err).lower()
    return any(k in msg for k in ("429", "resource_exhausted", "quota", "rate limit", "rate_limit", "exhausted"))


def _is_connector_closed_error(err):
    msg = str(err).lower()
    return "connector is closed" in msg or "clientconnectorerror" in msg


def _build_chunk_system_prompt(current_chunk, masked_chunk, raw, expected_img_count, is_censored, dicts, log_callback, prefix_log, check_i):
    if raw:
        system_prompt = SYSTEM_PROMPT_RAW
    else:
        system_prompt = SYSTEM_PROMPT if '+---+' in current_chunk else SYSTEM_PROMPT_NO_SPLIT

    if expected_img_count > 0:
        system_prompt += f"\n{IMG_PROMPT_RULE}\n"

    if is_censored and config.USE_ADVANCED_CENSOR:
        system_prompt += f"\n{CENSOR_PROMPT_RULE}\n"

    if config.CUSTOM_AI_PROMPT != '':
        system_prompt += f"""[사용자 지정 추가 지침]
{config.CUSTOM_AI_PROMPT}
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

    return system_prompt


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

    img_tags = config.IMG_TAG_PATTERN.findall(chunk)
    expected_img_count = len(img_tags)
    masked_chunk = config.IMG_TAG_PATTERN.sub(IMG_PLACEHOLDER, chunk)

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

        if is_censored and config.USE_ADVANCED_CENSOR:
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

        cur_used_key = config.API
        cur_client = config.get_client(cur_used_key)

        try:
            system_prompt = _build_chunk_system_prompt(
                current_chunk, masked_chunk, raw, expected_img_count,
                is_censored, dicts, log_callback, prefix_log, check_i
            )

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
                response = await cur_client.aio.models.generate_content(
                    model=model_name,
                    contents=f'번역:\n{current_chunk}',
                    config=types.GenerateContentConfig(**config_params)
                )
            except asyncio.CancelledError:
                raise ForceStopException()
            except Exception as api_err:
                _is_stopped(check, check_i)
                if _is_connector_closed_error(api_err):
                    if log_callback and not (check_i and check_i()):
                        log_callback(f'{prefix_log} 알림: 세션 재연결 중...')
                    config.refresh_client(cur_used_key)
                    continue
                elif thinking_cfg is not None and any(kw in str(api_err).lower() for kw in ("thinking", "unsupported", "invalid argument")):
                    if log_callback and not (check_i and check_i()):
                        log_callback(f'{prefix_log} 알림: 모델이 해당 추론 설정을 미지원하여 제외 후 일반 모드로 재시도합니다.')
                    cur_thinking_budget = None
                    config_params.pop("thinking_config", None)
                    continue
                elif _is_rate_limit_error(api_err):
                    delay = _extract_retry_delay(api_err)
                    can_retry, new_idx, is_leader, wrapped = await config.switch_api_key_safe(cur_used_key, delay, log_callback)
                    if can_retry:
                        if log_callback and not (check_i and check_i()):
                            if is_leader and not wrapped:
                                log_callback(f'{prefix_log} 경고: Rate Limit 감지 -> 전체 API 키를 [{new_idx}]번으로 전환했습니다.')
                        continue
                    else:
                        if log_callback and not (check_i and check_i()):
                            log_callback(f'{prefix_log} 경고: Rate Limit 발생 (대기 시간: {int(delay)}초) -> {int(delay)}초 대기 후 재시도')
                        await asyncio.sleep(delay)
                        attempt += 1
                        continue
                else:
                    raise api_err

            _is_stopped(check, check_i)

            if response and response.text:
                res_text = response.text.strip()
                res_text = res_text.replace('「', '“').replace('」', '”').replace('｢', '“').replace('｣', '”')

                if is_censored and config.USE_ADVANCED_CENSOR and censor_data:
                    valid, err_msg = check_statrt_stain(censor_data, res_text)
                    if not valid:
                        if log_callback and not (check_i and check_i()):
                            log_callback(f"{prefix_log} 경고: 세분화 검열 무결성 검증 실패: {err_msg} ->{' 순서 재셔플 후' if config.CENSOR_SHUFFLE else ''} 재시도")
                        censor_data, current_chunk = make_statrt_stain(
                            masked_chunk,
                            shuffle=config.CENSOR_SHUFFLE,
                            extract_mode=config.CENSOR_EXTRACT_MODE,
                            papago=config.CENSOR_PAPAGO
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
                        current_chunk, is_censored, censor_data, attempt = reset_or_retry_censor(masked_chunk, is_censored, attempt)
                        continue

                if not raw and '+---+' in masked_chunk:
                    actual_delimiter_count = res_text.count('+---+')
                    if actual_delimiter_count != expected_delimiter_count:
                        if log_callback and not (check_i and check_i()):
                            log_callback(
                                f"{prefix_log} 경고: '+---+' 개수 불일치 "
                                f'(기대: {expected_delimiter_count}, 결과: {actual_delimiter_count}) -> 재시도'
                            )
                        current_chunk, is_censored, censor_data, attempt = reset_or_retry_censor(masked_chunk, is_censored, attempt)
                        continue

                if raw and '====' in masked_chunk:
                    actual_delimiter_count = len(re.findall(r'^={4,}$', res_text, re.MULTILINE))
                    if actual_delimiter_count != expected_delimiter_count:
                        if log_callback and not (check_i and check_i()):
                            log_callback(
                                f"{prefix_log} 경고: '====...' 라인 개수 불일치 "
                                f'(기대: {expected_delimiter_count}, 결과: {actual_delimiter_count}) -> 재시도'
                            )
                        current_chunk, is_censored, censor_data, attempt = reset_or_retry_censor(masked_chunk, is_censored, attempt)
                        continue

                success, jp_ratio, ko_ratio, min_ko_ratio, max_jp_ratio, line_ratio = validate_translation_ratios(
                    masked_chunk, check_text, raw
                )

                if success:
                    _is_stopped(check, check_i)
                    if is_censored and config.USE_ADVANCED_CENSOR and censor_data:
                        res_text = assemble_final_text(res_text, censor_data, use_translated=config.CENSOR_PAPAGO)

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

                current_chunk, is_censored, censor_data, attempt = reset_or_retry_censor(masked_chunk, is_censored, attempt)

            else:
                if isno_x:
                    if log_callback and not (check_i and check_i()):
                        log_callback(f'{prefix_log} 경고: API 응답이 비어있음 -> 검열 우회 설정으로 즉시 분할 실행')
                    break

                if is_censored:
                    if config.USE_ADVANCED_CENSOR:
                        if log_callback and not (check_i and check_i()):
                            log_callback(f'{prefix_log} 경고: 세분화 검열 중에도 응답 비어있음 -> 청크 분할')
                        break
                    else:
                        attempt += 1
                        break

                if config.USE_ADVANCED_CENSOR:
                    if log_callback and not (check_i and check_i()):
                        log_callback(f'{prefix_log} 경고: API 응답 비어있음 -> 세분화 검열 모드 진입 (최대 {max_censor_attempts}회 시도)')
                    is_censored = True
                    censor_attempt = 0
                    censor_data, current_chunk = make_statrt_stain(
                        masked_chunk,
                        shuffle=config.CENSOR_SHUFFLE,
                        extract_mode=config.CENSOR_EXTRACT_MODE,
                        papago=config.CENSOR_PAPAGO
                    )
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

            if _is_connector_closed_error(e):
                config.refresh_client(cur_used_key)
                if log_callback and not (check_i and check_i()):
                    log_callback(f'{prefix_log} 세션 재연결 완료 -> 재시도')
                continue

            if log_callback and not (check_i and check_i()):
                log_callback(f'{prefix_log} 오류: API 호출 중 예외 발생: {e} -> 재시도 (3배 대기)')

            await rate_limiter.wait()
            await rate_limiter.wait()

            if is_censored and config.USE_ADVANCED_CENSOR:
                censor_data, current_chunk = make_statrt_stain(
                    masked_chunk,
                    shuffle=config.CENSOR_SHUFFLE,
                    extract_mode=config.CENSOR_EXTRACT_MODE,
                    papago=config.CENSOR_PAPAGO
                )
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
    mid = adjust_split_mid(lines, mid, raw)

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