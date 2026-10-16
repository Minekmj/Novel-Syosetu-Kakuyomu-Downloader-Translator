from typing import Dict, Any, List

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QUrl
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QScrollArea, QFrame, QSplitter,
    QMessageBox, QApplication
)
from PySide6.QtGui import QCursor, QDesktopServices
from src.system.data import load_data, save_data
from src.trans.trans import Translator
from src.find.site_list import site_point_text
from src.main.thread_pyqt import ModelLoadThread
from src.recommend.suggestion import NovelRecommender

detail_ui = None


class TitleTranslateWorker(QThread):
    finished = Signal(str)

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def run(self):
        try:
            res = Translator(self.text, True)
            self.finished.emit(res)
        except Exception:
            self.finished.emit(self.text)


class RecommendWorker(QThread):
    log_signal = Signal(str, str)
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, api_key: str, model: str, condition: str, top_k: int, user_data: dict):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.condition = condition
        self.top_k = top_k
        self.user_data = user_data

    def run(self):
        try:
            if NovelRecommender is None:
                raise RuntimeError("NovelRecommender 모듈을 찾을 수 없습니다.")

            def log_callback(l_type: str, text: str):
                self.log_signal.emit(l_type, str(text))

            recommender = NovelRecommender(
                gemini_api_key=self.api_key,
                model=self.model,
                user_data=self.user_data,
                log=log_callback
            )

            result = recommender.run_recommendation(
                top_k=self.top_k,
                user_custom_prompt=self.condition
            )
            self.finished_signal.emit(result)

        except Exception as e:
            self.error_signal.emit(str(e))


class ClickableTitleLabel(QLabel):
    def __init__(self, title_text: str, url_string: str = "", parent=None):
        super().__init__(title_text, parent)
        self.url_string = url_string
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setWordWrap(True)
        self.setObjectName("lbl_title")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.url_string:
            QDesktopServices.openUrl(QUrl(self.url_string))
        super().mousePressEvent(event)

