import json
import os
from datetime import datetime
from typing import List, Optional
from src.system.config import DATA_FILE_BACK_MODEL

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QMessageBox
)
from src.ai import AiRoute, AiTarget
from src.system.data import load_data, save_data
from src.main.thread_pyqt import ModelLoadThread
from .widgets import SmoothListWidget


class RecommendControlPanel(QWidget):
    start_requested = Signal(str, str, str, int, dict, int)
    stop_requested = Signal()
    log_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_load_thread = None
        self.is_running = False
        self.is_stopping = False

        self.api_timer = QTimer(self)
        self.api_timer.setSingleShot(True)
        self.api_timer.setInterval(700)
        self._auto_checked_targets = set()
        self.api_timer.timeout.connect(lambda: self.fetch_models(manual=False))

        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 10, 2)
        layout.setSpacing(10)

        api_lbl = QLabel("API 설정")
        api_lbl.setObjectName("cat_label")
        layout.addWidget(api_lbl)

        api_box = QHBoxLayout()
        api_box.setSpacing(6)

        self.target_combo = QComboBox()
        self.target_combo.setFixedHeight(34)
        self.target_combo.setFixedWidth(85)
        for target_id, name in sorted(AiRoute.TARGET_NAMES.items()):
            if target_id == AiTarget.OLLAMA:
                continue
            
            self.target_combo.addItem(name, target_id)
        self.target_combo.currentIndexChanged.connect(self.on_target_combo_changed)
        api_box.addWidget(self.target_combo)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("API Key")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setFixedHeight(34)
        self.api_key_edit.textChanged.connect(self.on_api_key_changed)
        api_box.addWidget(self.api_key_edit, stretch=1)

        self.api_toggle_btn = QPushButton("보기")
        self.api_toggle_btn.setCheckable(True)
        self.api_toggle_btn.setObjectName("subtleBtn")
        self.api_toggle_btn.setFixedSize(50, 34)
        self.api_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.api_toggle_btn.clicked.connect(self.toggle_api_visibility)
        api_box.addWidget(self.api_toggle_btn)
        layout.addLayout(api_box)

        model_box = QHBoxLayout()
        model_box.setSpacing(6)

        self.model_combo = QComboBox()
        self.model_combo.setFixedHeight(34)
        model_box.addWidget(self.model_combo, stretch=1)

        self.refresh_model_btn = QPushButton("조회")
        self.refresh_model_btn.setObjectName("subtleBtn")
        self.refresh_model_btn.setFixedSize(60, 34)
        self.refresh_model_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_model_btn.clicked.connect(lambda: self.fetch_models(manual=True))
        model_box.addWidget(self.refresh_model_btn)
        layout.addLayout(model_box)

        model_desc = QLabel("라이트 계열 모델을 추천합니다. 반복 작업으로 인해 무료 티어 시 제한이 빨리 찾아옵니다.")
        model_desc.setObjectName("lbl_url")
        model_desc.setStyleSheet("font-size: 11px; line-height: 1.3;")
        model_desc.setWordWrap(True)
        layout.addWidget(model_desc)

        history_header = QHBoxLayout()
        history_header.setSpacing(6)
        self.chk_use_history = QCheckBox("내 감상 목록 반영")
        self.chk_use_history.setChecked(True)
        self.chk_use_history.toggled.connect(self.on_history_toggled)
        history_header.addWidget(self.chk_use_history)
        history_header.addStretch()

        self.btn_select_all_history = QPushButton("전체")
        self.btn_select_all_history.setObjectName("subtleBtn")
        self.btn_select_all_history.setFixedSize(48, 26)
        self.btn_select_all_history.setCursor(Qt.PointingHandCursor)
        self.btn_select_all_history.clicked.connect(self.toggle_all_history_checks)
        history_header.addWidget(self.btn_select_all_history)
        layout.addLayout(history_header)

        self.history_list_widget = SmoothListWidget()
        self.history_list_widget.setMinimumHeight(120)
        self.history_list_widget.setMaximumHeight(200)
        self.history_list_widget.setObjectName("group_box")
        self.history_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list_widget.setTextElideMode(Qt.ElideRight)
        self.history_list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.history_list_widget.setStyleSheet(
            "QListWidget::item {"
            "  padding: 5px 6px;"
            "  border-bottom: 1px solid rgba(128, 128, 128, 0.15);"
            "}"
            "QListWidget::item:hover {"
            "  background-color: rgba(128, 128, 128, 0.15);"
            "  border-radius: 4px;"
            "}"
        )
        layout.addWidget(self.history_list_widget)

        list_desc = QLabel("AI 추천 시 반영할 목록입니다. 작품을 선택하여 반영 여부를 결정할 수 있습니다.")
        list_desc.setObjectName("lbl_url")
        list_desc.setStyleSheet("font-size: 11px; line-height: 1.3;")
        list_desc.setWordWrap(True)
        layout.addWidget(list_desc)

        req_lbl = QLabel("요청사항")
        req_lbl.setObjectName("cat_label")
        layout.addWidget(req_lbl)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("예: 주인공이 지능적이고 분위기가 진지한 다크 판타지 추천해줘.")
        layout.addWidget(self.prompt_edit, stretch=1)

        rec_count_box = QHBoxLayout()
        rec_count_box.setSpacing(8)
        rec_count_lbl = QLabel("추천 수:")
        rec_count_lbl.setObjectName("cat_label")
        rec_count_box.addWidget(rec_count_lbl)

        self.top_k_combo = QComboBox()
        self.top_k_combo.setFixedHeight(34)
        for num in [3, 5, 7, 10, 15]:
            self.top_k_combo.addItem(f"{num}작품 추천", num)
        self.top_k_combo.setCurrentIndex(1)
        rec_count_box.addWidget(self.top_k_combo, stretch=1)
        layout.addLayout(rec_count_box)

        self.start_btn = QPushButton("추천 시작")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedHeight(44)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.on_action_btn_clicked)
        layout.addWidget(self.start_btn)

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

    def get_current_target(self) -> int:
        data = self.target_combo.currentData()
        return int(data) if data is not None else AiRoute.DEFAULT_TARGET

    def on_target_combo_changed(self, index: int):
        target = self.get_current_target()
        target_name = AiRoute.get_target_name(target)
        is_pg = (target == int(AiTarget.PLAYGROUND))
        if is_pg:
            self.api_key_edit.setPlaceholderText("Playground 프로필 (기본: default)")
            self.api_key_edit.setEchoMode(QLineEdit.Normal)
            self.api_toggle_btn.hide()
        else:
            self.api_key_edit.setPlaceholderText(f"{target_name} API Key 또는 Endpoint")
            self.api_key_edit.setEchoMode(QLineEdit.Normal if self.api_toggle_btn.isChecked() else QLineEdit.Password)
            self.api_toggle_btn.show()

        user_data = load_data()
        single_k, list_k, _ = AiRoute.get_storage_keys(target)
        saved_api = str(user_data.get(single_k, "")).strip()
        if not saved_api:
            keys = user_data.get(list_k, [])
            if isinstance(keys, list) and keys:
                saved_api = str(keys[0]).strip()
        if is_pg and not saved_api:
            saved_api = "default"

        self.api_key_edit.blockSignals(True)
        self.api_key_edit.setText(saved_api)
        self.api_key_edit.blockSignals(False)

        models = list(AiRoute.get_popular_models(target))
        today_str = datetime.now().strftime('%Y-%m-%d')
        is_fresh_today = False
        if target != int(AiTarget.OLLAMA):
            entry = self._load_back_models().get(target_name)
            if isinstance(entry, dict) and isinstance(entry.get('models'), list) and entry['models']:
                models = list(entry['models'])
                if str(entry.get('date') or '') == today_str:
                    is_fresh_today = True

        self.model_combo.clear()
        self.model_combo.addItems(models)

        def_model = AiRoute.get_default_model(target)
        if def_model in models:
            self.model_combo.setCurrentText(def_model)
        elif models:
            self.model_combo.setCurrentIndex(0)

        self.refresh_model_btn.setEnabled(True)
        if not is_fresh_today and (target, today_str) not in self._auto_checked_targets:
            if is_pg:
                if AiRoute(ai_target=target, api=saved_api).check_login(api_key=saved_api, target=target):
                    self._auto_checked_targets.add((target, today_str))
                    QTimer.singleShot(100, lambda: self.fetch_models(manual=False))
            elif saved_api or target == int(AiTarget.OLLAMA):
                self._auto_checked_targets.add((target, today_str))
                QTimer.singleShot(100, lambda: self.fetch_models(manual=False))

    def load_initial_data(self):
        user_data = load_data()

        curr_target = int(AiTarget.GEMINI)

        t_idx = self.target_combo.findData(curr_target)
        if t_idx >= 0:
            self.target_combo.setCurrentIndex(t_idx)
        else:
            self.target_combo.setCurrentIndex(0)

        self.on_target_combo_changed(self.target_combo.currentIndex())

        raw_list = user_data.get("list", {})
        self.history_list_widget.clear()

        if isinstance(raw_list, dict) and raw_list:
            for title, info in raw_list.items():
                if not isinstance(info, dict):
                    continue
                item = QListWidgetItem(title)
                item.setToolTip(title)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                item.setData(Qt.UserRole, info)
                self.history_list_widget.addItem(item)
        else:
            item = QListWidgetItem("저장된 감상 목록이 없습니다.")
            item.setFlags(Qt.NoItemFlags)
            self.history_list_widget.addItem(item)

    def on_api_key_changed(self):
        key = self.api_key_edit.text().strip()
        if len(key) >= 20 and self.get_current_target() not in (int(AiTarget.OLLAMA), int(AiTarget.PLAYGROUND)):
            self.api_timer.start()

    def toggle_api_visibility(self, checked: bool):
        if checked:
            self.api_key_edit.setEchoMode(QLineEdit.Normal)
            self.api_toggle_btn.setText("숨김")
        else:
            self.api_key_edit.setEchoMode(QLineEdit.Password)
            self.api_toggle_btn.setText("보기")

    def on_history_toggled(self, checked: bool):
        self.history_list_widget.setEnabled(checked)
        self.btn_select_all_history.setEnabled(checked)

    def toggle_all_history_checks(self):
        any_unchecked = False
        for i in range(self.history_list_widget.count()):
            item = self.history_list_widget.item(i)
            if item.checkState() == Qt.Unchecked:
                any_unchecked = True
                break

        target_state = Qt.Checked if any_unchecked else Qt.Unchecked
        for i in range(self.history_list_widget.count()):
            item = self.history_list_widget.item(i)
            item.setCheckState(target_state)

    def fetch_models(self, manual=True):
        target = self.get_current_target()
        name = AiRoute.get_target_name(target)
        today_str = datetime.now().strftime('%Y-%m-%d')

        api_key = self.api_key_edit.text().strip()
        if target == int(AiTarget.PLAYGROUND):
            api_key = api_key or "default"
            if not AiRoute(ai_target=target, api=api_key).check_login(api_key=api_key, target=target):
                if manual:
                    QMessageBox.warning(self, "알림", "Playground 로그인이 필요합니다.\n[번역 -> API 설정 -> Playground]에서 로그인을 진행하세요.")
                return
        elif not api_key and target != int(AiTarget.OLLAMA):
            return

        if not manual and target != int(AiTarget.OLLAMA):
            entry = self._load_back_models().get(name)
            if isinstance(entry, dict) and isinstance(entry.get('models'), list) and entry['models'] and str(entry.get('date') or '') == today_str:
                return

        if ModelLoadThread is None:
            return

        if self.model_load_thread is not None and self.model_load_thread.isRunning():
            return

        self.refresh_model_btn.setEnabled(False)
        self.log_requested.emit(f"{name} 사용 가능 모델 목록을 조회 중입니다...")

        self.model_load_thread = ModelLoadThread(
            api_key, ai_target=target
        )
        self.model_load_thread.finished.connect(lambda m, e, t=target: self.on_models_fetched(m, e, t))
        self.model_load_thread.start()

    def on_models_fetched(self, models: List[str], err_msg: str, target_idx: Optional[int] = None):
        self.refresh_model_btn.setEnabled(True)
        if err_msg:
            self.log_requested.emit(f"모델 목록 조회 실패: {err_msg}")
            return

        if target_idx is None:
            target_idx = self.get_current_target()

        if models:
            if target_idx != int(AiTarget.OLLAMA):
                popular = set(AiRoute.get_popular_models(target_idx))
                if set(models) != popular:
                    back = self._load_back_models()
                    back[AiRoute.get_target_name(target_idx)] = {
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'models': list(models)
                    }
                    self._save_back_models(back)

            if self.get_current_target() == target_idx:
                current = self.model_combo.currentText()
                all_models = list(models)
                if not all_models:
                    all_models = AiRoute.get_popular_models(target_idx)

                self.model_combo.clear()
                self.model_combo.addItems(all_models)

                def_model = AiRoute.get_default_model(target_idx)
                if current and current in all_models:
                    self.model_combo.setCurrentText(current)
                elif def_model in all_models:
                    self.model_combo.setCurrentText(def_model)
                elif all_models:
                    self.model_combo.setCurrentIndex(0)

            self.log_requested.emit(f"모델 {len(models)}개를 불러왔습니다.")

    def set_running(self, running: bool):
        self.is_running = running
        self.is_stopping = False
        self.start_btn.setEnabled(True)
        self.start_btn.setText("추천 중단" if running else "추천 시작")

    def set_stopping(self):
        self.is_stopping = True
        self.start_btn.setEnabled(False)
        self.start_btn.setText("중단 중...")

    def on_action_btn_clicked(self):
        if self.is_running:
            if not self.is_stopping:
                self.set_stopping()
                self.stop_requested.emit()
            return
        self.start_recommendation()

    def start_recommendation(self):
        api_key = self.api_key_edit.text().strip()
        target = self.get_current_target()
        target_name = AiRoute.get_target_name(target)

        if target == int(AiTarget.PLAYGROUND):
            api_key = api_key or "default"
            if not AiRoute(ai_target=target, api=api_key).check_login(api_key=api_key, target=target):
                QMessageBox.warning(self, "알림", "Playground 로그인이 필요합니다.\n[번역 -> API 설정 -> Playground]에서 로그인을 진행하세요.")
                return
        elif not api_key and target != int(AiTarget.OLLAMA):
            QMessageBox.warning(self, "알림", f"{target_name} API 키를 입력하세요.")
            self.api_key_edit.setFocus()
            return

        model = self.model_combo.currentText().strip() or AiRoute.get_default_model(target)
        final_target = target

        condition = self.prompt_edit.toPlainText().strip()
        top_k = self.top_k_combo.currentData() or 5

        user_data = {"list": {}}
        if self.chk_use_history.isChecked():
            selected_works = {}
            for i in range(self.history_list_widget.count()):
                item = self.history_list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    title = item.text().strip()
                    info = item.data(Qt.UserRole)
                    if isinstance(info, dict):
                        selected_works[title] = info
            user_data["list"] = selected_works

        saved = load_data()
        single_k, list_k, _ = AiRoute.get_storage_keys(target)
        saved[single_k] = api_key
        keys_list = saved.get(list_k, [])
        if not isinstance(keys_list, list) or not keys_list:
            saved[list_k] = [api_key] if api_key else []
        elif api_key and api_key not in keys_list:
            saved[list_k].insert(0, api_key)
        save_data(saved)

        self.start_requested.emit(api_key, model, condition, top_k, user_data, final_target)