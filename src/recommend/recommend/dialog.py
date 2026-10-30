from typing import Dict, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QSplitter, QMessageBox
from src.main.thread_pyqt import RecommendWorker
from .control_panel import RecommendControlPanel
from . import workspace_panel

class NovelRecommendDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 추천")
        self.resize(1150, 720)
        self.setMinimumSize(1150, 720)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self.recommend_worker = None
        self.init_ui()
        
    def set_value_detail_ui(ui):
        workspace_panel.card.detail_ui = ui

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(8)

        self.control_panel = RecommendControlPanel(self)
        self.workspace_panel = workspace_panel.RecommendWorkspacePanel(self)

        self.control_panel.start_requested.connect(self.on_start_recommendation)
        self.control_panel.log_requested.connect(self.workspace_panel.append_info_card)

        self.splitter.addWidget(self.control_panel)
        self.splitter.addWidget(self.workspace_panel)

        self.splitter.setSizes([380, 900])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        root.addWidget(self.splitter)

    def on_start_recommendation(self, api_key: str, model: str, condition: str, top_k: int, user_data: dict):
        if self.recommend_worker and self.recommend_worker.isRunning():
            QMessageBox.warning(self, "알림", "추천 작업이 진행 중입니다.")
            return

        self.workspace_panel.clear_result_cards()
        self.control_panel.set_running(True)
        self.workspace_panel.set_status("AI 분석 중...")
        self.workspace_panel.set_tab_index(1)

        self.workspace_panel.append_ai_speech_card("<center><b>새 추천 시작</b></center>")
        self.workspace_panel.append_info_card(
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
            self.workspace_panel.append_ai_speech_card(text)
        else:
            self.workspace_panel.append_info_card(text)

    def on_recommendation_finished(self, result: Dict[str, Any]):
        self.control_panel.set_running(False)
        works = result.get("recommended_works", [])
        curator_note = result.get("curator_note", "")

        if curator_note:
            self.workspace_panel.append_ai_speech_card(f"<b>[최종 선별 총평]</b>\n{curator_note}")

        if not works:
            self.workspace_panel.set_status("후보작 없음")
            self.workspace_panel.display_empty()
            self.workspace_panel.set_tab_index(0)
            return

        self.workspace_panel.set_status(f"{len(works)}작품 추천 완료")
        self.workspace_panel.display_results(works, curator_note, self)
        self.workspace_panel.set_tab_index(0)

    def on_recommendation_failed(self, error_msg: str):
        self.control_panel.set_running(False)
        self.workspace_panel.set_status("추천 실패")
        self.workspace_panel.append_info_card(f"오류 발생: {error_msg}")
        self.workspace_panel.set_tab_index(1)
        QMessageBox.critical(self, "추천 오류", f"추천 파이프라인 수행 중 오류가 발생했습니다:\n{error_msg}")