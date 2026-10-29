from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel
)
from PySide6.QtCore import Qt
import src.main.thread_pyqt as thread_pyqt

class EditTitleDialog(QDialog):
    def __init__(self, current_title, parent=None):
        super().__init__(parent)
        self.setWindowTitle("제목 수정")
        self.setFixedSize(800, 140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.title_edit = QLineEdit(self)
        self.title_edit.setText(current_title)
        self.title_edit.setSelection(0, len(current_title))
        layout.addWidget(self.title_edit)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        cancel_btn = QPushButton("취소", self)
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("저장", self)
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def get_new_title(self):
        return self.title_edit.text().strip()

class EditTitleRawDialog(QDialog):
    def __init__(self, current_title, parent=None):
        super().__init__(parent)
        self.setWindowTitle("제목 수정 - 원본")
        self.setFixedSize(800, 190)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.title_edit = QLineEdit(self)
        self.title_edit.setText(current_title)
        self.title_edit.setSelection(0, len(current_title))
        layout.addWidget(self.title_edit)

        info = QLabel(
            "작품의 일본어 제목을 수정하는 것으로, 원문 제목 다운로드 시 제목을 변경 하고 싶거나\n"
            "백업 또는 원문 제목 다운로드 시 경로 문제가 생기는 경우 변경하십시오.\n"
            "변경 시 백업 폴더가 다르게 되어 백업이 달라집니다."
        )
        layout.addWidget(info)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        cancel_btn = QPushButton("취소", self)
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("저장", self)
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def get_new_title(self):
        return self.title_edit.text().strip()

class EditActDialog(QDialog):
    def __init__(self, current_massage, parent=None):
        super().__init__(parent)
        self.setWindowTitle("작가의 말 트리거 수정")
        self.setFixedSize(630, 180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.massage_edit = QLineEdit(self)
        self.massage_edit.setText(current_massage)
        self.massage_edit.setSelection(0, len(current_massage))
        layout.addWidget(self.massage_edit)

        label = QLabel(
            "카쿠요무에서 작가의 말을 구분하는 텍스트를 찾아 붙여 넣으세요.\n"
            "이는 백업 텍스트에는 반영되지 않으며, 작품 다운로드로 인한 다운로드에서 이 트리거 이후의 글자를 제외합니다."
        )
        label.setObjectName("lbl_original_title")
        layout.addWidget(label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        cancel_btn = QPushButton("취소", self)
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("저장", self)
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def get_new_massage(self):
        return self.massage_edit.text().strip()

class DownloadDetailDialog(QDialog):
    def __init__(self, site_url, title_text, last_down, parent, now_s, act_massage, row_widget, raw_title, main_window):
        super().__init__(parent)
        self.site_url = site_url
        self.title_text = title_text
        self.last_down = last_down
        self.now_state = now_s
        self.row_widget = row_widget
        self.main_window = main_window
        self.now_res = ""
        self.act_massage = act_massage
        self.title_raw_text = raw_title

        self.setWindowTitle("다운로드 설정")
        self.setFixedSize(360, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(self.title_text, self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("title")
        title.setWordWrap(True)
        layout.addWidget(title)

        self.new_lbl = QLabel("확인 중...", self)
        self.new_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.new_lbl.setObjectName("nex_lbl")
        layout.addWidget(self.new_lbl)

        range_layout = QHBoxLayout()
        range_layout.setSpacing(8)

        self.start_edit = QLineEdit(self)
        self.start_edit.setPlaceholderText("시작")
        self.start_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.last_down:
            self.start_edit.setText(str(int(self.last_down) + 1))

        tilde = QLabel("-", self)
        tilde.setObjectName("tilde")
        tilde.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.end_edit = QLineEdit(self)
        self.end_edit.setPlaceholderText("끝")
        self.end_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        range_layout.addWidget(self.start_edit)
        range_layout.addWidget(tilde)
        range_layout.addWidget(self.end_edit)
        layout.addLayout(range_layout)

        layout.addStretch()

        self.down_btn = QPushButton("다운로드 대기열 추가", self)
        self.down_btn.setObjectName("primaryBtn")
        self.down_btn.setFixedHeight(40)
        self.down_btn.clicked.connect(self.enqueue_and_close)
        layout.addWidget(self.down_btn)

        if self.now_state == "-":
            self.start_async_fetch()
        else:
            self.new_lbl.setText(f"최신: {self.now_state}화")
            self.now_res = self.now_state
            if not self.end_edit.text():
                self.end_edit.setText(self.now_res)

    def start_async_fetch(self):
        self.worker = thread_pyqt.FetchNewNumberWorker(self.site_url)
        self.worker.finished.connect(self.update_new_label)
        self.worker.start()

    def update_new_label(self, result_text):
        self.new_lbl.setText(f"최신: {result_text[0]}화")
        self.now_res = str(result_text[0])
        if not self.end_edit.text():
            self.end_edit.setText(self.now_res)

    def enqueue_and_close(self):
        start = self.start_edit.text().strip()
        end = self.end_edit.text().strip()

        if not start or not end:
            return

        if self.now_res.isdigit():
            if int(start) > int(self.now_res):
                start = self.now_res
            if int(end) > int(self.now_res):
                end = self.now_res

        if int(end) < int(start):
            end = start

        task = {
            "site_url": self.site_url,
            "title_text": self.title_text,
            "start": start,
            "end": end,
            "act_massage": self.act_massage,
            "raw_title": self.title_raw_text,
            "row_widget": self.row_widget
        }
        self.main_window.add_download_task(task)
        self.accept()