from .text_cleaner import has_japanese
from .workers import JapaneseTranslateWorker
from src.trans.trans_ai_utils import apply_japanese_corrections
from PySide6.QtCore import QEventLoop

def JapaneseCheckCode(inspection_data: dict, log_data=None) -> bool:
    if log_data is None:
        log_data = print

    json_path = inspection_data.get('json_path', '')
    raw_items = inspection_data.get('items', [])

    log_data("일본어 검출 항목 필터링 중...")

    items = [
        item for item in raw_items
        if has_japanese(item.get('original_text', ''))
    ]

    if not items:
        log_data("일본어가 검출된 항목 없음")
        return True

    log_data(f"총 {len(items)}개 항목에서 일본어가 검출")

    tasks = []
    for idx, item in enumerate(items):
        orig_text = item.get('original_text', '').strip()
        tasks.append((idx, orig_text))

    translated_results = {}
    loop = QEventLoop()

    worker = JapaneseTranslateWorker(tasks, glossary={}, is_word_mode=False)

    def on_item_translated(idx: int, result_text: str):
        translated_results[idx] = result_text

    def on_progress_changed(done: int, total: int):
        percent = (done / total) * 100 if total > 0 else 0
        log_data(f"변환 진행 중: {done}/{total} ({percent:.1f}%)")

    worker.item_translated.connect(on_item_translated)
    worker.progress_changed.connect(on_progress_changed)
    worker.finished_signal.connect(loop.quit)

    worker.start()
    loop.exec()
    worker.wait()

    log_data("전체 번역 완료")

    corrections = []
    for idx, item in enumerate(items):
        orig = item.get('original_text', '')
        new_text = translated_results.get(idx, orig.rstrip('\n'))

        if orig.endswith('\n') and not new_text.endswith('\n'):
            new_text += '\n'

        corrections.append({
            'chunk_key': item['chunk_key'],
            'start_line': item['start_line'],
            'end_line': item['end_line'],
            'new_text': new_text
        })

    try:
        log_data(f"파일({json_path})에 변경 사항 적용 중...")
        success, count, err = apply_japanese_corrections(json_path, corrections)
        
        if success:
            log_data(f"총 {count}개의 검출 블록이 성공적으로 수정 및 저장")
            return True
        else:
            log_data(f"저장 실패: {err}")
            return False
            
    except Exception as e:
        log_data(f"저장 중 예외 발생: {str(e)}")
        return False