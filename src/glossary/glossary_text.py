import ast
import asyncio
from collections import Counter
import re
from typing import Optional

from src.ai import AiRoute, AiTarget
from src.trans.prompt_sanitizer import get_safety_settings
from src.glossary.glossary import extract_glossary_sample as _extract_glossary_sample
from src.trans.trans_ai_utils import SYSTEM_PROMPT_EXTRACTION, FILTER_SYSTEM_PROMPT

get_japanese_ratio = None  # 참조용


class AsyncRateLimiter:
    def __init__(self, rpm: float):
        self.interval = 60.0 / max(float(rpm), 0.1)
        self.lock = asyncio.Lock()
        self.last_called = 0.0

    async def wait(self):
        async with self.lock:
            now = asyncio.get_running_loop().time()
            elapsed = now - self.last_called
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)
            self.last_called = asyncio.get_running_loop().time()


def _get_route(model: Optional[str] = None, ai_target: Optional[int] = None):
    if model:
        target = int(ai_target) if ai_target is not None else AiRoute.detect_target(model)
        resolved_model = model
    else:
        target = int(ai_target) if ai_target is not None else AiRoute.DEFAULT_TARGET
        resolved_model = AiRoute.get_default_model(target)

    try:
        from src.trans.trans_ai import config as trans_config
        route = trans_config.ai_route
    except Exception:
        route = AiRoute(ai_target=target)

    return route, target, resolved_model


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
        if current and current_length + line_length > chunk:
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
    return any(0xAC00 <= ord(char) <= 0xD7A3 for char in text)


VALID_CATEGORIES = {"이름", "고유명사", "일반", "제도", "명칭"}


def _parse_glossary_response(response_text, log_callback=None):
    result = {}
    if not response_text:
        return result

    text = response_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:python|text)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    lines = text.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            value = ast.literal_eval(line)
            if not isinstance(value, tuple) or len(value) != 3:
                continue

            source, target, category = value
            if not isinstance(source, str) or not isinstance(target, str) or not isinstance(category, str):
                continue

            source = source.strip()
            target = target.strip()
            category = category.strip()

            if not source or not target:
                continue

            if category not in VALID_CATEGORIES:
                if "이름" in category or "인명" in category:
                    category = "이름"
                elif "고유" in category:
                    category = "고유명사"
                elif "제도" in category:
                    category = "제도"
                elif "명칭" in category or "호칭" in category:
                    category = "명칭"
                else:
                    category = "일반"

            if not _is_japanese_text(source) or not _is_korean_text(target):
                continue

            result[source] = (target, category)

        except Exception:
            continue

    return result


def _is_blocked_by_safety(response=None, exception=None) -> bool:
    if exception is not None:
        err_msg = str(exception).lower()
        return "safety" in err_msg or "blocked" in err_msg

    raw = getattr(response, "raw_response", response)
    if raw is not None:
        try:
            if hasattr(raw, "candidates") and raw.candidates:
                finish_reason = getattr(raw.candidates[0], "finish_reason", None)
                if finish_reason and "SAFETY" in str(finish_reason).upper():
                    return True
        except Exception:
            pass

        try:
            _ = getattr(raw, "text", None)
        except Exception as e:
            if "safety" in str(e).lower() or "blocked" in str(e).lower():
                return True

    return False

async def _call_chunk_api_once(
    chunk_text,
    chunk_idx,
    total_chunks,
    rate_limiter: AsyncRateLimiter,
    log_callback=None,
    model=None,
    ai_target=None,
):
    await rate_limiter.wait()
    route, target, model_name = _get_route(model, ai_target)

    setting = {
        "ai_target": target,
        "model_name": model_name,
        "system_instruction": SYSTEM_PROMPT_EXTRACTION,
        "temperature": 0.1,
        "top_p": 0.8,
        "safety_settings": get_safety_settings(),
    }

    try:
        response = await route.send_text(
            message=f"다음 일본어 본문에서 용어집을 추출하십시오.\n\n{chunk_text}",
            setting=setting
        )

        if _is_blocked_by_safety(response=response):
            if log_callback:
                log_callback(f"[용어집 {chunk_idx}/{total_chunks}] 안전 검열에 의해 차단됨 -> 영구 포기")
            return False, None, True

        if not response or not response.text:
            return False, None, False

        parsed = _parse_glossary_response(response.text, log_callback)
        return True, parsed, False

    except Exception as e:
        if _is_blocked_by_safety(exception=e):
            if log_callback:
                log_callback(f"[용어집 {chunk_idx}/{total_chunks}] 검열 예외 감지 ({e}) -> 영구 포기")
            return False, None, True

        if route.is_connection_error(e):
            route.refresh_client()
            if log_callback:
                log_callback(f"[용어집 {chunk_idx}/{total_chunks}] 세션 연결 끊김 -> 재연결 완료")

        if log_callback:
            log_callback(f"[용어집 {chunk_idx}/{total_chunks}] 일시 오류: {e} (다른 청크로 순서 양보)")
        return False, None, False


