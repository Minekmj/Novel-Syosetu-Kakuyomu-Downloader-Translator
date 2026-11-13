from typing import Dict, Any, List

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QTabWidget, QSizePolicy
)
from .widgets import SmoothScrollArea
from . import card as cd


class RecommendSessionTab(QWidget):
    close_requested = Signal(object)
    count_changed = Signal(object, int)

    def __init__(
        self,
        session_number: int,
        works: List[Dict[str, Any]],
        curator_note: str,
        parent_dialog,
        condition: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.session_number = session_number
        self.works = works
        self.curator_note = curator_note
        self.parent_dialog = parent_dialog
        self.condition = condition.strip()
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 8, 0, 0)
        root_layout.setSpacing(0)

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

        session_bar = QFrame()
        session_bar.setObjectName("CardFrame_ui")
        bar_layout = QHBoxLayout(session_bar)
        bar_layout.setContentsMargins(14, 8, 14, 8)
        bar_layout.setSpacing(8)

        summary_text = f"세션 #{self.session_number}"
        if self.condition:
            compact_cond = " ".join(self.condition.splitlines()).strip()
            if len(compact_cond) > 65:
                compact_cond = compact_cond[:65] + "..."
            summary_text = f"{summary_text}  ·  {compact_cond}"

        info_lbl = QLabel(summary_text)
        info_lbl.setObjectName("lbl_url")
        info_lbl.setStyleSheet("font-size: 12px;")
        info_lbl.setWordWrap(True)
        bar_layout.addWidget(info_lbl, stretch=1)

        close_btn = QPushButton("탭 닫기")
        close_btn.setObjectName("subtleBtn")
        close_btn.setFixedSize(70, 50)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(lambda: self.close_requested.emit(self))
        bar_layout.addWidget(close_btn)

        self.cards_layout.addWidget(session_bar)

        if self.curator_note:
            note_card = QFrame()
            note_card.setObjectName("CardFrame_ui")
            n_layout = QVBoxLayout(note_card)
            n_layout.setContentsMargins(16, 12, 16, 12)
            n_layout.setSpacing(6)
            note_desc = QLabel(self.curator_note)
            note_desc.setObjectName("detail_description")
            note_desc.setWordWrap(True)
            n_layout.addWidget(note_desc)
            self.cards_layout.addWidget(note_card)

        if not self.works:
            no_lbl = QLabel("조건에 부합하는 작품을 발견하지 못했습니다. 검색 조건을 조정해 보세요.")
            no_lbl.setObjectName("new_and_now")
            no_lbl.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(no_lbl)
        else:
            for order, work in enumerate(self.works):
                card = cd.RecommendedWorkCard(work, order + 1, self.parent_dialog)
                card.work_excluded.connect(self.parent_dialog.on_work_excluded)
                card.work_excluded.connect(self.on_card_excluded)
                self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        root_layout.addWidget(self.scroll_area)

    def on_card_excluded(self, url: str, title_ja: str, title_ko: str):
        QTimer.singleShot(0, self.update_count)

    def get_remaining_cards_count(self) -> int:
        count = 0
        for i in range(self.cards_layout.count()):
            w = self.cards_layout.itemAt(i).widget()
            if isinstance(w, cd.RecommendedWorkCard):
                count += 1
        return count

    def update_count(self):
        cnt = self.get_remaining_cards_count()
        self.count_changed.emit(self, cnt)


