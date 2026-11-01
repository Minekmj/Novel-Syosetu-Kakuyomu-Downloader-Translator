import os
import re
import threading
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal
from src.ai import AiRoute, AiTarget
import src.find.findsyou as findsyou
from src.recommend.suggestion import NovelRecommender
from src.trans.trans import Translator
import src.trans.trans_ai as trans_ai

DOWN = None
STOP_CLICK = False


class ClickWatcher(QObject):
    update_address = Signal(str)
    add_address = Signal()

    def __init__(self):
        super().__init__()
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while not self.stop_event.is_set():
            if STOP_CLICK:
                break
            if findsyou.detail_ui.click:
                url = findsyou.detail_ui.click_plus_url
                findsyou.detail_ui.click = False
                self.update_address.emit(url)
                self.add_address.emit()
            self.stop_event.wait(0.05)

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive() and threading.current_thread() is not self.thread:
            self.thread.join(timeout=1)
        self.thread = None


class DownloadThread(QThread):
    finished_signal = Signal(bool, str)

    def __init__(self, site_url, start, end, label, title, act_massage, raw_title):
        super().__init__()
        self.site_url = site_url
        self.start_num = start
        self.end_num = end
        self.label = label
        self.title = title
        self.act_massage = act_massage
        self.raw_title = raw_title

    def run(self):
        try:
            DOWN.downin.Download(self.site_url, self.start_num, self.end_num, self.label, self.title, self.raw_title, self.act_massage)
            self.finished_signal.emit(True, "")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class EpubConvertThread(QThread):
    finished_signal = Signal(bool, str, str)

    def __init__(self, txt_paths):
        super().__init__()
        self.txt_paths = txt_paths

    def run(self):
        try:
            for path in self.txt_paths:
                DOWN.create_epub_from_merged_txt(path)

            output_dir = os.path.join(DOWN.downin.base_data.OUTFOLDER, "epub")
            self.finished_signal.emit(True, "EPUB 변환이 완료되었습니다.", output_dir)
        except Exception as e:
            self.finished_signal.emit(False, str(e), "")


class FetchNewNumberWorker(QThread):
    finished = Signal(tuple)
    _semaphore = threading.Semaphore(10)

    def __init__(self, site_url, use_have=False):
        super().__init__()
        self.site_url = site_url
        self.use_have = use_have

    def run(self):
        try:
            with FetchNewNumberWorker._semaphore:
                if self.use_have:
                    num, time = DOWN.downin.new_number(self.site_url, True)
                    self.finished.emit((str(num), time))
                else:
                    num = DOWN.downin.new_number(self.site_url)
                    self.finished.emit((str(num), ""))
        except Exception:
            self.finished.emit(("오류", ""))


