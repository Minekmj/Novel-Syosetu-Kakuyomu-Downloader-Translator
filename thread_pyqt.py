import trans_ai
from PySide6.QtCore import QThread, Signal
import findsyou
import time
import os
from google import genai

DOWN = None;

class ClickWatcher(QThread):
    update_address = Signal(str)
    add_address = Signal()

    def run(self):
        while True:
            if findsyou.click:
                url = findsyou.click_plus_url
                findsyou.click = False

                self.update_address.emit(url)
                self.add_address.emit()
            time.sleep(0.05)

class DownloadThread(QThread):
    finished_signal = Signal(bool, str)

    def __init__(self, site_url, start, end, label, title):
        super().__init__()
        self.site_url = site_url
        self.start_num = start
        self.end_num = end
        self.label = label
        self.title = title

    def run(self):
        try:
            DOWN.downin.Download(self.site_url, self.start_num, self.end_num, self.label, self.title)
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
               
                DOWN.create_epub_from_merged_txt(path, )
            
            output_dir = getattr(DOWN.downin, 'OUTFOLDER', '')
            if not output_dir and self.txt_paths:
                output_dir = os.path.dirname(self.txt_paths[0])

            self.finished_signal.emit(True, "EPUB 변환이 완료되었습니다.", output_dir)
        except Exception as e:
            self.finished_signal.emit(False, str(e), "")

class FetchNewNumberWorker(QThread):
    finished = Signal(str)

    def __init__(self, site_url):
        super().__init__()
        self.site_url = site_url

    def run(self):
        try:
            num = DOWN.downin.new_number(self.site_url)
            self.finished.emit(str(num))
        except Exception:
            self.finished.emit("오류")
            
class TranslateThread(QThread):
    progress_changed = Signal(int, int, str)
    log_changed = Signal(str)
    finished_signal = Signal(bool, str, str)

    def __init__(self, file_path, model_name, rpm, temperature, max_concurrent, max_chars):
        super().__init__()

        self.file_path = file_path
        self.model_name = model_name
        self.rpm = rpm
        self.temperature = temperature
        self.max_concurrent = max_concurrent
        self.max_chars = max_chars

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
                    log_callback=self.log_changed.emit
                )

            else:
                self.log_changed.emit("TXT 파일 감지 → 전체 번역 모드")

                with open(self.file_path, "r", encoding="utf-8") as f:
                    text = f.read()

                trans_ai.TransAi_All(
                    text,
                    max_chars=self.max_chars,
                    model_name=self.model_name,
                    rpm=self.rpm,
                    temperature=self.temperature,
                    max_concurrent=self.max_concurrent,
                    progress_callback=progress,
                    log_callback=self.log_changed.emit
                )

            output_dir = getattr(DOWN.downin, "OUTFOLDER", "./out/")

            self.log_changed.emit("=" * 60)
            self.log_changed.emit("번역 완료")
            self.log_changed.emit(f"출력 폴더: {output_dir}")
            self.log_changed.emit("=" * 60)

            self.finished_signal.emit(
                True,
                "번역이 완료되었습니다.",
                output_dir
            )

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

    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key

    def run(self):
        try:
            client = genai.Client(api_key=self.api_key)
            models = client.models.list()
            model_names = []
            
            for model in models:
                name = getattr(model, "name", "")
                if not name:
                    continue
                
                if name.startswith("models/"):
                    name = name.replace("models/", "", 1)
                
               
                if not name.lower().startswith("gemini"):
                    continue
                    
               
                exclude_keywords = [
                    "embedding", "robotics", "tts", "audio", "image", 
                    "omni", "computer-use", "customtools", "live", "transcribe"
                ]
                if any(keyword in name.lower() for keyword in exclude_keywords):
                    continue

               
                supported_methods = getattr(model, "supported_generation_methods", None)
                if supported_methods and "generateContent" not in supported_methods:
                    continue
                
                model_names.append(name)
            self.finished.emit(sorted(set(model_names)), "")
        except Exception as e:
            self.finished.emit([], str(e))