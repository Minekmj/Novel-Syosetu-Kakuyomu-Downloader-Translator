from PySide6.QtWidgets import (
    QFrame, QGridLayout, QListWidget, QListWidgetItem, QSizePolicy, QTabWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QFileDialog, QDialog, QMessageBox, QTextEdit, QComboBox,
    QProgressBar, QScrollArea, QWidget
)
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtCore import Qt

import html
import os
import json
import re

from src.system.data import open_folder, return_theme, load_data, save_data
from src.main.thread_pyqt import TranslateThread, ModelLoadThread, trans_ai
import src.trans.trans_check_jp as check_jp
from src.trans.trans_glossary import *

check_jp.trans_ai = trans_ai

OUT = "./out/"


class PasteOnlyLineEdit(QLineEdit):
    def keyPressEvent(self, event: QKeyEvent):
        if (
            event.matches(QKeySequence.StandardKey.Paste)
            or event.matches(QKeySequence.StandardKey.Copy)
            or event.matches(QKeySequence.StandardKey.SelectAll)
        ):
            super().keyPressEvent(event)
        else:
            event.ignore()


class PresetLoadDialog(QDialog):
    def __init__(self, presets, parent=None):
        super().__init__(parent)
        self.setWindowTitle('프리셋 불러오기')
        self.resize(560, 400)
        self.setMinimumSize(500, 360)
        self.presets = presets
        self.selected_name = ''

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel('프리셋 불러오기')
        title.setObjectName('dialogTitle')
        layout.addWidget(title)

        subtitle = QLabel('저장된 프리셋을 선택하세요.')
        subtitle.setObjectName('secondaryInfo')
        layout.addWidget(subtitle)

        content = QHBoxLayout()
        content.setSpacing(10)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName('presetList')
        self.list_widget.setMinimumWidth(230)
        self.list_widget.setSpacing(2)
        self.list_widget.addItems(sorted(self.presets.keys()))
        self.list_widget.currentItemChanged.connect(self.on_preset_selected)
        self.list_widget.itemDoubleClicked.connect(self.accept_selected)
        content.addWidget(self.list_widget, 1)

        self.model_list = QListWidget()
        self.model_list.setObjectName('presetModelList')
        self.model_list.setMinimumWidth(230)
        self.model_list.setSpacing(2)
        self.model_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        content.addWidget(self.model_list, 1)

        layout.addLayout(content, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(7)

        self.delete_btn = QPushButton('삭제')
        self.delete_btn.setObjectName('subtleBtn')
        self.delete_btn.setMinimumHeight(34)
        self.delete_btn.setEnabled(False)

        cancel_btn = QPushButton('취소')
        cancel_btn.setMinimumHeight(34)

        load_btn = QPushButton('불러오기')
        load_btn.setObjectName('primaryBtn')
        load_btn.setMinimumHeight(36)
        load_btn.setMinimumWidth(90)

        self.delete_btn.clicked.connect(self.delete_selected)
        cancel_btn.clicked.connect(self.reject)
        load_btn.clicked.connect(self.accept_selected)

        buttons.addWidget(self.delete_btn)
        buttons.addStretch(1)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(load_btn)
        layout.addLayout(buttons)

        self.setStyleSheet('''
            QListWidget#presetList,
            QListWidget#presetModelList {
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                background: transparent;
                outline: none;
                padding: 4px;
            }

            QListWidget#presetList::item,
            QListWidget#presetModelList::item {
                min-height: 34px;
                padding: 5px 9px;
                border-radius: 6px;
            }

            QListWidget#presetList::item:hover {
                background: rgba(255, 255, 255, 0.05);
            }

            QListWidget#presetList::item:selected {
                background: rgba(255, 255, 255, 0.09);
            }

            QListWidget#presetModelList::item {
                color: palette(text);
            }

            QPushButton {
                min-height: 34px;
                padding-left: 11px;
                padding-right: 11px;
            }
        ''')

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def on_preset_selected(self, current, previous=None):
        self.model_list.clear()
        if current is None:
            self.delete_btn.setEnabled(False)
            return

        name = current.text()
        if name not in self.presets:
            self.delete_btn.setEnabled(False)
            return

        self.delete_btn.setEnabled(True)
        preset = self.presets.get(name)
        if not isinstance(preset, dict):
            return

        models = preset.get('selected_models') or preset.get('models') or []
        if isinstance(models, dict):
            models = [models]

        model_names = []
        for model in models:
            if isinstance(model, dict):
                model_name = model.get('model') or model.get('name') or ''
            else:
                model_name = str(model)
            model_name = str(model_name).strip()
            if model_name and model_name.casefold() not in {x.casefold() for x in model_names}:
                model_names.append(model_name)

        if not model_names:
            model_name = preset.get('model') or preset.get('model_name') or ''
            if model_name:
                model_names.append(str(model_name).strip())

        for model_name in model_names:
            item = QListWidgetItem(model_name)
            self.model_list.addItem(item)

    def accept_selected(self, *args):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, '알림', '프리셋을 선택하세요.')
            return

        name = item.text()
        if name not in self.presets:
            QMessageBox.warning(self, '알림', '선택한 프리셋을 찾을 수 없습니다.')
            return

        self.selected_name = name
        self.accept()

    def delete_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return

        name = item.text()
        if name not in self.presets:
            return

        result = QMessageBox.question(
            self,
            '프리셋 삭제',
            f"「{name}」 프리셋을 삭제하시겠습니까?\n삭제한 프리셋은 복구할 수 없습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        if name in self.presets:
            del self.presets[name]

        parent = self.parent()
        settings_file = parent.SETTINGS_FILE
        try:
            data = {}
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            if 'pre' in data and isinstance(data['pre'], dict):
                if name in data['pre']:
                    del data['pre'][name]
                with open(settings_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.critical(self, '저장 오류', f'프리셋 삭제 저장 중 오류가 발생했습니다: {e}')

        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
        self.model_list.clear()

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(min(row, self.list_widget.count() - 1))
        else:
            self.delete_btn.setEnabled(False)

        self.selected_name = ''

        if parent is not None:
            if hasattr(parent, 'preset_status') and hasattr(parent, 'preset_name_edit'):
                if parent.preset_name_edit.text().strip() == name:
                    parent.preset_name_edit.clear()
                    parent.preset_status.setText('현재 프리셋 없음')
            if hasattr(parent, 'add_log'):
                parent.add_log(f"프리셋 삭제 완료: {name}")


class TranslateDialog(QDialog):
    SETTINGS_FILE = './data.json'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_trans = False
        self.is_stop = False
        self.file_path = ''
        self.file_title = ''
        self.current_dictionary = {}
        self.selected_models = []
        self.active_model_index = -1
        self.glossary_enabled = True
        self.thread = None
        self.model_load_thread = None
        self.log_history = []

        self.setWindowTitle('AI 번역')
        self.resize(920, 710)
        self.setMinimumSize(920, 710)
        self.setAcceptDrops(True)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        top_file_layout = QVBoxLayout()
        top_file_layout.setContentsMargins(0, 0, 0, 0)
        top_file_layout.setSpacing(5)

        self.drop_label = QLabel('TXT 또는 JSON 파일을 여기에 드래그하세요')
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setObjectName('dropArea')
        self.drop_label.setMinimumHeight(48)
        self.drop_label.setMaximumHeight(54)
        top_file_layout.addWidget(self.drop_label)

        file_layout = QHBoxLayout()
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(7)

        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText('번역할 TXT 또는 JSON 파일 선택')
        self.file_edit.setMinimumHeight(35)

        browse_btn = QPushButton('파일 찾기')
        browse_btn.setObjectName('subtleBtn')
        browse_btn.setFixedHeight(35)
        browse_btn.clicked.connect(self.browse_file)

        file_layout.addWidget(self.file_edit, 1)
        file_layout.addWidget(browse_btn)
        top_file_layout.addLayout(file_layout)
        root.addLayout(top_file_layout)

        main_hlayout = QHBoxLayout()
        main_hlayout.setContentsMargins(0, 0, 0, 0)
        main_hlayout.setSpacing(14)

        left_widget = QWidget()
        left_widget.setObjectName('no_back-leftWidget')
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        model_add_layout = QHBoxLayout()
        model_add_layout.setContentsMargins(0, 0, 0, 0)
        model_add_layout.setSpacing(7)

        model_label = QLabel('모델')
        model_label.setFixedWidth(36)

        self.model_add_combo = QComboBox()
        self.model_add_combo.setMinimumHeight(35)
        self.model_add_combo.setPlaceholderText('Gemini 모델 선택')
        self.model_combo = self.model_add_combo

        add_model_btn = QPushButton('추가')
        add_model_btn.setObjectName('subtleBtn')
        add_model_btn.setFixedHeight(35)
        add_model_btn.setFixedWidth(56)
        add_model_btn.clicked.connect(self.add_selected_model)

        self.refresh_model_btn = QPushButton('새로고침')
        self.refresh_model_btn.setObjectName('subtleBtn')
        self.refresh_model_btn.setFixedHeight(35)
        self.refresh_model_btn.setFixedWidth(76)
        self.refresh_model_btn.clicked.connect(self.load_gemini_models)

        model_add_layout.addWidget(model_label)
        model_add_layout.addWidget(self.model_add_combo, 1)
        model_add_layout.addWidget(add_model_btn)
        model_add_layout.addWidget(self.refresh_model_btn)
        left_layout.addLayout(model_add_layout)

        used_title = QLabel('사용 모델 목록')
        used_title.setObjectName('subLabel')
        left_layout.addWidget(used_title)

        self.model_list_container = QWidget()
        self.model_list_container.setObjectName('no_back-modelListContainer')
        self.model_list_layout = QVBoxLayout(self.model_list_container)
        self.model_list_layout.setContentsMargins(0, 0, 0, 0)
        self.model_list_layout.setSpacing(4)

        self.model_scroll = QScrollArea()
        self.model_scroll.setObjectName('no_back-modelScroll')
        self.model_scroll.setWidgetResizable(True)
        self.model_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.model_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.model_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.model_scroll.setWidget(self.model_list_container)
        self.model_scroll.setFixedHeight(112)
        left_layout.addWidget(self.model_scroll)

        self.settings_tab = QTabWidget()
        self.settings_tab.setObjectName('no_back-settingsTab')
        self.settings_tab.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.settings_tab.setAutoFillBackground(False)
        tab_params = QWidget()
        tab_params.setObjectName('no_back-tabParams')
        tab_params_layout = QVBoxLayout(tab_params)
        tab_params_layout.setContentsMargins(6, 8, 6, 6)
        tab_params_layout.setSpacing(7)

        cur_model_hlayout = QHBoxLayout()
        cur_model_hlayout.setContentsMargins(0, 0, 0, 0)
        cur_model_hlayout.setSpacing(7)

        cur_lbl = QLabel('선택 모델')
        cur_lbl.setObjectName('optionLabel')

        self.selected_model_edit = QLineEdit()
        self.selected_model_edit.setObjectName('selectedModelDisplay')
        self.selected_model_edit.setReadOnly(True)
        self.selected_model_edit.setMinimumHeight(35)
        self.selected_model_edit.setPlaceholderText('위 사용 모델 목록에서 모델을 선택하세요')

        cur_model_hlayout.addWidget(cur_lbl)
        cur_model_hlayout.addWidget(self.selected_model_edit, 1)
        tab_params_layout.addLayout(cur_model_hlayout)

        option_grid = QGridLayout()
        option_grid.setContentsMargins(0, 0, 0, 0)
        option_grid.setHorizontalSpacing(8)
        option_grid.setVerticalSpacing(7)

        lbl_rpm = QLabel('RPM')
        lbl_temp = QLabel('Temperature')
        lbl_conc = QLabel('동시 작업')
        lbl_chars = QLabel('청크 글자수')
        lbl_br = QLabel('분할 시작')
        lbl_censor = QLabel('검열하기')

        for label in [lbl_rpm, lbl_temp, lbl_conc, lbl_chars, lbl_br, lbl_censor]:
            label.setObjectName('optionLabel')

        self.rpm_combo = QComboBox()
        self.rpm_combo.addItems(['1', '2', '3', '5', '7', '10', '15', '20', '30', '60'])
        self.rpm_combo.setCurrentText('15')
        self.rpm_combo.setMinimumHeight(35)

        self.temp_combo = QComboBox()
        self.temp_combo.addItems(['0.0', '0.1', '0.2', '0.3', '0.5', '0.7', '1.0'])
        self.temp_combo.setCurrentText('0.1')
        self.temp_combo.setMinimumHeight(35)

        self.concurrency_combo = QComboBox()
        self.concurrency_combo.addItems([str(i) for i in range(1, 16)])
        self.concurrency_combo.setCurrentText('4')
        self.concurrency_combo.setMinimumHeight(35)

        self.chars_combo = QComboBox()
        self.chars_combo.addItems(['500', '1000', '2000', '3000', '4000', '5000', '7000', '10000', '15000', '20000', '30000'])
        self.chars_combo.setCurrentText('5000')
        self.chars_combo.setMinimumHeight(35)

        self.br_start_combo = QComboBox()
        self.br_start_combo.addItems(['0', '1', '2', '3', '4'])
        self.br_start_combo.setCurrentText('0')
        self.br_start_combo.setMinimumHeight(35)

        self.censor_combo = QComboBox()
        self.censor_combo.addItems(['사용', '사용 안함'])
        self.censor_combo.setCurrentText('사용')
        self.censor_combo.setMinimumHeight(35)
        self.censor_combo.setToolTip('사용: 검열 시도 후 분할 / 사용 안함: 검열 건너뛰고 바로 분할(isno_x)')

        option_grid.addWidget(lbl_rpm, 0, 0)
        option_grid.addWidget(self.rpm_combo, 0, 1)
        option_grid.addWidget(lbl_temp, 0, 2)
        option_grid.addWidget(self.temp_combo, 0, 3)

        option_grid.addWidget(lbl_conc, 1, 0)
        option_grid.addWidget(self.concurrency_combo, 1, 1)
        option_grid.addWidget(lbl_chars, 1, 2)
        option_grid.addWidget(self.chars_combo, 1, 3)

        option_grid.addWidget(lbl_br, 2, 0)
        option_grid.addWidget(self.br_start_combo, 2, 1)
        option_grid.addWidget(lbl_censor, 2, 2)
        option_grid.addWidget(self.censor_combo, 2, 3)

        self.rpm_combo.currentTextChanged.connect(self.update_active_model)
        self.temp_combo.currentTextChanged.connect(self.update_active_model)
        self.concurrency_combo.currentTextChanged.connect(self.update_active_model)
        self.br_start_combo.currentTextChanged.connect(self.update_active_model)
        self.censor_combo.currentTextChanged.connect(self.update_active_model)

        tab_params_layout.addLayout(option_grid)
        tab_params_layout.addStretch(1)
        self.settings_tab.addTab(tab_params, '매개변수')

        tab_dict = QWidget()
        tab_dict.setObjectName('no_back-tabDict')
        tab_dict_layout = QVBoxLayout(tab_dict)
        tab_dict_layout.setContentsMargins(6, 8, 6, 6)
        tab_dict_layout.setSpacing(8)

        dictionary_layout = QHBoxLayout()
        dictionary_layout.setContentsMargins(0, 0, 0, 0)
        dictionary_layout.setSpacing(7)

        self.dictionary_status = QLabel('선택된 작품 없음')
        self.dictionary_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.dictionary_status.setWordWrap(True)

        self.dictionary_btn = QPushButton('설정')
        self.dictionary_btn.setObjectName('subtleBtn')
        self.dictionary_btn.setFixedHeight(35)
        self.dictionary_btn.setFixedWidth(58)
        self.dictionary_btn.clicked.connect(self.open_dictionary_dialog)

        dictionary_layout.addWidget(self.dictionary_status, 1)
        dictionary_layout.addWidget(self.dictionary_btn)
        tab_dict_layout.addLayout(dictionary_layout)

        glossary_toggle_layout = QHBoxLayout()
        glossary_toggle_layout.setContentsMargins(0, 0, 0, 0)
        glossary_toggle_layout.setSpacing(8)

        glossary_label = QLabel('번역에 용어집 사용')
        glossary_toggle_layout.addWidget(glossary_label)
        glossary_toggle_layout.addStretch(1)

        self.glossary_toggle_btn = QPushButton()
        self.glossary_toggle_btn.setCheckable(True)
        self.glossary_toggle_btn.setFixedHeight(35)
        self.glossary_toggle_btn.setFixedWidth(78)
        self.glossary_toggle_btn.clicked.connect(self.toggle_glossary)

        glossary_toggle_layout.addWidget(self.glossary_toggle_btn)
        tab_dict_layout.addLayout(glossary_toggle_layout)
        tab_dict_layout.addStretch(1)
        self.settings_tab.addTab(tab_dict, '용어집')

        tab_pre = QWidget()
        tab_pre.setObjectName('no_back-tabPre')
        tab_pre_layout = QVBoxLayout(tab_pre)
        tab_pre_layout.setContentsMargins(6, 8, 6, 6)
        tab_pre_layout.setSpacing(8)

        preset_layout = QHBoxLayout()
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(7)

        self.preset_name_edit = QLineEdit()
        self.preset_name_edit.setPlaceholderText('프리셋 이름')
        self.preset_name_edit.setMinimumHeight(35)

        preset_save_btn = QPushButton('저장')
        preset_save_btn.setObjectName('subtleBtn')
        preset_save_btn.setFixedHeight(35)
        preset_save_btn.setFixedWidth(58)
        preset_save_btn.clicked.connect(self.save_preset)

        preset_load_btn = QPushButton('불러오기')
        preset_load_btn.setObjectName('subtleBtn')
        preset_load_btn.setFixedHeight(35)
        preset_load_btn.setFixedWidth(76)
        preset_load_btn.clicked.connect(self.load_preset)

        preset_layout.addWidget(self.preset_name_edit, 1)
        preset_layout.addWidget(preset_save_btn)
        preset_layout.addWidget(preset_load_btn)
        tab_pre_layout.addLayout(preset_layout)

        self.preset_status = QLabel('현재 프리셋 없음')
        self.preset_status.setObjectName('secondaryInfo')
        tab_pre_layout.addWidget(self.preset_status)
        tab_pre_layout.addStretch(1)
        self.settings_tab.addTab(tab_pre, '프리셋')

        tab_api = QWidget()
        tab_api.setObjectName('no_back-tabApi')
        tab_api_layout = QVBoxLayout(tab_api)
        tab_api_layout.setContentsMargins(6, 8, 6, 6)
        tab_api_layout.setSpacing(8)

        api_layout = QHBoxLayout()
        api_layout.setContentsMargins(0, 0, 0, 0)
        api_layout.setSpacing(7)

        try:
            self.api_edit = PasteOnlyLineEdit()
        except NameError:
            self.api_edit = QLineEdit()

        self.api_edit.setPlaceholderText('Gemini API Key')
        self.api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_edit.setMinimumHeight(35)

        self.api_show_btn = QPushButton('보기')
        self.api_show_btn.setCheckable(True)
        self.api_show_btn.setObjectName('subtleBtn')
        self.api_show_btn.setFixedHeight(35)
        self.api_show_btn.setFixedWidth(58)
        self.api_show_btn.toggled.connect(self.toggle_api_visibility)

        api_layout.addWidget(self.api_edit, 1)
        api_layout.addWidget(self.api_show_btn)
        tab_api_layout.addLayout(api_layout)
        tab_api_layout.addStretch(1)
        self.settings_tab.addTab(tab_api, 'API 설정')

        # [검사 탭 개편]
        tab_inspect = QWidget()
        tab_inspect.setObjectName('no_back-tabInspect')
        tab_inspect_layout = QVBoxLayout(tab_inspect)
        tab_inspect_layout.setContentsMargins(8, 10, 8, 8)
        tab_inspect_layout.setSpacing(10)

        # 1. [일본어 잔존 검사]
        inspect_title = QLabel('일본어 잔존 검사')
        inspect_title.setObjectName('subLabel')
        tab_inspect_layout.addWidget(inspect_title)

        # 2. [모드]
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(8)

        mode_lbl = QLabel('모드')
        mode_lbl.setObjectName('optionLabel')
        mode_lbl.setFixedWidth(50)

        self.inspect_mode_combo = QComboBox()
        self.inspect_mode_combo.addItems(['비율 모드', '글자 수 모드'])
        self.inspect_mode_combo.setMinimumHeight(35)
        self.inspect_mode_combo.currentTextChanged.connect(self.on_inspect_mode_changed)

        mode_layout.addWidget(mode_lbl)
        mode_layout.addWidget(self.inspect_mode_combo, 1)
        tab_inspect_layout.addLayout(mode_layout)

        # 3. [(비율 모드 시) % 이상] - 콤보 박스
        self.inspect_ratio_widget = QWidget()
        inspect_ratio_layout = QHBoxLayout(self.inspect_ratio_widget)
        inspect_ratio_layout.setContentsMargins(0, 0, 0, 0)
        inspect_ratio_layout.setSpacing(8)

        self.inspect_ratio_combo = QComboBox()
        ratio_options = [1, 2, 3, 5, 7, 10, 15, 20, 30, 40, 50]
        for val in ratio_options:
            self.inspect_ratio_combo.addItem(f"{val}% 이상", float(val))
        self.inspect_ratio_combo.setCurrentIndex(ratio_options.index(10))  # 기본 10%
        self.inspect_ratio_combo.setMinimumHeight(35)

        inspect_ratio_layout.addWidget(self.inspect_ratio_combo, 1)
        tab_inspect_layout.addWidget(self.inspect_ratio_widget)

        # 4. [(글자 수 모드 시) 자 이상] - 콤보 박스
        self.inspect_count_widget = QWidget()
        inspect_count_layout = QHBoxLayout(self.inspect_count_widget)
        inspect_count_layout.setContentsMargins(0, 0, 0, 0)
        inspect_count_layout.setSpacing(8)


        self.inspect_count_combo = QComboBox()
        count_options = [1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 100]
        for val in count_options:
            self.inspect_count_combo.addItem(f"{val}자 이상", int(val))
        self.inspect_count_combo.setCurrentIndex(count_options.index(5))  # 기본 5자
        self.inspect_count_combo.setMinimumHeight(35)

        inspect_count_layout.addWidget(self.inspect_count_combo, 1)
        tab_inspect_layout.addWidget(self.inspect_count_widget)
        self.inspect_count_widget.setVisible(False)

        # 5. [검사하기]
        self.inspect_btn = QPushButton('검사하기')
        self.inspect_btn.setObjectName('primaryBtn')
        self.inspect_btn.setFixedHeight(36)
        self.inspect_btn.clicked.connect(self.run_japanese_inspection)
        tab_inspect_layout.addWidget(self.inspect_btn)

        self.inspect_status_lbl = QLabel('선택된 검사 파일 없음')
        self.inspect_status_lbl.setObjectName('secondaryInfo')
        self.inspect_status_lbl.setVisible(False)
        tab_inspect_layout.addWidget(self.inspect_status_lbl)

        # 6. [검사 설명]
        self.inspect_info = QLabel(
            "trs 폴더 내의 번역 JSON 파일을 분석하여, 각 줄에서 설정한 일본어 비율 또는 "
            "글자 수 이상 남은 문장(연속 줄 포함)을 찾아내고 직접 수정한 뒤 재저장합니다."
        )
        self.inspect_info.setObjectName('secondaryInfo')
        self.inspect_info.setWordWrap(True)
        tab_inspect_layout.addWidget(self.inspect_info)

        tab_inspect_layout.addStretch(1)
        self.settings_tab.addTab(tab_inspect, '검사')

        left_layout.addWidget(self.settings_tab)

        save_api_btn = QPushButton('설정 전체 저장')
        save_api_btn.setObjectName('subtleBtn')
        save_api_btn.setFixedHeight(35)
        save_api_btn.clicked.connect(self.save_settings)
        left_layout.addWidget(save_api_btn)

        main_hlayout.addWidget(left_widget, 5)

        right_widget = QWidget()
        right_widget.setObjectName('no_back-rightWidget')
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)

        self.status_label = QLabel('파일을 선택하세요.')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.percent_label = QLabel('0%')
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        status_layout.addWidget(self.status_label, 1)
        status_layout.addWidget(self.percent_label)
        right_layout.addLayout(status_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        right_layout.addWidget(self.progress_bar)

        log_title = QHBoxLayout()
        log_title.setContentsMargins(0, 4, 0, 0)
        log_title.setSpacing(7)

        log_label = QLabel('번역 로그')
        log_label.setObjectName('subLabel')
        log_title.addWidget(log_label)
        log_title.addStretch(1)

        self.log_filter_combo = QComboBox()
        self.log_filter_combo.addItems(['전체', '일반', '경고', '오류'])
        self.log_filter_combo.setFixedHeight(32)
        self.log_filter_combo.setFixedWidth(78)
        self.log_filter_combo.currentTextChanged.connect(self.filter_logs)

        clear_log_btn = QPushButton('지우기')
        clear_log_btn.setObjectName('subtleBtn')
        clear_log_btn.setFixedHeight(32)
        clear_log_btn.setFixedWidth(58)
        clear_log_btn.clicked.connect(self.clear_logs)

        log_title.addWidget(self.log_filter_combo)
        log_title.addWidget(clear_log_btn)
        right_layout.addLayout(log_title)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setPlaceholderText('번역 로그가 여기에 표시됩니다.')
        self.log_edit.setObjectName('detail_description')
        self.log_edit.viewport().setStyleSheet('background: transparent;')
        right_layout.addWidget(self.log_edit, 1)

        main_hlayout.addWidget(right_widget, 6)
        root.addLayout(main_hlayout, 1)

        self.start_btn = QPushButton('번역 시작')
        self.start_btn.setObjectName('primaryBtn')
        self.start_btn.setFixedHeight(42)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_translate)
        root.addWidget(self.start_btn)

        self.apply_ui_style()
        self.update_glossary_button()

    def on_inspect_mode_changed(self, mode_text):
        is_ratio = (mode_text == '비율 모드')
        self.inspect_ratio_widget.setVisible(is_ratio)
        self.inspect_count_widget.setVisible(not is_ratio)

    def run_japanese_inspection(self):
        trs_dir = os.path.abspath(os.path.join(globals().get('OUT', './out/'), 'trs'))
        if not os.path.exists(trs_dir):
            os.makedirs(trs_dir, exist_ok=True)

        json_path, _ = QFileDialog.getOpenFileName(
            self,
            '일본어 검사할 JSON 파일 선택',
            trs_dir,
            'JSON 파일 (*.json)'
        )

        if not json_path:
            return

        self.inspect_status_lbl.setText(f"선택: {os.path.basename(json_path)}")
        self.add_log(f"일본어 검사 시작: {json_path}")

        mode = self.inspect_mode_combo.currentText()
        if mode == '비율 모드':
            ratio_val = float(self.inspect_ratio_combo.currentData() or 10.0)
            count_val = 0
            criteria_desc = f"비율 {ratio_val}% 이상"
        else:
            ratio_val = 0.0
            count_val = int(self.inspect_count_combo.currentData() or 5)
            criteria_desc = f"글자 수 {count_val}자 이상"

        try:
            result = trans_ai.inspect_json_japanese(
                json_path,
                ratio_threshold=ratio_val,
                char_count_threshold=count_val
            )
            items = result.get('items', [])
            title = result.get('title', '작품')

            if not items:
                self.add_log(f"일본어 검사 결과: [{criteria_desc}] 만족하는 남은 일본어가 검출되지 않았습니다 ({title})")
                QMessageBox.information(
                    self,
                    '일본어 검사 완료',
                    f"'{title}'\n\n검출 기준({criteria_desc})에 해당하는 문장이 없습니다.\n번역이 양호합니다."
                )
                return

            self.add_log(f"일본어 검사: {len(items)}개 블록 검출 완료 ({criteria_desc}). 검사 창을 엽니다.")
            dialog = check_jp.JapaneseCheckDialog(result, self)
            dialog.exec()

        except Exception as e:
            self.add_log(f"일본어 검사 실패: {e}")
            QMessageBox.critical(self, '검사 실패', f"일본어 검사 중 오류가 발생했습니다: {e}")

    def apply_ui_style(self):
        self.setStyleSheet('''
            QWidget[objectName^="no_back-"] {
                background: transparent;
                background-color: transparent;
            }

            QFrame#chunkSepBox {
                border: 1px solid rgba(77, 166, 255, 0.3);
                border-radius: 6px;
                background: rgba(77, 166, 255, 0.06);
            }

            QLabel#dropArea {
                background: transparent;
                border-radius: 6px;
                padding: 4px;
            }

            QLabel#subLabel {
                background: transparent;
                font-size: 11px;
                font-weight: 600;
                margin-top: 2px;
                margin-bottom: 2px;
            }

            QLabel#optionLabel {
                background: transparent;
                font-size: 11px;
            }

            QLabel#secondaryInfo {
                background: transparent;
                font-size: 10px;
            }

            QPushButton#subtleBtn {
                min-height: 34px;
                padding: 0px 11px;
                border-radius: 5px;
            }

            QPushButton#subtleBtn:pressed {
                padding-top: 1px;
            }

            QLineEdit,
            QComboBox,
            QSpinBox,
            QDoubleSpinBox {
                min-height: 34px;
                padding: 0px 8px;
                border-radius: 5px;
            }

            QLineEdit#selectedModelDisplay {
                min-height: 35px;
            }

            QScrollArea#no_back-modelScroll {
                border: none;
                background: transparent;
                background-color: transparent;
            }

            QScrollArea#no_back-modelScroll > QWidget {
                border: none;
                background: transparent;
                background-color: transparent;
            }

            QScrollArea#no_back-modelScroll QWidget#no_back-modelListContainer {
                border: none;
                background: transparent;
                background-color: transparent;
            }

            QWidget#no_back-modelRow {
                background: transparent;
                background-color: transparent;
            }

            QComboBox#modelRowCombo {
                min-height: 36px;
                padding: 0px 9px;
                border-radius: 5px;
            }

            QPushButton#modelSelectBtn,
            QPushButton#modelDeleteBtn {
                min-height: 36px;
                padding: 0px 10px;
                border-radius: 5px;
            }

            QLabel#modelActiveIndicator {
                background: transparent;
                min-width: 12px;
                max-width: 12px;
            }

            QTabWidget#no_back-settingsTab {
                background: transparent;
                background-color: transparent;
                border: none;
            }

            QTabWidget#no_back-settingsTab::pane {
                background: transparent;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }

            QTabWidget#no_back-settingsTab::tab-bar {
                background: transparent;
                background-color: transparent;
            }

            QWidget#no_back-tabParams,
            QWidget#no_back-tabDict,
            QWidget#no_back-tabPre,
            QWidget#no_back-tabApi,
            QWidget#no_back-tabInspect {
                background: transparent;
                background-color: transparent;
                border: none;
            }

            QTabWidget#no_back-settingsTab QTabBar {
                background: transparent;
                background-color: transparent;
            }

            QTabWidget#no_back-settingsTab QTabBar::tab {
                background: transparent;
                background-color: transparent;
                border: none;
                border-radius: 5px;
                padding: 7px 14px;
                margin-right: 2px;
                font-size: 11px;
                min-height: 34px;
            }

            QTabWidget#no_back-settingsTab QTabBar::tab:selected {
                background: transparent;
                background-color: transparent;
            }

            QTabWidget#no_back-settingsTab QTabBar::tab:hover {
                background: transparent;
                background-color: transparent;
            }

            QTabWidget#no_back-settingsTab QAbstractScrollArea {
                background: transparent;
                background-color: transparent;
                border: none;
            }

            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                background: rgba(255, 255, 255, 0.05);
                text-align: center;
            }

            QProgressBar::chunk {
                border-radius: 3px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #60a5fa);
            }

            QTextEdit#detail_description {
                border-radius: 6px;
                padding: 5px;
            }
        ''')
        self.setAutoFillBackground(False)
        self.settings_tab.setAutoFillBackground(False)

        for i in range(self.settings_tab.count()):
            page = self.settings_tab.widget(i)
            if page is not None:
                page.setAutoFillBackground(False)

        self.model_list_container.setAutoFillBackground(False)
        self.model_scroll.setAutoFillBackground(False)
        self.log_edit.setAutoFillBackground(False)
        self.log_edit.viewport().setAutoFillBackground(False)

    def _available_model_names(self):
        names = []
        combo = self.model_add_combo
        if combo is None:
            return names
        for i in range(combo.count()):
            name = combo.itemText(i).strip()
            if not name:
                continue
            if name.casefold() in {x.casefold() for x in names}:
                continue
            names.append(name)
        return names

    def load_gemini_models(self):
        api = self.api_edit.text().strip()
        if not api:
            QMessageBox.warning(self, '알림', 'Gemini API 키를 먼저 입력하세요.')
            self.settings_tab.setCurrentIndex(3)
            self.api_edit.setFocus()
            return

        self.refresh_model_btn.setEnabled(False)
        self.status_label.setText('Gemini 모델 목록을 불러오는 중...')
        try:
            self.model_load_thread = ModelLoadThread(api)
            self.model_load_thread.finished.connect(self.on_models_loaded)
            self.model_load_thread.start()
        except NameError:
            self.refresh_model_btn.setEnabled(True)

    def on_models_loaded(self, model_names, error_msg):
        self.refresh_model_btn.setEnabled(True)
        if error_msg:
            self.add_log(f"모델 조회 실패: {error_msg}")
            QMessageBox.critical(self, '모델 조회 실패', error_msg)
            return

        current = self.model_add_combo.currentText()
        self.model_add_combo.clear()
        self.model_add_combo.addItems(model_names)

        if current:
            index = self.model_add_combo.findText(current)
            if index >= 0:
                self.model_add_combo.setCurrentIndex(index)
        elif model_names:
            self.model_add_combo.setCurrentIndex(0)

        if self.selected_models:
            current_active = self.active_model_index
            self.rebuild_model_list()
            if 0 <= current_active < len(self.selected_models):
                self.active_model_index = current_active
                self.select_model(current_active)

        if model_names:
            self.add_log(f"텍스트 생성이 가능한 Gemini 모델 {len(model_names)}개를 불러왔습니다.")
            self.status_label.setText('Gemini 모델 목록을 불러왔습니다.')
        else:
            self.add_log('사용 가능한 Gemini 텍스트 모델을 찾지 못했습니다.')
            self.status_label.setText('사용 가능한 모델이 없습니다.')

    def add_selected_model(self):
        model = self.model_add_combo.currentText().strip()
        if not model:
            QMessageBox.warning(self, '알림', '추가할 모델을 선택하세요.')
            return

        model_key = model.casefold()
        if any(str(x.get('model', '')).strip().casefold() == model_key for x in self.selected_models):
            QMessageBox.warning(self, '알림', '이미 추가된 모델입니다.')
            return

        self.selected_models.append({
            'model': model,
            'rpm': 15,
            'temperature': 0.1,
            'concurrency': 4,
            'br_start': 0,
            'isno_x': False
        })
        new_index = len(self.selected_models) - 1
        self.active_model_index = new_index
        self.rebuild_model_list()
        self.select_model(new_index)
        self.add_log(f"모델 추가: {model}")

    def change_selected_model(self, index, new_model):
        if index < 0 or index >= len(self.selected_models):
            return

        new_model = str(new_model).strip()
        if not new_model:
            return

        new_key = new_model.casefold()
        for i, config in enumerate(self.selected_models):
            if i == index:
                continue
            old = str(config.get('model', '')).strip()
            if old.casefold() == new_key:
                QMessageBox.warning(self, '모델 중복', f"'{new_model}'은 이미 사용 중인 모델입니다.")
                self.rebuild_model_list()
                return

        old_model = str(self.selected_models[index].get('model', '')).strip()
        if old_model == new_model:
            return

        self.selected_models[index]['model'] = new_model
        if index == self.active_model_index:
            self.selected_model_edit.setText(new_model)

        current_active = self.active_model_index
        self.rebuild_model_list()
        if 0 <= current_active < len(self.selected_models):
            self.active_model_index = current_active
            self.update_active_model_display()

        self.add_log(f"모델 변경: {old_model} → {new_model}")

    def rebuild_model_list(self):
        while self.model_list_layout.count():
            item = self.model_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        available_models = self._available_model_names()
        for index, item in enumerate(self.selected_models):
            model_name = str(item.get('model', '')).strip()

            row = QWidget()
            row.setObjectName('no_back-modelRow')
            row.setFixedHeight(38)

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(2, 1, 2, 1)
            row_layout.setSpacing(5)

            indicator = QLabel()
            indicator.setObjectName('modelActiveIndicator')
            indicator.setFixedWidth(12)
            if index == self.active_model_index:
                indicator.setText('●')
            else:
                indicator.setText('')
            indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row_layout.addWidget(indicator)

            model_combo = QComboBox()
            model_combo.setObjectName('modelRowCombo')
            model_combo.setMinimumHeight(36)
            model_combo.setToolTip('클릭하여 이 모델을 다른 Gemini 모델로 변경')

            row_models = list(available_models)
            if model_name and model_name not in row_models:
                row_models.insert(0, model_name)
            model_combo.addItems(row_models)

            current_index = model_combo.findText(model_name)
            if current_index >= 0:
                model_combo.setCurrentIndex(current_index)

            model_combo.activated.connect(
                lambda combo_index, i=index, combo=model_combo: self.change_selected_model(i, combo.currentText())
            )
            row_layout.addWidget(model_combo, 1)

            select_btn = QPushButton('선택')
            select_btn.setObjectName('modelSelectBtn')
            select_btn.setFixedSize(54, 36)
            select_btn.setToolTip('이 모델의 설정을 편집')
            select_btn.clicked.connect(lambda checked=False, i=index: self.select_model(i))
            row_layout.addWidget(select_btn)

            delete_btn = QPushButton('삭제')
            delete_btn.setObjectName('modelDeleteBtn')
            delete_btn.setFixedSize(54, 36)
            delete_btn.setToolTip('이 모델 삭제')
            delete_btn.clicked.connect(lambda checked=False, i=index: self.delete_model(i))
            row_layout.addWidget(delete_btn)

            self.model_list_layout.addWidget(row)

        self.model_list_layout.addStretch(1)
        self.update_active_model_display()

    def update_active_model_display(self):
        if 0 <= self.active_model_index < len(self.selected_models):
            model = str(self.selected_models[self.active_model_index].get('model', '')).strip()
            self.selected_model_edit.setText(model)
        else:
            self.selected_model_edit.clear()

    def select_model(self, index, save_current=True):
        if index < 0 or index >= len(self.selected_models):
            return

        if save_current:
            self.update_active_model()

        self.active_model_index = index
        model = self.selected_models[index]

        self.selected_model_edit.setText(str(model.get('model', '')))

        rpm_val = str(model.get('rpm', 15))
        self.rpm_combo.blockSignals(True)
        if self.rpm_combo.findText(rpm_val) < 0:
            self.rpm_combo.addItem(rpm_val)
        self.rpm_combo.setCurrentText(rpm_val)
        self.rpm_combo.blockSignals(False)

        temp_val = str(model.get('temperature', 0.1))
        self.temp_combo.blockSignals(True)
        if self.temp_combo.findText(temp_val) < 0:
            self.temp_combo.addItem(temp_val)
        self.temp_combo.setCurrentText(temp_val)
        self.temp_combo.blockSignals(False)

        conc_val = str(model.get('concurrency', 4))
        self.concurrency_combo.blockSignals(True)
        if self.concurrency_combo.findText(conc_val) < 0:
            self.concurrency_combo.addItem(conc_val)
        self.concurrency_combo.setCurrentText(conc_val)
        self.concurrency_combo.blockSignals(False)

        br_val = str(model.get('br_start', 0))
        self.br_start_combo.blockSignals(True)
        if self.br_start_combo.findText(br_val) < 0:
            self.br_start_combo.addItem(br_val)
        self.br_start_combo.setCurrentText(br_val)
        self.br_start_combo.blockSignals(False)

        isno_x_val = bool(model.get('isno_x', False))
        censor_text = '사용 안함' if isno_x_val else '사용'
        self.censor_combo.blockSignals(True)
        self.censor_combo.setCurrentText(censor_text)
        self.censor_combo.blockSignals(False)

        self.rebuild_model_list()

    def update_active_model(self, *args):
        if self.active_model_index < 0 or self.active_model_index >= len(self.selected_models):
            return

        try:
            self.selected_models[self.active_model_index]['rpm'] = int(self.rpm_combo.currentText())
            self.selected_models[self.active_model_index]['temperature'] = float(self.temp_combo.currentText())
            self.selected_models[self.active_model_index]['concurrency'] = int(self.concurrency_combo.currentText())
            self.selected_models[self.active_model_index]['br_start'] = int(self.br_start_combo.currentText())
            self.selected_models[self.active_model_index]['isno_x'] = (self.censor_combo.currentText() == '사용 안함')
        except (ValueError, TypeError):
            pass

    def delete_model(self, index):
        if index < 0 or index >= len(self.selected_models):
            return

        if len(self.selected_models) <= 1:
            QMessageBox.warning(self, '알림', '최소 하나의 모델은 필요합니다.')
            return

        model = self.selected_models[index].get('model', '')
        self.selected_models.pop(index)

        if self.active_model_index == index:
            self.active_model_index = min(index, len(self.selected_models) - 1)
        elif self.active_model_index > index:
            self.active_model_index -= 1

        self.rebuild_model_list()
        if self.selected_models:
            self.select_model(self.active_model_index)

        self.add_log(f"모델 삭제: {model}")

    def get_model_configs(self):
        self.update_active_model()
        return [
            {
                'model': str(x.get('model', '')).strip(),
                'rpm': int(x.get('rpm', 15)),
                'temperature': float(x.get('temperature', 0.1)),
                'concurrency': int(x.get('concurrency', 4)),
                'br_start': int(x.get('br_start', 0)),
                'isno_x': bool(x.get('isno_x', False))
            }
            for x in self.selected_models if str(x.get('model', '')).strip()
        ]

    def load_settings(self):
        data = {}
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                self.add_log(f"설정 불러오기 실패: {e}")

        api = str(data.get('api', '')).strip()
        self.api_edit.setText(api)

        def set_api(value):
            try:
                trans_ai.set_api_key(value)
            except NameError:
                pass

        self.api_edit.textChanged.connect(set_api)

        default_br = int(data.get('translate_br_start', 0))
        default_isno_x = bool(data.get('translate_isno_x', False))
        models = data.get('translate_models')
        self.selected_models = []

        if isinstance(models, list):
            used_model_names = set()
            for item in models:
                if isinstance(item, str):
                    model_name = item.strip()
                    if not model_name:
                        continue
                    model_key = model_name.casefold()
                    if model_key in used_model_names:
                        continue
                    used_model_names.add(model_key)
                    self.selected_models.append({
                        'model': model_name,
                        'rpm': int(data.get('translate_rpm', 15)),
                        'temperature': float(data.get('translate_temperature', 0.1)),
                        'concurrency': int(data.get('translate_concurrency', 4)),
                        'br_start': default_br,
                        'isno_x': default_isno_x
                    })
                elif isinstance(item, dict):
                    model = str(item.get('model', '')).strip()
                    if not model:
                        continue
                    model_key = model.casefold()
                    if model_key in used_model_names:
                        continue
                    used_model_names.add(model_key)
                    self.selected_models.append({
                        'model': model,
                        'rpm': int(item.get('rpm', data.get('translate_rpm', 15))),
                        'temperature': float(item.get('temperature', data.get('translate_temperature', 0.1))),
                        'concurrency': int(item.get('concurrency', data.get('translate_concurrency', 4))),
                        'br_start': int(item.get('br_start', default_br)),
                        'isno_x': bool(item.get('isno_x', default_isno_x))
                    })

        if not self.selected_models:
            model_name = str(data.get('translate_model', '')).strip()
            if model_name:
                self.selected_models.append({
                    'model': model_name,
                    'rpm': int(data.get('translate_rpm', 15)),
                    'temperature': float(data.get('translate_temperature', 0.1)),
                    'concurrency': int(data.get('translate_concurrency', 4)),
                    'br_start': default_br,
                    'isno_x': default_isno_x
                })

        max_chars = str(data.get('translate_max_chars', 5000))
        self.glossary_enabled = bool(data.get('translate_glossary_enabled', True))

        if self.chars_combo.findText(max_chars) < 0:
            self.chars_combo.addItem(max_chars)
        self.chars_combo.setCurrentText(max_chars)

        self.glossary_toggle_btn.setChecked(self.glossary_enabled)
        self.update_glossary_button()

        if self.selected_models:
            self.active_model_index = -1
            self.select_model(0, save_current=False)

        if not api:
            self.settings_tab.setCurrentIndex(3)
            self.status_label.setText('Gemini API 키를 설정하세요.')
        else:
            self.settings_tab.setCurrentIndex(0)
            try:
                self.load_gemini_models()
            except Exception as e:
                self.add_log(f"자동 모델 조회 실패: {e}")

        self.add_log('저장된 번역 설정을 불러왔습니다.')

    def save_settings(self):
        self.update_active_model()
        api = self.api_edit.text().strip()
        configs = self.get_model_configs()

        if not api or not configs:
            QMessageBox.warning(self, '알림', 'API 키와 Gemini 모델을 확인하세요.')
            return False

        try:
            data = {}
            if os.path.exists(self.SETTINGS_FILE):
                try:
                    with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    data = {}

            first = configs[0]
            data.update({
                'api': api,
                'translate_model': first['model'],
                'translate_models': configs,
                'translate_rpm': first['rpm'],
                'translate_temperature': first['temperature'],
                'translate_concurrency': first['concurrency'],
                'translate_br_start': first['br_start'],
                'translate_isno_x': bool(first.get('isno_x', False)),
                'translate_max_chars': int(self.chars_combo.currentText()),
                'translate_glossary_enabled': bool(self.glossary_enabled)
            })

            if not isinstance(data.get('dictionary'), dict):
                data['dictionary'] = {}
            if not isinstance(data.get('pre'), dict):
                data['pre'] = {}

            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            self.add_log('번역 기본 설정이 저장되었습니다.')
            return True
        except Exception as e:
            QMessageBox.critical(self, '오류', str(e))
            return False

    def save_preset(self):
        self.update_active_model()
        name = self.preset_name_edit.text().strip()
        configs = self.get_model_configs()

        if not name:
            QMessageBox.warning(self, '알림', '프리셋 이름을 입력하세요.')
            return

        if not configs:
            QMessageBox.warning(self, '알림', '최소 하나의 모델을 추가하세요.')
            return

        try:
            data = {}
            if os.path.exists(self.SETTINGS_FILE):
                try:
                    with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    data = {}

            if not isinstance(data.get('pre'), dict):
                data['pre'] = {}

            data['pre'][name] = {
                'models': configs,
                'max_chars': int(self.chars_combo.currentText()),
                'glossary_enabled': bool(self.glossary_enabled)
            }

            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            self.preset_status.setText(f"현재 프리셋: {name}")
            self.add_log(f"프리셋 저장 완료: {name}")
        except Exception as e:
            QMessageBox.critical(self, '프리셋 저장 오류', str(e))

    def load_preset(self):
        try:
            data = {}
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            presets = data.get('pre', {})
            if not isinstance(presets, dict) or not presets:
                QMessageBox.information(self, '프리셋', '저장된 프리셋이 없습니다.')
                return

            dialog = PresetLoadDialog(presets, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            name = dialog.selected_name
            preset = presets.get(name)
            if not isinstance(preset, dict):
                QMessageBox.warning(self, '알림', '프리셋 데이터가 올바르지 않습니다.')
                return

            models = preset.get('models', [])
            if not isinstance(models, list) or not models:
                QMessageBox.warning(self, '알림', '프리셋에 모델이 없습니다.')
                return

            default_br = int(preset.get('br_start', 0))
            default_isno_x = bool(preset.get('isno_x', False))

            new_models = []
            used_names = set()
            for item in models:
                if isinstance(item, str):
                    model = item.strip()
                    if not model:
                        continue
                    key = model.casefold()
                    if key in used_names:
                        continue
                    used_names.add(key)
                    new_models.append({
                        'model': model,
                        'rpm': 15,
                        'temperature': 0.1,
                        'concurrency': 4,
                        'br_start': default_br,
                        'isno_x': default_isno_x
                    })
                elif isinstance(item, dict):
                    model = str(item.get('model', '')).strip()
                    if not model:
                        continue
                    key = model.casefold()
                    if key in used_names:
                        continue
                    used_names.add(key)
                    new_models.append({
                        'model': model,
                        'rpm': int(item.get('rpm', 15)),
                        'temperature': float(item.get('temperature', 0.1)),
                        'concurrency': int(item.get('concurrency', 4)),
                        'br_start': int(item.get('br_start', default_br)),
                        'isno_x': bool(item.get('isno_x', default_isno_x))
                    })

            if not new_models:
                QMessageBox.warning(self, '알림', '유효한 모델이 없습니다.')
                return

            self.selected_models = new_models
            self.active_model_index = -1

            max_chars = str(preset.get('max_chars', 5000))
            if self.chars_combo.findText(max_chars) < 0:
                self.chars_combo.addItem(max_chars)
            self.chars_combo.setCurrentText(max_chars)

            self.glossary_enabled = bool(preset.get('glossary_enabled', True))
            self.glossary_toggle_btn.setChecked(self.glossary_enabled)
            self.update_glossary_button()

            self.preset_name_edit.setText(name)
            self.preset_status.setText(f"현재 프리셋: {name}")

            self.select_model(0, save_current=False)
            self.add_log(f"프리셋 불러오기 완료: {name}")

        except Exception as e:
            QMessageBox.critical(self, '프리셋 불러오기 오류', str(e))

    def toggle_glossary(self, checked):
        self.glossary_enabled = bool(checked)
        self.update_glossary_button()

    def update_glossary_button(self):
        if self.glossary_enabled:
            self.glossary_toggle_btn.setText('활성')
        else:
            self.glossary_toggle_btn.setText('비활성')

    def toggle_api_visibility(self, checked):
        if checked:
            self.api_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.api_show_btn.setText('숨기기')
        else:
            self.api_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.api_show_btn.setText('보기')

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile().lower()
            if path.endswith(('.txt', '.json')):
                event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.set_file(urls[0].toLocalFile())

    def browse_file(self):
        out_path = globals().get('OUT', '')
        path, _ = QFileDialog.getOpenFileName(self, '번역할 파일 선택', out_path, '지원 파일 (*.txt *.json)')
        if path:
            self.set_file(path)

    def extract_title(self, path):
        try:
            if path.lower().endswith('.txt'):
                with open(path, 'r', encoding='utf-8-sig') as f:
                    first_line = f.readline().strip()
                if first_line and set(first_line) == {"="}:
                    first_line = os.path.basename(os.path.dirname(path))
                    
                return first_line
            if path.lower().endswith('.json'):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for key in ['title', 'name', 'novel_title', 'work_title']:
                        value = data.get(key)
                        if not isinstance(value, str):
                            continue
                        value = value.strip()
                        if not value:
                            continue
                        while value.endswith('_복원'):
                            value = value[:-len('_복원')].rstrip()
                        match = re.search(r'_\d+\s*~\s*\d+$', value)
                        if match:
                            value = value[:match.start()].rstrip()
                        return value
        except Exception as e:
            self.add_log(f"작품명 추출 실패: {e}")
        return ''

    def load_dictionary_for_title(self):
        data = load_data()
        dictionary = data.get('dictionary', {}) if isinstance(data, dict) else {}
        if not isinstance(dictionary, dict):
            dictionary = {}

        self.current_dictionary = dictionary.get(self.file_title, {})
        if not isinstance(self.current_dictionary, dict):
            self.current_dictionary = {}

        if self.file_title:
            if self.current_dictionary:
                self.dictionary_status.setText(f"{self.file_title} ({len(self.current_dictionary)}개)")
            else:
                self.dictionary_status.setText(f"{self.file_title} (등록된 용어 없음)")
        else:
            self.dictionary_status.setText('작품명을 찾을 수 없습니다.')

    def open_dictionary_dialog(self):
        if not self.file_title:
            QMessageBox.warning(self, '알림', '먼저 번역할 파일을 선택하세요.\nTXT 파일은 첫 줄을 작품명으로 사용합니다.')
            return

        model_name = ''
        rpm = 15
        if 0 <= self.active_model_index < len(self.selected_models):
            model_name = self.selected_models[self.active_model_index].get('model', '')
            rpm = int(self.selected_models[self.active_model_index].get('rpm', 15))

        try:
            dialog = DictionaryDialog(self, self.file_title, self.current_dictionary, model_name, rpm)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            self.current_dictionary = dict(dialog.dictionary)
            data = load_data()
            if not isinstance(data.get('dictionary'), dict):
                data['dictionary'] = {}
            data['dictionary'][self.file_title] = self.current_dictionary
            save_data(data)
            self.dictionary_status.setText(f"{self.file_title} ({len(self.current_dictionary)}개)")
            self.add_log(f"용어집 저장 완료: {self.file_title} ({len(self.current_dictionary)}개)")
        except NameError:
            pass

    def set_file(self, path):
        if not path.lower().endswith(('.txt', '.json')):
            QMessageBox.warning(self, '알림', 'TXT 또는 JSON 파일만 선택할 수 있습니다.')
            return

        self.file_path = path
        self.file_edit.setText(path)
        kind = 'JSON 복원/재번역' if path.lower().endswith('.json') else 'TXT 전체 번역'
        self.file_title = self.extract_title(path)
        self.drop_label.setText(f"선택됨: {os.path.basename(path)}")

        if self.file_title:
            self.status_label.setText(f"{kind}  ·  {self.file_title}")
        else:
            self.status_label.setText(kind)

        self.add_log(f"파일 선택: {path}")
        self.add_log(f"작업 방식: {kind}")

        if self.file_title:
            self.add_log(f"작품명 감지: {self.file_title}")
        else:
            self.add_log('작품명을 찾지 못했습니다.')

        self.load_dictionary_for_title()
        if self.current_dictionary:
            self.add_log(f"용어집 자동 선택: {len(self.current_dictionary)}개")
        else:
            self.add_log('해당 작품에 등록된 용어집이 없습니다.')

    def start_translate(self):
        if self.is_trans:
            self.stop_trans()
            return

        if not self.file_path:
            QMessageBox.warning(self, '알림', 'TXT 또는 JSON 파일을 선택하세요.')
            return

        api = self.api_edit.text().strip()
        if not api:
            QMessageBox.warning(self, '알림', 'Gemini API 키를 먼저 설정하세요.')
            self.settings_tab.setCurrentIndex(3)
            return

        self.update_active_model()
        model_configs = self.get_model_configs()
        if not model_configs:
            QMessageBox.warning(self, '알림', '최소 하나의 모델을 추가하세요.')
            return

        try:
            max_chars = int(self.chars_combo.currentText())
        except ValueError:
            QMessageBox.warning(self, '알림', '설정 값이 올바르지 않습니다.')
            return

        if not self.save_settings():
            return

        model_names = ','.join(x['model'] for x in model_configs)
        rpms = tuple(x['rpm'] for x in model_configs)
        temperatures = tuple(x['temperature'] for x in model_configs)
        concurrencies = tuple(x['concurrency'] for x in model_configs)
        br_starts = tuple(x['br_start'] for x in model_configs)
        isno_xs = tuple(x['isno_x'] for x in model_configs)
        dict_data = dict(self.current_dictionary) if self.glossary_enabled else {}

        self.is_trans = True
        self.is_stop = False
        self.start_btn.setText('번역 중지')
        self.progress_bar.setValue(0)
        self.percent_label.setText('0%')

        self.add_log('')
        self.add_log('=' * 55)
        self.add_log('번역 시작')
        for i, config in enumerate(model_configs, 1):
            censor_state = "건너뜀(isno_x)" if config['isno_x'] else "적용"
            self.add_log(
                f"모델 {i}: {config['model']} / RPM {config['rpm']} / Temp {config['temperature']} / "
                f"동시 {config['concurrency']} / 분할시작 {config['br_start']} / 검열: {censor_state}"
            )
        self.add_log(f"작품명: {self.file_title}")
        self.add_log(f"청크 글자수: {max_chars}")
        self.add_log('용어집: ' + (f"활성 ({len(dict_data)}개)" if self.glossary_enabled else '비활성'))
        self.add_log('=' * 55)

        try:
            try:
                self.thread = TranslateThread(
                    self.file_path,
                    model_names,
                    rpms,
                    temperatures,
                    concurrencies,
                    max_chars,
                    dicts=dict_data,
                    check=self.get_out,
                    br_start=br_starts,
                    isno_x=isno_xs
                )
            except TypeError:
                self.thread = TranslateThread(
                    self.file_path,
                    model_names,
                    rpms,
                    temperatures,
                    concurrencies,
                    max_chars,
                    dicts=dict_data,
                    check=self.get_out,
                    br_start=br_starts,
                    isno_x=isno_xs
                )
            self.thread.progress_changed.connect(self.update_progress)
            self.thread.log_changed.connect(self.add_log)
            self.thread.finished_signal.connect(self.on_finished)
            self.thread.start()
        except NameError:
            self.add_log('TranslateThread 실행 실패: 모듈을 찾을 수 없습니다.')
            self.is_trans = False
            self.start_btn.setText('번역 시작')

    def stop_trans(self):
        if not self.is_trans:
            return
        self.is_stop = True
        self.add_log('중지: 번역 중지 요청 중... 작업 종료 후 중지')
        self.start_btn.setEnabled(False)
        self.start_btn.setText('중지 중...')

    def get_out(self):
        return self.is_stop

    def update_progress(self, done, total, message):
        total = max(int(total), 1)
        done = min(int(done), total)
        percent = int(done * 100 / total)

        self.progress_bar.setValue(percent)
        self.percent_label.setText(f"{percent}%")
        self.status_label.setText(str(message))

    def get_brightness(self, hex_color):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return 255
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r * 299 + g * 587 + b * 114) / 1000

    def add_log(self, text):
        if not text:
            return

        log_type = 'NORMAL'
        if '오류' in text or '실패' in text or '에러' in text:
            log_type = 'ERROR'
        elif '경고' in text:
            log_type = 'WARN'
        elif '성공' in text or '완료' in text or '통과' in text:
            log_type = 'SUCCESS'
        elif '시작' in text or '로드' in text or '감지' in text or '중지' in text or '강제분할' in text or '검사' in text:
            log_type = 'INFO'

        bg_color = return_theme()
        is_dark = self.get_brightness(bg_color) < 128

        color_map = {
            'DARK': {'NORMAL': '#e0e0e0', 'ERROR': '#ff5555', 'WARN': '#ffb86c', 'SUCCESS': '#50fa7b', 'INFO': '#8be9fd'},
            'LIGHT': {'NORMAL': '#222222', 'ERROR': '#d32f2f', 'WARN': '#e65100', 'SUCCESS': '#2e7d32', 'INFO': '#0288d1'}
        }
        mode = 'DARK' if is_dark else 'LIGHT'
        color = color_map[mode][log_type]

        safe_text = html.escape(str(text)).replace('\n', '<br>')
        formatted_html = f'<span style="color: {color}; font-family: Consolas, monospace;">{safe_text}</span>'
        self.log_history.append((log_type, formatted_html))

        current_filter = self.log_filter_combo.currentText()
        if self._matches_filter(log_type, current_filter):
            self.log_edit.append(formatted_html)

    def _matches_filter(self, log_type, filter_text):
        if filter_text == '전체':
            return True
        elif filter_text == '일반' and log_type in ['NORMAL', 'INFO', 'SUCCESS']:
            return True
        elif filter_text == '경고' and log_type == 'WARN':
            return True
        elif filter_text == '오류' and log_type == 'ERROR':
            return True
        return False

    def filter_logs(self, filter_text):
        self.log_edit.clear()
        for log_type, formatted_html in self.log_history:
            if self._matches_filter(log_type, filter_text):
                self.log_edit.append(formatted_html)

    def clear_logs(self):
        self.log_history.clear()
        self.log_edit.clear()

    def on_finished(self, success, message, output_dir):
        self.start_btn.setEnabled(True)
        self.start_btn.setText('번역 시작')
        self.is_trans = False
        self.is_stop = False

        if success:
            self.progress_bar.setValue(100)
            self.percent_label.setText('100%')
            self.status_label.setText(message)
            self.add_log('번역이 정상적으로 완료되었습니다.')
            QMessageBox.information(self, '번역 완료', message)
            if output_dir:
                try:
                    open_folder(output_dir)
                except Exception:
                    pass
        else:
            self.status_label.setText('번역 실패')
            self.add_log(f"번역 실패: {message}")
            QMessageBox.critical(self, '번역 오류', message)

    def closeEvent(self, event):
        if self.is_trans:
            QMessageBox.critical(
                self,
                '종료 거부',
                '현재 번역 작업 중 입니다.\n종료를 거부 합니다. 번역 중지 혹은 번역 완료 후 종료 해 주세요.'
            )
            event.ignore()
        else:
            super().closeEvent(event)