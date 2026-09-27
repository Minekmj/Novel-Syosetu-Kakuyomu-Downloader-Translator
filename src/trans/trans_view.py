from PySide6.QtWidgets import (
    QFrame, QGridLayout, QSizePolicy, QTabWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QFileDialog, QDialog, QMessageBox, QTextEdit, QComboBox,
    QProgressBar, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics

import html
import os
import json
import re

from src.system.data import open_folder, return_theme, load_data, save_data
from src.main.thread_pyqt import TranslateThread, ModelLoadThread, trans_ai
import src.trans.trans_check_jp as check_jp
import src.trans.preset as preset
from src.trans.trans_glossary import *

check_jp.trans_ai = trans_ai

OUT = "./out/"


class ElidedLabel(QLabel):
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def setText(self, text):
        self._full_text = text
        self._update_elided_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_text()

    def _update_elided_text(self):
        width = self.width()
        if width <= 0:
            return
        metrics = QFontMetrics(self.font())
        super().setText(metrics.elidedText(self._full_text, Qt.ElideRight, width))


class TranslateDialog(QDialog):
    SETTINGS_FILE = './data.json'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_trans = False
        self.is_stop = False
        self.is_stop_i = False
        self.file_path = ''
        self.file_title = ''
        self.current_dictionary = {}
        self.selected_models = []
        self.active_model_index = -1
        self.glossary_enabled = True
        self.log_follow_enabled = True
        self.thread = None
        self.model_load_thread = None
        self.log_history = []

        self.setWindowTitle('AI 번역')
        self.resize(920, 750)
        self.setMinimumSize(920, 730)
        self.setAcceptDrops(True)
        self.init_ui()
        self.load_settings()

    def _layout(self, kind, margins=(0, 0, 0, 0), spacing=7, parent=None):
        layout = (QVBoxLayout if kind == 'v' else QHBoxLayout if kind == 'h' else QGridLayout)(parent)
        layout.setContentsMargins(*margins)
        if kind == 'g':
            layout.setHorizontalSpacing(spacing)
            layout.setVerticalSpacing(spacing)
        else:
            layout.setSpacing(spacing)
        return layout

    def _label(self, text, obj=None, width=None):
        w = QLabel(text)
        if obj:
            w.setObjectName(obj)
        if width:
            w.setFixedWidth(width)
        return w

    def _button(self, text, slot=None, obj='subtleBtn', h=35, w=None, checkable=False):
        b = QPushButton(text)
        if obj:
            b.setObjectName(obj)
        b.setFixedHeight(h)
        if w:
            b.setFixedWidth(w)
        b.setCheckable(checkable)
        if slot:
            (b.toggled if checkable else b.clicked).connect(slot)
        return b

    def _combo(self, items, current=None, slot=None, h=35):
        c = QComboBox()
        c.addItems([str(x) for x in items])
        if current is not None:
            c.setCurrentText(str(current))
        c.setMinimumHeight(h)
        if slot:
            c.currentTextChanged.connect(slot)
        return c

    def _tab(self, title, obj):
        tab = QWidget()
        tab.setObjectName(obj)
        self.settings_tab.addTab(tab, title)
        return tab, self._layout('v', (6, 8, 6, 6), 7, tab)

    def _set_combo(self, combo, value):
        value = str(value)
        combo.blockSignals(True)
        if combo.findText(value) < 0:
            combo.addItem(value)
        combo.setCurrentText(value)
        combo.blockSignals(False)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def init_ui(self):
        root = self._layout('v', (14, 14, 14, 14), 10, self)

        top = self._layout('v', spacing=5)
        self.drop_label = self._label('TXT 또는 JSON 파일을 여기에 드래그하세요', 'dropArea')
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumHeight(48)
        self.drop_label.setMaximumHeight(54)
        top.addWidget(self.drop_label)

        file_row = self._layout('h')
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText('번역할 TXT 또는 JSON 파일 선택')
        self.file_edit.setMinimumHeight(35)
        file_row.addWidget(self.file_edit, 1)
        file_row.addWidget(self._button('파일 찾기', self.browse_file, w=70))
        top.addLayout(file_row)
        root.addLayout(top)

        main = self._layout('h', spacing=14)

        left = QWidget()
        left.setObjectName('no_back-leftWidget')
        ll = self._layout('v', spacing=8, parent=left)

        model_row = self._layout('h')
        model_row.addWidget(self._label('모델', width=36))
        self.model_add_combo = self._combo([], h=35)
        self.model_add_combo.setPlaceholderText('Gemini 모델 선택')
        self.model_combo = self.model_add_combo
        model_row.addWidget(self.model_add_combo, 1)
        model_row.addWidget(self._button('추가', self.add_selected_model, w=56))
        self.refresh_model_btn = self._button('새로고침', self.load_gemini_models, w=76)
        model_row.addWidget(self.refresh_model_btn)
        ll.addLayout(model_row)
        ll.addWidget(self._label('사용 모델 목록', 'subLabel'))

        self.model_list_container = QWidget()
        self.model_list_container.setObjectName('no_back-modelListContainer')
        self.model_list_layout = self._layout('v', spacing=4, parent=self.model_list_container)

        self.model_scroll = QScrollArea()
        self.model_scroll.setObjectName('no_back-modelScroll')
        self.model_scroll.setWidgetResizable(True)
        self.model_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.model_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.model_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.model_scroll.setWidget(self.model_list_container)
        self.model_scroll.setFixedHeight(112)
        ll.addWidget(self.model_scroll)

        self.settings_tab = QTabWidget()
        self.settings_tab.setObjectName('settingsTab')
        self.settings_tab.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.settings_tab.setAutoFillBackground(False)

        tab, tl = self._tab('매개변수', 'no_back-tabParams')

        row = self._layout('h')
        row.addWidget(self._label('선택 모델', 'optionLabel'))

        self.selected_model_edit = QLineEdit()
        self.selected_model_edit.setObjectName('selectedModelDisplay')
        self.selected_model_edit.setReadOnly(True)
        self.selected_model_edit.setMinimumHeight(35)
        self.selected_model_edit.setPlaceholderText('위 사용 모델 목록에서 모델을 선택하세요')
        row.addWidget(self.selected_model_edit, 1)
        tl.addLayout(row)

        grid = self._layout('g', spacing=7)
        options = [
            ('RPM', 'rpm_combo', ['1', '2', '3', '5', '7', '10', '15', '20', '30', '60'], '15'),
            ('Temperature', 'temp_combo', ['0.0', '0.1', '0.2', '0.3', '0.5', '0.7', '1.0'], '0.1'),
            ('동시 작업', 'concurrency_combo', [str(i) for i in range(1, 16)], '4'),
            ('청크 글자수', 'chars_combo', ['500', '1000', '2000', '3000', '4000', '5000', '7000', '10000', '15000', '20000', '30000'], '5000'),
            ('분할 시작', 'br_start_combo', ['0', '1', '2', '3', '4'], '0'),
            ('검열하기', 'censor_combo', ['사용', '사용 안함'], '사용')
        ]

        for i, (label, attr, items, current) in enumerate(options):
            r, c = divmod(i, 2)
            grid.addWidget(self._label(label, 'optionLabel'), r, c * 2)
            setattr(self, attr, self._combo(items, current, self.update_active_model))
            grid.addWidget(getattr(self, attr), r, c * 2 + 1)

        self.censor_combo.setToolTip('사용: 검열 시도 후 분할 / 사용 안함: 검열 건너뛰고 바로 분할')

        grid.addWidget(self._label('추론', 'optionLabel'), 3, 0)
        self.thinking_combo = self._combo(['기본값', 'minimal', 'low', 'medium', 'high'], '기본값', self.update_active_model)
        grid.addWidget(self.thinking_combo, 3, 1, 1, 3)
        tl.addLayout(grid)
        tl.addStretch(1)

        tab, tl = self._tab('용어집', 'no_back-tabDict')

        row = self._layout('h')
        self.dictionary_status = self._label('선택된 작품 없음')
        self.dictionary_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.dictionary_status.setWordWrap(True)
        row.addWidget(self.dictionary_status, 1)
        self.dictionary_btn = self._button('설정', self.open_dictionary_dialog, w=58)
        row.addWidget(self.dictionary_btn)
        tl.addLayout(row)

        row = self._layout('h')
        row.addWidget(self._label('번역에 용어집 사용'))
        row.addStretch(1)
        self.glossary_toggle_btn = self._button('', self.toggle_glossary, w=78, checkable=True)
        row.addWidget(self.glossary_toggle_btn)
        tl.addLayout(row)
        tl.addStretch(1)

        tab, tl = self._tab('프리셋', 'no_back-tabPre')

        row = self._layout('h')
        self.preset_name_edit = QLineEdit()
        self.preset_name_edit.setPlaceholderText('프리셋 이름')
        self.preset_name_edit.setMinimumHeight(35)
        row.addWidget(self.preset_name_edit, 1)
        row.addWidget(self._button('저장', self.save_preset, w=58))
        row.addWidget(self._button('불러오기', self.load_preset, w=76))
        tl.addLayout(row)

        self.preset_status = self._label('현재 프리셋 없음', 'secondaryInfo')
        tl.addWidget(self.preset_status)
        tl.addStretch(1)

        tab, tl = self._tab('API 설정', 'no_back-tabApi')

        row = self._layout('h')
        try:
            self.api_edit = preset.PasteOnlyLineEdit()
        except NameError:
            self.api_edit = QLineEdit()

        self.api_edit.setPlaceholderText('Gemini API Key')
        self.api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_edit.setMinimumHeight(35)
        row.addWidget(self.api_edit, 1)

        self.api_show_btn = self._button('보기', self.toggle_api_visibility, w=58, checkable=True)
        row.addWidget(self.api_show_btn)
        tl.addLayout(row)
        tl.addStretch(1)

        tab, tl = self._tab('검사', 'no_back-tabInspect')
        tl.setContentsMargins(8, 10, 8, 8)
        tl.setSpacing(10)
        tl.addWidget(self._label('일본어 잔존 검사', 'subLabel'))

        row = self._layout('h')
        row.addWidget(self._label('모드', 'optionLabel', 50))
        self.inspect_mode_combo = self._combo(['비율 모드', '글자 수 모드'], '비율 모드', self.on_inspect_mode_changed)
        row.addWidget(self.inspect_mode_combo, 1)
        tl.addLayout(row)

        self.inspect_ratio_widget = QWidget()
        rlay = self._layout('h', parent=self.inspect_ratio_widget)
        self.inspect_ratio_combo = QComboBox()

        for v in [1, 2, 3, 5, 7, 10, 15, 20, 30, 40, 50]:
            self.inspect_ratio_combo.addItem(f'{v}% 이상', float(v))

        self.inspect_ratio_combo.setCurrentIndex(5)
        self.inspect_ratio_combo.setMinimumHeight(35)
        rlay.addWidget(self.inspect_ratio_combo, 1)
        tl.addWidget(self.inspect_ratio_widget)

        self.inspect_count_widget = QWidget()
        clay = self._layout('h', parent=self.inspect_count_widget)
        self.inspect_count_combo = QComboBox()

        for v in [1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 100]:
            self.inspect_count_combo.addItem(f'{v}자 이상', int(v))

        self.inspect_count_combo.setCurrentIndex(3)
        self.inspect_count_combo.setMinimumHeight(35)
        clay.addWidget(self.inspect_count_combo, 1)
        tl.addWidget(self.inspect_count_widget)
        self.inspect_count_widget.setVisible(False)

        self.inspect_btn = self._button('검사하기', self.run_japanese_inspection, 'primaryBtn', 36)
        tl.addWidget(self.inspect_btn)

        self.inspect_status_lbl = self._label('선택된 검사 파일 없음', 'secondaryInfo')
        self.inspect_status_lbl.setVisible(False)
        tl.addWidget(self.inspect_status_lbl)

        self.inspect_info = self._label('trs 폴더 내의 번역 JSON 파일을 분석하여, 각 줄에서 설정한 일본어 비율 또는 글자 수 이상 남은 문장(연속 줄 포함)을 찾아내고 직접 수정한 뒤 재저장합니다.', 'secondaryInfo')
        self.inspect_info.setWordWrap(True)
        tl.addWidget(self.inspect_info)
        tl.addStretch(1)

        ll.addWidget(self.settings_tab)
        ll.addWidget(self._button('설정 전체 저장', self.save_settings))

        right = QWidget()
        right.setObjectName('no_back-rightWidget')
        rl = self._layout('v', spacing=6, parent=right)

        row = self._layout('h')
        self.status_label = ElidedLabel('파일을 선택하세요.')
        self.status_label.setMaximumWidth(int(self.width() * 0.4))
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row.addWidget(self.status_label, 1)

        self.percent_label = self._label('0%')
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.percent_label)
        rl.addLayout(row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        rl.addWidget(self.progress_bar)

        row = self._layout('h', (0, 4, 0, 0))
        row.addWidget(self._label('번역 로그', 'subLabel'))
        row.addStretch(1)

        self.log_follow_btn = self._button('번역 로그 추적', self.toggle_log_follow, 'subtleBtn', 32, 100, True)
        self.log_follow_btn.setChecked(True)
        row.addWidget(self.log_follow_btn)

        self.log_filter_combo = self._combo(['전체', '일반', '경고', '오류'], h=32)
        self.log_filter_combo.setFixedWidth(78)
        self.log_filter_combo.currentTextChanged.connect(self.filter_logs)
        row.addWidget(self.log_filter_combo)

        row.addWidget(self._button('지우기', self.clear_logs, w=58, h=32))
        rl.addLayout(row)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setPlaceholderText('번역 로그가 여기에 표시됩니다.')
        self.log_edit.setObjectName('detail_description')
        self.log_edit.viewport().setStyleSheet('background: transparent;')
        rl.addWidget(self.log_edit, 1)

        main.addWidget(left, 5)
        main.addWidget(right, 6)
        root.addLayout(main, 1)

        self.start_btn = self._button('번역 시작', self.start_translate, 'primaryBtn', 42)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        root.addWidget(self.start_btn)

        self.apply_ui_style()
        self.update_glossary_button()
        self.update_log_follow_button()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'status_label'):
            self.status_label.setMaximumWidth(int(self.width() * 0.4))

    def on_inspect_mode_changed(self, mode_text):
        is_ratio = mode_text == '비율 모드'
        self.inspect_ratio_widget.setVisible(is_ratio)
        self.inspect_count_widget.setVisible(not is_ratio)

    def toggle_log_follow(self, checked):
        self.log_follow_enabled = bool(checked)
        self.update_log_follow_button()

        if self.log_follow_enabled and hasattr(self, 'log_edit'):
            scrollbar = self.log_edit.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def update_log_follow_button(self):
        if not hasattr(self, 'log_follow_btn'):
            return

        self.log_follow_btn.setText('로그 추적 ON' if self.log_follow_enabled else '로그 추적 OFF')
        self.log_follow_btn.setChecked(self.log_follow_enabled)

    def scroll_log_to_bottom(self):
        if not self.log_follow_enabled or not hasattr(self, 'log_edit'):
            return

        scrollbar = self.log_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def run_japanese_inspection(self):
        trs_dir = os.path.abspath(os.path.join(globals().get('OUT', './out/'), 'trs'))

        if not os.path.exists(trs_dir):
            os.makedirs(trs_dir, exist_ok=True)

        json_path, _ = QFileDialog.getOpenFileName(self, '일본어 검사할 JSON 파일 선택', trs_dir, 'JSON 파일 (*.json)')

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
            result = trans_ai.inspect_json_japanese(json_path, ratio_threshold=ratio_val, char_count_threshold=count_val)
            items = result.get('items', [])
            title = result.get('title', '작품')

            if not items:
                self.add_log(f"일본어 검사 결과: [{criteria_desc}] 만족하는 남은 일본어가 검출되지 않았습니다 ({title})")
                QMessageBox.information(self, '일본어 검사 완료', f"'{title}'\n\n검출 기준({criteria_desc})에 해당하는 문장이 없습니다.\n번역이 양호합니다.")
                return

            self.add_log(f"일본어 검사: {len(items)}개 블록 검출 완료 ({criteria_desc}). 검사 창을 엽니다.")
            dialog = check_jp.JapaneseCheckDialog(result, self)
            dialog.exec()

        except Exception as e:
            self.add_log(f"일본어 검사 실패: {e}")
            QMessageBox.critical(self, '검사 실패', f"일본어 검사 중 오류가 발생했습니다: {e}")

    def apply_ui_style(self):
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
            'isno_x': False,
            'thinking_budget': '기본값'
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
        self._clear_layout(self.model_list_layout)
        available = self._available_model_names()

        for i, item in enumerate(self.selected_models):
            name = str(item.get('model', '')).strip()

            row = QWidget()
            row.setObjectName('no_back-modelRow')
            row.setFixedHeight(38)

            rl = self._layout('h', (2, 1, 2, 1), 5, row)

            indicator = self._label('●' if i == self.active_model_index else '', 'modelActiveIndicator', 12)
            indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rl.addWidget(indicator)

            combo = self._combo([], h=36)
            combo.setObjectName('modelRowCombo')
            combo.setToolTip('클릭하여 이 모델을 다른 Gemini 모델로 변경')

            models = list(available)

            if name and name not in models:
                models.insert(0, name)

            combo.addItems(models)
            combo.setCurrentText(name)
            combo.activated.connect(lambda _, idx=i, c=combo: self.change_selected_model(idx, c.currentText()))
            rl.addWidget(combo, 1)

            select = self._button('선택', lambda _, idx=i: self.select_model(idx), 'modelSelectBtn', 36, 54)
            select.setToolTip('이 모델의 설정을 편집')

            delete = self._button('삭제', lambda _, idx=i: self.delete_model(idx), 'modelDeleteBtn', 36, 54)
            delete.setToolTip('이 모델 삭제')

            rl.addWidget(select)
            rl.addWidget(delete)
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
        if not 0 <= index < len(self.selected_models):
            return

        if save_current:
            self.update_active_model()

        self.active_model_index = index
        model = self.selected_models[index]

        self.selected_model_edit.setText(str(model.get('model', '')))
        self._set_combo(self.rpm_combo, model.get('rpm', 15))
        self._set_combo(self.temp_combo, model.get('temperature', 0.1))
        self._set_combo(self.concurrency_combo, model.get('concurrency', 4))
        self._set_combo(self.br_start_combo, model.get('br_start', 0))
        self._set_combo(self.censor_combo, '사용 안함' if model.get('isno_x', False) else '사용')

        value = str(model.get('thinking_budget', '기본값'))
        matches = [self.thinking_combo.itemText(i) for i in range(self.thinking_combo.count())]
        match = next((x for x in matches if value.lower() in x.lower()), value)

        self._set_combo(self.thinking_combo, match)
        self.rebuild_model_list()

    def update_active_model(self, *args):
        if self.active_model_index < 0 or self.active_model_index >= len(self.selected_models):
            return

        try:
            self.selected_models[self.active_model_index]['rpm'] = int(self.rpm_combo.currentText())
            self.selected_models[self.active_model_index]['temperature'] = float(self.temp_combo.currentText())
            self.selected_models[self.active_model_index]['concurrency'] = int(self.concurrency_combo.currentText())
            self.selected_models[self.active_model_index]['br_start'] = int(self.br_start_combo.currentText())
            self.selected_models[self.active_model_index]['isno_x'] = self.censor_combo.currentText() == '사용 안함'
            self.selected_models[self.active_model_index]['thinking_budget'] = self.thinking_combo.currentText()
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
                'isno_x': bool(x.get('isno_x', False)),
                'thinking_budget': str(x.get('thinking_budget', '기본값'))
            }
            for x in self.selected_models
            if str(x.get('model', '')).strip()
        ]

    def _load_json(self):
        if not os.path.exists(self.SETTINGS_FILE):
            return {}

        try:
            with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.add_log(f'설정 불러오기 실패: {e}')
            return {}

    def _save_json(self, data):
        with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _model_config(self, model, base=None):
        base = base or {}

        return {
            'model': str(model).strip(),
            'rpm': int(base.get('rpm', 15)),
            'temperature': float(base.get('temperature', 0.1)),
            'concurrency': int(base.get('concurrency', 4)),
            'br_start': int(base.get('br_start', 0)),
            'isno_x': bool(base.get('isno_x', False)),
            'thinking_budget': str(base.get('thinking_budget', '기본값'))
        }

    def _models_from_data(self, models, defaults=None):
        defaults = defaults or {}
        result, used = [], set()

        for item in models if isinstance(models, list) else []:
            raw = {'model': item} if isinstance(item, str) else item if isinstance(item, dict) else {}
            model = str(raw.get('model', '')).strip()
            key = model.casefold()

            if model and key not in used:
                used.add(key)
                result.append(self._model_config(model, {**defaults, **raw}))

        return result

    def load_settings(self):
        data = self._load_json()

        api = str(data.get('api', '')).strip()
        self.api_edit.setText(api)
        self.api_edit.textChanged.connect(lambda value: trans_ai.set_api_key(value) if value else None)

        defaults = {
            'rpm': data.get('translate_rpm', 15),
            'temperature': data.get('translate_temperature', 0.1),
            'concurrency': data.get('translate_concurrency', 4),
            'br_start': data.get('translate_br_start', 0),
            'isno_x': data.get('translate_isno_x', False),
            'thinking_budget': data.get('translate_thinking_budget', '기본값')
        }

        self.selected_models = self._models_from_data(data.get('translate_models'), defaults)

        if not self.selected_models and data.get('translate_model'):
            self.selected_models = [self._model_config(data['translate_model'], defaults)]

        max_chars = str(data.get('translate_max_chars', 5000))
        self._set_combo(self.chars_combo, max_chars)

        self.glossary_enabled = bool(data.get('translate_glossary_enabled', True))
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
                self.add_log(f'자동 모델 조회 실패: {e}')

        self.add_log('저장된 번역 설정을 불러왔습니다.')

    def save_settings(self):
        self.update_active_model()
        api, configs = self.api_edit.text().strip(), self.get_model_configs()

        if not api or not configs:
            QMessageBox.warning(self, '알림', 'API 키와 Gemini 모델을 확인하세요.')
            return False

        try:
            data = self._load_json()
            first = configs[0]

            data.update({
                'api': api,
                'translate_model': first['model'],
                'translate_models': configs,
                'translate_rpm': first['rpm'],
                'translate_temperature': first['temperature'],
                'translate_concurrency': first['concurrency'],
                'translate_br_start': first['br_start'],
                'translate_isno_x': first['isno_x'],
                'translate_thinking_budget': first['thinking_budget'],
                'translate_max_chars': int(self.chars_combo.currentText()),
                'translate_glossary_enabled': self.glossary_enabled
            })

            data['dictionary'] = data.get('dictionary') if isinstance(data.get('dictionary'), dict) else {}
            data['pre'] = data.get('pre') if isinstance(data.get('pre'), dict) else {}

            self._save_json(data)
            self.add_log('번역 기본 설정이 저장되었습니다.')
            return True

        except Exception as e:
            QMessageBox.critical(self, '오류', str(e))
            return False

    def save_preset(self):
        self.update_active_model()
        name, configs = self.preset_name_edit.text().strip(), self.get_model_configs()

        if not name:
            QMessageBox.warning(self, '알림', '프리셋 이름을 입력하세요.')
            return

        if not configs:
            QMessageBox.warning(self, '알림', '최소 하나의 모델을 추가하세요.')
            return

        try:
            data = self._load_json()
            data['pre'] = data.get('pre') if isinstance(data.get('pre'), dict) else {}

            data['pre'][name] = {
                'models': configs,
                'max_chars': int(self.chars_combo.currentText()),
                'glossary_enabled': self.glossary_enabled
            }

            self._save_json(data)
            self.preset_name_edit.setText(name)
            self.preset_status.setText(f'현재 프리셋: {name}')
            self.add_log(f'프리셋 저장 완료: {name}')

        except Exception as e:
            QMessageBox.critical(self, '프리셋 저장 오류', str(e))

    def load_preset(self):
        try:
            data = self._load_json()
            presets = data.get('pre', {})

            if not isinstance(presets, dict) or not presets:
                QMessageBox.information(self, '프리셋', '저장된 프리셋이 없습니다.')
                return

            dialog = preset.PresetLoadDialog(presets, self)

            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            name, presetq = dialog.selected_name, presets.get(dialog.selected_name)

            if not isinstance(presetq, dict):
                QMessageBox.warning(self, '알림', '프리셋 데이터가 올바르지 않습니다.')
                return

            models = self._models_from_data(presetq.get('models'), presetq)

            if not models:
                QMessageBox.warning(self, '알림', '프리셋에 유효한 모델이 없습니다.')
                return

            self.selected_models, self.active_model_index = models, -1
            self._set_combo(self.chars_combo, presetq.get('max_chars', 5000))

            self.glossary_enabled = bool(presetq.get('glossary_enabled', True))
            self.glossary_toggle_btn.setChecked(self.glossary_enabled)
            self.update_glossary_button()

            self.preset_name_edit.setText(name)
            self.preset_status.setText(f'현재 프리셋: {name}')
            self.select_model(0, save_current=False)
            self.add_log(f'프리셋 불러오기 완료: {name}')

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
        if self.is_trans and not self.is_stop:
            self.stop_trans()
            return
        elif self.is_trans and not self.is_stop_i:
            self.stop_trans_i()
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
        thinking_budgets = tuple(x.get('thinking_budget', '기본값') for x in model_configs)
        dict_data = dict(self.current_dictionary) if self.glossary_enabled else {}

        self.is_trans = True
        self.is_stop = False
        self.is_stop_i = False
        self.start_btn.setText('번역 중지')
        self.progress_bar.setValue(0)
        self.percent_label.setText('0%')

        self.add_log('')
        self.add_log('=' * 55)
        self.add_log('번역 시작')

        for i, config in enumerate(model_configs, 1):
            censor_state = "건너뜀" if config['isno_x'] else "적용"

            self.add_log(
                f"모델 {i}: {config['model']} / RPM {config['rpm']} / Temp {config['temperature']} / "
                f"동시 {config['concurrency']} / 분할시작 {config['br_start']} / 검열: {censor_state} / "
                f"추론: {config.get('thinking_budget', '기본값')}"
            )

        self.add_log(f"작품명: {self.file_title}")
        self.add_log(f"청크 글자수: {max_chars}")
        self.add_log('용어집: ' + (f"활성 ({len(dict_data)}개)" if self.glossary_enabled else '비활성'))
        self.add_log('=' * 55)

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
                check_i=self.get_out_i,
                br_start=br_starts,
                isno_x=isno_xs,
                thinking_budget=thinking_budgets
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
        self.start_btn.setText('중지 중... (다시 눌를 시 강제 번역 종료)')

    def stop_trans_i(self):
        if not self.is_trans:
            return

        self.is_stop_i = True
        self.add_log('중지: 번역 강제 중지 요청 중...')
        self.start_btn.setEnabled(False)
        self.start_btn.setText('중지 중...')

    def get_out(self):
        return self.is_stop

    def get_out_i(self):
        return self.is_stop_i

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
        is_dark = self.get_brightness(bg_color) < 200

        color_map = {
            'DARK': {
                'NORMAL': '#e0e0e0',
                'ERROR': '#ff5555',
                'WARN': '#ffb86c',
                'SUCCESS': '#50fa7b',
                'INFO': '#8be9fd'
            },
            'LIGHT': {
                'NORMAL': '#222222',
                'ERROR': '#d32f2f',
                'WARN': '#e65100',
                'SUCCESS': '#2e7d32',
                'INFO': '#0288d1'
            }
        }

        mode = 'DARK' if is_dark else 'LIGHT'
        color = color_map[mode][log_type]

        safe_text = html.escape(str(text)).replace('\n', '<br>')
        formatted_html = f'<span style="color: {color}; font-family: Consolas, monospace;">{safe_text}</span>'

        self.log_history.append((log_type, formatted_html))

        current_filter = self.log_filter_combo.currentText()

        if self._matches_filter(log_type, current_filter):
            self.log_edit.append(formatted_html)
            self.scroll_log_to_bottom()

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

        self.scroll_log_to_bottom()

    def clear_logs(self):
        self.log_history.clear()
        self.log_edit.clear()

    def on_finished(self, success, message, output_dir):
        self.start_btn.setEnabled(True)
        self.start_btn.setText('번역 시작')
        self.is_trans = False
        self.is_stop = False
        self.is_stop_i = False

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