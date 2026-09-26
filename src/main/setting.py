from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QTextEdit, QTabWidget, QGroupBox, QScrollArea, QFrame,
    QFileDialog
)
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
import src.system.v as vsc
import src.main.epub_setting as ep

import src.main.update as im

data_iteam = None


class PathSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("환경 설정")
        self.resize(580, 520)
        self.setMinimumSize(500, 420)

        self.epub_data = ep.merge_epub_data(None)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setObjectName("settingsTab")
        main_layout.addWidget(self.tab_widget)

        self.tab_widget.addTab(self._create_general_tab(), "일반")
        self.tab_widget.addTab(self._create_download_tab(), "다운로드 / 출력")
        self.tab_widget.addTab(self._create_translation_tab(), "번역 / 검열")
        self.tab_widget.addTab(self._create_info_tab(), "정보")

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        cancel_btn = QPushButton("취소", self)
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        save_btn = QPushButton("저장", self)
        save_btn.setObjectName("primaryBtn")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(save_btn)

        main_layout.addLayout(bottom_layout)

    def _create_general_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        path_group = QGroupBox("기본 저장 경로")
        path_group.setObjectName('group_box')
        path_layout = QHBoxLayout(path_group)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("저장 폴더를 선택하세요")
        self.path_edit.setReadOnly(True)
        folder_btn = QPushButton("찾기")
        folder_btn.setObjectName("secondaryBtn")
        folder_btn.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(folder_btn)
        layout.addWidget(path_group)

        theme_group = QGroupBox("테마")
        theme_group.setObjectName('group_box')
        theme_layout = QHBoxLayout(theme_group)
        theme_label = QLabel("테마 선택:")
        self.theme_combo = QComboBox()
        
        if data_iteam and hasattr(data_iteam, "THEME_DATA"):
            self.theme_combo.addItems(list(data_iteam.THEME_DATA.keys()))
            inv_map = {v: k for k, v in data_iteam.THEME_DATA.items()}
            current_theme = inv_map.get(getattr(data_iteam, "THEME_NAME", ""), None)
            if current_theme:
                self.theme_combo.setCurrentText(current_theme)

        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo, 1)
        layout.addWidget(theme_group)

        layout.addStretch()
        return widget

    def _create_download_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        down_group = QGroupBox("다운로드 파일 옵션")
        down_group.setObjectName('group_box')
        down_layout = QVBoxLayout(down_group)
        down_layout.setSpacing(8)

        self.origin_name_toggle = QCheckBox("원문 제목으로 파일 저장")
        down_layout.addWidget(self.origin_name_toggle)

        self.raw_text_toggle = QCheckBox("원문(RAW) 다운로드")
        down_layout.addWidget(self.raw_text_toggle)

        raw_desc = QLabel("• 줄바꿈 구조를 원문 그대로 유지하여 TXT로 함께 저장합니다.\n• AI 번역 시에도 원문 줄바꿈 기준을 유지합니다.")
        raw_desc.setObjectName("lbl_original_title")
        raw_desc.setWordWrap(True)
        down_layout.addWidget(raw_desc)
        layout.addWidget(down_group)

        epub_group = QGroupBox("EPUB 설정")
        epub_group.setObjectName('group_box')
        epub_layout = QHBoxLayout(epub_group)
        epub_label = QLabel("EPUB 서식 및 본문 레이아웃 설정")
        epub_btn = QPushButton("EPUB 상세 설정")
        epub_btn.setObjectName("secondaryBtn")
        epub_btn.clicked.connect(self.open_epub_settings)
        epub_layout.addWidget(epub_label)
        epub_layout.addStretch()
        epub_layout.addWidget(epub_btn)
        layout.addWidget(epub_group)

        layout.addStretch()
        return widget

    def _create_translation_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        prompt_group = QGroupBox("사용자 지정 AI 프롬프트")
        prompt_group.setObjectName('group_box')
        prompt_layout = QVBoxLayout(prompt_group)
        self.ai_prompt_edit = QTextEdit(self)
        self.ai_prompt_edit.setPlaceholderText("AI 번역 시 사용할 추가 프롬프트를 입력하세요.\n비워두면 기본 번역 프롬프트만 사용합니다.")
        self.ai_prompt_edit.setMinimumHeight(70)
        self.ai_prompt_edit.setMaximumHeight(100)
        self.ai_prompt_edit.setObjectName("detail_description")
        self.ai_prompt_edit.viewport().setStyleSheet("background: transparent;")
        prompt_layout.addWidget(self.ai_prompt_edit)
        layout.addWidget(prompt_group)

        censor_group = QGroupBox("AI 검열 우회 및 방지 옵션")
        censor_group.setObjectName('group_box')
        censor_layout = QVBoxLayout(censor_group)
        censor_layout.setSpacing(10)
        
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
        censor_layout.addLayout(censor_main_layout)
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
        censor_layout.addWidget(self.censor_sub_widget)
        censor_layout.addStretch()

        censor_desc = QLabel("※ 단어 유지 및 재시도(최대 3회), 셔플을 통해 AI 검열 회피율을 높입니다.\n(단, 셔플 활성화 시 문맥 흐름이 부자연스러울 수 있습니다.)")
        censor_desc.setObjectName("lbl_original_title")
        censor_desc.setWordWrap(True)
        censor_layout.addWidget(censor_desc)

        layout.addWidget(censor_group)
        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _create_info_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        version_str = getattr(vsc, 'V', 'Unknown')
        version_label = QLabel(f"<b>MINE DOWNLOADER</b><br>{version_str}")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        layout.addSpacing(10)

        link_layout = QHBoxLayout()
        link_layout.setSpacing(12)

        def create_link_btn(text, url:str):
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            if "UpdateView" == url:
                btn.clicked.connect(lambda: im.UpdateView(self).show())
            else: 
                btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
            return btn

        btn_opinion = create_link_btn("의견 보내기", "https://minekmj.github.io/Novel-Syosetu-Kakuyomu-Downloader-Translator/opinion/home.html")
        btn_release = create_link_btn("릴리즈", "https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/releases")
        btn_github = create_link_btn("GitHub", "https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator")
        
        btn_update = create_link_btn("업데이트 내역", "UpdateView")

        link_layout.addWidget(btn_opinion)
        link_layout.addWidget(btn_release)
        link_layout.addWidget(btn_github)
        link_layout.addWidget(btn_update)
        layout.addLayout(link_layout)

        layout.addStretch()
        return widget

    def open_epub_settings(self):
        dlg = ep.EpubSettingsDialog(self.epub_data, self)
        if dlg.exec():
            self.epub_data = dlg.get_config()

    def set_epub_data(self, data):
        self.epub_data = ep.merge_epub_data(data)

    def get_epub_data(self):
        try:
            return self.epub_data.get("epub_data") if isinstance(self.epub_data, dict) else None
        except Exception:
            return None

    def browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "저장 폴더 선택", self.path_edit.text())
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