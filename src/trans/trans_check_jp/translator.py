import asyncio
import inspect
import re
import sys
import traceback

from src.trans.trans import Translator
from .constants import (
    FAST_LEXICON_REPLACEMENTS, JP_PATTERN, KO_PATTERN, JP_BLOCK_PATTERN
)
from .text_cleaner import (
    has_japanese, resolve_arrows_and_memos, resolve_brackets_from_raw,
    clean_explanation_residue, sanitize_dot_addition, sanitize_translated_word,
    fix_japanese_interjections, fix_embedded_katakana
)


def call_translator_safely(text_to_translate: str) -> str:
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        stripped = text_to_translate.strip()
        has_curly_quotes = stripped.startswith('“') and stripped.endswith('”')
        has_straight_quotes = stripped.startswith('"') and stripped.endswith('"')

        if inspect.iscoroutinefunction(Translator):
            res = loop.run_until_complete(Translator(text_to_translate))
        else:
            res = Translator(text_to_translate)
            if inspect.iscoroutine(res):
                res = loop.run_until_complete(res)

        res_str = str(res).strip()
        if has_curly_quotes:
            if not (res_str.startswith('“') and res_str.endswith('”')):
                res_str = res_str.strip('“"').strip('”"')
                res_str = f"“{res_str}”"
        elif has_straight_quotes:
            if not (res_str.startswith('"') and res_str.endswith('"')):
                res_str = res_str.strip('"')
                res_str = f'"{res_str}"'

        return res_str
    except Exception as e:
        print(f"\n[ERROR Translator] 호출 실패! {e}", file=sys.stderr)
        traceback.print_exc()
        raise e


def smart_translate(text: str, glossary: dict = None, is_word_mode: bool = False) -> str:
    if not text or not text.strip():
        return text

    orig_input = text
    print(f"\n[DEBUG Pipeline] >>> 입력 [모드={'단어' if is_word_mode else '문장'}]: {orig_input!r}")

    res = resolve_arrows_and_memos(text)
    res = resolve_brackets_from_raw(res)

    if glossary:
        sorted_glossary = sorted(glossary.items(), key=lambda x: len(x[0]), reverse=True)
        for jp_word, ko_word in sorted_glossary:
            if jp_word and ko_word and jp_word != ko_word and jp_word in res:
                res = res.replace(jp_word, ko_word)

    for pattern, repl in FAST_LEXICON_REPLACEMENTS:
        res = re.sub(pattern, repl, res)

    res = fix_japanese_interjections(res)
    res = re.sub(r'([가-힣])ー+', r'\1―', res)
    res = clean_explanation_residue(res)
    res = re.sub(r' +', ' ', res).strip()

    if not has_japanese(res):
        print(f"[DEBUG Pipeline] 규칙/괄호 해석만으로 완료: {res!r}")
        if is_word_mode:
            res = sanitize_dot_addition(orig_input, res)
        return res

    jp_chars_count = len(JP_PATTERN.findall(res))
    ko_chars_count = len(KO_PATTERN.findall(res))

    if ko_chars_count >= 10 and jp_chars_count <= 4 and not is_word_mode:
        print(f"[DEBUG Pipeline] [한국어 보호] 문장 전체 API 호출 생략하고 단어만 음차: {res!r}")
        res = fix_embedded_katakana(res)
        if not has_japanese(res):
            return res

    print(f"[DEBUG Pipeline] [API 호출 필요] 잔여 일문 존재 -> Translator 호출: {res!r}")
    try:
        translated = call_translator_safely(res)
        print(f"[DEBUG Pipeline] Translator 반환 성공: {translated!r}")
        if is_word_mode:
            translated = sanitize_translated_word(translated, orig_text=res)
        res = translated
    except Exception as e:
        print(f"[WARNING Pipeline] 번역기 호출 실패 ({e}), 폴백 진행", file=sys.stderr)

    res = resolve_arrows_and_memos(res)
    res = resolve_brackets_from_raw(res)
    res = fix_japanese_interjections(res)

    if has_japanese(res):
        jp_matches = list(JP_BLOCK_PATTERN.finditer(res))
        if jp_matches:
            chars = list(res)
            for m in reversed(jp_matches):
                sub_jp = m.group()
                if not JP_PATTERN.search(sub_jp):
                    chars[m.start():m.end()] = []
                    continue

                if len(sub_jp.strip()) >= 3:
                    try:
                        print(f"[DEBUG Pipeline] 블록 세부 번역 시도: {sub_jp!r}")
                        sub_trans = call_translator_safely(sub_jp)
                        sub_trans = sanitize_translated_word(sub_trans, orig_text=sub_jp)
                    except Exception:
                        sub_trans = fix_embedded_katakana(sub_jp)
                else:
                    sub_trans = fix_embedded_katakana(sub_jp)

                chars[m.start():m.end()] = list(sub_trans)
            res = "".join(chars)

    res = fix_embedded_katakana(res)
    res = clean_explanation_residue(res)
    res = re.sub(r'~{2,}', '~', res)
    res = re.sub(r' +', ' ', res).strip()

    if is_word_mode:
        res = sanitize_translated_word(res, orig_text=orig_input)

    print(f"[DEBUG Pipeline] <<< 최종 완료 출력: {res!r}")
    return res