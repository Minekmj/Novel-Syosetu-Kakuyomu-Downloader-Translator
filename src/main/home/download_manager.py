import re
from collections import deque
from datetime import datetime
from PySide6.QtWidgets import QMessageBox
import src.down.down as down
from src.system.data import open_folder, save_data, load_data
import src.main.thread_pyqt as thread_pyqt
from .custom_widgets import ThreadProgressBridge

class DownloadManager:
    def __init__(self, window, bottom_bar):
        self.window = window
        self.bottom_bar = bottom_bar
        self.queue = deque()
        self.current_task = None
        self.current_thread = None
        self.progress_bridge = None

    def add_task(self, task):
        row_widget = task.get("row_widget")
        if row_widget:
            row_widget.set_download_state("대기", False)
        self.queue.append(task)
        self.update_ui()
        if self.current_task is None:
            self.process_next()

    def process_next(self):
        if not self.queue:
            self.current_task = None
            self.bottom_bar.hide()
            return

        self.current_task = self.queue.popleft()
        task = self.current_task

        site_url = task["site_url"]
        start = task["start"]
        end = task["end"]
        title_text = task["title_text"]
        act_massage = task["act_massage"]
        row_widget = task["row_widget"]
        raw_title = task["raw_title"]

        if row_widget:
            row_widget.set_download_state("다운 중...", False)

        self.bottom_bar.set_task_info(title_text, start, end)
        self.bottom_bar.show()
        self.update_ui()

        self.progress_bridge = ThreadProgressBridge()
        self.progress_bridge.progress_updated.connect(self.on_progress)

        self.current_thread = thread_pyqt.DownloadThread(
            site_url, start, end, self.progress_bridge, title_text, act_massage, raw_title
        )
        self.current_thread.finished_signal.connect(
            lambda success, err_msg: self.on_finished(success, err_msg, task)
        )
        self.current_thread.start()

    def on_progress(self, text):
        match = re.search(r"(\d+(\.\d+)?)%", text)
        val = int(float(match.group(1))) if match else None
        self.bottom_bar.update_progress(text, val)

    def on_finished(self, success, err_msg, task):
        start = task["start"]
        end = task["end"]
        title_text = task["title_text"]
        row_widget = task["row_widget"]

        if row_widget:
            row_widget.set_download_state("다운로드", True)

        if success:
            nums = [int(v) for v in [start, end] if str(v).isdigit()]
            now_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if nums:
                max_num = max(nums)
                data = load_data()
                if title_text in data.get("list", {}):
                    data["list"][title_text]["down"] = str(max_num)
                    data["list"][title_text]["down_time"] = now_time_str
                    save_data(data)

            if row_widget:
                row_widget.update_download_info(end, now_time_str)

            target_folder = down.downin.base_data.OUTFOLDER
            open_folder(target_folder if (target_folder.endswith("\\") or target_folder.endswith("/")) else (target_folder + "/"))
        else:
            QMessageBox.critical(self.window, "오류", f"[{title_text}] 다운로드 실패:\n{err_msg}")

        self.current_task = None
        self.process_next()

    def remove_tasks_by_widget(self, row_widget):
        self.queue = deque([t for t in self.queue if t.get("row_widget") != row_widget])
        self.update_ui()

    def update_ui(self):
        queue_count = len(self.queue)
        self.bottom_bar.update_queue_count(queue_count)
        if queue_count > 0 or self.current_task is not None:
            self.bottom_bar.show()
        else:
            self.bottom_bar.hide()