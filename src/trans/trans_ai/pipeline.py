import asyncio
import os
import src.down.down as down
from src.trans.prompt_sanitizer import get_safety_settings
from src.trans.trans_ai_utils import save_translation_json, save_translation_txt
from .config import ForceStopException
from .chunk_utils import _is_stopped, prepare_output_paths
from .chunk_translator import translate_chunk_safe_async
from .runner import run_worker_pool


class TranslationItem:
    def __init__(self, idx, source_text=None, orig_text=None, pre_translated=None, check_disk_cache=False, on_error='novel', log_extra=None):
        self.idx = idx
        self.source_text = source_text
        self.orig_text = orig_text if orig_text is not None else (source_text or '')
        self.pre_translated = pre_translated
        self.check_disk_cache = check_disk_cache
        self.on_error = on_error
        self.log_extra = log_extra


async def run_translation_batch(
    items,
    workers,
    title,
    max_chars,
    json_path,
    json_title,
    raw=False,
    dicts=None,
    check=None,
    check_i=None,
    progress_callback=None,
    log_callback=None,
    raw_txt_info=None,
    epub_text_builder=None
):
    out, safe, ai_dir = prepare_output_paths(title, max_chars)
    safety_settings = get_safety_settings()

    translated_parts = [None] * len(items)
    original_chunks = [None] * len(items)
    queue = asyncio.Queue()

    for pos, item in enumerate(items):
        await queue.put((pos, item))

    completed_count = 0
    ignored = False
    lock = asyncio.Lock()
    total_items = len(items)

    async def process_item(pos, item, worker):
        nonlocal completed_count, ignored
        if _is_stopped(check, check_i):
            if log_callback and not (check_i and check_i()):
                log_callback(f'[{item.idx}/{total_items}] [{worker.model_name}] 중지: 대기 중인 청크 건너뜀')
            return

        file_path = f'{ai_dir}/{item.idx}.txt'

        if item.check_disk_cache and os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    saved_text = f.read()
                if saved_text and not saved_text.startswith('[번역 실패'):
                    skip_msg = f'[{item.idx}/{total_items}] [{worker.model_name}] 이미 저장된 파일 존재 → 건너뜀'
                    if log_callback and not (check_i and check_i()):
                        log_callback(skip_msg)
                    async with lock:
                        translated_parts[pos] = saved_text
                        original_chunks[pos] = item.orig_text
                        completed_count += 1
                        if progress_callback and not (check_i and check_i()):
                            progress_callback(completed_count, total_items, f'{completed_count}/{total_items} 청크 완료')
                    return
            except Exception:
                pass

        result_ignore_back = False
        try:
            if _is_stopped(check, check_i):
                if log_callback and not (check_i and check_i()):
                    log_callback(f'[{item.idx}/{total_items}] [{worker.model_name}] 실행 대기 중 청크 건너뜀')
                return

            if item.pre_translated is not None:
                if log_callback and not (check_i and check_i()):
                    log_callback(f'[{item.idx}/{total_items}] [{worker.model_name}] 기존 번역 청크 통과 (인덱스 {item.idx - 1})')
                result_text = item.pre_translated
            else:
                if item.log_extra and log_callback and not (check_i and check_i()):
                    log_callback(item.log_extra)

                result_text, result_lines, result_ignore = await translate_chunk_safe_async(
                    chunk=item.source_text,
                    model_name=worker.model_name,
                    safety_settings=safety_settings,
                    rate_limiter=worker.rate_limiter,
                    temperature=worker.temperature,
                    log_callback=log_callback,
                    chunk_idx=item.idx,
                    raw=raw,
                    dicts=dicts or {},
                    check=check,
                    check_i=check_i,
                    br_start=worker.br_start,
                    isno_x=worker.isno_x,
                    thinking_budget=worker.thinking_budget
                )

                if result_ignore or result_text is None or _is_stopped(check, check_i):
                    result_ignore_back = True
                    async with lock:
                        ignored = True
                    return

            _is_stopped(check, check_i)

            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result_text)
            except Exception as save_err:
                if log_callback and not (check_i and check_i()):
                    log_callback(f'[{item.idx}번 청크] 파일 저장 실패: {save_err}')

            async with lock:
                translated_parts[pos] = result_text
                original_chunks[pos] = item.orig_text

            if _is_stopped(check, check_i):
                result_ignore_back = True
                async with lock:
                    ignored = True
                return

            if item.pre_translated is None and log_callback and not (check_i and check_i()):
                log_callback(f'[{item.idx}/{total_items}] [{worker.model_name}] 청크 번역 완료: 성공')

        except (ForceStopException, asyncio.CancelledError):
            result_ignore_back = True
            raise ForceStopException()
        except Exception as e:
            if log_callback and not (check_i and check_i()):
                log_callback(f' └ [{item.idx}번 청크] [{worker.model_name}] 번역 최종 실패: {e}')

            if item.on_error == 'novel':
                err_text = f'''
+---+

[번역 실패: {item.idx}번째 청크]

error+---+

error 청크 next

'''
                async with lock:
                    translated_parts[pos] = err_text
                    original_chunks[pos] = item.orig_text

                try:
                    error_path = f'{ai_dir}/{item.idx}_error.txt'
                    with open(error_path, 'w', encoding='utf-8') as f:
                        f.write(item.source_text)
                except Exception:
                    pass
            else:
                result_text = item.source_text
                try:
                    with open(file_path, 'w', encoding='utf-8') as f_out:
                        f_out.write(result_text)
                except Exception:
                    pass
                async with lock:
                    translated_parts[pos] = result_text
                    original_chunks[pos] = item.orig_text

        finally:
            if check_i and check_i():
                result_ignore_back = True

            if not result_ignore_back and not (check_i and check_i()):
                async with lock:
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, total_items, f'{completed_count}/{total_items} 청크 완료')

    async def model_worker(worker, worker_number):
        while True:
            if _is_stopped(check, check_i):
                return
            try:
                pos, item = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                await process_item(pos, item, worker)
            finally:
                queue.task_done()

    await run_worker_pool(workers, model_worker, check_i)

    _is_stopped(check, check_i)

    try:
        first_br = workers[0].br_start if workers else 0
        first_tb = workers[0].thinking_budget if workers else None
        save_translation_json(
            translated_parts, original_chunks, max_chars, json_title, json_path,
            raw=raw, br_start=first_br, thinking_budget=first_tb
        )
    except Exception as e:
        if log_callback and not (check_i and check_i()):
            log_callback(f'JSON 저장 실패: {e}')

    if ignored or _is_stopped(check, check_i):
        if epub_text_builder and log_callback and not (check_i and check_i()):
            log_callback('JSON 복원 중지됨 → EPUB 변환은 생략합니다.')
        return 'ignore'

    final_result = '\n\n'.join(p for p in translated_parts if p)

    if raw and raw_txt_info:
        txt_path, r_title = raw_txt_info
        _is_stopped(check, check_i)
        if not _is_stopped(check, check_i):
            save_translation_txt(translated_parts, r_title, txt_path)

    if epub_text_builder:
        epub_text = epub_text_builder(final_result)
        _is_stopped(check, check_i)
        if not _is_stopped(check, check_i):
            down.create_epub_from_merged_txt(txt_value=epub_text, RAW=raw)

    return final_result