import asyncio
import os
import re
import src.down.down as down
from src.trans.trans_ai_utils import (
    split_text_by_lines,
    detect_raw_text,
    prepare_raw_text
)
from . import config
from .config import ForceStopException
from .model_worker import _create_model_workers
from .chunk_utils import repair_chunk_boundaries, _is_stopped
from .pipeline import TranslationItem, run_translation_batch


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
    if config.API == '':
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

    print(repair_chunk_boundaries(split_text_by_lines(text, max_chars=max_chars), raw=raw))
    chunks = repair_chunk_boundaries(split_text_by_lines(text, max_chars=max_chars), raw=raw)
    items = [
        TranslationItem(idx=i, source_text=chunk, orig_text=chunk, check_disk_cache=True, on_error='novel')
        for i, chunk in enumerate(chunks, 1)
    ]

    out = down.downin.base_data.OUTFOLDER + '/'
    os.makedirs(f'{out}epub', exist_ok=True)
    os.makedirs(f'{out}epub\\raw_txt', exist_ok=True)
    safe = re.sub(r'[\\/:*?"<>|]', '_', title).strip()

    model_info = ', '.join(
        f'{worker.model_name}(RPM={worker.rpm},동시={worker.max_concurrent},온도={worker.temperature},분할={worker.br_start},검열건너뜀={worker.isno_x},추론={worker.thinking_budget})'
        for worker in workers
    )
    msg = f'총 {len(chunks)}개 청크 분할 완료 (청크 크기: {max_chars}). 사용 모델: {model_info}, RAW: {raw}'
    print(msg)
    if log_callback and not (check_i and check_i()):
        log_callback(msg)

    json_path = f'{out}trs\\save_{safe} _ {max_chars}.json'

    raw_txt_info = None
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
        raw_txt_info = (txt_path, r_title)

    return await run_translation_batch(
        items=items,
        workers=workers,
        title=title,
        max_chars=max_chars,
        json_path=json_path,
        json_title=title,
        raw=raw,
        dicts=dicts,
        check=check,
        check_i=check_i,
        progress_callback=progress_callback,
        log_callback=log_callback,
        raw_txt_info=raw_txt_info
    )


def translate_light_novel(
    text,
    max_chars=5000,
    model_name=config.MODEL_NAME,
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