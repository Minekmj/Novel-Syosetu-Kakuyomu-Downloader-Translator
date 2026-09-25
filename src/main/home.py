import webbrowser
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QFileDialog, QScrollArea, QFrame, QDialog, QMessageBox,
    QMenu, QCheckBox, QSizePolicy, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtGui import QIcon

import src.down.down as down
from src.system.data import open_folder, save_data, load_data
import src.system.data as data_iteam
import src.find.findsyou as findsyou
import src.find.site_list as sl
import src.main.thread_pyqt as thread_pyqt
import src.trans.trans_view as trans_view
import src.glossary.glossary_manager as glossary_manager
import src.qr.qr_view as qr_view
import src.main.setting as setting_ui
import src.main.update as update_ui
from src.system.src import resource_path

import src.system.v as vsc

data_iteam.rest()
thread_pyqt.DOWN = down
qr_view.down = down

setting_ui.data_iteam = data_iteam

trans_view.OUT = down.downin.base_data.OUTFOLDER

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
        
        label = QLabel("카쿠요무에서 작가의 말을 구분하는 텍스트를 찾아 붙여 넣으세요.\n이는 백업 텍스트에는 반영되지 않으며, 작품 다운로드로 인한 다운로드에서 이 트리거 이후의 글자를 제외합니다.")
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
    def __init__(self, site_url, title_text, last_down, parent, now_s, act_massage, row_widget):
        super().__init__(parent)
        self.site_url = site_url
        self.title_text = title_text
        self.last_down = last_down
        self.now_state = now_s
        self.row_widget = row_widget
        self.now_res = ""
        self.act_massage = act_massage
        
        self.setWindowTitle("다운로드")
        self.setFixedSize(360, 220)

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

        self.prograss = QLabel("", self)
        self.prograss.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prograss.setObjectName("prograss")
        layout.addWidget(self.prograss)

        self.down_btn = QPushButton("다운로드 시작", self)
        self.down_btn.setObjectName("primaryBtn")
        self.down_btn.setFixedHeight(40)
        self.down_btn.clicked.connect(self.run_download)
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

    def run_download(self):
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

        self.prograss.setText("0.0%")
        self.down_btn.setEnabled(False)
        self.down_btn.setText("진행 중...")

        self.thread = thread_pyqt.DownloadThread(self.site_url, start, end, self.prograss, self.title_text, self.act_massage)
        self.thread.finished_signal.connect(
            lambda success, err_msg: self.on_download_finished(success, err_msg, start, end)
        )
        self.thread.start()

    def on_download_finished(self, success, err_msg, start, end):
        self.down_btn.setEnabled(True)
        self.down_btn.setText("다운로드 시작")

        if success:
            nums = []
            for val in [start, end]:
                if val.isdigit():
                    nums.append(int(val))

            now_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if nums:
                max_num = max(nums)
                data = load_data()
                if self.title_text in data.get("list", {}):
                    data["list"][self.title_text]["down"] = str(max_num)
                    data["list"][self.title_text]["down_time"] = now_time_str
                    save_data(data)

            target_folder = down.downin.base_data.OUTFOLDER
            self.row_widget.update_download_info(end, now_time_str)
            open_folder(target_folder if (target_folder[len(target_folder) - 1] == "\\" or target_folder[len(target_folder) - 1] == "/") else (target_folder + "/"))
            self.accept()
        else:
            QMessageBox.critical(self, "오류", err_msg)
            self.prograss.setText("오류 발생")

