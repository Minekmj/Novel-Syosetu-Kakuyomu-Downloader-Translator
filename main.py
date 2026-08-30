import sys
import os
import json
import platform
import subprocess
import webbrowser
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLineEdit, QPushButton, QLabel,
                            QFileDialog, QScrollArea, QFrame, QDialog, QMessageBox, QTextBrowser,
                            QMenu, QCheckBox, QSizePolicy, QComboBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QFont
from PySide6.QtGui import QIcon
import ctypes

import down
import data as data_iteam
import findsyou
import thread_pyqt
from thread_pyqt import *
thread_pyqt.DOWN = down
from trans_view import TranslateDialog

from config import DATA_FILE

def open_folder(path):
    
    if path == "./out/":
        path = os.path.join(os.getcwd(), "out")
    
    if not path or not os.path.exists(path):
        return
    
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    except Exception as e:
        print(f"폴더 열기 실패: {e}")

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"src": "", "list": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"데이터 저장 실패: {e}")

class PathSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme_key="다크"
        self.setWindowTitle("환경 설정")
        self.setFixedSize(400, 180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)
        self.path_edit = QLineEdit(self)
        self.path_edit.setPlaceholderText("저장 폴더 경로")
        self.path_edit.setReadOnly(True) 

        folder_btn = QPushButton("찾기", self)
        folder_btn.setObjectName("secondaryBtn")
        folder_btn.clicked.connect(self.browse_folder)

        path_layout.addWidget(self.path_edit, stretch=1)
        path_layout.addWidget(folder_btn)
        layout.addLayout(path_layout)
        
        theme_layout = QHBoxLayout()
        theme_layout.setSpacing(8)
        
        theme_label = QLabel("테마 설정", self)
        self.theme_combo = QComboBox(self)
        
       
        self.theme_combo.addItems(list(data_iteam.THEME_DATA.keys()))
        
        g = {}
        for i , h  in data_iteam.THEME_DATA.items():
            g[h] = i

        self.theme_combo.setCurrentText(g[data_iteam.THEME_NAME])

        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo, stretch=1)
        layout.addLayout(theme_layout)
        

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        save_btn = QPushButton("저장", self)
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.accept)
        save_btn.setStyleSheet("width:100%")

        btn_layout.addWidget(save_btn)
        
        layout.spacing()
        layout.addLayout(btn_layout)

    def browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if directory:
            self.path_edit.setText(directory)
            
    def get_theme_display_name(self):
        return self.theme_combo.currentText()

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

class DownloadDetailDialog(QDialog):
    def __init__(self, site_url, title_text, last_down, parent, now_s, row_widget):
        super().__init__(parent)
        self.site_url = site_url
        self.title_text = title_text
        self.last_down = last_down
        self.now_state = now_s
        self.row_widget = row_widget
        self.now_res = ""
        
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
        self.worker = FetchNewNumberWorker(self.site_url)
        self.worker.finished.connect(self.update_new_label)
        self.worker.start()

    def update_new_label(self, result_text):
        self.new_lbl.setText(f"최신: {result_text}화")
        self.now_res = str(result_text)
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

        self.thread = DownloadThread(self.site_url, start, end, self.prograss, self.title_text)
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

            target_folder = getattr(down.downin, 'OUTFOLDER', '')
            self.row_widget.update_download_info(end, now_time_str)
            open_folder(target_folder)
            self.accept()
        else:
            QMessageBox.critical(self, "오류", err_msg)
            self.prograss.setText("오류 발생")

class AddressRowWidget(QWidget):
    status_updated = Signal()

    def __init__(self, site_url, title_text=None, parent=None, last="0", down_time="0"):
        super().__init__(parent)
        self.site_url = site_url
        self.last = "0" if last == "" else last
        self.down_time = "0" if not down_time else down_time
        self.now = "-"

        if title_text:
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

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 2, 0, 2)
        main_layout.addWidget(self.main_frame)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.start_async_fetch()
                
    def start_async_fetch(self):
        self.worker = FetchNewNumberWorker(self.site_url)
        self.worker.finished.connect(self.update_new_label)
        self.worker.start()

    def update_new_label(self, result_text):
        self.now = str(result_text)
        self.new_and_now.setText(f"{self.last} / {self.now} 화")
        self.status_updated.emit()

    def update_download_info(self, last, down_time):
        self.last = str(last)
        self.down_time = str(down_time)
        self.new_and_now.setText(f"{self.last} / {self.now} 화")
        self.status_updated.emit()

    def get_remaining_episodes(self):
        if self.now.isdigit() and self.last.isdigit():
            return max(0, int(self.now) - int(self.last))
        return 0

    def show_context_menu(self, pos):
        menu = QMenu(self)

        edit_title_action = QAction("제목 수정", self)
        copy_action = QAction("URL 복사", self)
        visit_action = QAction("브라우저 열기", self)
        delete_action = QAction("삭제", self)

        edit_title_action.triggered.connect(self.open_edit_title_dialog)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(self.site_url))
        visit_action.triggered.connect(self.open_browser)
        delete_action.triggered.connect(self.del_btn.click)

        menu.addAction(edit_title_action)
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
                save_data(data)

                self.title_text = new_title
                self.title_lbl.setText(new_title)

    def open_browser(self):
        webbrowser.open(self.site_url)

    def open_detail_dialog(self):
        dialog = DownloadDetailDialog(self.site_url, self.title_text, self.last, self, self.now, self)
        dialog.show()
        