class RecommendWorkspacePanel(QWidget):
    toggle_exclude_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session_counter = 0
        self.session_tabs: List[RecommendSessionTab] = []
        self.active_session_tab = None
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

        self.placeholder_tab = QWidget()
        placeholder_vbox = QVBoxLayout(self.placeholder_tab)
        placeholder_vbox.setContentsMargins(0, 8, 0, 0)
        placeholder_lbl = QLabel("추천을 시작하면 세션별로 결과 탭이 생성됩니다.")
        placeholder_lbl.setObjectName("lbl_url")
        placeholder_lbl.setAlignment(Qt.AlignCenter)
        placeholder_vbox.addWidget(placeholder_lbl)

        self.tab_feed = QWidget()
        feed_vbox = QVBoxLayout(self.tab_feed)
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

        self.tab_widget.addTab(self.placeholder_tab, "추천 결과")
        self.tab_widget.addTab(self.tab_feed, "실시간 AI 분석 로그")

        layout.addWidget(self.tab_widget, stretch=1)

    def set_status(self, text: str):
        self.results_status_lbl.setText(text)

    def set_exclude_count(self, count: int):
        self.btn_toggle_exclude.setText(f"제외 목록 ({count})")

    def set_tab_index(self, index: int):
        self.tab_widget.setCurrentIndex(index)

    def focus_log_tab(self):
        idx = self.tab_widget.indexOf(self.tab_feed)
        if idx >= 0:
            self.tab_widget.setCurrentIndex(idx)

    def get_next_session_number(self) -> int:
        return self.session_counter + 1

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

    def add_session_results(
        self,
        works: List[Dict[str, Any]],
        curator_note: str,
        parent_dialog,
        condition: str = ""
    ):
        self.session_counter += 1
        session_num = self.session_counter

        p_idx = self.tab_widget.indexOf(self.placeholder_tab)
        if p_idx >= 0:
            self.tab_widget.removeTab(p_idx)

        session_tab = RecommendSessionTab(
            session_number=session_num,
            works=works,
            curator_note=curator_note,
            parent_dialog=parent_dialog,
            condition=condition,
            parent=self
        )
        session_tab.close_requested.connect(self.close_session_tab)
        session_tab.count_changed.connect(self.on_session_count_changed)

        log_idx = self.tab_widget.indexOf(self.tab_feed)
        if log_idx < 0:
            log_idx = self.tab_widget.count()

        tab_title = f"추천 {session_num} ({len(works)})"
        new_idx = self.tab_widget.insertTab(log_idx, session_tab, tab_title)
        self.session_tabs.append(session_tab)
        self.active_session_tab = session_tab
        self.tab_widget.setCurrentIndex(new_idx)

    def on_session_count_changed(self, session_tab: RecommendSessionTab, count: int):
        idx = self.tab_widget.indexOf(session_tab)
        if idx >= 0:
            self.tab_widget.setTabText(idx, f"추천 {session_tab.session_number} ({count})")
        if session_tab == self.active_session_tab and count == 0:
            self.set_status("후보작 없음")

    def close_session_tab(self, session_tab: RecommendSessionTab):
        idx = self.tab_widget.indexOf(session_tab)
        if idx >= 0:
            self.tab_widget.removeTab(idx)
        if session_tab in self.session_tabs:
            self.session_tabs.remove(session_tab)
        if self.active_session_tab == session_tab:
            self.active_session_tab = self.session_tabs[-1] if self.session_tabs else None
        session_tab.deleteLater()

        if not self.session_tabs:
            log_idx = self.tab_widget.indexOf(self.tab_feed)
            insert_idx = log_idx if log_idx >= 0 else 0
            self.tab_widget.insertTab(insert_idx, self.placeholder_tab, "추천 결과")
            self.set_status("대기 중")

    def clear_result_cards(self):
        pass

    def display_empty(self):
        self.add_session_results([], "", self.parent())

    def get_remaining_cards_count(self) -> int:
        current = self.tab_widget.currentWidget()
        if isinstance(current, RecommendSessionTab):
            return current.get_remaining_cards_count()
        if self.active_session_tab is not None:
            return self.active_session_tab.get_remaining_cards_count()
        return 0

    def update_result_tab_count(self):
        for tab in self.session_tabs:
            tab.update_count()

    def display_results(self, works: List[Dict[str, Any]], curator_note: str, parent_dialog):
        self.add_session_results(works, curator_note, parent_dialog)