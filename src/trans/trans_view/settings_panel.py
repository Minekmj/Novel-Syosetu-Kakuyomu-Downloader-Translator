import os
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QTabWidget, QWidget, QLineEdit, QComboBox, QSizePolicy, QFileDialog, QMessageBox
)
from src.ai import AiRoute, AiTarget
from src.system.load_save import load_data, save_data
import src.trans.trans_ai as trans_ai
from src.trans.trans_ai_utils import inspect_json_japanese
import src.trans.trans_check_jp as check_jp
import src.trans.preset as preset
from .ui_factory import (
    create_layout, create_label, create_button, create_combo, set_combo_value
)
from .api_dialog import ApiManagerDialog


class SettingsPanel(QTabWidget):
    params_changed = Signal(dict)
    log_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('settingsTab')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.glossary_enabled = True

        self.api_edits = {}
        self.api_status_lbls = {}
        
        self.model_panel = None

        self.init_tabs()
        
    def set_model_panel(self, model_panel):
        self.model_panel = model_panel

    def _tab(self, title, obj):
        tab = QWidget()
        tab.setObjectName(obj)
        self.addTab(tab, title)
        return tab, create_layout('v', (6, 8, 6, 6), 7, tab)

    def init_tabs(self):
        tab, tl = self._tab('매개변수', 'no_back-tabParams')
        row = create_layout('h')
        row.addWidget(create_label('선택 모델', 'optionLabel'))
        self.selected_model_edit = QLineEdit()
        self.selected_model_edit.setObjectName('selectedModelDisplay')
        self.selected_model_edit.setReadOnly(True)
        self.selected_model_edit.setMinimumHeight(35)
        self.selected_model_edit.setPlaceholderText('위 사용 모델 목록에서 모델을 선택하세요')
        row.addWidget(self.selected_model_edit, 1)
        tl.addLayout(row)

        grid = create_layout('g', spacing=7)
        options = [
            ('RPM', 'rpm_combo', ['1', '2', '3', '5', '7', '10', '15', '20', '30', '60'], '15'),
            ('Temperature', 'temp_combo', ['0.0', '0.1', '0.2', '0.3', '0.5', '0.7', '1.0'], '0.1'),
            ('동시 작업', 'concurrency_combo', [str(i) for i in range(1, 61)], '4'),
            ('청크 글자수', 'chars_combo', ['100', '250', '500', '1000', '2000', '3000', '4000', '5000', '7000', '10000', '15000', '20000', '30000'], '5000'),
            ('분할 시작', 'br_start_combo', ['0', '1', '2', '3', '4'], '0'),
            ('검열하기', 'censor_combo', ['사용', '사용 안함'], '사용')
        ]

        for i, (label, attr, items, current) in enumerate(options):
            r, c = divmod(i, 2)
            grid.addWidget(create_label(label, 'optionLabel'), r, c * 2)
            setattr(self, attr, create_combo(items, current, self.notify_params_changed))
            grid.addWidget(getattr(self, attr), r, c * 2 + 1)

        self.censor_combo.setToolTip('사용: 검열 시도 후 분할 / 사용 안함: 검열 건너뛰고 바로 분할')

        grid.addWidget(create_label('추론', 'optionLabel'), 3, 0)
        self.thinking_combo = create_combo(['기본값', 'minimal', 'low', 'medium', 'high', 'xhigh'], '기본값', self.notify_params_changed)
        grid.addWidget(self.thinking_combo, 3, 1, 1, 3)
        tl.addLayout(grid)
        tl.addStretch(1)

        tab, tl = self._tab('용어집', 'no_back-tabDict')
        row = create_layout('h')
        self.dictionary_status = create_label('선택된 작품 없음')
        self.dictionary_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.dictionary_status.setWordWrap(True)
        row.addWidget(self.dictionary_status, 1)
        self.dictionary_btn = create_button('설정', None, w=58)
        row.addWidget(self.dictionary_btn)
        tl.addLayout(row)

        row = create_layout('h')
        row.addWidget(create_label('번역에 용어집 사용'))
        row.addStretch(1)
        self.glossary_toggle_btn = create_button('', self.toggle_glossary, w=78, checkable=True)
        row.addWidget(self.glossary_toggle_btn)
        tl.addLayout(row)
        tl.addStretch(1)

        tab, tl = self._tab('프리셋', 'no_back-tabPre')
        row = create_layout('h')
        self.preset_name_edit = QLineEdit()
        self.preset_name_edit.setPlaceholderText('프리셋 이름')
        self.preset_name_edit.setMinimumHeight(35)
        row.addWidget(self.preset_name_edit, 1)
        self.preset_save_btn = create_button('저장', None, w=58)
        self.preset_load_btn = create_button('불러오기', None, w=76)
        row.addWidget(self.preset_save_btn)
        row.addWidget(self.preset_load_btn)
        tl.addLayout(row)
        self.preset_status = create_label('현재 프리셋 없음', 'secondaryInfo')
        tl.addWidget(self.preset_status)
        tl.addStretch(1)

        tab, tl = self._tab('API 설정', 'no_back-tabApi')
        self.api_sub_tabs = QTabWidget()
        self.api_sub_tabs.setObjectName('apiSubTabs')

        for target_int, target_name in sorted(AiRoute.TARGET_NAMES.items()):
            sub_w = QWidget()
            sl = create_layout('v', (6, 6, 6, 6), spacing=6, parent=sub_w)
            srow = create_layout('h', spacing=6)

            is_vertex = False
            is_local = (target_int == int(AiTarget.OLLAMA))

            api_edit = preset.PasteOnlyLineEdit()
            api_edit.setMinimumHeight(34)
            srow.addWidget(api_edit, 1)

            clear_btn = create_button('✕', api_edit.clear, w=36)
            srow.addWidget(clear_btn)

            if is_vertex:
                browse_btn = create_button('파일 찾기', lambda _, e=api_edit: self._browse_vertex_key(e), w=75)
                srow.addWidget(browse_btn)

            show_btn = create_button('숨기기' if is_vertex else '보기', None, w=65, checkable=True)
            if is_vertex:
                show_btn.setChecked(True)
            show_btn.toggled.connect(lambda c, e=api_edit, b=show_btn: self._toggle_vis(e, b, c))
            srow.addWidget(show_btn)

            more_btn = create_button('더보기', lambda _, t=target_int: self.open_api_manager(t), w=64)
            srow.addWidget(more_btn)

            sl.addLayout(srow)

            status_lbl = create_label('', 'secondaryInfo')
            sl.addWidget(status_lbl)
            sl.addStretch(1)

            if is_vertex:
                api_edit.setPlaceholderText("JSON 키 파일 경로 (.json) 또는 Project ID")
                api_edit.setEchoMode(QLineEdit.EchoMode.Normal)
                show_btn.hide()
            elif is_local:
                api_edit.hide()
                clear_btn.hide()
                show_btn.hide()
                more_btn.setText("로컬 모델 설정")
                more_btn.setFixedWidth(400)
            else:
                api_edit.setPlaceholderText(f"{target_name} API Key 또는 Endpoint")
                api_edit.setEchoMode(QLineEdit.EchoMode.Password)

            api_edit.textChanged.connect(lambda text, t=target_int: self.on_api_key_changed(t, text))

            self.api_edits[target_int] = api_edit
            self.api_status_lbls[target_int] = status_lbl
            self.api_sub_tabs.addTab(sub_w, target_name)

        tl.addWidget(self.api_sub_tabs)

        tab, tl = self._tab('검사', 'no_back-tabInspect')
        tl.setContentsMargins(8, 10, 8, 8)
        tl.setSpacing(10)
        tl.addWidget(create_label('일본어 잔존 검사', 'subLabel'))

        row = create_layout('h')
        row.addWidget(create_label('모드', 'optionLabel', 50))
        self.inspect_mode_combo = create_combo(['비율 모드', '글자 수 모드'], '비율 모드', self.on_inspect_mode_changed)
        row.addWidget(self.inspect_mode_combo, 1)
        tl.addLayout(row)

        self.inspect_ratio_widget = QWidget()
        rlay = create_layout('h', parent=self.inspect_ratio_widget)
        self.inspect_ratio_combo = QComboBox()
        for v in [1, 2, 3, 5, 7, 10, 15, 20, 30, 40, 50]:
            self.inspect_ratio_combo.addItem(f'{v}% 이상', float(v))
        self.inspect_ratio_combo.setCurrentIndex(5)
        self.inspect_ratio_combo.setMinimumHeight(35)
        rlay.addWidget(self.inspect_ratio_combo, 1)
        tl.addWidget(self.inspect_ratio_widget)

        self.inspect_count_widget = QWidget()
        clay = create_layout('h', parent=self.inspect_count_widget)
        self.inspect_count_combo = QComboBox()
        for v in [1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 100]:
            self.inspect_count_combo.addItem(f'{v}자 이상', int(v))
        self.inspect_count_combo.setCurrentIndex(3)
        self.inspect_count_combo.setMinimumHeight(35)
        clay.addWidget(self.inspect_count_combo, 1)
        tl.addWidget(self.inspect_count_widget)
        self.inspect_count_widget.setVisible(False)

        self.inspect_btn = create_button('검사하기', self.run_japanese_inspection, 'primaryBtn', 36)
        tl.addWidget(self.inspect_btn)
        self.inspect_status_lbl = create_label('선택된 검사 파일 없음', 'secondaryInfo')
        self.inspect_status_lbl.setVisible(False)
        tl.addWidget(self.inspect_status_lbl)
        self.inspect_info = create_label('trs 폴더 내의 번역 JSON 파일을 분석하여 남은 문장을 검사합니다.', 'secondaryInfo')
        self.inspect_info.setWordWrap(True)
        tl.addWidget(self.inspect_info)
        tl.addStretch(1)

        self.update_glossary_button()

    def on_api_key_changed(self, target: int, text: str):
        if target == int(AiTarget.OLLAMA):
            return
        clean_text = text.strip()
        data = load_data()
        single_k, list_k, idx_k = AiRoute.get_storage_keys(target)
        keys_val = data.get(list_k, [])
        if not isinstance(keys_val, list):
            keys_val = []

        if clean_text:
            if clean_text not in keys_val:
                keys_val.insert(0, clean_text)
                idx = 0
            else:
                idx = keys_val.index(clean_text)
        else:
            idx = 0

        data[single_k] = clean_text
        data[list_k] = keys_val
        data[idx_k] = idx
        save_data(data)

        if target == AiRoute.DEFAULT_TARGET:
            trans_ai.set_api_keys(keys_val, idx)

        self.update_api_status_display(target, len(keys_val), idx)

    def _browse_vertex_key(self, edit_widget):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Vertex AI 서비스 계정 JSON 파일 선택', '', 'JSON 키 파일 (*.json);;모든 파일 (*.*)'
        )
        if path:
            edit_widget.setText(path)

    def get_api_key(self, target: int) -> str:
        edit = self.api_edits.get(int(target))
        return edit.text().strip() if edit else ""

    def set_api_key(self, target: int, key: str):
        edit = self.api_edits.get(int(target))
        if edit:
            edit.blockSignals(True)
            edit.setText(str(key or "").strip())
            edit.blockSignals(False)

    def _toggle_vis(self, edit_widget, btn_widget, checked):
        if checked:
            edit_widget.setEchoMode(QLineEdit.EchoMode.Normal)
            btn_widget.setText('숨기기')
        else:
            edit_widget.setEchoMode(QLineEdit.EchoMode.Password)
            btn_widget.setText('보기')

    def open_api_manager(self, target: int):
        dialog = ApiManagerDialog(self, ai_target=target)
        if dialog.exec() == ApiManagerDialog.DialogCode.Accepted:
            active_key, keys, idx = dialog.get_current_api_data()
            if target in self.api_edits:
                self.api_edits[target].setText(active_key)
            self.update_api_status_display(target, len(keys), idx)
        if target == AiTarget.OLLAMA:
            self.model_panel.load_models(target_idx=target, manual=False)

    def update_api_status_display(self, target: int, total_count: int, active_idx: int):
        lbl = self.api_status_lbls.get(int(target))
        if not lbl:
            return
        t_name = AiRoute.get_target_name(target)
        if int(target) == int(AiTarget.OLLAMA):
            lbl.setText(f"{t_name} 로컬 엔드포인트 설정 완료")
        elif total_count > 1:
            lbl.setText(f"등록된 {t_name} API: 총 {total_count}개 / 현재 활성: [{active_idx}]")
        elif total_count == 1:
            lbl.setText(f"등록된 {t_name} API: 1개 [0] 메인")
        else:
            lbl.setText("")

    def notify_params_changed(self, *args):
        try:
            self.params_changed.emit({
                'rpm': int(self.rpm_combo.currentText()),
                'temperature': float(self.temp_combo.currentText()),
                'concurrency': int(self.concurrency_combo.currentText()),
                'br_start': int(self.br_start_combo.currentText()),
                'isno_x': self.censor_combo.currentText() == '사용 안함',
                'thinking_budget': self.thinking_combo.currentText()
            })
        except (ValueError, TypeError):
            pass

    def toggle_glossary(self, checked):
        self.glossary_enabled = bool(checked)
        self.update_glossary_button()

    def update_glossary_button(self):
        self.glossary_toggle_btn.setText('활성' if self.glossary_enabled else '비활성')
        self.glossary_toggle_btn.setChecked(self.glossary_enabled)

    def on_inspect_mode_changed(self, mode_text):
        is_ratio = mode_text == '비율 모드'
        self.inspect_ratio_widget.setVisible(is_ratio)
        self.inspect_count_widget.setVisible(not is_ratio)

    def run_japanese_inspection(self):
        trs_dir = os.path.abspath(os.path.join(os.environ.get("minedown_setting_src", "./out/"), 'trs'))
        if not os.path.exists(trs_dir):
            os.makedirs(trs_dir, exist_ok=True)

        json_path, _ = QFileDialog.getOpenFileName(self, '일본어 검사할 JSON 파일 선택', trs_dir, 'JSON 파일 (*.json)')
        if not json_path:
            return

        self.inspect_status_lbl.setText(f"선택: {os.path.basename(json_path)}")
        self.log_requested.emit(f"일본어 검사 시작: {json_path}")

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
            result = inspect_json_japanese(json_path, ratio_threshold=ratio_val, char_count_threshold=count_val)
            items = result.get('items', [])
            title = result.get('title', '작품')

            if not items:
                self.log_requested.emit(f"일본어 검사 결과: [{criteria_desc}] 만족하는 남은 일본어가 검출되지 않았습니다 ({title})")
                QMessageBox.information(self, '일본어 검사 완료', f"'{title}'\n\n검출 기준({criteria_desc})에 해당하는 문장이 없습니다.\n번역이 양호합니다.")
                return

            self.log_requested.emit(f"일본어 검사: {len(items)}개 블록 검출 완료 ({criteria_desc}). 검사 창을 엽니다.")
            dialog = check_jp.JapaneseCheckDialog(result, self)
            dialog.exec()
        except Exception as e:
            self.log_requested.emit(f"일본어 검사 실패: {e}")
            QMessageBox.critical(self, '검사 실패', f"일본어 검사 중 오류가 발생했습니다: {e}")