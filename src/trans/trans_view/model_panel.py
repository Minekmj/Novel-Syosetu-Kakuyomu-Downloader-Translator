import json
import os
from datetime import datetime
from PySide6.QtCore import Qt, Signal
from src.system.config import DATA_FILE_BACK_MODEL
from PySide6.QtWidgets import QSizePolicy, QWidget, QScrollArea, QFrame, QMessageBox
from src.ai import AiRoute, AiTarget
from src.main.thread_pyqt import ModelLoadThread
from .model_utils import TARGET_NAMES
from .ui_factory import (
    create_layout, create_label, create_button, create_combo,
    set_combo_value, clear_layout
)

from src.app_state import state


class ModelPanel(QWidget):
    log_requested = Signal(str)
    status_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_models = []
        self.active_model_index = -1
        self.model_load_thread = None
        self.settings_panel = None
        cached = state.get("cached_models")
        if not isinstance(cached, dict):
            cached = {}
            state.set("cached_models", cached)
        self._cached_models = cached
        self._load_queue = []
        self._auto_checked_targets = set()
        self.init_ui()

    def set_settings_panel(self, settings_panel):
        self.settings_panel = settings_panel

    def init_ui(self):
        layout = create_layout('v', (0, 0, 0, 0), spacing=8, parent=self)

        model_row = create_layout('h')

        self.target_add_combo = create_combo([], h=35)
        self.target_add_combo.setFixedWidth(95)
        for t in sorted(AiRoute.TARGET_NAMES.keys()):
            self.target_add_combo.addItem(AiRoute.get_target_name(t), int(t))
        default_combo_idx = self.target_add_combo.findData(int(AiRoute.DEFAULT_TARGET))
        if default_combo_idx >= 0:
            self.target_add_combo.setCurrentIndex(default_combo_idx)
        self.target_add_combo.currentIndexChanged.connect(self.on_add_target_combo_changed)
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

    def on_add_target_combo_changed(self, combo_idx):
        target_data = self.target_add_combo.itemData(combo_idx)
        target_idx = int(target_data) if target_data is not None else int(AiRoute.DEFAULT_TARGET)
        self.on_add_target_changed(target_idx)

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

        self.refresh_model_btn.setEnabled(True)

    @staticmethod
    def _load_back_models():
        try:
            if os.path.exists(DATA_FILE_BACK_MODEL):
                with open(DATA_FILE_BACK_MODEL, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    @staticmethod
    def _save_back_models(data):
        try:
            parent = os.path.dirname(DATA_FILE_BACK_MODEL)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(DATA_FILE_BACK_MODEL, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _get_back_model_entry(self, target_name: str):
        data = self._load_back_models()
        entry = data.get(target_name)
        if isinstance(entry, dict) and isinstance(entry.get('models'), list) and entry['models']:
            return list(entry['models']), str(entry.get('date') or '')
        return None, ''

    def _save_back_model_entry(self, target_name: str, models: list):
        data = self._load_back_models()
        data[target_name] = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'models': list(models)
        }
        self._save_back_models(data)

    def _get_available_models_for_target(self, target_idx: int):
        base_models = list(AiRoute.get_popular_models(target_idx))
        target_name = AiRoute.get_target_name(target_idx)

        today_str = datetime.now().strftime('%Y-%m-%d')
        is_fresh_today = False
        if target_idx != int(AiTarget.OLLAMA):
            backed_models, backed_date = self._get_back_model_entry(target_name)
            if backed_models:
                if target_name not in self._cached_models:
                    self._cached_models[target_name] = list(backed_models)
                if backed_date == today_str:
                    is_fresh_today = True

        if target_idx == int(AiTarget.PLAYGROUND) and target_name not in self._cached_models:
            from src.system.load_save import load_data
            saved_pg = load_data().get("playground_cached_models", [])
            if isinstance(saved_pg, list) and saved_pg:
                self._cached_models[target_name] = list(saved_pg)

        need_auto = (target_name not in self._cached_models) or (target_idx != int(AiTarget.OLLAMA) and not is_fresh_today)
        if need_auto and (target_idx, today_str) not in self._auto_checked_targets:
            if self.settings_panel and target_idx in self.settings_panel.api_edits:
                api_key = self.settings_panel.api_edits[target_idx].text().strip()
                if target_idx == int(AiTarget.OLLAMA) and not api_key:
                    from src.system.load_save import load_data
                    api_key = str(load_data().get("ollama_url", "http://localhost:11434")).strip()
                    self.settings_panel.set_api_key(target_idx, api_key)
                if target_idx == int(AiTarget.PLAYGROUND):
                    if AiRoute(ai_target=target_idx, api=api_key).check_login(api_key=api_key, target=target_idx):
                        self._auto_checked_targets.add((target_idx, today_str))
                        self.load_models(api_key, target_idx, manual=False)
                elif target_idx == int(AiTarget.OLLAMA) or api_key:
                    self._auto_checked_targets.add((target_idx, today_str))
                    self.load_models(api_key, target_idx, manual=False)

        data = self._cached_models.get(target_name, [])
        return list(data) if data else base_models

    def on_manual_refresh_clicked(self, target_idx=None):
        if target_idx is None or isinstance(target_idx, bool) or target_idx < 0:
            target_idx = self.get_current_target()
        if self.settings_panel and target_idx in self.settings_panel.api_edits:
            api_key = self.settings_panel.api_edits[target_idx].text().strip()
            if target_idx == int(AiTarget.OLLAMA) and not api_key:
                from src.system.load_save import load_data
                api_key = str(load_data().get("ollama_url", "http://localhost:11434")).strip()
                self.settings_panel.set_api_key(target_idx, api_key)
            self.load_models(api_key, target_idx, manual=True)

    def rebuild_model_list(self):
        clear_layout(self.model_list_layout)
        sorted_targets = sorted(AiRoute.TARGET_NAMES.keys())

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

            row_target_combo = create_combo([], h=50)
            for t in sorted_targets:
                row_target_combo.addItem(AiRoute.get_target_name(t), int(t))
            t_combo_idx = row_target_combo.findData(target_int)
            if t_combo_idx >= 0:
                row_target_combo.setCurrentIndex(t_combo_idx)
            row_target_combo.setFixedWidth(90)
            row_target_combo.setToolTip('이 모델의 AI 종류 변경')
            row_target_combo.activated.connect(
                lambda _, idx=i, c=row_target_combo: self.change_selected_target(idx, int(c.currentData()))
            )
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
        target_idx = self.get_current_target()
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
            self.settings_panel.set_thinking_visible(target_int != int(AiTarget.OLLAMA))

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

    def load_models(self, api_key="", target_idx: int = -1, manual=False):
        if target_idx < 0:
            target_idx = self.get_current_target()

        target_name = AiRoute.get_target_name(target_idx)
        if not manual and target_idx != int(AiTarget.OLLAMA):
            today_str = datetime.now().strftime('%Y-%m-%d')
            backed_models, backed_date = self._get_back_model_entry(target_name)
            if backed_models and backed_date == today_str:
                self._cached_models[target_name] = list(backed_models)
                return True
            cached = state.get("cached_models") or {}
            if cached.get(target_name) and (target_idx, today_str) in self._auto_checked_targets:
                self._cached_models[target_name] = list(cached[target_name])
                return True

        if target_idx == int(AiTarget.OLLAMA) and not api_key:
            from src.system.load_save import load_data
            api_key = str(load_data().get("ollama_url", "http://localhost:11434")).strip()
            if self.settings_panel:
                self.settings_panel.set_api_key(target_idx, api_key)

        if target_idx == int(AiTarget.PLAYGROUND):
            api_key = (api_key or "default").strip()
            if not AiRoute(ai_target=target_idx, api=api_key).check_login(api_key=api_key, target=target_idx):
                if manual:
                    QMessageBox.warning(
                        self,
                        '알림',
                        'Playground 로그인이 필요합니다.\n[API 설정 -> Playground]에서 로그인을 진행하세요.'
                    )
                return False
        elif not api_key and target_idx != int(AiTarget.OLLAMA):
            if manual:
                is_vertex = hasattr(AiTarget, "VERTEX") and target_idx == int(getattr(AiTarget, "VERTEX"))
                msg = 'JSON 키 파일 경로 또는 인증 정보를 먼저 입력하세요.' if is_vertex else 'API 키를 먼저 입력하세요.'
                QMessageBox.warning(self, '알림', msg)
            return False

        for item in self._load_queue:
            if item['target_idx'] == target_idx:
                item['api_key'] = api_key
                item['manual'] = item['manual'] or manual
                self._process_next_load()
                return True

        self._load_queue.append({
            'api_key': api_key,
            'target_idx': target_idx,
            'manual': manual
        })

        self._process_next_load()
        return True

    def _process_next_load(self):
        if self.model_load_thread is not None and self.model_load_thread.isRunning():
            return

        if not self._load_queue:
            self.refresh_model_btn.setEnabled(True)
            return

        task = self._load_queue.pop(0)
        api_key = task['api_key']
        target_idx = task['target_idx']
        manual = task['manual']

        self.refresh_model_btn.setEnabled(False)
        name = AiRoute.get_target_name(target_idx)
        self.status_requested.emit(f'{name} 모델 목록을 자동으로 조회하는 중...')

        try:
            self.model_load_thread = ModelLoadThread(api_key, target_idx)
            self.model_load_thread.finished.connect(
                lambda names, err: self.on_models_loaded(names, err, target_idx, manual)
            )
            self.model_load_thread.start()
        except Exception as e:
            if manual:
                self.log_requested.emit(f"모델 조회 실패: {e}")
            self.model_load_thread = None
            self._process_next_load()

    def get_current_target(self):
        data = self.target_add_combo.currentData()
        return int(data) if data is not None else int(AiRoute.DEFAULT_TARGET)

    def on_models_loaded(self, model_names, error_msg, target_idx: int, manual=False):
        if error_msg:
            self.log_requested.emit(f"모델 조회 실패: {error_msg}")
            self.status_requested.emit("모델 조회 실패")
            if manual:
                QMessageBox.critical(self, '모델 조회 실패', error_msg)
        else:
            target_name = AiRoute.get_target_name(target_idx)
            popular = set(AiRoute.get_popular_models(target_idx))
            is_real_list = bool(model_names) and (
                target_idx == int(AiTarget.OLLAMA) or set(model_names) != popular
            )
            if is_real_list:
                cached = state.get("cached_models")
                if not isinstance(cached, dict):
                    cached = {}
                    state.set("cached_models", cached)
                cached[target_name] = list(model_names)
                self._cached_models[target_name] = list(model_names)
                if target_idx != int(AiTarget.OLLAMA):
                    self._save_back_model_entry(target_name, model_names)

            if self.get_current_target() == target_idx:
                current = self.model_add_combo.currentText()
                models = self._get_available_models_for_target(target_idx)

                self.model_add_combo.clear()
                self.model_add_combo.addItems(models)

                default_model = AiRoute.get_default_model(target_idx)
                if current and current in models:
                    self.model_add_combo.setCurrentText(current)
                elif default_model in models:
                    self.model_add_combo.setCurrentText(default_model)
                elif models:
                    self.model_add_combo.setCurrentIndex(0)

            self.rebuild_model_list()
            self.log_requested.emit(f"모델 목록 조회 완료 ({len(model_names)}개 모델)")

        self.model_load_thread = None
        self._process_next_load()