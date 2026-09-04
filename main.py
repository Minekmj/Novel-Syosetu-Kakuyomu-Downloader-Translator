import sys
import os
import json
import webbrowser
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSpacerItem, QToolButton, QWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QFileDialog, QScrollArea, QFrame, QDialog, QMessageBox, QTextBrowser,
    QTextEdit, QMenu, QCheckBox, QSizePolicy, QComboBox
)
from PySide6.QtCore import QSize, QUrl, Qt, Signal
from PySide6.QtGui import QAction, QDesktopServices, QFont
from PySide6.QtGui import QIcon
import ctypes
import re

import down
from data import open_folder, save_data, load_data
import data as data_iteam
data_iteam.rest()
import findsyou
import thread_pyqt
from thread_pyqt import *
thread_pyqt.DOWN = down
import trans_view

import v as vsc

trans_view.OUT = down.downin.OUTFOLDER

class PathSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme_key = "다크"
        self.setWindowTitle("환경 설정")
        
        self.widths = 600
        self.min_height = 220
        
        self.max_height = 550
        
        self.setBaseSize(self.widths, self.min_height)
        self.setFixedSize(self.widths, self.min_height)
        self.setMaximumWidth(self.widths)

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
        for i, h in data_iteam.THEME_DATA.items():
            g[h] = i

        self.theme_combo.setCurrentText(g[data_iteam.THEME_NAME])

        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo, stretch=1)
        layout.addLayout(theme_layout)

        advanced_button = QToolButton(self)
        advanced_button.setText("고급 옵션")
        advanced_button.setCheckable(True)
        advanced_button.setChecked(False)
        advanced_button.setArrowType(Qt.RightArrow)
        advanced_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        advanced_button.setObjectName("lbl_original_title")

        advanced_button.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
            }
            QToolButton:hover {
                background-color: transparent;
            }
            QToolButton:pressed {
                background-color: transparent;
            }
        """)

        def toggle_advanced(checked):
            advanced_widget.setVisible(checked)
            advanced_button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
            self.setFixedSize(self.width(), self.max_height if checked else self.min_height)

        advanced_button.toggled.connect(toggle_advanced)
        layout.addWidget(advanced_button)

        advanced_widget = QWidget(self)
        advanced_widget.setObjectName("advanced_widget")
        advanced_widget.setStyleSheet("""
            QWidget#advanced_widget {
                background-color: transparent;
                border: none;
            }
        """)

        advanced_layout = QVBoxLayout(advanced_widget)
        advanced_layout.setContentsMargins(0, 4, 0, 0)
        advanced_layout.setSpacing(4)

        raw_layout = QHBoxLayout()
        raw_layout.setSpacing(8)
        raw_layout.setContentsMargins(0, 0, 0, 0)

        raw_label = QLabel("원문 다운로드", self)
        self.raw_text_toggle = QCheckBox(self)
        self.raw_text_toggle.setChecked(False)

        raw_label.setCursor(Qt.PointingHandCursor)
        raw_label.mousePressEvent = lambda *event: self.raw_text_toggle.setChecked(
            not self.raw_text_toggle.isChecked()
        )

        raw_layout.addWidget(raw_label)
        raw_layout.addWidget(self.raw_text_toggle)
        raw_layout.addStretch()
        advanced_layout.addLayout(raw_layout)
        
        raw_description = QLabel("다운로드 시 파일을 원문 그대로 다운로드합니다.\n원문의 줄바꿈 구조를 유지하고, txt 상태에서 읽기 쉽도록 조정합니다.\nRAW 다운로드 파일이 ai번역 시 줄바꿈을 유지하여 번역되며 출력시 txt 파일이 epub와 같이 출력 됩니다.")
        raw_description.setWordWrap(True)
        raw_description.setObjectName("lbl_original_title")
        advanced_layout.addWidget(raw_description)

        advanced_layout.addSpacing(10)
        
        prompt_label = QLabel("사용자 지정 AI 번역 프롬프트", self)
        prompt_label.setObjectName("setting_title_txt")
        advanced_layout.addWidget(prompt_label)

        self.ai_prompt_edit = QTextEdit(self)
        self.ai_prompt_edit.setPlaceholderText(
            "AI 번역 시 사용할 추가 프롬프트를 입력하세요.\n"
            "비워두면 기본 번역 프롬프트만 사용합니다."
        )
        self.ai_prompt_edit.setMinimumHeight(90)
        self.ai_prompt_edit.setMaximumHeight(130)
        self.ai_prompt_edit.setObjectName(
            "detail_description"
        )
        self.ai_prompt_edit.viewport().setStyleSheet(
            "background: transparent;"
        )
        advanced_layout.addWidget(self.ai_prompt_edit)

        link_layout = QHBoxLayout()
        link_layout.setContentsMargins(0, 8, 0, 0)
        link_layout.setSpacing(6)

        def create_link_button(text, url):
            button = QToolButton(self)
            button.setText(text)
            button.setCursor(Qt.PointingHandCursor)
            button.setAutoRaise(True)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setStyleSheet("""
                QToolButton {
                    padding: 4px 6px;
                    font-size: 9pt;
                }
            """)
            button.setObjectName("link_button")
            button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
            return button

        opinion_button = create_link_button(
            "의견 보내기",
            "https://minekmj.github.io/Novel-Syosetu-Kakuyomu-Downloader-Translator/opinion/home.html"
        )

        release_button = create_link_button(
            "릴리스",
            "https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/releases"
        )

        github_button = create_link_button(
            "GitHub",
            "https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator"
        )

        link_layout.addWidget(opinion_button)
        link_layout.addWidget(release_button)
        link_layout.addWidget(github_button)
        link_layout.addStretch()
        
        link_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        advanced_layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        hr_line = QFrame(self)
        hr_line.setFrameShape(QFrame.HLine)
        hr_line.setFrameShadow(QFrame.Sunken)
        hr_line.setObjectName("hr_line")
        
        advanced_layout.addWidget(hr_line)

        advanced_layout.addLayout(link_layout)
        
        v_label = QLabel("현재 버전 : " + vsc.V, self)
        v_label.setObjectName("lbl_original_title")
        advanced_layout.addWidget(v_label)
        
        advanced_layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Expanding))

        advanced_widget.setVisible(False)
        layout.addWidget(advanced_widget)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        save_btn = QPushButton("저장", self)
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.accept)

        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if directory:
            self.path_edit.setText(directory)
    def get_theme_display_name(self):
        return self.theme_combo.currentText()

    def get_raw_text(self):
        return self.raw_text_toggle.isChecked()

    def get_ai_prompt(self):
        return self.ai_prompt_edit.toPlainText().strip()

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

            target_folder = getattr(down.downin, 'OUTFOLDER', './out/')
            self.row_widget.update_download_info(end, now_time_str)
            open_folder(target_folder if (target_folder[len(target_folder) - 1] == "\\" or target_folder[len(target_folder) - 1] == "/") else (target_folder + "/"))
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

    def open_browser(self):
        webbrowser.open(self.site_url)

    def open_detail_dialog(self):
        dialog = DownloadDetailDialog(self.site_url, self.title_text, self.last, self, self.now, self)
        dialog.show()


class DynamicTextBrowser(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def sizeHint(self):
        doc_height = int(self.document().size().height())
        return QSize(super().sizeHint().width(), doc_height + 40)


class CollapsibleSection(QWidget):
    def __init__(self, title, markdown_content, parent=None):
        super().__init__(parent)
        self.is_expanded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toggle_button = QPushButton(f"▼ {title}")
        self.toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                padding: 8px;
            }
        """)
        self.toggle_button.setObjectName("isCo")
        self.toggle_button.clicked.connect(self.toggle)
        layout.addWidget(self.toggle_button)

        self.text_browser = DynamicTextBrowser(self)
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setMarkdown(markdown_content)
        self.text_browser.setObjectName('detail_description')
        self.text_browser.viewport().setStyleSheet("background: transparent;")
        
        self.text_browser.setVisible(False)
        layout.addWidget(self.text_browser)

    def toggle(self):
        self.is_expanded = not self.is_expanded
        self.text_browser.setVisible(self.is_expanded)
        
        if self.is_expanded:
            self.text_browser.document().adjustSize()
            self.text_browser.updateGeometry()

        title_text = self.toggle_button.text()[2:]
        if self.is_expanded:
            self.toggle_button.setText(f"▲ {title_text}")
        else:
            self.toggle_button.setText(f"▼ {title_text}")