async def _filter_system_and_terms_async(
    terms_to_check,
    rate_limiter: AsyncRateLimiter,
    log_callback=None,
    model=None,
    ai_target=None,
):
    if not terms_to_check:
        return {}

    terms_list_str = "\n".join([f"{k}: {v}" for k, v in terms_to_check.items()])

    if log_callback:
        log_callback(f"[2차 검증] {len(terms_to_check)}개 항목 중 당연한 일반 어휘 필터링 시작...")

    await rate_limiter.wait()
    route, target, model_name = _get_route(model, ai_target)

    setting = {
        "ai_target": target,
        "model_name": model_name,
        "system_instruction": FILTER_SYSTEM_PROMPT,
        "temperature": 0.0,
        "top_p": 0.8,
        "safety_settings": get_safety_settings(),
    }

    try:
        response = await route.send_text(
            message=f"다음 목록 중 제외할 너무 당연한 일반 단어를 골라내십시오.\n\n{terms_list_str}",
            setting=setting
        )

        if _is_blocked_by_safety(response=response):
            if log_callback:
                log_callback("[2차 검증] 검열 차단됨 (해당 항목 원본 유지)")
            return terms_to_check

        if not response or not response.text:
            return terms_to_check

        raw_text = response.text.strip()
        if not raw_text:
            return terms_to_check

        remove_keywords = {
            item.strip()
            for item in raw_text.replace("\n", ",").split(",")
            if item.strip()
        }

        filtered = {k: v for k, v in terms_to_check.items() if k not in remove_keywords}
        removed_count = len(terms_to_check) - len(filtered)

        if log_callback:
            log_callback(f"[2차 검증 완료] 불필요한 제도/명칭 단어 {removed_count}개 제외 완료")

        return filtered

    except Exception as e:
        if log_callback:
            log_callback(f"[2차 검증 오류] {e} (해당 항목 원본 유지)")
        return terms_to_check


async def _extract_glossary_async(
    all_text,
    paserent,
    chunk,
    log_callback=None,
    model=None,
    RPM=5,
    max_retries=2,
    ai_target=None,
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

    sample_text = _extract_glossary_sample(all_text, paserent_value)
    if not sample_text:
        return {}

    chunks = _split_glossary_text(sample_text, chunk_value)
    if not chunks:
        return {}

    route, target, resolved_model = _get_route(model, ai_target)
    total_chunks = len(chunks)
    if log_callback:
        log_callback(f"용어집 분석 시작: 총 {total_chunks}개 청크 (타깃: {target}, 모델: {resolved_model}, RPM: {RPM})")

    rate_limiter = AsyncRateLimiter(rpm=RPM)
    pending_queue = list(enumerate(chunks, 1))

    glossary_raw_data = {}

    for round_num in range(1, max_retries + 2):
        if not pending_queue:
            break

        failed_queue = []
        if round_num > 1 and log_callback:
            log_callback(f"[재시도 {round_num - 1}] 남은 실패 청크 {len(pending_queue)}개 후순위 재시도 시작")

        for idx, chunk_text in pending_queue:
            if log_callback:
                log_callback(f"[용어집 {idx}/{total_chunks}] 추출 요청 중...")

            success, parsed_dict, is_censored = await _call_chunk_api_once(
                chunk_text=chunk_text,
                chunk_idx=idx,
                total_chunks=total_chunks,
                rate_limiter=rate_limiter,
                log_callback=log_callback,
                model=resolved_model,
                ai_target=target,
            )

            if is_censored:
                continue

            if success and parsed_dict is not None:
                if log_callback:
                    log_callback(f"[용어집 {idx}/{total_chunks}] {len(parsed_dict)}개 단어 추출 완료")

                for src, (tgt, cat) in parsed_dict.items():
                    if src not in glossary_raw_data:
                        glossary_raw_data[src] = {"targets": [], "categories": []}
                    glossary_raw_data[src]["targets"].append(tgt)
                    glossary_raw_data[src]["categories"].append(cat)
            else:
                failed_queue.append((idx, chunk_text))

        pending_queue = failed_queue

    if pending_queue and log_callback:
        log_callback(f"[경고] 최종적으로 {len(pending_queue)}개 청크가 처리되지 못했습니다.")

    safe_glossary = {}
    check_glossary = {}
    ignored_general = 0

    for source, data in glossary_raw_data.items():
        targets = data["targets"]
        categories = data["categories"]

        if not targets:
            continue

        best_target, _ = Counter(targets).most_common(1)[0]
        best_category, _ = Counter(categories).most_common(1)[0]

        if get_japanese_ratio and get_japanese_ratio(best_category) != 0:
            continue

        if best_category == "일반":
            ignored_general += 1
            continue
        elif best_category in ("이름", "고유명사"):
            safe_glossary[source] = best_target
        elif best_category in ("제도", "명칭"):
            check_glossary[source] = best_target

    if log_callback:
        log_callback(
            f"1차 분류 집계: 확정 보존 {len(safe_glossary)}개, "
            f"검증 대상 {len(check_glossary)}개, "
            f"자동 탈락 {ignored_general}개"
        )

    filtered_terms = await _filter_system_and_terms_async(
        terms_to_check=check_glossary,
        rate_limiter=rate_limiter,
        log_callback=log_callback,
        model=resolved_model,
        ai_target=target,
    )

    final_glossary = {**safe_glossary, **filtered_terms}

    if log_callback:
        log_callback(f"최종 용어집 확정: 총 {len(final_glossary)}개 (확정 {len(safe_glossary)}개 + 검증 통과 {len(filtered_terms)}개)")

    return final_glossary


def extract_glossary(
    all_text,
    paserent=10,
    chunk=5000,
    log_callback=None,
    model=None,
    RPM=5,
    ai_target=None,
):
    return asyncio.run(
        _extract_glossary_async(
            all_text=all_text,
            paserent=paserent,
            chunk=chunk,
            log_callback=log_callback,
            model=model,
            RPM=RPM,
            ai_target=ai_target,
        )
    )