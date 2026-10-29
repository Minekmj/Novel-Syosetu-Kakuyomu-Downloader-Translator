from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSizePolicy, QWidget, QScrollArea, QFrame, QMessageBox
from src.main.thread_pyqt import ModelLoadThread
from .ui_factory import (
    create_layout, create_label, create_button, create_combo,
    set_combo_value, clear_layout
)


class ModelPanel(QWidget):
    log_requested = Signal(str)
    status_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_models = []
        self.active_model_index = -1
        self.model_load_thread = None
        self.settings_panel = None
        self.init_ui()

    def set_settings_panel(self, settings_panel):
        self.settings_panel = settings_panel

    def init_ui(self):
        layout = create_layout('v', (0, 0, 0, 0), spacing=8, parent=self)

        model_row = create_layout('h')
        model_row.addWidget(create_label('모델', width=36))
        self.model_add_combo = create_combo([], h=35)
        self.model_add_combo.setPlaceholderText('Gemini 모델 선택')
        model_row.addWidget(self.model_add_combo, 1)
        model_row.addWidget(create_button('추가', self.add_selected_model, w=56))
        self.refresh_model_btn = create_button('새로고침', None, w=76)
        model_row.addWidget(self.refresh_model_btn)
        layout.addLayout(model_row)

        layout.addWidget(create_label('사용 모델 목록', 'subLabel'))

        self.model_list_container = QWidget()
        self.model_list_container.setObjectName('no_back-modelListContainer')
        self.model_list_layout = create_layout('v', spacing=4, parent=self.model_list_container)

        self.model_scroll = QScrollArea()
        self.model_scroll.setObjectName('no_back-modelScroll')
        self.model_scroll.setWidgetResizable(True)
        self.model_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.model_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.model_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.model_scroll.setWidget(self.model_list_container)
        self.model_scroll.setFixedHeight(112)
        layout.addWidget(self.model_scroll)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def rebuild_model_list(self):
        clear_layout(self.model_list_layout)
        available = self._available_model_names()

        for i, item in enumerate(self.selected_models):
            name = str(item.get('model', '')).strip()

            row = QWidget()
            row.setObjectName('no_back-modelRow')
            row.setFixedHeight(38)

            rl = create_layout('h', (2, 1, 2, 1), 5, row)

            indicator = create_label('●' if i == self.active_model_index else '', 'modelActiveIndicator', 12)
            indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rl.addWidget(indicator)

            combo = create_combo([], h=36)
            combo.setObjectName('modelRowCombo')
            combo.setToolTip('클릭하여 이 모델을 다른 Gemini 모델로 변경')

            models = list(available)

            if name and name not in models:
                models.insert(0, name)

            combo.addItems(models)
            combo.setCurrentText(name)
            combo.activated.connect(lambda _, idx=i, c=combo: self.change_selected_model(idx, c.currentText()))
            rl.addWidget(combo, 1)

            select = create_button('선택', lambda _, idx=i: self.select_model(idx), 'modelSelectBtn', 36, 54)
            select.setToolTip('이 모델의 설정을 편집')

            delete = create_button('삭제', lambda _, idx=i: self.delete_model(idx), 'modelDeleteBtn', 36, 54)
            delete.setToolTip('이 모델 삭제')

            rl.addWidget(select)
            rl.addWidget(delete)
            self.model_list_layout.addWidget(row)

        self.model_list_layout.addStretch(1)
        self.update_active_model_display()

    def _available_model_names(self):
        names = []
        for i in range(self.model_add_combo.count()):
            name = self.model_add_combo.itemText(i).strip()
            if name and name.casefold() not in {x.casefold() for x in names}:
                names.append(name)
        return names

    def load_gemini_models(self, api_key):
        if not api_key:
            QMessageBox.warning(self, '알림', 'Gemini API 키를 먼저 입력하세요.')
            return False

        self.refresh_model_btn.setEnabled(False)
        self.status_requested.emit('Gemini 모델 목록을 불러오는 중...')

        try:
            self.model_load_thread = ModelLoadThread(api_key)
            self.model_load_thread.finished.connect(self.on_models_loaded)
            self.model_load_thread.start()
            return True
        except NameError:
            self.refresh_model_btn.setEnabled(True)
            return False

    def on_models_loaded(self, model_names, error_msg):
        self.refresh_model_btn.setEnabled(True)

        if error_msg:
            self.log_requested.emit(f"모델 조회 실패: {error_msg}")
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
            self.log_requested.emit(f"텍스트 생성이 가능한 Gemini 모델 {len(model_names)}개를 불러왔습니다.")
            self.status_requested.emit('Gemini 모델 목록을 불러왔습니다.')
        else:
            self.log_requested.emit('사용 가능한 Gemini 텍스트 모델을 찾지 못했습니다.')
            self.status_requested.emit('사용 가능한 모델이 없습니다.')

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
        self.log_requested.emit(f"모델 추가: {model}")

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

        if index == self.active_model_index and self.settings_panel:
            self.settings_panel.selected_model_edit.setText(new_model)

        current_active = self.active_model_index
        self.rebuild_model_list()

        if 0 <= current_active < len(self.selected_models):
            self.active_model_index = current_active
            self.update_active_model_display()

        self.log_requested.emit(f"모델 변경: {old_model} → {new_model}")

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

        self.log_requested.emit(f"모델 삭제: {model}")

    def update_active_model_display(self):
        if not self.settings_panel:
            return
        if 0 <= self.active_model_index < len(self.selected_models):
            model = str(self.selected_models[self.active_model_index].get('model', '')).strip()
            self.settings_panel.selected_model_edit.setText(model)
        else:
            self.settings_panel.selected_model_edit.clear()

    def select_model(self, index, save_current=True):
        if not 0 <= index < len(self.selected_models):
            return

        if save_current:
            self.update_active_model()

        self.active_model_index = index
        model = self.selected_models[index]

        if self.settings_panel:
            self.settings_panel.selected_model_edit.setText(str(model.get('model', '')))
            set_combo_value(self.settings_panel.rpm_combo, model.get('rpm', 15))
            set_combo_value(self.settings_panel.temp_combo, model.get('temperature', 0.1))
            set_combo_value(self.settings_panel.concurrency_combo, model.get('concurrency', 4))
            set_combo_value(self.settings_panel.br_start_combo, model.get('br_start', 0))
            set_combo_value(self.settings_panel.censor_combo, '사용 안함' if model.get('isno_x', False) else '사용')

            value = str(model.get('thinking_budget', '기본값'))
            matches = [self.settings_panel.thinking_combo.itemText(i) for i in range(self.settings_panel.thinking_combo.count())]
            match = next((x for x in matches if value.lower() in x.lower()), value)
            set_combo_value(self.settings_panel.thinking_combo, match)

        self.rebuild_model_list()

    def update_active_model(self, *args):
        if not self.settings_panel or self.active_model_index < 0 or self.active_model_index >= len(self.selected_models):
            return

        try:
            self.selected_models[self.active_model_index]['rpm'] = int(self.settings_panel.rpm_combo.currentText())
            self.selected_models[self.active_model_index]['temperature'] = float(self.settings_panel.temp_combo.currentText())
            self.selected_models[self.active_model_index]['concurrency'] = int(self.settings_panel.concurrency_combo.currentText())
            self.selected_models[self.active_model_index]['br_start'] = int(self.settings_panel.br_start_combo.currentText())
            self.selected_models[self.active_model_index]['isno_x'] = self.settings_panel.censor_combo.currentText() == '사용 안함'
            self.selected_models[self.active_model_index]['thinking_budget'] = self.settings_panel.thinking_combo.currentText()
        except (ValueError, TypeError):
            pass

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