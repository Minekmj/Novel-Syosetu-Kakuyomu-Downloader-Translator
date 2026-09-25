from PySide6.QtWidgets import (
    QSpacerItem, QToolButton, QWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QFileDialog, QFrame, QDialog, QTextEdit, QCheckBox,
    QSizePolicy, QComboBox
)
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
import src.system.v as vsc

import src.main.epub_setting as ep

data_iteam = None

class PathSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme_key = "다크"
        self.setWindowTitle("환경 설정")
        self.widths = 600
        self.min_height = 220
        self.max_height = 760
        self.setBaseSize(self.widths, self.min_height)
        self.setFixedSize(self.widths, self.min_height)
        self.setMaximumWidth(self.widths)
        self.epub_data = ep.merge_epub_data(None)
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
        try:
            self.theme_combo.setCurrentText(g[data_iteam.THEME_NAME])
        except:
            self.theme_combo.setCurrentText(g[list(g.keys())[0]])
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
        advanced_button.setStyleSheet("QToolButton { background-color: transparent; border: none; } QToolButton:hover { background-color: transparent; } QToolButton:pressed { background-color: transparent; }")
        def toggle_advanced(checked):
            advanced_widget.setVisible(checked)
            advanced_button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
            self.setFixedSize(self.width(), self.max_height if checked else self.min_height)
        advanced_button.toggled.connect(toggle_advanced)
        layout.addWidget(advanced_button)
        advanced_widget = QWidget(self)
        advanced_widget.setObjectName("advanced_widget")
        advanced_widget.setStyleSheet("QWidget#advanced_widget { background-color: transparent; border: none; }")
        advanced_layout = QVBoxLayout(advanced_widget)
        advanced_layout.setContentsMargins(0, 4, 0, 0)
        advanced_layout.setSpacing(6)
        raw_layout = QHBoxLayout()
        raw_layout.setSpacing(8)
        raw_layout.setContentsMargins(0, 0, 0, 0)
        raw_label = QLabel("원문 다운로드", self)
        self.raw_text_toggle = QCheckBox(self)
        self.raw_text_toggle.setChecked(False)
        raw_label.setCursor(Qt.PointingHandCursor)
        raw_label.mousePressEvent = lambda *event: self.raw_text_toggle.setChecked(not self.raw_text_toggle.isChecked())
        raw_layout.addWidget(raw_label)
        raw_layout.addWidget(self.raw_text_toggle)
        raw_layout.addStretch()
        advanced_layout.addLayout(raw_layout)
        raw_description = QLabel("다운로드 시 파일을 원문 그대로 다운로드합니다.\n원문의 줄바꿈 구조를 유지하고, txt 상태에서 읽기 쉽도록 조정합니다.\nRAW 다운로드 파일이 ai번역 시 줄바꿈을 유지하여 번역되며 출력시 txt 파일이 epub와 같이 출력 됩니다.")
        raw_description.setWordWrap(True)
        raw_description.setObjectName("lbl_original_title")
        advanced_layout.addWidget(raw_description)
        origin_name_layout = QHBoxLayout()
        origin_name_layout.setSpacing(8)
        origin_name_layout.setContentsMargins(0, 4, 0, 0)
        origin_name_label = QLabel("원문 제목으로 파일 저장", self)
        self.origin_name_toggle = QCheckBox(self)
        self.origin_name_toggle.setChecked(False)
        origin_name_label.setCursor(Qt.PointingHandCursor)
        origin_name_label.mousePressEvent = lambda *event: self.origin_name_toggle.setChecked(not self.origin_name_toggle.isChecked())
        origin_name_layout.addWidget(origin_name_label)
        origin_name_layout.addWidget(self.origin_name_toggle)
        origin_name_layout.addStretch()
        advanced_layout.addLayout(origin_name_layout)
        epub_set_layout = QHBoxLayout()
        epub_set_layout.setSpacing(8)
        epub_set_layout.setContentsMargins(0, 4, 0, 0)
        epub_set_label = QLabel("EPUB 본문 출력 설정", self)
        epub_btn = QPushButton("EPUB 설정하기", self)
        epub_btn.setObjectName("secondaryBtn")
        epub_btn.clicked.connect(self.open_epub_settings)
        epub_set_layout.addWidget(epub_set_label)
        epub_set_layout.addWidget(epub_btn)
        epub_set_layout.addStretch()
        advanced_layout.addLayout(epub_set_layout)
        censor_group_layout = QVBoxLayout()
        censor_group_layout.setSpacing(4)
        censor_group_layout.setContentsMargins(0, 6, 0, 0)
        censor_main_layout = QHBoxLayout()
        censor_main_layout.setSpacing(8)
        censor_main_label = QLabel("세분화된 검열 옵션 활성화", self)
        self.censor_toggle = QCheckBox(self)
        self.censor_toggle.setChecked(False)
        censor_main_label.setCursor(Qt.PointingHandCursor)
        censor_main_label.mousePressEvent = lambda *event: self.censor_toggle.setChecked(not self.censor_toggle.isChecked())
        censor_main_layout.addWidget(censor_main_label)
        censor_main_layout.addWidget(self.censor_toggle)
        censor_main_layout.addStretch()
        censor_group_layout.addLayout(censor_main_layout)
        self.censor_sub_widget = QWidget(self)
        self.censor_sub_widget.setStyleSheet("#trans_back{background-color: transparent;}")
        self.censor_sub_widget.setObjectName("trans_back")
        censor_sub_layout = QVBoxLayout(self.censor_sub_widget)
        censor_sub_layout.setContentsMargins(16, 2, 0, 2)
        censor_sub_layout.setSpacing(4)
        shuffle_layout = QHBoxLayout()
        shuffle_label = QLabel("문맥 검열 방지 - 셔플", self)
        self.shuffle_toggle = QCheckBox(self)
        self.shuffle_toggle.setChecked(True)
        shuffle_label.setCursor(Qt.PointingHandCursor)
        shuffle_label.mousePressEvent = lambda *event: self.shuffle_toggle.setChecked(not self.shuffle_toggle.isChecked())
        shuffle_layout.addWidget(shuffle_label)
        shuffle_layout.addWidget(self.shuffle_toggle)
        shuffle_layout.addStretch()
        censor_sub_layout.addLayout(shuffle_layout)
        mode_layout = QHBoxLayout()
        mode_label = QLabel("검열 모드", self)
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItem("단어 검열", "word")
        self.mode_combo.addItem("줄 검열", "sentence")
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        censor_sub_layout.addLayout(mode_layout)
        papago_layout = QHBoxLayout()
        papago_label = QLabel("검열 항목 파파고 사전 번역 적용", self)
        self.papago_toggle = QCheckBox(self)
        self.papago_toggle.setChecked(False)
        papago_label.setCursor(Qt.PointingHandCursor)
        papago_label.mousePressEvent = lambda *event: self.papago_toggle.setChecked(not self.papago_toggle.isChecked())
        papago_layout.addWidget(papago_label)
        papago_layout.addWidget(self.papago_toggle)
        papago_layout.addStretch()
        censor_sub_layout.addLayout(papago_layout)
        self.censor_sub_widget.setVisible(False)
        self.censor_toggle.toggled.connect(self.censor_sub_widget.setVisible)
        censor_group_layout.addWidget(self.censor_sub_widget)
        censor_group_layout.addStretch()
        raw_description_c = QLabel("새로운 테스트 검열 방식 - 검열 시 단어 유지를 위한 방식\n검열 시 최대 3회 재시도 및, 문장 또는 단어를 사전에 제거하여 검열 확률을 높임.\n문장을 셔플하여 ai가 문맥을 파악하지 못 하게 하여 검열 확률을 높이는 옵션 포함.\n단점 : 문맥 보존 어려움")
        raw_description_c.setWordWrap(True)
        raw_description_c.setObjectName("lbl_original_title")
        censor_group_layout.addWidget(raw_description_c)
        advanced_layout.addLayout(censor_group_layout)
        advanced_layout.addSpacing(6)
        prompt_label = QLabel("사용자 지정 AI 번역 프롬프트", self)
        prompt_label.setObjectName("setting_title_txt")
        advanced_layout.addWidget(prompt_label)
        self.ai_prompt_edit = QTextEdit(self)
        self.ai_prompt_edit.setPlaceholderText("AI 번역 시 사용할 추가 프롬프트를 입력하세요.\n비워두면 기본 번역 프롬프트만 사용합니다.")
        self.ai_prompt_edit.setMinimumHeight(70)
        self.ai_prompt_edit.setMaximumHeight(100)
        self.ai_prompt_edit.setObjectName("detail_description")
        self.ai_prompt_edit.viewport().setStyleSheet("background: transparent;")
        advanced_layout.addWidget(self.ai_prompt_edit)
        link_layout = QHBoxLayout()
        link_layout.setContentsMargins(0, 4, 0, 0)
        link_layout.setSpacing(6)
        def create_link_button(text, url):
            button = QToolButton(self)
            button.setText(text)
            button.setCursor(Qt.PointingHandCursor)
            button.setAutoRaise(True)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setStyleSheet("QToolButton { padding: 4px 6px; font-size: 9pt; }")
            button.setObjectName("link_button")
            button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
            return button
        opinion_button = create_link_button("의견 보내기", "https://minekmj.github.io/Novel-Syosetu-Kakuyomu-Downloader-Translator/opinion/home.html")
        release_button = create_link_button("릴리스", "https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/releases")
        github_button = create_link_button("GitHub", "https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator")
        link_layout.addWidget(opinion_button)
        link_layout.addWidget(release_button)
        link_layout.addWidget(github_button)
        link_layout.addStretch()
        link_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        advanced_layout.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Expanding))
        hr_line = QFrame(self)
        hr_line.setFrameShape(QFrame.HLine)
        hr_line.setFrameShadow(QFrame.Sunken)
        hr_line.setObjectName("hr_line")
        advanced_layout.addWidget(hr_line)
        advanced_layout.addLayout(link_layout)
        v_label = QLabel("현재 버전 : " + vsc.V, self)
        v_label.setObjectName("lbl_original_title")
        advanced_layout.addWidget(v_label)
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

    def open_epub_settings(self):
        dlg = ep.EpubSettingsDialog(self.epub_data, self)
        if dlg.exec():
            self.epub_data = dlg.get_config()

    def set_epub_data(self, data):
        self.epub_data = ep.merge_epub_data(data)

    def get_epub_data(self):
        try:
            return self.epub_data["epub_data"]
        except:
            return None

    def browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if directory:
            self.path_edit.setText(directory)

    def get_theme_display_name(self):
        return self.theme_combo.currentText()

    def get_raw_text(self):
        return self.raw_text_toggle.isChecked()

    def get_origin_name(self):
        return self.origin_name_toggle.isChecked()

    def get_ai_prompt(self):
        return self.ai_prompt_edit.toPlainText().strip()

    def get_censor_advanced(self):
        return self.censor_toggle.isChecked()

    def get_censor_shuffle(self):
        return self.shuffle_toggle.isChecked()

    def get_censor_mode(self):
        return self.mode_combo.currentData()

    def get_censor_papago(self):
        return self.papago_toggle.isChecked()