class UpdateView(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("업데이트")
        self.setFixedSize(600, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        self.text_browser = QTextBrowser(self)
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setMarkdown(
            open(resource_path("update.md"), "r", encoding="UTF-8").read()
        )

        layout.addWidget(self.text_browser)
    

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.row_widgets = []

        self.setWindowTitle("다운로더")
        self.resize(950, 700)
        self.setMinimumSize(650, 550)
        self.setWindowIcon(QIcon(resource_path("main.ico")))

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

       
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header_layout.setSpacing(8)
        
        app_title = QLabel("목록")
        app_title.setObjectName("app_title")

        self.plus_bt_n = QPushButton("나로우 검색")
        self.plus_bt_n.setObjectName("secondaryBtn")
        self.plus_bt_n.clicked.connect(self.open_na)
                
        self.plus_bt = QPushButton("카쿠요무 검색")
        self.plus_bt.setObjectName("secondaryBtn")
        self.plus_bt.clicked.connect(self.open_kaku)
        
        self.epub_btn = QPushButton("EPUB 변환")
        self.epub_btn.setObjectName("secondaryBtn")
        self.epub_btn.clicked.connect(self.convert_txt_to_epub)

        self.translate_btn = QPushButton("AI 번역")
        self.translate_btn.setObjectName("secondaryBtn")
        self.translate_btn.clicked.connect(self.open_translate_dialog)

        self.manager_path_btn = QPushButton("환경 설정")
        self.manager_path_btn.setObjectName("secondaryBtn")
        self.manager_path_btn.clicked.connect(self.open_manager_path_dialog)

        header_layout.addWidget(app_title)
        header_layout.addStretch()
        header_layout.addWidget(self.plus_bt_n)
        header_layout.addWidget(self.plus_bt)
        header_layout.addWidget(self.epub_btn)
        header_layout.addWidget(self.translate_btn)
        header_layout.addWidget(self.manager_path_btn)
        self.main_layout.addLayout(header_layout)

       
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.main_address_edit = QLineEdit(self)
        self.main_address_edit.setPlaceholderText("URL 입력")
        self.main_address_edit.setFixedHeight(40)
        self.main_address_edit.returnPressed.connect(self.add_address_row)

        self.add_btn = QPushButton("추가")
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.setFixedSize(90, 40)
        self.add_btn.clicked.connect(self.add_address_row)

        input_layout.addWidget(self.main_address_edit, stretch=1)
        input_layout.addWidget(self.add_btn)
        self.main_layout.addLayout(input_layout)

       
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("이름 검색...")
        self.search_edit.textChanged.connect(self.apply_filter_and_sort)

        self.sort_combo = QComboBox(self)
        self.sort_combo.addItems(["이름순", "역이름순", "남은 화수순", "최근 다운로드순", "역 최근 다운로드순"])
        self.sort_combo.currentIndexChanged.connect(self.apply_filter_and_sort)

        self.filter_chk = QCheckBox("남은 화수 있음", self)
        self.filter_chk.stateChanged.connect(self.apply_filter_and_sort)

        control_layout.addWidget(self.search_edit, stretch=1)
        control_layout.addWidget(self.sort_combo)
        control_layout.addWidget(self.filter_chk)
        self.main_layout.addLayout(control_layout)

       
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("tag_container")
        self.rows_layout = QVBoxLayout(self.scroll_widget)
        self.rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.rows_layout.setContentsMargins(0, 8, 8, 8)
        self.rows_layout.setSpacing(8)

        self.scroll_area.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll_area)
        
        self.click_watcher = ClickWatcher()
        self.click_watcher.update_address.connect(self.main_address_edit.setText)
        self.click_watcher.add_address.connect(self.add_address_row)
        self.click_watcher.start()

        self.init_saved_data()
        
        from v import V
        data = load_data()
        vn = data.get("V", "")
        if vn == "" or vn != V:
            update = UpdateView(self)
            update.show()
            data["V"] = V
            save_data(data)
            

    def init_saved_data(self):
        data = load_data()

        if data.get("src"):
            down.downin.OUTFOLDER = data["src"]
            
        self.load_widgets_from_json()

    def load_widgets_from_json(self):
        data = load_data()
        items_dict = data.get("list", {})

        for title, item in items_dict.items():
            site_url = item.get("src", "")
            last_down = item.get("down", "0")
            down_time = item.get("down_time", "0")

            row = AddressRowWidget(site_url, title_text=title, parent=self, last=last_down, down_time=down_time)
            row.del_btn.clicked.connect(lambda _, r=row: self.delete_row(r))
            row.status_updated.connect(self.apply_filter_and_sort)

            self.rows_layout.addWidget(row)
            self.row_widgets.append(row)

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

       
        if sort_mode == 0:
            visible_widgets.sort(key=lambda x: x.title_text)
        elif sort_mode == 1:
            visible_widgets.sort(key=lambda x: x.title_text, reverse=True)
        elif sort_mode == 2:
            visible_widgets.sort(key=lambda x: x.get_remaining_episodes(), reverse=True)
        elif sort_mode == 3:
            visible_widgets.sort(key=lambda x: x.down_time, reverse=True)
        elif sort_mode == 4:
            visible_widgets.sort(key=lambda x: x.down_time)

       
        for row in visible_widgets:
            self.rows_layout.addWidget(row)

    def add_address_row(self):
        url = self.main_address_edit.text().strip()

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

        self.rows_layout.addWidget(row)
        self.row_widgets.append(row)

        self.apply_filter_and_sort()
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

       
        QMessageBox.information(self, "완료", "주소가 성공적으로 추가되었습니다.")

    def delete_row(self, row_widget):
        data = load_data()
        if row_widget.title_text in data.get("list", {}):
            del data["list"][row_widget.title_text]
            save_data(data)

        if row_widget in self.row_widgets:
            self.row_widgets.remove(row_widget)

        row_widget.deleteLater()

    def open_manager_path_dialog(self):
        data = load_data()
        if data.get("theme"):
            data_iteam.THEME_NAME = data["theme"]
        dialog = PathSettingsDialog(self)
        if data.get("src"):
            dialog.path_edit.setText(data["src"])
        elif hasattr(down.downin, 'OUTFOLDER'):
            dialog.path_edit.setText(down.downin.OUTFOLDER)

        if dialog.exec():
            selected_path = dialog.path_edit.text().strip()
            selected_theme = data_iteam.THEME_DATA.get(dialog.theme_combo.currentText(), "DARK")
            
            if selected_path:
                down.downin.OUTFOLDER = selected_path
                data["src"] = selected_path
                data["theme"] = selected_theme
            
            save_data(data)
            
            if data["theme"] != data_iteam.THEME_NAME:
                data_iteam.THEME_NAME = data["theme"]
                data_iteam.rest()
                findsyou.rest()
                app.setStyleSheet(data_iteam.MINIMAL_DARK_THEME)
            
    def open_kaku(self):
        findsyou.IS_KAKU = True
        dialog = findsyou.MainWindow_Find(self)
        dialog.show()
            
    def open_na(self):
        findsyou.IS_KAKU = False
        dialog = findsyou.MainWindow_Find(self)
        dialog.show()

    def open_translate_dialog(self):
        dialog = TranslateDialog(self)
        dialog.show()

    def convert_txt_to_epub(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "EPUB으로 변환할 TXT 파일 선택", 
            getattr(down.downin, 'OUTFOLDER', ''), 
            "Text Files (*.txt)"
        )

        if not file_paths:
            return

        self.epub_btn.setEnabled(False)
        self.epub_btn.setText("변환 중...")

        self.epub_thread = EpubConvertThread(file_paths)
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
        if not close_event is None: close_event()
        super().closeEvent(event)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

app = None
close_event = None

def main(callback = None, close = None):
    global app, close_event
    if sys.platform == "win32":  # 윈도우 환경일 경우에만 실행
        try:
            # 고유한 임의의 문자열 지정 (형식은 자유)
            myappid = 'mine.mn.downloader.v1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
        
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("main.ico")))
    close_event = close
        
    font = QFont("Pretendard", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    app.setStyleSheet(data_iteam.MINIMAL_DARK_THEME)

    window = MainWindow()
    window.setWindowIcon(QIcon(resource_path("main.ico")))
    callback()
    window.show()
    sys.exit(app.exec())
    
if __name__ == "__main__":
    main()