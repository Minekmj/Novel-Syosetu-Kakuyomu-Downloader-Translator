from typing import List

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QMessageBox
)
from src.system.data import load_data, save_data
from src.main.thread_pyqt import ModelLoadThread
from .widgets import SmoothListWidget

class RecommendControlPanel(QWidget):
    start_requested = Signal(str, str, str, int, dict)
    log_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_load_thread = None

        self.api_timer = QTimer(self)
        self.api_timer.setSingleShot(True)
        self.api_timer.setInterval(700)
        self.api_timer.timeout.connect(self.fetch_gemini_models)

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
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Gemini API Key")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setFixedHeight(34)
        self.api_key_edit.textChanged.connect(self.on_api_key_changed)
        api_box.addWidget(self.api_key_edit, stretch=1)

        self.api_toggle_btn = QPushButton("보기")
        self.api_toggle_btn.setCheckable(True)
        self.api_toggle_btn.setObjectName("subtleBtn")
        self.api_toggle_btn.setFixedSize(54, 34)
        self.api_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.api_toggle_btn.clicked.connect(self.toggle_api_visibility)
        api_box.addWidget(self.api_toggle_btn)
        layout.addLayout(api_box)

        model_box = QHBoxLayout()
        model_box.setSpacing(6)
        self.model_combo = QComboBox()
        self.model_combo.setFixedHeight(34)
        self.model_combo.setEditable(False)
        self.model_combo.addItem("gemini-3.5-flash-lite")
        model_box.addWidget(self.model_combo, stretch=1)

        self.refresh_model_btn = QPushButton("새로고침")
        self.refresh_model_btn.setObjectName("subtleBtn")
        self.refresh_model_btn.setFixedSize(68, 34)
        self.refresh_model_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_model_btn.clicked.connect(self.fetch_gemini_models)
        model_box.addWidget(self.refresh_model_btn)
        layout.addLayout(model_box)

        model_desc = QLabel("라이트 계열 모델을 추천합니다. 반복 작업으로 인해 무료 티어 시 제한이 빨리 찾아 옵니다.")
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

        list_desc = QLabel("Ai 추천 시 반영할 목록 입니다. 작품을 선택하여 반영 혹은 반영하지 않음을 선택 할 수 있습니다.\n작품 좌측 표시를 트리거 하세요.")
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
        self.start_btn.clicked.connect(self.start_recommendation)
        layout.addWidget(self.start_btn)

    def load_initial_data(self):
        user_data = load_data()
        saved_api = user_data.get("api", "").strip()
        if saved_api:
            self.api_key_edit.blockSignals(True)
            self.api_key_edit.setText(saved_api)
            self.api_key_edit.blockSignals(False)
            QTimer.singleShot(100, self.fetch_gemini_models)

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
        if len(key) >= 20:
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

    def fetch_gemini_models(self):
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            return

        if ModelLoadThread is None:
            return

        self.refresh_model_btn.setEnabled(False)
        self.log_requested.emit("Gemini 사용 가능 모델 목록을 조회 중입니다...")

        self.model_load_thread = ModelLoadThread(api_key)
        self.model_load_thread.finished.connect(self.on_models_fetched)
        self.model_load_thread.start()

    def on_models_fetched(self, models: List[str], err_msg: str):
        self.refresh_model_btn.setEnabled(True)
        if err_msg:
            self.log_requested.emit(f"모델 목록 조회 실패: {err_msg}")
            return

        if models:
            self.model_combo.clear()
            self.model_combo.addItems(models)

            matched_idx = -1
            priority_targets = ["gemini-3.5-flash-lite", "3.5-lite", "gemini-3.1-flash-lite", "flash-lite"]
            for target in priority_targets:
                for idx, name in enumerate(models):
                    if target in name.lower():
                        matched_idx = idx
                        break
                if matched_idx != -1:
                    break

            if matched_idx != -1:
                self.model_combo.setCurrentIndex(matched_idx)

            self.log_requested.emit(f"Gemini 모델 {len(models)}개를 불러왔습니다.")

    def set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.start_btn.setText("추천 탐색 진행 중..." if running else "추천 시작")

    def start_recommendation(self):
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "알림", "Gemini API 키를 입력하세요.")
            self.api_key_edit.setFocus()
            return

        model = self.model_combo.currentText().strip() or "gemini-3.5-flash-lite"
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
        saved["api"] = api_key
        save_data(saved)

        self.start_requested.emit(api_key, model, condition, top_k, user_data)