class RecommendedWorkCard(QFrame):
    def __init__(self, item_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.story_expanded = False
        self.setObjectName("CardFrame")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)

        title_ja = self.item_data.get("title_ja", self.item_data.get("title", ""))
        url = self.item_data.get("url", "")

        self.title_label = ClickableTitleLabel(title_ja, url)
        self.title_label.setObjectName('lbl_title')
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        title_col.addWidget(self.title_label)

        if title_ja:
            self.sub_title_label = QLabel(f"{title_ja}")
            self.sub_title_label.setObjectName("lbl_url")
            self.sub_title_label.setWordWrap(True)
            title_col.addWidget(self.sub_title_label)

        header_layout.addLayout(title_col, stretch=1)

        badge_box = QVBoxLayout()
        badge_box.setAlignment(Qt.AlignRight | Qt.AlignTop)
        badge_box.setSpacing(4)

        score = self.item_data.get("match_score", 0)
        score_lbl = QLabel(f"적합도 {score}점")
        score_lbl.setStyleSheet(
            "font-weight: bold; "
            "padding: 4px 8px; border-radius: 4px; font-size: 12px;"
        )
        score_lbl.setAlignment(Qt.AlignCenter)
        badge_box.addWidget(score_lbl)

        site = self.item_data.get("site", "kakuyomu")
        site_names = {"kakuyomu": "카쿠요무", "naro": "소설가가 되자", "hameln": "하멜른"}
        site_lbl = QLabel(site_names.get(site, site))
        site_lbl.setObjectName("new_and_now")
        site_lbl.setAlignment(Qt.AlignRight)
        badge_box.addWidget(site_lbl)

        header_layout.addLayout(badge_box)
        layout.addLayout(header_layout)

        info_box = QFrame()
        info_box.setObjectName("CardFrame_ui")
        info_box_layout = QVBoxLayout(info_box)
        info_box_layout.setContentsMargins(12, 10, 12, 10)
        info_box_layout.setSpacing(7)

        one_liner = self.item_data.get("curator_one_liner", "")
        if one_liner:
            one_liner_lbl = QLabel(f"\"{one_liner}\"")
            one_liner_lbl.setObjectName("detail_description")
            one_liner_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
            one_liner_lbl.setWordWrap(True)
            info_box_layout.addWidget(one_liner_lbl)

        rationale = self.item_data.get("score_rationale", "")
        if rationale:
            rat_lbl = QLabel(f"<b>평가:</b> {rationale}")
            rat_lbl.setObjectName("detail_description")
            rat_lbl.setWordWrap(True)
            info_box_layout.addWidget(rat_lbl)

        past_conn = self.item_data.get("connection_with_past_reads", "")
        if past_conn:
            conn_lbl = QLabel(f"<b>독자 취향 연계:</b> {past_conn}")
            conn_lbl.setObjectName("detail_description")
            conn_lbl.setWordWrap(True)
            info_box_layout.addWidget(conn_lbl)

        warnings = self.item_data.get("cons_and_warnings", [])
        if warnings:
            if isinstance(warnings, list):
                warn_text = " / ".join(str(w) for w in warnings if str(w).strip())
            else:
                warn_text = str(warnings)
            if warn_text:
                warn_lbl = QLabel(f"<b>호불호:</b> {warn_text}")
                warn_lbl.setObjectName("lbl_url")
                warn_lbl.setStyleSheet("font-size: 12px;")
                warn_lbl.setWordWrap(True)
                info_box_layout.addWidget(warn_lbl)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(12)

        stars = str(self.item_data.get("stars", "0"))
        if stars and stars != "0":
            site_int = {"kakuyomu": 2, "naro": 1, "hameln": 3}
            meta_row.addWidget(QLabel(f"{site_point_text(site_int.get(site, 1), stars)}"))

        episodes = str(self.item_data.get("status_episodes", ""))
        if episodes:
            meta_row.addWidget(QLabel(episodes))

        updated = str(self.item_data.get("updated_at", ""))
        if updated:
            meta_row.addWidget(QLabel(f"갱신: {updated}"))

        meta_row.addStretch()
        info_box_layout.addLayout(meta_row)

        layout.addWidget(info_box)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        if detail_ui:
            self.dialog_btn = QPushButton("상세보기")
            self.dialog_btn.setObjectName("subtleBtn")
            self.dialog_btn.setFixedSize(94, 32)
            self.dialog_btn.clicked.connect(self.open_detail_dialog)
            btn_row.addWidget(self.dialog_btn)

        self.add_work_btn = QPushButton("작품 추가")
        self.add_work_btn.setObjectName("subtleBtn")
        self.add_work_btn.setFixedSize(94, 32)
        self.add_work_btn.clicked.connect(self.save_to_user_list)
        btn_row.addWidget(self.add_work_btn)

        layout.addLayout(btn_row)

        if title_ja:
            self.trans_worker = TitleTranslateWorker(title_ja)
            self.trans_worker.finished.connect(self.on_title_translated)
            self.trans_worker.start()

    def on_title_translated(self, translated: str):
        if translated and translated != self.item_data.get("title_ja"):
            self.title_label.setText(translated)
            self.item_data["title_ko"] = translated

    def open_detail_dialog(self):
        if detail_ui:
            item_for_dialog = {
                "title": self.item_data.get("title_ja", ""),
                "title_ko": self.item_data.get("title_ko", self.item_data.get("title_ja", "")),
                "url": self.item_data.get("url", ""),
                "stars": self.item_data.get("stars", "0"),
                "status_episodes": self.item_data.get("status_episodes", ""),
                "updated_at": self.item_data.get("updated_at", ""),
                "story": self.item_data.get("story", ""),
                "keywords": self.item_data.get("keywords", [])
            }
            site_int = {"kakuyomu": 2, "naro": 1, "hameln": 3}
            dialog = detail_ui.DetailDialog(
                item_data=item_for_dialog,
                auto_translate=True,
                site=site_int.get(self.item_data.get("site", "kakuyomu")),
                parent=self
            )
            dialog.exec()

    def save_to_user_list(self):
        detail_ui.click_plus_url = self.item_data.get('url', '')
        detail_ui.click = True
        self.add_work_btn.setText("추가됨")
        self.add_work_btn.setEnabled(False)


class NovelRecommendDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 추천")
        self.resize(1320, 860)
        self.setMinimumSize(1150, 750)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self.recommend_worker = None
        self.model_load_thread = None
        self.history_items = []

        self.api_timer = QTimer(self)
        self.api_timer.setSingleShot(True)
        self.api_timer.setInterval(700)
        self.api_timer.timeout.connect(self.fetch_gemini_models)

        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(8)

        left_widget = self.build_left_panel()
        center_widget = self.build_center_panel()
        right_widget = self.build_right_panel()

        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(center_widget)
        self.splitter.addWidget(right_widget)

        self.splitter.setSizes([330, 620, 370])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)

        root.addWidget(self.splitter, 1)

    def build_left_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 8, 2)
        layout.setSpacing(9)

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
        self.refresh_model_btn.clicked.connect(self.fetch_gemini_models)
        model_box.addWidget(self.refresh_model_btn)
        layout.addLayout(model_box)

        model_desc = QLabel("라이트 계열 모델을 추천합니다. 반복 작업으로 인해 무료 티어 시 제한이 빨리 찾아 옵니다.")
        model_desc.setObjectName("lbl_url")
        model_desc.setStyleSheet("font-size: 11px; line-height: 1.3;")
        model_desc.setWordWrap(True)
        layout.addWidget(model_desc)

        history_header = QHBoxLayout()
        self.chk_use_history = QCheckBox("내 목록 허용")
        self.chk_use_history.setChecked(True)
        self.chk_use_history.toggled.connect(self.on_history_toggled)
        history_header.addWidget(self.chk_use_history)
        history_header.addStretch()

        self.btn_select_all_history = QPushButton("전체")
        self.btn_select_all_history.setObjectName("subtleBtn")
        self.btn_select_all_history.setFixedSize(44, 26)
        self.btn_select_all_history.clicked.connect(self.toggle_all_history_checks)
        history_header.addWidget(self.btn_select_all_history)
        layout.addLayout(history_header)

        self.history_list_widget = QListWidget()
        self.history_list_widget.setFixedHeight(220)
        self.history_list_widget.setObjectName("group_box")
        self.history_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list_widget.setTextElideMode(Qt.ElideRight)
        self.history_list_widget.setStyleSheet(
            "QListWidget::item {"
            "  padding: 5px 6px;"
            "  border-bottom: 1px solid rgba(128, 128, 128, 0.15);"
            "}"
            "QListWidget::item:hover {"
            "  background-color: rgba(128, 128, 128, 0.15);"
            "  border-radius: 4px;"
            "}"
            "QListWidget::item:selected {"
            "  background-color: rgba(50, 120, 240, 0.25);"
            "  color: inherit;"
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
        layout.addWidget(self.prompt_edit, stretch=1)

        rec_count_box = QHBoxLayout()
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

        return container

    def build_center_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(10)

        header = QFrame()
        header.setObjectName("CardFrame_ui")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 10, 14, 10)

        self.results_title_lbl = QLabel("추천 결과")
        self.results_title_lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
        h_layout.addWidget(self.results_title_lbl)
        h_layout.addStretch()

        self.results_status_lbl = QLabel("")
        self.results_status_lbl.setObjectName("new_and_now")
        h_layout.addWidget(self.results_status_lbl)
        layout.addWidget(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setObjectName("t_123")
        self.scroll_area.setStyleSheet("#t_123{background: transparent;}")

        self.cards_container = QWidget()
        self.cards_container.setObjectName("t_123")
        self.cards_container.setStyleSheet("#t_123{background: transparent;}")
        
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 8, 0)
        self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area, stretch=1)

        return container

    def build_right_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 2, 2, 2)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_lbl = QLabel("추천 상태 로그")
        header_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_row.addWidget(header_lbl)
        header_row.addStretch()

        clear_btn = QPushButton("지우기")
        clear_btn.setObjectName("subtleBtn")
        clear_btn.setFixedSize(70, 28)
        clear_btn.clicked.connect(self.clear_feed)
        header_row.addWidget(clear_btn)
        layout.addLayout(header_row)

        self.feed_scroll = QScrollArea()
        self.feed_scroll.setWidgetResizable(True)
        self.feed_scroll.setFrameShape(QFrame.NoFrame)
        self.feed_scroll.setObjectName("t_123")
        self.feed_scroll.setStyleSheet("#t_123{background: transparent;}")

        self.feed_container = QWidget()
        self.feed_container.setObjectName("t_123")
        self.feed_container.setStyleSheet("#t_123{background: transparent;}")
        
        self.feed_layout = QVBoxLayout(self.feed_container)
        self.feed_layout.setContentsMargins(0, 0, 8, 0)
        self.feed_layout.setSpacing(10)
        self.feed_layout.addStretch()

        self.feed_scroll.setWidget(self.feed_container)
        layout.addWidget(self.feed_scroll, stretch=1)

        return container

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
        self.append_info_card("Gemini 사용 가능 모델 목록을 조회 중입니다...")

        self.model_load_thread = ModelLoadThread(api_key)
        self.model_load_thread.finished.connect(self.on_models_fetched)
        self.model_load_thread.start()

    def on_models_fetched(self, models: List[str], err_msg: str):
        self.refresh_model_btn.setEnabled(True)
        if err_msg:
            self.append_info_card(f"모델 목록 조회 실패: {err_msg}")
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

            self.append_info_card(f"Gemini 모델 {len(models)}개를 불러왔습니다.")

    def clear_feed(self):
        while self.feed_layout.count() > 1:
            child = self.feed_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def append_info_card(self, message: str):
        card = QFrame()
        card.setObjectName("CardFrame_ui")
        c_layout = QHBoxLayout(card)
        c_layout.setContentsMargins(10, 8, 10, 8)
        c_layout.setSpacing(8)

        msg_lbl = QLabel(message)
        msg_lbl.setObjectName("new_and_now")
        msg_lbl.setWordWrap(True)
        c_layout.addWidget(msg_lbl, stretch=1)

        self.feed_layout.insertWidget(self.feed_layout.count() - 1, card)
        QTimer.singleShot(50, self.scroll_feed_to_bottom)

    def append_ai_speech_card(self, thought_or_note: str):
        card = QFrame()
        card.setObjectName("CardFrame_ui")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(6)

        body_lbl = QLabel(thought_or_note)
        body_lbl.setWordWrap(True)
        body_lbl.setStyleSheet("font-weight: bold; font-size: 13px; line-height: 1.4;")
        c_layout.addWidget(body_lbl)

        self.feed_layout.insertWidget(self.feed_layout.count() - 1, card)
        QTimer.singleShot(50, self.scroll_feed_to_bottom)

    def scroll_feed_to_bottom(self):
        bar = self.feed_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def clear_result_cards(self):
        while self.cards_layout.count() > 1:
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def start_recommendation(self):
        if self.recommend_worker and self.recommend_worker.isRunning():
            QMessageBox.warning(self, "알림", "추천 작업이 진행 중입니다.")
            return

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

        self.clear_result_cards()
        self.start_btn.setEnabled(False)
        self.start_btn.setText("추천 탐색 진행 중...")
        self.results_status_lbl.setText("Ai 추천 중...")

        self.append_info_card(
            f"추천 세션 가동: 모델 {model}, 상위 {top_k}작품 선별, 기존 목록 {len(user_data['list'])}개 참조"
        )

        self.recommend_worker = RecommendWorker(
            api_key=api_key,
            model=model,
            condition=condition,
            top_k=top_k,
            user_data=user_data
        )
        self.recommend_worker.log_signal.connect(self.on_worker_log)
        self.recommend_worker.finished_signal.connect(self.on_recommendation_finished)
        self.recommend_worker.error_signal.connect(self.on_recommendation_failed)
        self.recommend_worker.start()

    def on_worker_log(self, log_type: str, text: str):
        if log_type == "ai":
            self.append_ai_speech_card(text)
        else:
            self.append_info_card(text)

    def on_recommendation_finished(self, result: Dict[str, Any]):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("추천 시작")

        works = result.get("recommended_works", [])
        curator_note = result.get("curator_note", "")

        if curator_note:
            self.append_ai_speech_card(f"<b>[최종 선별 총평]</b>\n{curator_note}")

        if not works:
            self.results_status_lbl.setText("추천 후보작 없음")
            no_lbl = QLabel("조건에 부합하는 작품을 발견하지 못했습니다. 검색 조건을 완화해 보세요.")
            no_lbl.setObjectName("new_and_now")
            no_lbl.setAlignment(Qt.AlignCenter)
            self.cards_layout.insertWidget(0, no_lbl)
            return

        self.results_status_lbl.setText(f"{len(works)} 작품 추천")

        for work in works:
            card = RecommendedWorkCard(work, self)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

        self.scroll_area.verticalScrollBar().setValue(0)

    def on_recommendation_failed(self, error_msg: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("추천 시작")
        self.results_status_lbl.setText("추천 실패")
        self.append_info_card(f"치명적 오류 발생: {error_msg}")
        QMessageBox.critical(self, "추천 오류", f"추천 파이프라인 수행 중 오류가 발생했습니다:\n{error_msg}")