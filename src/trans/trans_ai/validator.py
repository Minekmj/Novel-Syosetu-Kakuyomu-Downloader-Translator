from src.trans.prompt_sanitizer import make_statrt_stain
from src.trans.trans_ai_utils import (
    get_japanese_ratio,
    get_korean_ratio,
    get_linebreak_preservation_ratio
)
from . import config


def get_ratio_thresholds(text_len):
    if text_len < 100:
        return 60.0, 5.0, 30.0
    elif text_len < 600:
        return 70.0, 3.0, 70.0
    elif text_len < 1500:
        return 75.0, 1.5, 75.0
    elif text_len < 9000:
        return 80.0, 1.2, 90.0
    else:
        return 80.0, 1.1, 90.0


def validate_translation_ratios(masked_chunk, check_text, raw):
    jp_ratio = get_japanese_ratio(check_text)
    ko_ratio = get_korean_ratio(check_text)
    text_len = len(masked_chunk.strip())
    min_ko_ratio, max_jp_ratio, min_line_ratio = get_ratio_thresholds(text_len)

    if raw:
        line_ratio = get_linebreak_preservation_ratio(masked_chunk, check_text)
        success = jp_ratio < max_jp_ratio and ko_ratio >= min_ko_ratio and line_ratio >= min_line_ratio
    else:
        line_ratio = 100.0
        success = jp_ratio < max_jp_ratio and ko_ratio >= min_ko_ratio

    return success, jp_ratio, ko_ratio, min_ko_ratio, max_jp_ratio, line_ratio


def reset_or_retry_censor(masked_chunk, is_censored, attempt):
    if is_censored and config.USE_ADVANCED_CENSOR:
        censor_data, current_chunk = make_statrt_stain(
            masked_chunk,
            shuffle=config.CENSOR_SHUFFLE,
            extract_mode=config.CENSOR_EXTRACT_MODE,
            papago=config.CENSOR_PAPAGO
        )
        return current_chunk, True, censor_data, attempt
    else:
        return masked_chunk, False, None, attempt + 1