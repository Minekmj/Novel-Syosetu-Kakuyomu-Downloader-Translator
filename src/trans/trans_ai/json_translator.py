import asyncio
import json
import os
import re
from src.trans.trans_ai_utils import get_japanese_ratio
import src.down.down as down
from .config import ForceStopException
from .model_worker import _create_model_workers
from .chunk_utils import _is_stopped
from .pipeline import TranslationItem, run_translation_batch


def _parse_json_title_metadata(title):
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

    return restored_book_title, author, episode, restored_name


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

    items = []
    for pos, chunk_idx in enumerate(chunk_indices, 1):
        display_idx = chunk_idx + 1
        trans_text = data.get(str(chunk_idx))
        orig_text = data.get(f"{chunk_idx}-j")
        if orig_text is None and trans_text is not None:
            orig_text = trans_text

        need_translate = False
        source_to_use = orig_text if orig_text else trans_text

        if not trans_text or str(trans_text).startswith('[번역 실패'):
            need_translate = True
        else:
            jp_ratio = get_japanese_ratio(str(trans_text))
            if jp_ratio >= 0.1:
                need_translate = True

        if need_translate:
            clean_source = str(source_to_use or '').replace("%'%", '"').replace('\\\n', '\n')
            jp_ratio_orig = get_japanese_ratio(clean_source)
            log_msg = f'[{pos}/{len(chunk_indices)}] [{workers[0].model_name}] 원문 번역 실행 (인덱스 {chunk_idx}, 원문 일어 비율 {jp_ratio_orig:.2f}%)'
            items.append(TranslationItem(
                idx=display_idx,
                source_text=clean_source,
                orig_text=orig_text,
                check_disk_cache=False,
                on_error='json',
                log_extra=log_msg
            ))
        else:
            clean_trans = str(trans_text).replace("%'%", '"').replace('\\\n', '\n')
            items.append(TranslationItem(
                idx=display_idx,
                source_text=None,
                orig_text=orig_text,
                pre_translated=clean_trans,
                check_disk_cache=False,
                on_error='json'
            ))

    restored_book_title, author, episode, restored_name = _parse_json_title_metadata(title)
    out = down.downin.base_data.OUTFOLDER + '/'
    safe_title = re.sub(r'[\\/:*?"<>|]', '_', restored_book_title).strip()
    save_path = f'{out}trs\\save_{safe_title}_{max_chars}_복원.json'

    raw_txt_info = None
    if raw:
        os.makedirs(f'{out}epub', exist_ok=True)
        os.makedirs(f'{out}epub\\raw_txt', exist_ok=True)
        txt_path = f'{out}epub\\raw_txt\\{safe_title}.txt'
        r_title = f'''{restored_book_title}
{author}
(raw)
{'+---+\n'}{restored_book_title} | {author}

'''
        raw_txt_info = (txt_path, r_title)

    def build_epub_text(final_result):
        if raw:
            raw_header = [restored_book_title, author, '(raw)']
            if episode:
                raw_header.append(episode)
            return '\n'.join(raw_header) + f'\n{"+---+\n"}{final_result}'
        else:
            normal_header = [f'{restored_book_title}_번역']
            if author:
                normal_header.append(author)
            if episode:
                normal_header.append(episode)
            return '\n'.join(normal_header) + f'\n{"+---+\n"}{final_result}'

    return await run_translation_batch(
        items=items,
        workers=workers,
        title=restored_book_title,
        max_chars=max_chars,
        json_path=save_path,
        json_title=restored_name,
        raw=raw,
        dicts=dicts,
        check=check,
        check_i=check_i,
        progress_callback=progress_callback,
        log_callback=log_callback,
        raw_txt_info=raw_txt_info,
        epub_text_builder=build_epub_text
    )


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