import concurrent.futures
import sys
import traceback
from PySide6.QtCore import QThread, Signal
from .constants import WORD_TOKEN_PATTERN, JP_PATTERN
from .text_cleaner import clean_explanation_residue, strip_korean_particles
from .translator import smart_translate


class GlossaryExtractWorker(QThread):
    extracted_signal = Signal(list)

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items

    def run(self):
        word_freq = {}
        for item in self.items:
            text = item.get('original_text', '').strip()
            if not text:
                continue

            text = clean_explanation_residue(text)
            tokens = WORD_TOKEN_PATTERN.findall(text)
            for tok in tokens:
                tok = tok.strip()
                if not JP_PATTERN.search(tok):
                    continue
                tok = strip_korean_particles(tok)
                if len(tok) >= 2 and JP_PATTERN.search(tok):
                    word_freq[tok] = word_freq.get(tok, 0) + 1

        candidates = [word for word, count in word_freq.items() if count >= 2]
        candidates.sort(key=lambda k: word_freq[k], reverse=True)
        self.extracted_signal.emit(candidates)


class JapaneseTranslateWorker(QThread):
    item_translated = Signal(int, str)
    progress_changed = Signal(int, int)
    finished_signal = Signal()

    def __init__(self, tasks, glossary=None, is_word_mode=False, parent=None):
        super().__init__(parent)
        self.tasks = tasks
        self.glossary = glossary or {}
        self.is_word_mode = is_word_mode
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        total = len(self.tasks)
        done = 0
        print(f"\n=======================================================")
        print(f"[DEBUG Thread] 번역 시작: 총 {total}개 작업 (단어모드={self.is_word_mode})")
        print(f"=======================================================")

        def worker_task(task_item):
            if self._is_cancelled:
                return task_item[0], None
            idx, text = task_item
            try:
                result = smart_translate(text, glossary=self.glossary, is_word_mode=self.is_word_mode)
                return idx, result
            except Exception as e:
                print(f"[ERROR Thread] 작업 #{idx} 실패! 텍스트={text!r}, 오류={e}", file=sys.stderr)
                traceback.print_exc()
                return idx, text

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_idx = {
                executor.submit(worker_task, task): task[0]
                for task in self.tasks
            }
            for future in concurrent.futures.as_completed(future_to_idx):
                if self._is_cancelled:
                    break
                try:
                    idx, res = future.result()
                    if res is not None and not self._is_cancelled:
                        self.item_translated.emit(idx, res)
                except Exception as e:
                    print(f"[ERROR Thread] Future 수신 오류: {e}", file=sys.stderr)
                    traceback.print_exc()
                done += 1
                self.progress_changed.emit(done, total)

        print(f"[DEBUG Thread] 모든 번역 작업 완료.")
        self.finished_signal.emit()