class UpdateView(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("업데이트")
        self.setFixedSize(600, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)

        try:
            with open(resource_path("update.md"), "r", encoding="UTF-8") as f:
                md_content = f.read()
            
            sections = self.parse_markdown(md_content)
            for i, (title, content) in enumerate(sections):
                section_widget = CollapsibleSection(title, content)
                if i == 0:
                    section_widget.toggle()
                self.scroll_layout.addWidget(section_widget)

        except Exception as e:
            err_browser = QTextBrowser(self)
            err_browser.setText(f"업데이트 내역을 불러오는데 실패했습니다: {e}")
            self.scroll_layout.addWidget(err_browser)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

    def parse_markdown(self, md_text):
        clean_text = re.sub(r'<hr\s*/?>', '', md_text)
        raw_sections = clean_text.split("## ")
        parsed = []
        
        for section in raw_sections:
            if not section.strip():
                continue
            lines = section.strip().split("\n")
            title = lines[0].strip()
            content = "\n".join(lines[1:]).strip()
            parsed.append((title, content))
            
        return parsed
    

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.row_widgets = []

        self.setWindowTitle(f"MINE DOWNLOADER - Novel(Syosetu, Kakuyomu) Downloader & Translator - {vsc.V}")
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
        self.filter_chk.setObjectName("isCo")

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

        self.is_first_massage = AddressRowWidget("")
        self.is_first_massage.hide()
        self.rows_layout.addWidget(self.is_first_massage)
        
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

        trans_view.trans_ai.CUSTOM_AI_PROMPT = data.get("AI_PROMPT", "")
        down.downin.EXPORT_TEXT = data.get("RAW_TEXT", False)
        
        if data.get("src"):
            down.downin.OUTFOLDER = data["src"]
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

            row = AddressRowWidget(site_url, title_text=title, parent=self, last=last_down, down_time=down_time)
            row.del_btn.clicked.connect(lambda _, r=row: self.delete_row(r))
            row.status_updated.connect(self.apply_filter_and_sort)

            self.rows_layout.addWidget(row)
            self.row_widgets.append(row)
            
            if len(self.row_widgets) > 0:
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

        self.rows_layout.addWidget(row)
        self.row_widgets.append(row)
        
        if len(self.row_widgets) > 0:
            self.is_first_massage.hide()

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
            
        if len(self.row_widgets) <= 0:
            self.is_first_massage.show()

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

        dialog.raw_text_toggle.setChecked(data.get("RAW_TEXT", False))
        dialog.ai_prompt_edit.setPlainText(data.get("AI_PROMPT", ""))

        if dialog.exec():
            selected_path = dialog.path_edit.text().strip()
            selected_theme = data_iteam.THEME_DATA.get(dialog.theme_combo.currentText(), "DARK")
            raw_text = dialog.get_raw_text()
            ai_prompt = dialog.get_ai_prompt()

            if selected_path:
                down.downin.OUTFOLDER = selected_path
                trans_view.OUT = selected_path
                data["src"] = selected_path

            down.downin.EXPORT_TEXT = raw_text
            data["theme"] = selected_theme
            data["RAW_TEXT"] = raw_text
            data["AI_PROMPT"] = ai_prompt
            save_data(data)

            trans_view.trans_ai.CUSTOM_AI_PROMPT = ai_prompt

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
        dialog = trans_view.TranslateDialog(self)
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
    if sys.platform == "win32":
        try:
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