class AddressRowWidget(QWidget):
    status_updated = Signal()

    def __init__(self, site_url, title_text=None, parent=None, last="0", down_time="0", act_massage = ""):
        super().__init__(parent)
        self.site_url = site_url
        self.last = "0" if last == "" else last
        self.down_time = "0" if not down_time else down_time
        self.now = "-"
        self.time = ""
        self.act_massage = act_massage

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
        self.worker = thread_pyqt.FetchNewNumberWorker(self.site_url, True)
        self.worker.finished.connect(self.update_new_label)
        self.worker.start()

    def update_new_label(self, result_text):
        self.now = str(result_text[0])
        self.time = str(result_text[1]) if len(result_text) > 1 and result_text[1] else ""
        time_display = f" - {self.time}" if self.time else ""
        self.new_and_now.setText(f"{self.last} / {self.now} 화{time_display}")
        self.status_updated.emit()

    def update_download_info(self, last, down_time):
        self.last = str(last)
        self.down_time = str(down_time)
        time_display = f" - {self.time}" if self.time else ""
        self.new_and_now.setText(f"{self.last} / {self.now} 화{time_display}")
        self.status_updated.emit()

    def get_remaining_episodes(self):
        if self.now.isdigit() and self.last.isdigit():
            return max(0, int(self.now) - int(self.last))
        return 0

    def show_context_menu(self, pos):
        menu = QMenu(self)

        edit_title_action = QAction("제목 수정", self)
        act_massege_action = QAction("작가의 말 트리거 수정", self)
        copy_action = QAction("URL 복사", self)
        visit_action = QAction("브라우저 열기", self)
        delete_action = QAction("삭제", self)

        edit_title_action.triggered.connect(self.open_edit_title_dialog)
        act_massege_action.triggered.connect(self.open_edit_act_massege_dialog)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(self.site_url))
        visit_action.triggered.connect(self.open_browser)
        delete_action.triggered.connect(self.del_btn.click)

        menu.addAction(edit_title_action)
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
        dialog = DownloadDetailDialog(self.site_url, self.title_text, self.last, self, self.now, self.act_massage, self)
        dialog.show()
    

