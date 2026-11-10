from typing import Dict, Any

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidgetItem, QListWidget, QMessageBox
)
from src.system.data import load_data, save_data
from src.main.thread_pyqt import TitleTranslateWorker
from .widgets import SmoothListWidget


class ExcludedWorkItemWidget(QWidget):
    delete_requested = Signal(str)

    def __init__(self, key: str, title: str, title_ko: str, url: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.title = title
        self.title_ko = title_ko
        self.url = url
        self.trans_worker = None
        self.init_ui()

        if not self.title_ko and self.title:
            self.trans_worker = TitleTranslateWorker(self.title)
            self.trans_worker.finished.connect(self.on_translated)
            self.trans_worker.start()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignVCenter)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        text_layout.setAlignment(Qt.AlignVCenter)

        main_text = self.title_ko or self.title or self.url or self.key
        self.title_ko_lbl = QLabel(main_text)
        self.title_ko_lbl.setObjectName("lbl_title")
        self.title_ko_lbl.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.title_ko_lbl.setTextFormat(Qt.PlainText)
        self.title_ko_lbl.setWordWrap(False)
        text_layout.addWidget(self.title_ko_lbl)

        sub_text = f"원제: {self.title}" if (self.title_ko and self.title and self.title_ko != self.title) else ""
        self.sub_title_lbl = QLabel(sub_text)
        self.sub_title_lbl.setObjectName("lbl_url")
        self.sub_title_lbl.setStyleSheet("font-size: 11px;")
        self.sub_title_lbl.setTextFormat(Qt.PlainText)
        self.sub_title_lbl.setWordWrap(False)
        if not sub_text:
            self.sub_title_lbl.hide()
        text_layout.addWidget(self.sub_title_lbl)

        if self.url:
            self.url_lbl = QLabel(self.url)
            self.url_lbl.setObjectName("lbl_url")
            self.url_lbl.setStyleSheet("font-size: 10px; opacity: 0.8;")
            self.url_lbl.setTextFormat(Qt.PlainText)
            self.url_lbl.setWordWrap(False)
            text_layout.addWidget(self.url_lbl)

        layout.addLayout(text_layout, stretch=1)

        del_btn = QPushButton("삭제")
        del_btn.setObjectName("subtleBtn")
        del_btn.setFixedSize(50, 32)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.key))
        layout.addWidget(del_btn)

    def on_translated(self, translated: str):
        if translated and translated != self.title:
            self.title_ko = translated
            self.title_ko_lbl.setText(translated)
            self.sub_title_lbl.setText(f"원제: {self.title}")
            self.sub_title_lbl.show()

            data = load_data()
            excluded = data.get("recommend_excluded", {})
            if isinstance(excluded, dict) and self.key in excluded:
                if isinstance(excluded[self.key], dict):
                    excluded[self.key]["title_ko"] = translated
                    data["recommend_excluded"] = excluded
                    save_data(data)


class RecommendExcludedPanel(QWidget):
    excluded_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 8)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 4, 2, 0)
        self.title_lbl = QLabel("제외 작품 목록 (0)")
        self.title_lbl.setObjectName("cat_label")
        self.title_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        desc_lbl = QLabel("등록된 작품은 향후 AI 탐색 및 추천 후보군에서 자동으로 배제됩니다.")
        desc_lbl.setObjectName("lbl_url")
        desc_lbl.setStyleSheet("font-size: 11px; line-height: 1.3;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        self.list_widget = SmoothListWidget()
        self.list_widget.setObjectName("group_box")
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet(
            "QListWidget::item {"
            "  border-bottom: 1px solid rgba(128, 128, 128, 0.15);"
            "}"
            "QListWidget::item:hover {"
            "  background-color: rgba(128, 128, 128, 0.15);"
            "  border-radius: 4px;"
            "}"
        )
        layout.addWidget(self.list_widget, stretch=1)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 2, 0, 2)
        self.clear_btn = QPushButton("전체 삭제")
        self.clear_btn.setObjectName("subtleBtn")
        self.clear_btn.setFixedHeight(34)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_all)
        bottom_layout.addWidget(self.clear_btn)
        layout.addLayout(bottom_layout)

    def refresh_list(self):
        data = load_data()
        excluded = data.get("recommend_excluded", {})
        if not isinstance(excluded, dict):
            excluded = {}

        self.list_widget.clear()
        self.title_lbl.setText(f"제외 작품 목록 ({len(excluded)})")

        for key, item_info in excluded.items():
            title = ""
            title_ko = ""
            url = ""
            if isinstance(item_info, dict):
                title = item_info.get("title", "")
                title_ko = item_info.get("title_ko", "")
                url = item_info.get("url", "")
            elif isinstance(item_info, str):
                title = item_info
                url = key if key.startswith("http") else ""

            if not url and key.startswith("http"):
                url = key

            widget = ExcludedWorkItemWidget(key, title, title_ko, url, self)
            widget.delete_requested.connect(self.remove_excluded)

            list_item = QListWidgetItem(self.list_widget)
            list_item.setSizeHint(QSize(200, 72))
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, widget)

        self.excluded_changed.emit(len(excluded))

    def add_excluded(self, url: str, title: str, title_ko: str = ""):
        clean_url = (url or "").strip()
        clean_title = (title or "").strip()
        clean_title_ko = (title_ko or "").strip()

        if not clean_url and not clean_title and not clean_title_ko:
            return

        key = clean_url if clean_url else f"title:{clean_title or clean_title_ko}"

        data = load_data()
        excluded = data.get("recommend_excluded", {})
        if not isinstance(excluded, dict):
            excluded = {}

        excluded[key] = {
            "title": clean_title,
            "title_ko": clean_title_ko,
            "url": clean_url
        }
        data["recommend_excluded"] = excluded
        save_data(data)
        self.refresh_list()

    def remove_excluded(self, key: str):
        data = load_data()
        excluded = data.get("recommend_excluded", {})
        if isinstance(excluded, dict) and key in excluded:
            del excluded[key]
            data["recommend_excluded"] = excluded
            save_data(data)
            self.refresh_list()

    def clear_all(self):
        data = load_data()
        excluded = data.get("recommend_excluded", {})
        if not excluded:
            return
        reply = QMessageBox.question(
            self,
            "전체 삭제 확인",
            "제외 목록에 등록된 모든 작품을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            data["recommend_excluded"] = {}
            save_data(data)
            self.refresh_list()