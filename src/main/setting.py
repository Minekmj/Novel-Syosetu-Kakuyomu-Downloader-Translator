
import os
from PySide6.QtWidgets import (
    QDialog, QSizePolicy, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QTextEdit, QTabWidget, QGroupBox, QScrollArea, QFrame,
    QFileDialog
)
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
import src.system.v as vsc
import src.main.epub_setting as ep
import src.main.update as im
try:
    import src.system.data as data_iteam
except ImportError:
    data_iteam = None


def export_env_settings(settings_dict):
    if not isinstance(settings_dict, dict):
        return
    for data_name, val in settings_dict.items():
        type_s = type(val)
        if type_s == bool:
            os.environ[f"minedown_setting_{data_name}"] = str(val)
        elif type_s == str:
            if "\n" not in val and "\r" not in val:
                os.environ[f"minedown_setting_{data_name}"] = val
        elif type_s == int or type_s == float:
            os.environ[f"minedown_setting_{data_name}"] = str(val)


class BaseSettingItem:
    def __init__(self, key, default=None):
        self.key = key
        self.default = default
        self.widget = None

    def get_value(self):
        return self.default

    def set_value(self, value):
        pass


class SettingPathEdit(BaseSettingItem):
    def __init__(self, key, default="", placeholder="저장 폴더를 선택하세요", parent=None):
        super().__init__(key, default)
        self.parent = parent
        self.widget = QWidget(parent)
        self.widget.setObjectName("noback")
        layout = QHBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.edit = QLineEdit(self.widget)
        self.edit.setPlaceholderText(placeholder)
        self.edit.setReadOnly(True)

        self.btn = QPushButton("찾기", self.widget)
        self.btn.setObjectName("secondaryBtn")
        self.btn.clicked.connect(self.browse)

        layout.addWidget(self.edit)
        layout.addWidget(self.btn)

    def browse(self):
        directory = QFileDialog.getExistingDirectory(self.parent, "저장 폴더 선택", self.edit.text().strip())
        if directory:
            self.edit.setText(directory)

    def get_value(self):
        return self.edit.text().strip()

    def set_value(self, value):
        self.edit.setText(str(value) if value is not None else self.default)


