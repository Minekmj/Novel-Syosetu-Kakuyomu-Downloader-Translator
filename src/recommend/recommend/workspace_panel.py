from typing import Dict, Any, List

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QTabWidget, QSizePolicy
)
from .widgets import SmoothScrollArea
from . import card as cd

class RecommendWorkspacePanel(QWidget):
    toggle_exclude_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 2, 2, 2)
        layout.setSpacing(8)

        header = QFrame()
        header.setObjectName("CardFrame_ui")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 8, 14, 8)
        h_layout.setSpacing(10)

        self.results_title_lbl = QLabel("AI 작품 추천")
        self.results_title_lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
        h_layout.addWidget(self.results_title_lbl)

        h_layout.addStretch()

        self.results_status_lbl = QLabel("대기 중")
        self.results_status_lbl.setObjectName("new_and_now")
        h_layout.addWidget(self.results_status_lbl)

        self.btn_toggle_exclude = QPushButton("제외 목록 (0)")
        self.btn_toggle_exclude.setObjectName("subtleBtn")
        self.btn_toggle_exclude.setFixedHeight(34)
        self.btn_toggle_exclude.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_exclude.clicked.connect(self.toggle_exclude_requested.emit)
        h_layout.addWidget(self.btn_toggle_exclude)

        self.clear_feed_btn = QPushButton("로그 지우기")
        self.clear_feed_btn.setObjectName("subtleBtn")
        self.clear_feed_btn.setFixedHeight(34)
        self.clear_feed_btn.setCursor(Qt.PointingHandCursor)
        self.clear_feed_btn.clicked.connect(self.clear_feed)
        h_layout.addWidget(self.clear_feed_btn)

        layout.addWidget(header)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("settingsTab")

        tab_results = QWidget()
        results_vbox = QVBoxLayout(tab_results)
        results_vbox.setContentsMargins(0, 8, 0, 0)
        results_vbox.setSpacing(0)

        self.scroll_area = SmoothScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setObjectName("t_123")
        self.scroll_area.setStyleSheet("#t_123{background: transparent;}")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_container.setObjectName("t_123")
        self.cards_container.setStyleSheet("#t_123{background: transparent;}")
        self.cards_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(10, 8, 8, 8)
        self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        results_vbox.addWidget(self.scroll_area)

        tab_feed = QWidget()
        feed_vbox = QVBoxLayout(tab_feed)
        feed_vbox.setContentsMargins(10, 8, 8, 8)
        feed_vbox.setSpacing(0)

        self.feed_scroll = SmoothScrollArea()
        self.feed_scroll.setWidgetResizable(True)
        self.feed_scroll.setFrameShape(QFrame.NoFrame)
        self.feed_scroll.setObjectName("t_123")
        self.feed_scroll.setStyleSheet("#t_123{background: transparent;}")
        self.feed_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.feed_container = QWidget()
        self.feed_container.setObjectName("t_123")
        self.feed_container.setStyleSheet("#t_123{background: transparent;}")

        self.feed_layout = QVBoxLayout(self.feed_container)
        self.feed_layout.setContentsMargins(0, 0, 8, 0)
        self.feed_layout.setSpacing(10)
        self.feed_layout.addStretch()

        self.feed_scroll.setWidget(self.feed_container)
        feed_vbox.addWidget(self.feed_scroll)

        self.tab_widget.addTab(tab_results, "추천 결과")
        self.tab_widget.addTab(tab_feed, "실시간 AI 분석 로그")

        layout.addWidget(self.tab_widget, stretch=1)

    def set_status(self, text: str):
        self.results_status_lbl.setText(text)

    def set_exclude_count(self, count: int):
        self.btn_toggle_exclude.setText(f"제외 목록 ({count})")

    def set_tab_index(self, index: int):
        self.tab_widget.setCurrentIndex(index)

    def clear_feed(self):
        while self.feed_layout.count() > 1:
            child = self.feed_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def append_info_card(self, message: str):
        prev_index = self.feed_layout.count() - 2
        if prev_index >= 0:
            prev_item = self.feed_layout.itemAt(prev_index)
            prev_widget = prev_item.widget() if prev_item else None

            if prev_widget and prev_widget.objectName() == "CardFrame_ui":
                msg_lbl = prev_widget.findChild(QLabel, "new_and_now")
                if msg_lbl:
                    msg_lbl.setText(f"{msg_lbl.text()}\n{message}")
                    QTimer.singleShot(50, self.scroll_feed_to_bottom)
                    return

        card = QFrame()
        card.setObjectName("CardFrame_ui")
        c_layout = QHBoxLayout(card)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(8)

        msg_lbl = QLabel(message)
        msg_lbl.setObjectName("new_and_now")
        msg_lbl.setWordWrap(True)
        c_layout.addWidget(msg_lbl, stretch=1)

        self.feed_layout.insertWidget(self.feed_layout.count() - 1, card)
        QTimer.singleShot(50, self.scroll_feed_to_bottom)

    def append_ai_speech_card(self, thought_or_note: str):
        card = QFrame()
        card.setObjectName("CardFrame_ui_h")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 12, 14, 12)
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

    def display_empty(self):
        no_lbl = QLabel("조건에 부합하는 작품을 발견하지 못했습니다. 검색 조건을 완화해 보세요.")
        no_lbl.setObjectName("new_and_now")
        no_lbl.setAlignment(Qt.AlignCenter)
        self.cards_layout.insertWidget(0, no_lbl)

    def get_remaining_cards_count(self) -> int:
        count = 0
        for i in range(self.cards_layout.count() - 1):
            w = self.cards_layout.itemAt(i).widget()
            if isinstance(w, cd.RecommendedWorkCard):
                count += 1
        return count

    def update_result_tab_count(self):
        cnt = self.get_remaining_cards_count()
        self.tab_widget.setTabText(0, f"추천 결과 ({cnt})")
        if cnt == 0:
            self.set_status("후보작 없음")

    def display_results(self, works: List[Dict[str, Any]], curator_note: str, parent_dialog):
        self.tab_widget.setTabText(0, f"추천 결과 ({len(works)})")

        if curator_note:
            note_card = QFrame()
            note_card.setObjectName("CardFrame_ui")
            n_layout = QVBoxLayout(note_card)
            n_layout.setContentsMargins(16, 12, 16, 12)
            n_layout.setSpacing(6)
            note_desc = QLabel(curator_note)
            note_desc.setObjectName("detail_description")
            note_desc.setWordWrap(True)
            n_layout.addWidget(note_desc)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, note_card)

        for order, work in enumerate(works):
            card = cd.RecommendedWorkCard(work, order + 1, parent_dialog)
            card.work_excluded.connect(parent_dialog.on_work_excluded)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

        self.scroll_area.verticalScrollBar().setValue(0)