class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.row_widgets = []
        self.newly_added_widget = None

        self.setWindowTitle(f"MINE DOWNLOADER - Novel(Syosetu, Kakuyomu) Downloader & Translator - {vsc.V}")
        self.resize(1200, 700)
        self.setMinimumSize(1200, 550)
        self.setWindowIcon(QIcon(resource_path("main.ico")))

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(24, 22, 24, 24)
        self.main_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(7)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        app_title = QLabel("목록")
        app_title.setObjectName("app_title")

        header_layout.addWidget(app_title)
        header_layout.addStretch()

        self.gloss_bt = QPushButton("용어집 관리")
        self.gloss_bt.setObjectName("secondaryBtn")
        self.gloss_bt.clicked.connect(self.open_gloss)
        header_layout.addWidget(self.gloss_bt)

        for i in sl.Sites:
            def open_window(checked=False, site_key=i):
                dialog = findsyou.MainWindow_Find(site_key, self)
                dialog.show()

            plus_bt = QPushButton(f"{sl.SITES.get(i).get('name')} 검색")
            plus_bt.setObjectName("secondaryBtn")
            plus_bt.clicked.connect(open_window)
            header_layout.addWidget(plus_bt)

        self.epub_btn = QPushButton("EPUB 변환")
        self.epub_btn.setObjectName("secondaryBtn")
        self.epub_btn.clicked.connect(self.convert_txt_to_epub)
        header_layout.addWidget(self.epub_btn)

        self.translate_btn = QPushButton("AI 번역")
        self.translate_btn.setObjectName("secondaryBtn")
        self.translate_btn.clicked.connect(self.open_translate_dialog)
        header_layout.addWidget(self.translate_btn)

        self.qr_btn = QPushButton("번역 목록")
        self.qr_btn.setObjectName("secondaryBtn")
        self.qr_btn.clicked.connect(lambda: qr_view.QRViewDialog(self).show())
        header_layout.addWidget(self.qr_btn)

        self.manager_path_btn = QPushButton("환경 설정")
        self.manager_path_btn.setObjectName("secondaryBtn")
        self.manager_path_btn.clicked.connect(self.open_manager_path_dialog)
        header_layout.addWidget(self.manager_path_btn)

        self.main_layout.addLayout(header_layout)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.main_address_edit = QLineEdit(self)
        self.main_address_edit.setPlaceholderText("작품 URL을 입력하세요")
        self.main_address_edit.setFixedHeight(40)
        self.main_address_edit.returnPressed.connect(self.add_address_row)

        self.add_btn = QPushButton("추가")
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.setFixedSize(90, 40)
        self.add_btn.clicked.connect(self.add_address_row)

        input_layout.addWidget(self.main_address_edit, 1)
        input_layout.addWidget(self.add_btn)

        self.main_layout.addLayout(input_layout)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("목록에서 작품 검색")
        self.search_edit.setFixedHeight(36)
        self.search_edit.textChanged.connect(self.apply_filter_and_sort)

        self.sort_combo = QComboBox(self)
        self.sort_combo.setFixedHeight(36)
        self.sort_combo.addItems([
            "이름순",
            "역이름순",
            "남은 화수순",
            "역 남은 화수순",
            "최근 다운로드순",
            "역 최근 다운로드순",
            "최신화 날짜순",
            "역 최신화 날짜순"
        ])
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)

        self.filter_chk = QCheckBox("남은 화수 있음", self)
        self.filter_chk.setObjectName("isCo")
        self.filter_chk.stateChanged.connect(self.apply_filter_and_sort)

        control_layout.addWidget(self.search_edit, 1)
        control_layout.addWidget(self.sort_combo)
        control_layout.addWidget(self.filter_chk)

        self.main_layout.addLayout(control_layout)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("tag_container")

        self.rows_layout = QVBoxLayout(self.scroll_widget)
        self.rows_layout.setContentsMargins(0, 4, 8, 8)
        self.rows_layout.setSpacing(8)
        self.rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll_area, 1)

        self.click_watcher = thread_pyqt.ClickWatcher()
        self.click_watcher.update_address.connect(self.main_address_edit.setText)
        self.click_watcher.add_address.connect(self.add_address_row)
        self.click_watcher.start()

        self.is_first_massage = AddressRowWidget("")
        self.is_first_massage.hide()
        self.rows_layout.addWidget(self.is_first_massage)

        self.init_saved_data()

        from src.system.v import V
        data = load_data()
        vn = data.get("V", "")

        if vn == "" or vn != V:
            data["V"] = V
            save_data(data)
            update = update_ui.UpdateView(self)
            update.show()

    def on_sort_changed(self):
        self.newly_added_widget = None
        self.apply_filter_and_sort()

    def init_saved_data(self):
        data = load_data()

        trans_view.trans_ai.CUSTOM_AI_PROMPT = data.get("AI_PROMPT", "")
        down.downin.base_data.EXPORT_TEXT = data.get("RAW_TEXT", False)
        down.downin.base_data.ORIGIN_NAME = data.get("origin_name", False)

        trans_view.trans_ai.USE_ADVANCED_CENSOR = data.get("CENSOR_ADVANCED", False)
        trans_view.trans_ai.CENSOR_SHUFFLE = data.get("CENSOR_SHUFFLE", True)
        trans_view.trans_ai.CENSOR_EXTRACT_MODE = data.get("CENSOR_MODE", "word")
        trans_view.trans_ai.CENSOR_PAPAGO = data.get("CENSOR_PAPAGO", False)

        if data.get("src"):
            down.downin.base_data.OUTFOLDER = data["src"]
            trans_view.OUT = data["src"]

        self.load_widgets_from_json()

    def load_widgets_from_json(self):
        data = load_data()
        items_dict = data.get("list", {})
        nu = 0

        for title, item in items_dict.items():
            nu += 1

            site_url = item.get("src", "")
            last_down = item.get("down", "0")
            down_time = item.get("down_time", "0")
            act_masseage = item.get("act_masseage", "")

            row = AddressRowWidget(
                site_url,
                title_text=title,
                parent=self,
                last=last_down,
                down_time=down_time,
                act_massage=act_masseage
            )

            row.del_btn.clicked.connect(lambda _, r=row: self.delete_row(r))
            row.status_updated.connect(self.apply_filter_and_sort)

            self.rows_layout.addWidget(row)
            self.row_widgets.append(row)

            if self.row_widgets:
                self.is_first_massage.hide()

        if nu == 0:
            self.is_first_massage.show()

        self.apply_filter_and_sort()

    def apply_filter_and_sort(self):
        search_query = self.search_edit.text().strip().lower()
        sort_mode = self.sort_combo.currentIndex()
        only_remaining = self.filter_chk.isChecked()

        visible_widgets = []

        for row in self.row_widgets:
            if search_query and search_query not in row.title_text.lower():
                row.hide()
                continue

            remaining = row.get_remaining_episodes()

            if only_remaining and remaining <= 0:
                row.hide()
                continue

            row.show()
            visible_widgets.append(row)

        is_pinned = self.newly_added_widget in visible_widgets

        if is_pinned:
            visible_widgets.remove(self.newly_added_widget)

        if sort_mode == 0:
            visible_widgets.sort(key=lambda x: x.title_text)
        elif sort_mode == 1:
            visible_widgets.sort(key=lambda x: x.title_text, reverse=True)
        elif sort_mode == 2:
            visible_widgets.sort(key=lambda x: x.get_remaining_episodes(), reverse=True)
        elif sort_mode == 3:
            visible_widgets.sort(key=lambda x: x.get_remaining_episodes())
        elif sort_mode == 4:
            visible_widgets.sort(key=lambda x: x.down_time, reverse=True)
        elif sort_mode == 5:
            visible_widgets.sort(key=lambda x: x.down_time)
        elif sort_mode == 6:
            visible_widgets.sort(key=lambda x: (x.time != "", x.time), reverse=True)
        elif sort_mode == 7:
            visible_widgets.sort(key=lambda x: (x.time == "", x.time))

        if is_pinned:
            visible_widgets.insert(0, self.newly_added_widget)

        for row in visible_widgets:
            self.rows_layout.addWidget(row)

    def add_address_row(self):
        url = self.main_address_edit.text().strip()

        if "syosetu.com" in url:
            if not url.endswith("/"):
                url += "/"
        elif "kakuyomu.jp" in url:
            if url.endswith("/"):
                url = url.rstrip("/")

        if not url:
            return

        data = load_data()

        if any(item.get("src") == url for item in data.get("list", {}).values()):
            QMessageBox.warning(self, "알림", "이미 등록된 주소입니다.")
            self.main_address_edit.clear()
            return

        self.main_address_edit.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.add_btn.setText("...")
        QApplication.processEvents()

        temp_row = AddressRowWidget(url)
        title_text = temp_row.title_text

        if "list" not in data:
            data["list"] = {}

        data["list"][title_text] = {
            "src": url,
            "down": "",
            "down_time": "0"
        }

        save_data(data)

        self.main_address_edit.clear()
        self.main_address_edit.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.add_btn.setText("추가")

        row = temp_row
        row.setParent(self)
        row.del_btn.clicked.connect(lambda _, r=row: self.delete_row(r))
        row.status_updated.connect(self.apply_filter_and_sort)

        self.row_widgets.insert(0, row)
        self.newly_added_widget = row

        if self.row_widgets:
            self.is_first_massage.hide()

        if self.search_edit.text():
            self.search_edit.blockSignals(True)
            self.search_edit.clear()
            self.search_edit.blockSignals(False)

        self.apply_filter_and_sort()
        self.scroll_area.verticalScrollBar().setValue(0)

        QMessageBox.information(self, "완료", "주소가 성공적으로 추가되었습니다.")

    def delete_row(self, row_widget):
        if self.newly_added_widget == row_widget:
            self.newly_added_widget = None

        data = load_data()

        if row_widget.title_text in data.get("list", {}):
            del data["list"][row_widget.title_text]
            save_data(data)

        if row_widget in self.row_widgets:
            self.row_widgets.remove(row_widget)

        if not self.row_widgets:
            self.is_first_massage.show()

        row_widget.deleteLater()

    def open_manager_path_dialog(self):
        data = load_data()
        
        if data.get("theme"):
            data_iteam.THEME_NAME = data["theme"]
        dialog = setting_ui.PathSettingsDialog(self)
        
        if data.get("src"):
            dialog.path_edit.setText(data["src"])
        elif down.downin.base_data.OUTFOLDER:
            dialog.path_edit.setText(down.downin.base_data.OUTFOLDER)
            
        dialog.raw_text_toggle.setChecked(data.get("RAW_TEXT", False))
        dialog.origin_name_toggle.setChecked(data.get("origin_name", False))
        dialog.ai_prompt_edit.setPlainText(data.get("AI_PROMPT", ""))
        censor_adv = data.get("CENSOR_ADVANCED", False)
        dialog.censor_toggle.setChecked(censor_adv)
        dialog.censor_sub_widget.setVisible(censor_adv)
        dialog.shuffle_toggle.setChecked(data.get("CENSOR_SHUFFLE", True))
        saved_mode = data.get("CENSOR_MODE", "word")
        idx = dialog.mode_combo.findData(saved_mode)
        
        if idx >= 0:
            dialog.mode_combo.setCurrentIndex(idx)
        dialog.papago_toggle.setChecked(data.get("CENSOR_PAPAGO", False))
        
        if "epub_data" in data:
            dialog.set_epub_data(data["epub_data"])
            
        if dialog.exec():
            selected_path = dialog.path_edit.text().strip()
            selected_theme = data_iteam.THEME_DATA.get(dialog.theme_combo.currentText(), "DARK")
            
            raw_text = dialog.get_raw_text()
            origin_name = dialog.get_origin_name()
            ai_prompt = dialog.get_ai_prompt()
            censor_advanced = dialog.get_censor_advanced()
            censor_shuffle = dialog.get_censor_shuffle()
            censor_mode = dialog.get_censor_mode()
            censor_papago = dialog.get_censor_papago()
            epub_data = dialog.get_epub_data()
            
            if selected_path:
                down.downin.base_data.OUTFOLDER = selected_path
                trans_view.OUT = selected_path
                data["src"] = selected_path
                
            down.downin.base_data.EXPORT_TEXT = raw_text
            down.downin.base_data.ORIGIN_NAME = origin_name
            
            data["theme"] = selected_theme
            data["RAW_TEXT"] = raw_text
            data["origin_name"] = origin_name
            data["AI_PROMPT"] = ai_prompt
            data["CENSOR_ADVANCED"] = censor_advanced
            data["CENSOR_SHUFFLE"] = censor_shuffle
            data["CENSOR_MODE"] = censor_mode
            data["CENSOR_PAPAGO"] = censor_papago
            if not epub_data is None:
                data["epub_data"] = epub_data
            
            save_data(data)
            
            trans_view.trans_ai.CUSTOM_AI_PROMPT = ai_prompt
            trans_view.trans_ai.USE_ADVANCED_CENSOR = censor_advanced
            trans_view.trans_ai.CENSOR_SHUFFLE = censor_shuffle
            trans_view.trans_ai.CENSOR_EXTRACT_MODE = censor_mode
            trans_view.trans_ai.CENSOR_PAPAGO = censor_papago
            
            if data["theme"] != data_iteam.THEME_NAME:
                data_iteam.THEME_NAME = data["theme"]
                data_iteam.rest()
                findsyou.rest()
                self.app.setStyleSheet(data_iteam.MINIMAL_DARK_THEME)

    def open_translate_dialog(self):
        dialog = trans_view.TranslateDialog(self)
        dialog.show()

    def open_gloss(self):
        dialog = glossary_manager.GlossaryManagerDialog(self)
        dialog.show()

    def convert_txt_to_epub(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "EPUB으로 변환할 TXT 파일 선택",
            down.downin.base_data.OUTFOLDER,
            "Text Files (*.txt)"
        )

        if not file_paths:
            return

        self.epub_btn.setEnabled(False)
        self.epub_btn.setText("변환 중...")

        self.epub_thread = thread_pyqt.EpubConvertThread(file_paths)
        self.epub_thread.finished_signal.connect(self.on_epub_convert_finished)
        self.epub_thread.start()

    def on_epub_convert_finished(self, success, message, output_dir):
        self.epub_btn.setEnabled(True)
        self.epub_btn.setText("EPUB 변환")

        if success:
            if output_dir:
                open_folder(output_dir)
        else:
            QMessageBox.critical(self, "오류", f"EPUB 변환 도중 오류가 발생했습니다:\n{message}")

    def closeEvent(self, event):
        thread_pyqt.STOP_CLICK = True
        self.click_watcher.stop()
        super().closeEvent(event)