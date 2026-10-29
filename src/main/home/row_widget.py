import webbrowser
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QMenu,
    QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

import src.down.down as down
from src.system.data import load_data, save_data
import src.main.thread_pyqt as thread_pyqt
from .dialogs import EditTitleDialog, EditTitleRawDialog, EditActDialog, DownloadDetailDialog

class AddressRowWidget(QWidget):
    status_updated = Signal()
    fetch_finished = Signal()

    def __init__(self, site_url, title_text=None, parent=None, last="0", down_time="0", act_massage="", title_raw_text="", main_window=None):
        super().__init__(parent)
        self.site_url = site_url
        self.main_window = main_window
        self.last = "0" if last == "" else last
        self.down_time = "0" if not down_time else down_time
        self.now = "-"
        self.time = ""
        self.act_massage = act_massage
        self.is_loading = False

        self.title_raw_text = title_raw_text
        self.is_empty = not site_url

        if self.is_empty:
            self.title_text = ""
        elif title_text:
            self.title_text = title_text
        else:
            try:
                self.title_text = down.downin.CheckTitle(self.site_url)
            except Exception:
                self.title_text = "제목을 가져올 수 없습니다"

        self.init_ui()

    def init_ui(self):
        self.main_frame = QFrame()
        self.main_frame.setObjectName("CardFrame")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 2, 0, 2)
        main_layout.addWidget(self.main_frame)

        if self.is_empty:
            card_layout = QVBoxLayout(self.main_frame)
            card_layout.setContentsMargins(20, 24, 20, 24)
            card_layout.setSpacing(6)
            card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            welcome_lbl = QLabel("처음 오셨나요?")
            welcome_lbl.setObjectName("title_lbl")
            welcome_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            guide_lbl = QLabel("URL을 입력하여 직접 추가하시거나\n작품을 검색해서 추가하여 당신만의 목록을 만드세요!")
            guide_lbl.setObjectName("url_lbl")
            guide_lbl.setWordWrap(True)
            guide_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            guide_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            guide_lbl.setMinimumWidth(0)
            guide_lbl.setStyleSheet("""
                                    font-size: 13px;
                                    font-weight: 570;
                                    """)

            card_layout.addWidget(welcome_lbl)
            card_layout.addWidget(guide_lbl)
            return

        card_layout = QHBoxLayout(self.main_frame)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(16)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_lbl = QLabel(self.title_text)
        self.title_lbl.setObjectName("title_lbl")
        self.title_lbl.setMinimumWidth(50)
        self.title_lbl.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)

        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(12)
        sub_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.new_and_now = QLabel("조회 중...")
        self.new_and_now.setObjectName("new_and_now")

        url_lbl = QLabel(self.site_url)
        url_lbl.setObjectName("url_lbl")
        url_lbl.setMinimumWidth(50)
        url_lbl.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)

        sub_layout.addWidget(self.new_and_now)
        sub_layout.addWidget(url_lbl)
        sub_layout.addStretch()

        info_layout.addWidget(self.title_lbl)
        info_layout.addLayout(sub_layout)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.select_btn = QPushButton("다운로드")
        self.select_btn.setObjectName("secondaryBtn")
        self.select_btn.setFixedSize(95, 32)
        self.select_btn.clicked.connect(self.open_detail_dialog)

        self.del_btn = QPushButton("삭제")
        self.del_btn.setFixedSize(65, 32)
        self.del_btn.setObjectName("del")
        self.del_btn.hide()

        button_layout.addWidget(self.select_btn)
        button_layout.addWidget(self.del_btn)

        card_layout.addLayout(info_layout, stretch=1)
        card_layout.addLayout(button_layout)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.start_async_fetch()

    def start_async_fetch(self):
        if self.is_empty:
            return
        self.is_loading = True
        self.new_and_now.setText("조회 중...")
        self.worker = thread_pyqt.FetchNewNumberWorker(self.site_url, True)
        self.worker.finished.connect(self.update_new_label)
        self.worker.start()

    def update_new_label(self, result_text):
        self.is_loading = False
        self.now = str(result_text[0])
        self.time = str(result_text[1]) if len(result_text) > 1 and result_text[1] else ""
        time_display = f" - {self.time}" if self.time else ""
        self.new_and_now.setText(f"{self.last} / {self.now} 화{time_display}")
        self.status_updated.emit()
        self.fetch_finished.emit()

    def update_download_info(self, last, down_time):
        self.last = str(last)
        self.down_time = str(down_time)
        time_display = f" - {self.time}" if self.time else ""
        self.new_and_now.setText(f"{self.last} / {self.now} 화{time_display}")
        self.status_updated.emit()

    def set_download_state(self, state_text, enabled=True):
        self.select_btn.setText(state_text)
        self.select_btn.setEnabled(enabled)

    def get_remaining_episodes(self):
        if self.now.isdigit() and self.last.isdigit():
            return max(0, int(self.now) - int(self.last))
        return 0

    def show_context_menu(self, pos):
        menu = QMenu(self)

        edit_title_action = QAction("제목 수정", self)
        edit_title_original_action = QAction("제목 수정 (원본)", self)
        act_massege_action = QAction("작가의 말 트리거 수정", self)
        copy_action = QAction("URL 복사", self)
        visit_action = QAction("브라우저 열기", self)
        delete_action = QAction("삭제", self)

        edit_title_action.triggered.connect(self.open_edit_title_dialog)
        edit_title_original_action.triggered.connect(self.open_edit_title_original_dialog)
        act_massege_action.triggered.connect(self.open_edit_act_massege_dialog)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(self.site_url))
        visit_action.triggered.connect(self.open_browser)
        delete_action.triggered.connect(self.del_btn.click)

        menu.addAction(edit_title_action)
        menu.addAction(edit_title_original_action)
        if "https://kakuyomu.jp/" in self.site_url:
            menu.addAction(act_massege_action)
        menu.addSeparator()
        menu.addAction(copy_action)
        menu.addAction(visit_action)
        menu.addSeparator()
        menu.addAction(delete_action)

        menu.exec(self.mapToGlobal(pos))

    def open_edit_title_dialog(self):
        dialog = EditTitleDialog(self.title_text, self)

        if dialog.exec():
            new_title = dialog.get_new_title()
            if not new_title or new_title == self.title_text:
                return

            data = load_data()

            if "list" in data and self.title_text in data["list"]:
                item_data = data["list"].pop(self.title_text)
                data["list"][new_title] = item_data

            dictionary = data.get("dictionary", {})

            if isinstance(dictionary, dict) and self.title_text in dictionary:
                if new_title in dictionary:
                    QMessageBox.warning(
                        self,
                        "알림",
                        f"'{new_title}'의 용어집이 이미 존재합니다."
                    )
                    return
                dictionary[new_title] = dictionary.pop(self.title_text)

            data["dictionary"] = dictionary
            save_data(data)

            self.title_text = new_title
            self.title_lbl.setText(new_title)

    def open_edit_title_original_dialog(self):
        data = load_data()
        if self.title_raw_text == "":
            base = down.downin.CheckTitle_Raw(self.site_url)
        else:
            base = data["list"][self.title_text].get("original_title", "")

        dialog = EditTitleRawDialog(base, self)

        if dialog.exec():
            new_title = dialog.get_new_title()
            if not new_title or new_title == base:
                return

            data = load_data()
            if "list" in data and self.title_text in data["list"]:
                data["list"][self.title_text]["original_title"] = new_title

            save_data(data)
            self.title_raw_text = new_title

    def open_edit_act_massege_dialog(self):
        dialog = EditActDialog(self.act_massage, self)

        if dialog.exec():
            new_massage = dialog.get_new_massage()
            data = load_data()

            if "list" in data and self.title_text in data["list"]:
                data["list"][self.title_text]["act_masseage"] = new_massage

            save_data(data)
            self.act_massage = new_massage

    def open_browser(self):
        webbrowser.open(self.site_url)

    def open_detail_dialog(self):
        main_win = self.main_window if self.main_window else self.window()
        dialog = DownloadDetailDialog(
            self.site_url, self.title_text, self.last, self, self.now,
            self.act_massage, self, self.title_raw_text, main_win
        )
        dialog.show()