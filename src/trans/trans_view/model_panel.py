from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSizePolicy, QWidget, QScrollArea, QFrame, QMessageBox
from src.ai import AiRoute, AiTarget
from src.main.thread_pyqt import ModelLoadThread
from .model_utils import TARGET_NAMES
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
        self._cached_gemini_models = []
        self.init_ui()

    def set_settings_panel(self, settings_panel):
        self.settings_panel = settings_panel

    def init_ui(self):
        layout = create_layout('v', (0, 0, 0, 0), spacing=8, parent=self)

        model_row = create_layout('h')
        model_row.addWidget(create_label('모델', width=32))

        target_list = [AiRoute.get_target_name(t) for t in sorted(AiRoute.TARGET_NAMES.keys())]
        self.target_add_combo = create_combo(target_list, AiRoute.get_target_name(AiRoute.DEFAULT_TARGET), h=35)
        self.target_add_combo.setFixedWidth(85)
        self.target_add_combo.currentIndexChanged.connect(self.on_add_target_changed)
        model_row.addWidget(self.target_add_combo)

        self.model_add_combo = create_combo([], h=35)
        model_row.addWidget(self.model_add_combo, 1)

        model_row.addWidget(create_button('추가', self.add_selected_model, w=54))
        self.refresh_model_btn = create_button('조회', self.on_manual_refresh_clicked, w=54)
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
        self.model_scroll.setFixedHeight(115)
        layout.addWidget(self.model_scroll)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self.on_add_target_changed(AiRoute.DEFAULT_TARGET)

    def on_add_target_changed(self, target_idx):
        target_idx = int(target_idx)
        models = self._get_available_models_for_target(target_idx)

        self.model_add_combo.clear()
        self.model_add_combo.addItems(models)

        default_model = AiRoute.get_default_model(target_idx)
        if default_model in models:
            self.model_add_combo.setCurrentText(default_model)
        elif models:
            self.model_add_combo.setCurrentIndex(0)

        self.refresh_model_btn.setEnabled(target_idx == int(AiTarget.GEMINI))

    def _get_available_models_for_target(self, target_idx: int):
        base_models = list(AiRoute.get_popular_models(target_idx))
        if target_idx == int(AiTarget.GEMINI) and self._cached_gemini_models:
            for gm in self._cached_gemini_models:
                if gm not in base_models:
                    base_models.append(gm)
        return base_models

    def on_manual_refresh_clicked(self):
        if self.settings_panel:
            api_key = self.settings_panel.gemini_api_edit.text().strip()
            self.load_gemini_models(api_key, manual=True)

    def rebuild_model_list(self):
        clear_layout(self.model_list_layout)
        target_list = [AiRoute.get_target_name(t) for t in sorted(AiRoute.TARGET_NAMES.keys())]

        for i, item in enumerate(self.selected_models):
            name = str(item.get('model', '')).strip()
            target_int = int(item.get('ai_target', AiRoute.DEFAULT_TARGET))

            row = QWidget()
            row.setObjectName('no_back-modelRow')
            row.setFixedHeight(38)

            rl = create_layout('h', (2, 1, 2, 1), 4, row)

            indicator = create_label('●' if i == self.active_model_index else '', 'modelActiveIndicator', 12)
            indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rl.addWidget(indicator)

            row_target_combo = create_combo(target_list, AiRoute.get_target_name(target_int), h=50)
            row_target_combo.setFixedWidth(82)
            row_target_combo.setToolTip('이 모델의 AI 종류 변경')
            row_target_combo.activated.connect(lambda _, idx=i, c=row_target_combo: self.change_selected_target(idx, c.currentIndex()))
            rl.addWidget(row_target_combo)

            row_model_combo = create_combo([], h=32)
            row_model_combo.setObjectName('modelRowCombo')

            available = self._get_available_models_for_target(target_int)
            if name and name not in available:
                available.insert(0, name)

            row_model_combo.addItems(available)
            row_model_combo.setCurrentText(name)
            row_model_combo.activated.connect(lambda _, idx=i, c=row_model_combo: self.change_selected_model(idx, c.currentText()))
            rl.addWidget(row_model_combo, 1)

            select = create_button('선택', lambda _, idx=i: self.select_model(idx), 'modelSelectBtn', 50, 48)
            select.setToolTip('이 모델의 파라미터 편집')

            delete = create_button('삭제', lambda _, idx=i: self.delete_model(idx), 'modelDeleteBtn', 50, 44)
            delete.setToolTip('이 모델 삭제')

            rl.addWidget(select)
            rl.addWidget(delete)
            self.model_list_layout.addWidget(row)

        self.model_list_layout.addStretch(1)
        self.update_active_model_display()

    def change_selected_target(self, index, new_target_idx):
        if not (0 <= index < len(self.selected_models)):
            return

        old_target = int(self.selected_models[index].get('ai_target', 0))
        if old_target == new_target_idx:
            return

        self.selected_models[index]['ai_target'] = new_target_idx

        current_model = str(self.selected_models[index].get('model', '')).strip()
        if AiRoute.detect_target(current_model) == old_target:
            self.selected_models[index]['model'] = AiRoute.get_default_model(new_target_idx)

        defaults = AiRoute.get_default_config(new_target_idx)
        self.selected_models[index]['rpm'] = defaults['rpm']
        self.selected_models[index]['concurrency'] = defaults['concurrency']

        self.rebuild_model_list()

        if index == self.active_model_index:
            self.select_model(index, save_current=False)

        self.log_requested.emit(
            f"종류 변경: [{AiRoute.get_target_name(old_target)}] → [{AiRoute.get_target_name(new_target_idx)}] ({self.selected_models[index]['model']})"
        )

    def change_selected_model(self, index, new_model):
        if not (0 <= index < len(self.selected_models)):
            return

        new_model = str(new_model).strip()
        if not new_model:
            return

        target_idx = int(self.selected_models[index].get('ai_target', 0))
        new_key = (target_idx, new_model.casefold())

        for i, config in enumerate(self.selected_models):
            if i == index:
                continue
            if (int(config.get('ai_target', 0)), str(config.get('model', '')).strip().casefold()) == new_key:
                QMessageBox.warning(self, '모델 중복', f"'{new_model}'은 해당 종류에 이미 등록된 모델입니다.")
                self.rebuild_model_list()
                return

        old_model = str(self.selected_models[index].get('model', '')).strip()
        if old_model == new_model:
            return

        self.selected_models[index]['model'] = new_model

        if index == self.active_model_index and self.settings_panel:
            self.settings_panel.selected_model_edit.setText(f"[{AiRoute.get_target_name(target_idx)}] {new_model}")

        current_active = self.active_model_index
        self.rebuild_model_list()

        if 0 <= current_active < len(self.selected_models):
            self.active_model_index = current_active
            self.update_active_model_display()

        self.log_requested.emit(f"모델 변경: {old_model} → [{AiRoute.get_target_name(target_idx)}] {new_model}")

    def add_selected_model(self):
        target_idx = self.target_add_combo.currentIndex()
        model = self.model_add_combo.currentText().strip()

        if not model:
            QMessageBox.warning(self, '알림', '추가할 모델명을 입력하거나 선택하세요.')
            return

        model_key = (target_idx, model.casefold())

        if any((int(x.get('ai_target', 0)), str(x.get('model', '')).strip().casefold()) == model_key for x in self.selected_models):
            QMessageBox.warning(self, '알림', '이미 추가된 모델입니다.')
            return

        defaults = AiRoute.get_default_config(target_idx)
        self.selected_models.append({
            'ai_target': target_idx,
            'model': model,
            'rpm': defaults['rpm'],
            'temperature': defaults['temperature'],
            'concurrency': defaults['concurrency'],
            'br_start': defaults['br_start'],
            'isno_x': defaults['isno_x'],
            'thinking_budget': defaults['thinking_budget']
        })

        new_index = len(self.selected_models) - 1
        self.active_model_index = new_index
        self.rebuild_model_list()
        self.select_model(new_index)
        self.log_requested.emit(f"모델 추가: [{AiRoute.get_target_name(target_idx)}] {model}")

    def delete_model(self, index):
        if not (0 <= index < len(self.selected_models)):
            return

        if len(self.selected_models) <= 1:
            QMessageBox.warning(self, '알림', '최소 하나의 모델은 필요합니다.')
            return

        model = self.selected_models[index].get('model', '')
        target_int = int(self.selected_models[index].get('ai_target', 0))
        self.selected_models.pop(index)

        if self.active_model_index == index:
            self.active_model_index = min(index, len(self.selected_models) - 1)
        elif self.active_model_index > index:
            self.active_model_index -= 1

        self.rebuild_model_list()

        if self.selected_models:
            self.select_model(self.active_model_index)

        self.log_requested.emit(f"모델 삭제: [{AiRoute.get_target_name(target_int)}] {model}")

    def update_active_model_display(self):
        if not self.settings_panel:
            return
        if 0 <= self.active_model_index < len(self.selected_models):
            m = self.selected_models[self.active_model_index]
            target_name = AiRoute.get_target_name(int(m.get('ai_target', 0)))
            model_text = str(m.get('model', '')).strip()
            self.settings_panel.selected_model_edit.setText(f"[{target_name}] {model_text}")
        else:
            self.settings_panel.selected_model_edit.clear()

    def select_model(self, index, save_current=True):
        if not (0 <= index < len(self.selected_models)):
            return

        if save_current:
            self.update_active_model()

        self.active_model_index = index
        model = self.selected_models[index]

        if self.settings_panel:
            target_int = int(model.get('ai_target', 0))
            target_name = AiRoute.get_target_name(target_int)

            self.settings_panel.selected_model_edit.setText(f"[{target_name}] {model.get('model', '')}")
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
        if not self.settings_panel or not (0 <= self.active_model_index < len(self.selected_models)):
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
                'ai_target': int(x.get('ai_target', 0)),
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

    def load_gemini_models(self, api_key, manual=False):
        if not api_key:
            if manual:
                QMessageBox.warning(self, '알림', 'Gemini API 키를 먼저 입력하세요.')
            return False

        self.refresh_model_btn.setEnabled(False)
        self.status_requested.emit('Gemini 모델 목록을 자동으로 조회하는 중...')

        try:
            self.model_load_thread = ModelLoadThread(api_key)
            self.model_load_thread.finished.connect(lambda names, err: self.on_models_loaded(names, err, manual))
            self.model_load_thread.start()
            return True
        except Exception as e:
            self.refresh_model_btn.setEnabled(True)
            if manual:
                self.log_requested.emit(f"모델 조회 실패: {e}")
            return False

    def on_models_loaded(self, model_names, error_msg, manual=False):
        self.refresh_model_btn.setEnabled(True)

        if error_msg:
            if manual:
                self.log_requested.emit(f"모델 조회 실패: {error_msg}")
                QMessageBox.critical(self, '모델 조회 실패', error_msg)
            return

        self._cached_gemini_models = list(model_names)

        if self.target_add_combo.currentIndex() == int(AiTarget.GEMINI):
            current = self.model_add_combo.currentText()
            models = self._get_available_models_for_target(AiTarget.GEMINI)

            self.model_add_combo.clear()
            self.model_add_combo.addItems(models)

            if current and current in models:
                self.model_add_combo.setCurrentText(current)
            elif AiRoute.DEFAULT_MODEL in models:
                self.model_add_combo.setCurrentText(AiRoute.DEFAULT_MODEL)
            elif models:
                self.model_add_combo.setCurrentIndex(0)

        self.rebuild_model_list()

        self.log_requested.emit(f"Gemini 모델 목록 조회 완료 ({len(model_names)}개 모델)")
        self.status_requested.emit('Gemini 모델 목록 자동 갱신 완료')