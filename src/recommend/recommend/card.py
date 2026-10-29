from typing import Dict, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame
)
from src.find.site_list import site_point_text
from src.main.thread_pyqt import TitleTranslateWorker
from .widgets import ClickableTitleLabel

detail_ui = None

class RecommendedWorkCard(QFrame):
    def __init__(self, item_data: Dict[str, Any], order_number=1, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.order_number = order_number
        self.story_expanded = False
        self.setObjectName("CardFrame")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        header_layout.setAlignment(Qt.AlignTop)

        title_container = QHBoxLayout()
        title_container.setSpacing(8)
        title_container.setAlignment(Qt.AlignTop)

        order_label = QLabel(str(self.order_number))
        order_label.setObjectName("lbl_title")
        order_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        order_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        order_label.setFixedWidth(22)
        title_container.addWidget(order_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        title_ja = self.item_data.get("title_ja", self.item_data.get("title", ""))
        url = self.item_data.get("url", "")

        self.title_label = ClickableTitleLabel(title_ja, url)
        self.title_label.setObjectName("lbl_title")
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.title_label.setWordWrap(True)
        title_col.addWidget(self.title_label)

        if title_ja:
            self.sub_title_label = QLabel(f"원제: {title_ja}")
            self.sub_title_label.setObjectName("lbl_url")
            self.sub_title_label.setStyleSheet("font-size: 11px;")
            self.sub_title_label.setWordWrap(True)
            title_col.addWidget(self.sub_title_label)

        title_container.addLayout(title_col, stretch=1)
        header_layout.addLayout(title_container, stretch=1)

        badge_box = QHBoxLayout()
        badge_box.setSpacing(6)
        badge_box.setAlignment(Qt.AlignRight | Qt.AlignTop)

        site = self.item_data.get("site", "kakuyomu")
        site_names = {"kakuyomu": "카쿠요무", "naro": "소설가가 되자", "hameln": "하멜른"}
        site_lbl = QLabel(site_names.get(site, site))
        site_lbl.setObjectName("new_and_now")
        site_lbl.setStyleSheet("font-size: 11px; padding: 3px 6px;")
        site_lbl.setAlignment(Qt.AlignCenter)
        badge_box.addWidget(site_lbl)

        score = self.item_data.get("match_score", 0)
        score_lbl = QLabel(f"적합도 {score}점")
        score_lbl.setStyleSheet(
            "font-weight: bold; padding: 4px 10px; border-radius: 4px; font-size: 12px;"
        )
        score_lbl.setAlignment(Qt.AlignCenter)
        badge_box.addWidget(score_lbl)

        header_layout.addLayout(badge_box)
        layout.addLayout(header_layout)

        info_box = QFrame()
        info_box.setObjectName("CardFrame_ui")
        info_box_layout = QVBoxLayout(info_box)
        info_box_layout.setContentsMargins(14, 12, 14, 12)
        info_box_layout.setSpacing(10)

        one_liner = self.item_data.get("curator_one_liner", "")
        if one_liner:
            one_liner_lbl = QLabel(f"“ {one_liner} ”")
            one_liner_lbl.setObjectName("detail_description")
            one_liner_lbl.setStyleSheet("font-weight: bold; font-size: 13px; padding-bottom: 2px;")
            one_liner_lbl.setWordWrap(True)
            info_box_layout.addWidget(one_liner_lbl)

        details_col = QVBoxLayout()
        details_col.setSpacing(6)

        rationale = self.item_data.get("score_rationale", "")
        if rationale:
            rat_lbl = QLabel(f"<span style='font-size:11px;'>●</span> <b>평가 :</b> {rationale}")
            rat_lbl.setObjectName("detail_description")
            rat_lbl.setWordWrap(True)
            details_col.addWidget(rat_lbl)

        past_conn = self.item_data.get("connection_with_past_reads", "")
        if past_conn:
            conn_lbl = QLabel(f"<span style='font-size:11px;'>●</span> <b>독자 취향 연계 :</b> {past_conn}")
            conn_lbl.setObjectName("detail_description")
            conn_lbl.setWordWrap(True)
            details_col.addWidget(conn_lbl)

        warnings = self.item_data.get("cons_and_warnings", [])
        if warnings:
            if isinstance(warnings, list):
                warn_text = " · ".join(str(w) for w in warnings if str(w).strip())
            else:
                warn_text = str(warnings)
            if warn_text:
                warn_lbl = QLabel(f"<span style='font-size:11px;'>●</span> <b>주의 / 호불호 :</b> {warn_text}")
                warn_lbl.setObjectName("lbl_url")
                warn_lbl.setStyleSheet("font-size: 12px;")
                warn_lbl.setWordWrap(True)
                details_col.addWidget(warn_lbl)

        info_box_layout.addLayout(details_col)
        layout.addWidget(info_box)

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(2, 0, 2, 0)
        footer_layout.setSpacing(12)
        footer_layout.setAlignment(Qt.AlignVCenter)

        meta_items = []
        stars = str(self.item_data.get("stars", "0"))
        if stars and stars != "0":
            site_int = {"kakuyomu": 2, "naro": 1, "hameln": 3}
            meta_items.append(f"{site_point_text(site_int.get(site, 1), stars)}")

        episodes = str(self.item_data.get("status_episodes", ""))
        if episodes:
            meta_items.append(episodes)

        updated = str(self.item_data.get("updated_at", ""))
        if updated:
            meta_items.append(f"갱신 {updated}")

        meta_text = "  ·  ".join(meta_items)
        meta_lbl = QLabel(meta_text)
        meta_lbl.setObjectName("lbl_url")
        meta_lbl.setStyleSheet("font-size: 12px;")
        
        footer_layout.addWidget(meta_lbl, stretch=1)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(6)

        if detail_ui:
            self.dialog_btn = QPushButton("상세보기")
            self.dialog_btn.setObjectName("subtleBtn")
            self.dialog_btn.setFixedSize(88, 30)
            self.dialog_btn.setCursor(Qt.PointingHandCursor)
            self.dialog_btn.clicked.connect(self.open_detail_dialog)
            btn_box.addWidget(self.dialog_btn)

        self.add_work_btn = QPushButton("작품 추가")
        self.add_work_btn.setObjectName("subtleBtn")
        self.add_work_btn.setFixedSize(88, 30)
        self.add_work_btn.setCursor(Qt.PointingHandCursor)
        self.add_work_btn.clicked.connect(self.save_to_user_list)
        btn_box.addWidget(self.add_work_btn)

        footer_layout.addLayout(btn_box)
        layout.addLayout(footer_layout)

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
        if detail_ui:
            detail_ui.click_plus_url = self.item_data.get('url', '')
            detail_ui.click = True
        self.add_work_btn.setText("추가됨")
        self.add_work_btn.setEnabled(False)