class SettingCheckBox(BaseSettingItem):
    def __init__(self, key, text="", default=False, clickable_label=False, parent=None):
        super().__init__(key, default)
        self.text = text
        self.clickable_label = clickable_label
        self.checkbox = QCheckBox(parent)
        self.checkbox.setChecked(default)

        if clickable_label:
            self.widget = QWidget(parent)
            self.widget.setObjectName("noback")
            
            layout = QHBoxLayout(self.widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
            self.label = QLabel(text, self.widget)
            self.label.setCursor(Qt.PointingHandCursor)
            self.label.mousePressEvent = lambda *_: self.checkbox.setChecked(not self.checkbox.isChecked())
            layout.addWidget(self.label)
            layout.addWidget(self.checkbox)
            layout.addStretch()
        else:
            self.checkbox.setText(text)
            self.widget = self.checkbox

    def get_value(self):
        return self.checkbox.isChecked()

    def set_value(self, value):
        self.checkbox.setChecked(bool(value) if value is not None else self.default)


class SettingComboBox(BaseSettingItem):
    def __init__(self, key, label_text="", items=None, default=None, stretch=False, parent=None):
        super().__init__(key, default)
        self.widget = QWidget(parent)
        self.widget.setObjectName("noback")
        
        layout = QHBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        if label_text:
            self.label = QLabel(label_text, self.widget)
            layout.addWidget(self.label)

        self.combo = QComboBox(self.widget)
        if stretch:
            layout.addWidget(self.combo, 1)
        else:
            layout.addWidget(self.combo)
            layout.addStretch()

        if items:
            self.set_items(items)

    def set_items(self, items):
        self.combo.clear()
        if isinstance(items, dict):
            for k, v in items.items():
                self.combo.addItem(str(k), v)
        elif isinstance(items, (list, tuple)):
            for item in items:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    self.combo.addItem(str(item[0]), item[1])
                else:
                    self.combo.addItem(str(item), item)

    def get_value(self):
        data = self.combo.currentData()
        if data is not None:
            return data
        return self.combo.currentText()

    def set_value(self, value):
        if value is None:
            value = self.default
        idx = self.combo.findData(value)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
            return
        idx = self.combo.findText(str(value))
        if idx >= 0:
            self.combo.setCurrentIndex(idx)


class SettingTextEdit(BaseSettingItem):
    def __init__(self, key, default="", placeholder="", min_height=70, parent=None):
        super().__init__(key, default)
        self.text_edit = QTextEdit(parent)
        self.text_edit.setPlaceholderText(placeholder)
        self.text_edit.setMinimumHeight(min_height)
        self.text_edit.setObjectName("detail_description")
        self.text_edit.viewport().setStyleSheet("background: transparent;")
        self.widget = self.text_edit

    def get_value(self):
        return self.text_edit.toPlainText().strip()

    def set_value(self, value):
        self.text_edit.setPlainText(str(value) if value is not None else self.default)


class BaseSettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []

    def register_item(self, item):
        self._items.append(item)
        return item

    def set_data(self, data):
        if not isinstance(data, dict):
            return
        for item in self._items:
            if item.key in data:
                item.set_value(data[item.key])

    def get_data(self):
        result = {}
        for item in self._items:
            result[item.key] = item.get_value()
        return result


class GeneralTab(BaseSettingsTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        path_group = QGroupBox("기본 저장 경로")
        path_group.setObjectName('group_box')
        path_layout = QVBoxLayout(path_group)
        self.path_item = self.register_item(
            SettingPathEdit("src", default="", placeholder="저장 폴더를 선택하세요", parent=self)
        )
        path_layout.addWidget(self.path_item.widget)
        layout.addWidget(path_group)

        theme_group = QGroupBox("테마")
        theme_group.setObjectName('group_box')
        theme_layout = QVBoxLayout(theme_group)
        self.theme_item = self.register_item(
            SettingComboBox("theme", label_text="테마 선택:", stretch=True, default="DARK", parent=self)
        )
        self._refresh_theme_items()
        theme_layout.addWidget(self.theme_item.widget)
        layout.addWidget(theme_group)

        layout.addStretch()

    def _refresh_theme_items(self):
        if data_iteam:
            data_iteam.rest()
            items = [(k, v) for k, v in data_iteam.THEME_DATA.items()]
            self.theme_item.set_items(items)
            inv_map = {v: k for k, v in data_iteam.THEME_DATA.items()}
            current_theme = inv_map.get(data_iteam.THEME_NAME, None)
            if current_theme:
                self.theme_item.combo.setCurrentText(current_theme)

    def set_data(self, data):
        self._refresh_theme_items()
        super().set_data(data)


class DownloadTab(BaseSettingsTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.epub_data = ep.merge_epub_data(None)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        down_group = QGroupBox("다운로드 파일 옵션")
        down_group.setObjectName('group_box')
        down_layout = QVBoxLayout(down_group)
        down_layout.setSpacing(8)

        self.origin_name_item = self.register_item(
            SettingCheckBox("origin_name", text="원문 제목으로 파일 저장", default=False, parent=self)
        )
        down_layout.addWidget(self.origin_name_item.widget)
        
        self.no_change_text_item = self.register_item(
            SettingCheckBox("change_no_mark", text="따옴표 자동 변경 금지", default=False, parent=self)
        )
        down_layout.addWidget(self.no_change_text_item.widget)

        self.raw_text_item = self.register_item(
            SettingCheckBox("RAW_TEXT", text="원문(RAW) 다운로드", default=False, parent=self)
        )
        down_layout.addWidget(self.raw_text_item.widget)
        
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

    def open_epub_settings(self):
        dlg = ep.EpubSettingsDialog(self.epub_data, self)
        if dlg.exec():
            self.epub_data = dlg.get_config()

    def set_data(self, data):
        super().set_data(data)
        if isinstance(data, dict) and "epub_data" in data:
            self.epub_data = ep.merge_epub_data(data["epub_data"])

    def get_data(self):
        data = super().get_data()
        try:
            val = self.epub_data.get("epub_data") if isinstance(self.epub_data, dict) else self.epub_data
            data["epub_data"] = val
        except Exception:
            data["epub_data"] = None
        return data


class TranslationTab(BaseSettingsTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        prompt_group = QGroupBox("사용자 지정 AI 프롬프트")
        prompt_group.setObjectName('group_box')
        prompt_layout = QVBoxLayout(prompt_group)
        self.ai_prompt_item = self.register_item(
            SettingTextEdit(
                "AI_PROMPT",
                placeholder="AI 번역 시 사용할 추가 프롬프트를 입력하세요.\n비워두면 기본 번역 프롬프트만 사용합니다.",
                parent=self
            )
        )
        prompt_layout.addWidget(self.ai_prompt_item.widget)
        layout.addWidget(prompt_group)

        censor_group = QGroupBox("AI 검열 우회 및 방지 옵션")
        censor_group.setObjectName('group_box')
        censor_layout = QVBoxLayout(censor_group)
        censor_layout.setSpacing(10)

        self.censor_item = self.register_item(
            SettingCheckBox("CENSOR_ADVANCED", text="세분화된 검열 옵션 활성화", default=False, clickable_label=True, parent=self)
        )
        censor_layout.addWidget(self.censor_item.widget)

        self.censor_sub_widget = QWidget(self)
        self.censor_sub_widget.setMinimumHeight(0)
        self.censor_sub_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.censor_sub_widget.setStyleSheet("#trans_back{background-color: transparent;}")
        self.censor_sub_widget.setObjectName("trans_back")
        censor_sub_layout = QVBoxLayout(self.censor_sub_widget)
        censor_sub_layout.setContentsMargins(16, 2, 0, 2)
        censor_sub_layout.setSpacing(4)

        self.shuffle_item = self.register_item(
            SettingCheckBox("CENSOR_SHUFFLE", text="문맥 검열 방지 - 셔플", default=True, clickable_label=True, parent=self)
        )
        censor_sub_layout.addWidget(self.shuffle_item.widget)

        mode_items = [("단어 검열", "word"), ("줄 검열", "sentence")]
        self.mode_item = self.register_item(
            SettingComboBox("CENSOR_MODE", label_text="검열 모드", items=mode_items, default="word", stretch=False, parent=self)
        )
        censor_sub_layout.addWidget(self.mode_item.widget)

        self.papago_item = self.register_item(
            SettingCheckBox("CENSOR_PAPAGO", text="검열 항목 파파고 사전 번역 적용", default=False, clickable_label=True, parent=self)
        )
        censor_sub_layout.addWidget(self.papago_item.widget)

        self.censor_sub_widget.setVisible(False)
        self.censor_item.checkbox.toggled.connect(self.censor_sub_widget.setVisible)
        censor_layout.addWidget(self.censor_sub_widget)

        censor_desc = QLabel("※ 단어 유지 및 재시도(최대 3회), 셔플을 통해 AI 검열 회피율을 높입니다.\n(단, 셔플 활성화 시 문맥 흐름이 부자연스러울 수 있습니다.)")
        censor_desc.setObjectName("lbl_original_title")
        censor_desc.setWordWrap(True)
        censor_layout.addWidget(censor_desc)

        layout.addWidget(censor_group)
        layout.addStretch()

        scroll.setWidget(widget)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def set_data(self, data):
        super().set_data(data)
        self.censor_sub_widget.setVisible(self.censor_item.get_value())


class InfoTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        version_str = getattr(vsc, 'V', 'Unknown')
        version_label = QLabel(f"<b>MINE DOWNLOADER</b><br>{version_str}")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        layout.addSpacing(10)

        link_layout = QHBoxLayout()
        link_layout.setSpacing(12)

        def create_link_btn(text, url: str):
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

        link_layout.addStretch(1)
        link_layout.addWidget(btn_opinion)
        link_layout.addWidget(btn_release)
        link_layout.addWidget(btn_github)
        link_layout.addWidget(btn_update)
        link_layout.addStretch(1)

        layout.addLayout(link_layout)
        layout.addStretch()

    def set_data(self, data):
        pass

    def get_data(self):
        return {}


class PathSettingsDialog(QDialog):
    def __init__(self, initial_data=None, parent=None):
        if isinstance(initial_data, QWidget) and parent is None:
            parent = initial_data
            initial_data = None
        super().__init__(parent)
        self.setWindowTitle("환경 설정")
        self.resize(580, 520)
        self.setMinimumSize(500, 420)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setObjectName("settingsTab")
        main_layout.addWidget(self.tab_widget)

        self.general_tab = GeneralTab(self)
        self.download_tab = DownloadTab(self)
        self.translation_tab = TranslationTab(self)
        self.info_tab = InfoTab(self)

        self.tab_widget.addTab(self.general_tab, "일반")
        self.tab_widget.addTab(self.download_tab, "다운로드 / 출력")
        self.tab_widget.addTab(self.translation_tab, "번역 / 검열")
        self.tab_widget.addTab(self.info_tab, "정보")

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

        if initial_data:
            self.set_data(initial_data)

    def set_data(self, data):
        if not isinstance(data, dict):
            return
        self.general_tab.set_data(data)
        self.download_tab.set_data(data)
        self.translation_tab.set_data(data)
        self.info_tab.set_data(data)

    def get_data(self):
        result = {}
        result.update(self.general_tab.get_data())
        result.update(self.download_tab.get_data())
        result.update(self.translation_tab.get_data())
        result.update(self.info_tab.get_data())
        export_env_settings(result)
        return result

    @property
    def path_edit(self):
        return self.general_tab.path_item.edit

    @property
    def theme_combo(self):
        return self.general_tab.theme_item.combo

    @property
    def origin_name_toggle(self):
        return self.download_tab.origin_name_item.checkbox

    @property
    def raw_text_toggle(self):
        return self.download_tab.raw_text_item.checkbox

    @property
    def epub_data(self):
        return self.download_tab.epub_data

    @epub_data.setter
    def epub_data(self, value):
        self.download_tab.epub_data = value

    @property
    def ai_prompt_edit(self):
        return self.translation_tab.ai_prompt_item.text_edit

    @property
    def censor_toggle(self):
        return self.translation_tab.censor_item.checkbox

    @property
    def censor_sub_widget(self):
        return self.translation_tab.censor_sub_widget

    @property
    def shuffle_toggle(self):
        return self.translation_tab.shuffle_item.checkbox

    @property
    def mode_combo(self):
        return self.translation_tab.mode_item.combo

    @property
    def papago_toggle(self):
        return self.translation_tab.papago_item.checkbox

    def open_epub_settings(self):
        self.download_tab.open_epub_settings()

    def set_epub_data(self, data):
        self.download_tab.set_data({"epub_data": data})

    def get_epub_data(self):
        return self.download_tab.get_data().get("epub_data")

    def browse_folder(self):
        self.general_tab.path_item.browse()

    def get_theme_display_name(self):
        return self.theme_combo.currentText()

    def get_raw_text(self):
        return self.download_tab.raw_text_item.get_value()

    def get_origin_name(self):
        return self.download_tab.origin_name_item.get_value()

    def get_ai_prompt(self):
        return self.translation_tab.ai_prompt_item.get_value()

    def get_censor_advanced(self):
        return self.translation_tab.censor_item.get_value()

    def get_censor_shuffle(self):
        return self.translation_tab.shuffle_item.get_value()

    def get_censor_mode(self):
        return self.translation_tab.mode_item.get_value()

    def get_censor_papago(self):
        return self.translation_tab.papago_item.get_value()