class TranslateThread(QThread):
    progress_changed = Signal(int, int, str)
    log_changed = Signal(str)
    finished_signal = Signal(bool, str, str)

    def __init__(
        self,
        file_path,
        model_name,
        rpm,
        temperature,
        max_concurrent,
        max_chars,
        dicts,
        check,
        check_i,
        br_start,
        isno_x,
        thinking_budget=None,
        ai_target=None
    ):
        super().__init__()
        self.file_path = file_path
        self.model_name = model_name
        self.rpm = rpm
        self.temperature = temperature
        self.max_concurrent = max_concurrent
        self.max_chars = max_chars
        self.dict = dicts
        self.check = check
        self.check_i = check_i
        self.br_start = br_start
        self.isno_x = isno_x
        self.thinking_budget = thinking_budget
        self.ai_target = ai_target

    def run(self):
        try:
            def progress(done, total, message):
                self.progress_changed.emit(done, total, message)
                self.log_changed.emit(message)

            self.log_changed.emit("=" * 60)
            self.log_changed.emit(f"파일: {self.file_path}")
            self.log_changed.emit(f"모델: {self.model_name}")
            self.log_changed.emit(f"RPM: {self.rpm}")
            self.log_changed.emit(f"Temperature: {self.temperature}")
            self.log_changed.emit(f"동시 작업수: {self.max_concurrent}")
            self.log_changed.emit(f"청크 글자수: {self.max_chars}")
            self.log_changed.emit(f"추론: {self.thinking_budget}")
            self.log_changed.emit("번역 작업 시작")
            self.log_changed.emit("=" * 60)

            if self.file_path.lower().endswith(".json"):
                self.log_changed.emit("JSON 파일 감지 → 복원/재번역 모드")

                trans_ai.TransAi_From_Json(
                    self.file_path,
                    model_name=self.model_name,
                    rpm=self.rpm,
                    temperature=self.temperature,
                    max_concurrent=self.max_concurrent,
                    progress_callback=progress,
                    log_callback=self.log_changed.emit,
                    dicts=self.dict,
                    check=self.check,
                    check_i=self.check_i,
                    br_start=self.br_start,
                    isno_x=self.isno_x,
                    thinking_budget=self.thinking_budget,
                    ai_target=self.ai_target
                )

            else:
                self.log_changed.emit("TXT 파일 감지 → 전체 번역 모드")

                with open(self.file_path, "r", encoding="utf-8") as f:
                    text = f.read()

                first_line = text.splitlines()[0].strip() if text.splitlines() else ""
                if first_line and set(first_line) == {"="}:
                    filepath = self.file_path
                    ff = os.path.basename(os.path.dirname(filepath))
                    filename = os.path.splitext(os.path.basename(filepath))[0]
                    if filename.startswith("["):
                        s = re.sub(r"^\[.*?[\]\"'\)]\s*", "", filename)
                    else:
                        s = filename
                    result = f"{ff}\n{s}\n(raw)\n+---+\n"
                    text = result + text

                trans_ai.TransAi_All(
                    text,
                    max_chars=self.max_chars,
                    model_name=self.model_name,
                    rpm=self.rpm,
                    temperature=self.temperature,
                    max_concurrent=self.max_concurrent,
                    progress_callback=progress,
                    log_callback=self.log_changed.emit,
                    dicts=self.dict,
                    check=self.check,
                    check_i=self.check_i,
                    br_start=self.br_start,
                    isno_x=self.isno_x,
                    thinking_budget=self.thinking_budget,
                    ai_target=self.ai_target
                )

            if not self.check():
                output_dir = os.path.join(DOWN.downin.base_data.OUTFOLDER, "epub")
                self.log_changed.emit("=" * 60)
                self.log_changed.emit("번역 완료")
                self.log_changed.emit(f"출력 폴더: {output_dir}")
                self.log_changed.emit("=" * 60)
                self.finished_signal.emit(True, "번역이 완료되었습니다.", output_dir)
            else:
                self.log_changed.emit("=" * 60)
                self.log_changed.emit("번역 중지")
                self.log_changed.emit("=" * 60)
                self.finished_signal.emit(False, "번역이 중지 되었습니다.", "")

        except Exception as e:
            import traceback
            error_text = traceback.format_exc()
            self.log_changed.emit("=" * 60)
            self.log_changed.emit("번역 중 오류 발생")
            self.log_changed.emit(error_text)
            self.log_changed.emit("=" * 60)
            self.finished_signal.emit(False, str(e), "")


class ModelLoadThread(QThread):
    finished = Signal(list, str)

    def __init__(self, api_key: str, ai_target: Optional[int] = None):
        super().__init__()
        self.api_key = api_key
        self.ai_target = ai_target

    def run(self):
        try:
            model_names = AiRoute.fetch_models(api_key=self.api_key, target=self.ai_target)
            self.finished.emit(model_names, "")
        except Exception as e:
            self.finished.emit([], str(e))


class GlossaryExtractThread(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(dict, str)

    def __init__(self, all_text, paserent, chunk, model, rpm, parent=None, ai_target=None):
        super().__init__(parent)
        self.all_text = all_text
        self.paserent = paserent
        self.chunk = chunk
        self.model = model
        self.rpm = rpm
        self.ai_target = ai_target

    def run(self):
        try:
            def log_callback(text):
                self.log_signal.emit(str(text))

            self.log_signal.emit(
                f"AI 용어집 분석 시작 / 분석 비율: {self.paserent}% / 청크: {self.chunk}"
            )

            result = trans_ai.extract_glossary(
                self.all_text,
                paserent=self.paserent,
                chunk=self.chunk,
                log_callback=log_callback,
                model=self.model,
                RPM=self.rpm,
                ai_target=self.ai_target
            )

            if not isinstance(result, dict):
                result = {}

            self.finished_signal.emit(result, "")

        except Exception as e:
            self.finished_signal.emit({}, str(e))


class TitleTranslateWorker(QThread):
    finished = Signal(str)

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def run(self):
        try:
            res = Translator(self.text, True)
            self.finished.emit(res)
        except Exception:
            self.finished.emit(self.text)


class RecommendWorker(QThread):
    log_signal = Signal(str, str)
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(
        self,
        api_key: str,
        model: str,
        condition: str,
        top_k: int,
        user_data: dict,
        ai_target: Optional[int] = None
    ):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.condition = condition
        self.top_k = top_k
        self.user_data = user_data
        self.ai_target = ai_target

    def run(self):
        try:
            if NovelRecommender is None:
                raise RuntimeError("NovelRecommender 모듈을 찾을 수 없습니다.")

            def log_callback(l_type: str, text: str):
                self.log_signal.emit(l_type, str(text))

            recommender = NovelRecommender(
                api_key=self.api_key,
                model=self.model,
                user_data=self.user_data,
                log=log_callback,
                ai_target=self.ai_target
            )

            result = recommender.run_recommendation(
                top_k=self.top_k,
                user_custom_prompt=self.condition
            )
            self.finished_signal.emit(result)

        except Exception as e:
            self.error_signal.emit(str(e))