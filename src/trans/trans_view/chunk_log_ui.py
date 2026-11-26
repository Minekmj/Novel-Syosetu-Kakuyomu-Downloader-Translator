import asyncio
import datetime
import html
import json
import os
import re
import uuid
from typing import Any, Dict, List, Optional, Set

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QButtonGroup,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from src.system.BasicUi import SmoothScrollArea
from src.system.data import return_theme
from .ui_factory import create_button, create_label, create_layout


class EpubRebuildWorker(QThread):
    finished_signal = Signal(bool, str)

    def __init__(self, target_path: str, max_chars: Optional[int] = None):
        super().__init__(None)
        self.target_path = target_path
        self.max_chars = max_chars

    def run(self):
        try:
            from src.trans.trans_ai.change_translator import Change_file
            res = Change_file(self.target_path, chunk=self.max_chars)
            if res:
                self.finished_signal.emit(True, res)
            else:
                self.finished_signal.emit(False, "백업 폴더에서 EPUB을 재생성할 수 없습니다.")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class ChunkRetryWorker(QThread):
    finished_signal = Signal(bool, str, str)
    log_signal = Signal(int, str)
    _active_workers: Set["ChunkRetryWorker"] = set()

    def __init__(
        self,
        kind: str,
        idx: int,
        source_text: str,
        retry_config: Dict[str, Any],
    ):
        super().__init__(None)
        self.kind = kind
        self.idx = idx
        self.source_text = source_text
        self.retry_config = dict(retry_config or {})
        ChunkRetryWorker._active_workers.add(self)
        self.finished.connect(self._cleanup_self)

    def _cleanup_self(self):
        ChunkRetryWorker._active_workers.discard(self)
        self.deleteLater()

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        retry_sid = f"retry_{self.idx}_{uuid.uuid4().hex[:6]}"

        def _emit_log(msg: str):
            self.log_signal.emit(self.idx, str(msg))

        try:
            _emit_log(f"[{self.idx}] 다시하기 시작...")
            if self.kind == "AI 용어집":
                from src.glossary.glossary_text import _call_chunk_api_once
                from src.trans.trans_ai.rate_limiter import AsyncRateLimiter

                rpm = int(self.retry_config.get("rpm", 5))
                model = self.retry_config.get("model_name")
                ai_target = self.retry_config.get("ai_target")

                async def _run_glossary():
                    limiter = AsyncRateLimiter(rpm=rpm)
                    return await _call_chunk_api_once(
                        chunk_text=self.source_text,
                        chunk_idx=self.idx,
                        total_chunks=1,
                        rate_limiter=limiter,
                        log_callback=_emit_log,
                        model=model,
                        ai_target=ai_target,
                        session_id=retry_sid,
                        check=None,
                    )

                success, parsed_dict, is_censored = loop.run_until_complete(_run_glossary())
                if is_censored:
                    _emit_log(f"[{self.idx}] 검열로 인해 건너뛰어졌습니다.")
                    self.finished_signal.emit(False, "", "검열로 인해 건너뛰어졌습니다.")
                    return
                if not success or parsed_dict is None:
                    _emit_log(f"[{self.idx}] 용어집 재추출 실패")
                    self.finished_signal.emit(False, "", "용어집 재추출에 실패했습니다.")
                    return
                lines = [f"{src} -> {tgt} ({cat})" for src, (tgt, cat) in parsed_dict.items()]
                _emit_log(f"[{self.idx}] 용어집 재추출 완료 ({len(lines)}개)")
                self.finished_signal.emit(True, "\n".join(lines), "")
                return

            from src.ai import AiTarget
            from src.trans.prompt_sanitizer import get_safety_settings
            from src.trans.trans_ai.chunk_translator import translate_chunk_safe_async
            from src.trans.trans_ai.rate_limiter import AsyncRateLimiter

            model_name = self.retry_config.get("model_name", "gemini-2.5-flash-lite")
            rpm = int(self.retry_config.get("rpm", 15))
            temperature = float(self.retry_config.get("temperature", 0.1))
            br_start = int(self.retry_config.get("br_start", 0))
            isno_x = bool(self.retry_config.get("isno_x", False))
            thinking_budget = self.retry_config.get("thinking_budget", "기본값")
            ai_target = self.retry_config.get("ai_target", int(AiTarget.GEMINI))
            raw = bool(self.retry_config.get("raw", False))
            dicts = dict(self.retry_config.get("dicts") or {})

            async def _run_trans():
                limiter = AsyncRateLimiter(rpm=rpm)
                return await translate_chunk_safe_async(
                    chunk=self.source_text,
                    model_name=model_name,
                    safety_settings=get_safety_settings(),
                    rate_limiter=limiter,
                    temperature=temperature,
                    log_callback=_emit_log,
                    chunk_idx=self.idx,
                    raw=raw,
                    dicts=dicts,
                    check=None,
                    check_i=None,
                    br_start=br_start,
                    isno_x=isno_x,
                    thinking_budget=thinking_budget,
                    ai_target=ai_target,
                    semaphore=None,
                    concurrency=1,
                    session_id=retry_sid,
                )

            result_text, _, ignored = loop.run_until_complete(_run_trans())
            if ignored or result_text is None:
                _emit_log(f"[{self.idx}] 재번역 결과를 받지 못했습니다.")
                self.finished_signal.emit(False, "", "재번역 결과를 받지 못했습니다.")
                return
            _emit_log(f"[{self.idx}] 재번역 완료")
            self.finished_signal.emit(True, str(result_text), "")
        except Exception as e:
            _emit_log(f"[{self.idx}] 재시도 오류: {e}")
            self.finished_signal.emit(False, "", str(e))
        finally:
            try:
                from src.ai.models.playground import PlaygroundModel
                PlaygroundModel.close_session(retry_sid)
            except Exception:
                pass
            try:
                loop.close()
            except Exception:
                pass


class ChunkCompareDialog(QDialog):
    result_updated = Signal(int, str, str)
    log_emitted = Signal(int, str)

    def __init__(
        self,
        idx: int,
        kind: str,
        status: str,
        source_text: str,
        result_text: str,
        session_context: Dict[str, Any],
        parent=None,
    ):
        super().__init__(parent)
        self.idx = idx
        self.kind = kind
        self.status = status
        self.source_text = source_text or ""
        self.result_text = result_text or ""
        self.session_context = session_context or {}
        self.retry_worker: Optional[ChunkRetryWorker] = None
        self._is_closed = False

        self.setWindowTitle(f"{kind} · 청크 {idx} 비교")
        self.resize(960, 640)
        self.setMinimumSize(720, 480)
        self.init_ui()

    def init_ui(self):
        root = create_layout("v", (16, 16, 16, 16), spacing=12, parent=self)

        top_card = QFrame()
        top_card.setObjectName("CardFrame_ui")
        top = create_layout("h", (14, 10, 14, 10), spacing=10, parent=top_card)
        title_lbl = create_label(f"청크 {self.idx} 원문 / 결과 비교", "lbl_title")
        top.addWidget(title_lbl)
        top.addStretch(1)
        self.status_lbl = create_label(f"상태: {self.status}", "secondaryInfo")
        top.addWidget(self.status_lbl)
        root.addWidget(top_card)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_box = QFrame()
        left_box.setObjectName("CardFrame_ui")
        left_lay = create_layout("v", (12, 10, 12, 10), spacing=8, parent=left_box)
        left_lay.addWidget(create_label("잘린 원문", "detail_section_title"))
        self.source_edit = QTextEdit()
        self.source_edit.setObjectName("detail_description")
        self.source_edit.viewport().setStyleSheet("background: transparent;")
        self.source_edit.setReadOnly(True)
        self.source_edit.setPlainText(self.source_text)
        left_lay.addWidget(self.source_edit, 1)

        right_box = QFrame()
        right_box.setObjectName("CardFrame_ui")
        right_lay = create_layout("v", (12, 10, 12, 10), spacing=8, parent=right_box)
        right_lay.addWidget(create_label("결과 (직접 수정 가능)", "detail_section_title"))
        self.result_edit = QTextEdit()
        self.result_edit.setObjectName("detail_description")
        self.result_edit.viewport().setStyleSheet("background: transparent;")
        self.result_edit.setPlainText(self.result_text)
        if self.status in ("대기중", "진행중") and not self.result_text:
            self.result_edit.setPlaceholderText("아직 완료되지 않았습니다. 완료 후 결과를 확인하거나 수정할 수 있습니다.")
        right_lay.addWidget(self.result_edit, 1)

        splitter.addWidget(left_box)
        splitter.addWidget(right_box)
        splitter.setSizes([460, 460])
        root.addWidget(splitter, 1)

        btn_row = create_layout("h", spacing=8)
        self.retry_btn = create_button("다시하기", self.on_retry_clicked, "subtleBtn", h=36, w=100)
        self.save_btn = create_button("수정 저장", self.on_save_clicked, "primaryBtn", h=36, w=100)
        close_btn = create_button("닫기", self.close, "secondaryBtn", h=36, w=80)

        if not self.source_text.strip():
            self.retry_btn.setEnabled(False)

        btn_row.addWidget(self.retry_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _persist_result(self, new_text: str):
        ai_dir = self.session_context.get("ai_dir")
        if ai_dir and os.path.isdir(ai_dir):
            file_path = os.path.join(ai_dir, f"{self.idx}.txt")
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_text)
            except Exception:
                pass

        json_path = self.session_context.get("json_path")
        if json_path and os.path.isfile(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                key = str(self.idx - 1)
                if isinstance(data, dict) and key in data:
                    data[key] = new_text
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def on_save_clicked(self):
        new_text = self.result_edit.toPlainText()
        self.result_text = new_text
        self.status = "완료"
        self.status_lbl.setText("상태: 완료")
        self._persist_result(new_text)
        self.result_updated.emit(self.idx, "완료", new_text)
        QMessageBox.information(self, "저장 완료", f"청크 {self.idx} 수정 내용이 저장되었습니다.")

    def on_retry_clicked(self):
        if self.retry_worker is not None and self.retry_worker.isRunning():
            return
        retry_config = self.session_context.get("retry_config") or {}
        self.retry_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.status_lbl.setText("상태: 진행중 (재실행)")

        self.retry_worker = ChunkRetryWorker(
            kind=self.kind,
            idx=self.idx,
            source_text=self.source_text,
            retry_config=retry_config,
        )
        self.retry_worker.log_signal.connect(self.log_emitted.emit)
        self.retry_worker.finished_signal.connect(self._on_retry_finished)
        self.retry_worker.start()

    def _on_retry_finished(self, success: bool, new_text: str, err: str):
        if self._is_closed:
            return
        self.retry_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.retry_worker = None
        if success:
            self.result_text = new_text
            self.status = "완료"
            self.result_edit.setPlainText(new_text)
            self.status_lbl.setText("상태: 완료")
            self._persist_result(new_text)
            self.result_updated.emit(self.idx, "완료", new_text)
        else:
            self.status_lbl.setText(f"상태: {self.status}")
            QMessageBox.warning(self, "다시하기 실패", err or "작업에 실패했습니다.")

    def closeEvent(self, event):
        self._is_closed = True
        if self.retry_worker is not None:
            try:
                self.retry_worker.finished_signal.disconnect(self._on_retry_finished)
            except Exception:
                pass
            self.retry_worker = None
        super().closeEvent(event)

    def reject(self):
        self._is_closed = True
        if self.retry_worker is not None:
            try:
                self.retry_worker.finished_signal.disconnect(self._on_retry_finished)
            except Exception:
                pass
            self.retry_worker = None
        super().reject()


class ChunkCardWidget(QFrame):
    compare_requested = Signal(int)
    retry_requested = Signal(int)

    def __init__(self, idx: int, source_text: str = "", status: str = "대기중", result_text: str = "", kind: str = "번역", label: str = "", parent=None):
        super().__init__(parent)
        self.idx = idx
        self.kind = kind
        self.label = label or f"청크 {idx}"
        self.source_text = source_text or ""
        self.status = status or "대기중"
        self.result_text = result_text or ""
        self._logs: List[str] = []
        self._expanded = False

        self.setObjectName("CardFrame_ui")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.init_ui()
        self.set_status(self.status, self.result_text)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        header_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(3)

        self.title_lbl = QLabel(self.label)
        self.title_lbl.setObjectName("lbl_title")
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
        left_col.addWidget(self.title_lbl)

        self.status_lbl = QLabel("대기중")
        left_col.addWidget(self.status_lbl)

        header_row.addLayout(left_col, 1)

        self.more_btn = QPushButton("⋮")
        self.more_btn.setObjectName("subtleBtn")
        self.more_btn.setFixedSize(28, 28)
        self.more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_btn.setStyleSheet("font-size: 15px; font-weight: bold; padding: 0px;")
        self.more_btn.clicked.connect(self.show_options_menu)
        header_row.addWidget(self.more_btn, 0, Qt.AlignmentFlag.AlignTop)

        layout.addLayout(header_row)

        self.log_frame = QFrame()
        self.log_frame.setObjectName("CardFrame_ui")
        self.log_frame.setVisible(False)
        log_lay = QVBoxLayout(self.log_frame)
        log_lay.setContentsMargins(10, 8, 10, 8)
        log_lay.setSpacing(0)

        self.log_box = QTextEdit()
        self.log_box.setObjectName("detail_description")
        self.log_box.viewport().setStyleSheet("background: transparent;")
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(104)
        self.log_box.setPlaceholderText("이 청크의 로그가 여기에 표시됩니다.")
        log_lay.addWidget(self.log_box)

        layout.addWidget(self.log_frame)

    def show_options_menu(self):
        menu = QMenu(self)
        compare_act = None
        retry_act = None
        if self.kind != "AI 용어집":
            compare_act = menu.addAction("비교 / 수정")
            retry_act = menu.addAction("다시하기")
            if not self.source_text.strip() or self.status == "진행중":
                retry_act.setEnabled(False)
        log_text = "로그 숨기기" if self._expanded else f"로그 보기 ({len(self._logs)}줄)"
        log_act = menu.addAction(log_text)

        action = menu.exec(self.more_btn.mapToGlobal(self.more_btn.rect().bottomRight()))
        if compare_act is not None and action == compare_act:
            self.compare_requested.emit(self.idx)
        elif retry_act is not None and action == retry_act:
            self.retry_requested.emit(self.idx)
        elif action == log_act:
            self.toggle_log_view()

    def set_status(self, status: str, result_text: Optional[str] = None):
        self.status = status
        if result_text is not None:
            self.result_text = result_text

        target_obj = "CardFrame_ui_h" if status == "완료" else "CardFrame_ui"
        if self.objectName() != target_obj:
            self.setObjectName(target_obj)
            self.style().unpolish(self)
            self.style().polish(self)

        color_map = {
            "대기중": "#9aa0a6",
            "진행중": "#8be9fd",
            "완료": "#50fa7b",
            "오류": "#ff5555",
        }
        fg = color_map.get(status, "#e0e0e0")
        self.status_lbl.setText(status)
        self.status_lbl.setStyleSheet(f"color: {fg}; font-size: 11.5px; font-weight: 600;")

    def append_log(self, formatted_html: str):
        self._logs.append(formatted_html)
        self.log_box.append(formatted_html)

    def toggle_log_view(self):
        self._expanded = not self._expanded
        self.log_frame.setVisible(self._expanded)


class ChunkSessionWidget(QWidget):
    def __init__(self, session_id: str, kind: str, title: str, session_context: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setObjectName("no_back-chunkSession")
        self.session_id = session_id
        self.kind = kind
        self.title = title
        self.session_context = dict(session_context or {})
        self.cards: Dict[int, ChunkCardWidget] = {}
        self._retry_workers: Dict[int, ChunkRetryWorker] = {}
        self._epub_worker: Optional[EpubRebuildWorker] = None
        self.init_ui()

    def init_ui(self):
        root = create_layout("v", (2, 6, 2, 2), spacing=8, parent=self)

        session_bar = QFrame()
        session_bar.setObjectName("CardFrame_ui")
        bar_layout = QHBoxLayout(session_bar)
        bar_layout.setContentsMargins(12, 8, 12, 8)
        bar_layout.setSpacing(10)

        display_title = f"{self.kind} · {self.title}"
        if len(display_title) > 40:
            display_title = display_title[:40] + "..."
        self.summary_lbl = create_label(display_title, "lbl_url")
        self.summary_lbl.setStyleSheet("font-size: 11.5px; font-weight: 600;")
        bar_layout.addWidget(self.summary_lbl, 1)

        self.count_lbl = create_label("0 / 0 완료", "new_and_now")
        self.count_lbl.setStyleSheet("font-size: 11px;")
        bar_layout.addWidget(self.count_lbl)
        root.addWidget(session_bar)

        self.scroll = SmoothScrollArea()
        self.scroll.setObjectName("no_back-chunkScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("#no_back-chunkScroll { background: transparent; border: none; }")

        self.container = QWidget()
        self.container.setObjectName("no_back-chunkContainer")
        self.container.setStyleSheet("#no_back-chunkContainer { background: transparent; }")
        self.container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(2, 2, 6, 4)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch(1)

        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)

        if self.kind == "번역":
            self.rebuild_epub_btn = create_button("EPUB 재생성", self.rebuild_epub_from_backup, "subtleBtn", h=34)
            self.rebuild_epub_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            root.addWidget(self.rebuild_epub_btn)

    def _create_card(self, idx: int, source_text: str, status: str, result_text: str, label: str = "") -> ChunkCardWidget:
        card = ChunkCardWidget(
            idx=idx,
            source_text=source_text,
            status=status,
            result_text=result_text,
            kind=self.kind,
            label=label,
            parent=self.container,
        )
        card.compare_requested.connect(self.open_compare_dialog)
        card.retry_requested.connect(self.retry_chunk_direct)
        return card

    def set_chunks(self, chunks: List[Dict[str, Any]]):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.cards.clear()

        for ch in chunks:
            idx = int(ch.get("idx", 0))
            if idx <= 0:
                continue
            card = self._create_card(
                idx=idx,
                source_text=str(ch.get("source") or ""),
                status=str(ch.get("status") or "대기중"),
                result_text=str(ch.get("result") or ""),
                label=str(ch.get("label") or ""),
            )
            self.cards[idx] = card
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

        self._refresh_counts()

    def update_chunk(self, idx: int, status: str, result_text: Optional[str] = None, source_text: Optional[str] = None):
        card = self.cards.get(idx)
        if card is None:
            card = self._create_card(
                idx=idx,
                source_text=source_text or "",
                status=status,
                result_text=result_text or "",
            )
            self.cards[idx] = card
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        else:
            if source_text is not None:
                card.source_text = source_text
            card.set_status(status, result_text)
        self._refresh_counts()

    def append_chunk_log(self, idx: int, formatted_html: str):
        card = self.cards.get(idx)
        if card is not None:
            card.append_log(formatted_html)

    def _append_plain_chunk_log(self, idx: int, text: str):
        safe = html.escape(str(text)).replace("\n", "<br>")
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.append_chunk_log(idx, f'<span style="color: #8be9fd; font-family: Consolas, monospace;">[{now_str}] {safe}</span>')

    def _refresh_counts(self):
        total = len(self.cards)
        done = sum(1 for c in self.cards.values() if c.status == "완료")
        running = sum(1 for c in self.cards.values() if c.status == "진행중")
        waiting = sum(1 for c in self.cards.values() if c.status == "대기중")
        self.count_lbl.setText(f"완료 {done} · 진행중 {running} · 대기중 {waiting} / 총 {total}")

    def _persist_chunk_result(self, idx: int, new_text: str):
        ai_dir = self.session_context.get("ai_dir")
        if ai_dir and os.path.isdir(ai_dir):
            file_path = os.path.join(ai_dir, f"{idx}.txt")
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_text)
            except Exception:
                pass

        json_path = self.session_context.get("json_path")
        if json_path and os.path.isfile(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                key = str(idx - 1)
                if isinstance(data, dict) and key in data:
                    data[key] = new_text
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def retry_chunk_direct(self, idx: int):
        if idx in self._retry_workers and self._retry_workers[idx].isRunning():
            return
        card = self.cards.get(idx)
        if card is None or not card.source_text.strip():
            return
        self.update_chunk(idx, "진행중")
        worker = ChunkRetryWorker(
            kind=self.kind,
            idx=idx,
            source_text=card.source_text,
            retry_config=self.session_context.get("retry_config") or {},
        )
        self._retry_workers[idx] = worker
        worker.log_signal.connect(self._append_plain_chunk_log)
        worker.finished_signal.connect(lambda ok, txt, err, i=idx: self._on_direct_retry_finished(i, ok, txt, err))
        worker.start()

    def _on_direct_retry_finished(self, idx: int, ok: bool, txt: str, err: str):
        self._retry_workers.pop(idx, None)
        if ok:
            self._persist_chunk_result(idx, txt)
            self.update_chunk(idx, "완료", txt)
        else:
            self.update_chunk(idx, "오류", err)

    def rebuild_epub_from_backup(self):
        if self._epub_worker is not None and self._epub_worker.isRunning():
            return
        target_path = self.session_context.get("ai_dir") or self.session_context.get("json_path") or ""
        if not target_path or not os.path.exists(target_path):
            QMessageBox.warning(self, "알림", "백업 폴더를 찾을 수 없습니다.")
            return
        self.rebuild_epub_btn.setEnabled(False)
        self.rebuild_epub_btn.setText("EPUB 재생성 중...")
        self._epub_worker = EpubRebuildWorker(target_path)
        self._epub_worker.finished_signal.connect(self._on_epub_rebuilt)
        self._epub_worker.start()

    def _on_epub_rebuilt(self, ok: bool, msg: str):
        self.rebuild_epub_btn.setEnabled(True)
        self.rebuild_epub_btn.setText("EPUB 재생성")
        self._epub_worker = None
        if ok:
            QMessageBox.information(self, "완료", "백업 폴더 내용으로 EPUB을 재생성했습니다.")
        else:
            QMessageBox.warning(self, "실패", msg)

    def open_compare_dialog(self, idx: int):
        card = self.cards.get(idx)
        if card is None:
            return
        dlg = ChunkCompareDialog(
            idx=idx,
            kind=self.kind,
            status=card.status,
            source_text=card.source_text,
            result_text=card.result_text,
            session_context=self.session_context,
            parent=self,
        )
        dlg.log_emitted.connect(self._append_plain_chunk_log)
        dlg.result_updated.connect(lambda i, st, txt: self.update_chunk(i, st, txt))
        dlg.exec()


class ChunkBoardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("no_back-chunkBoard")
        self.sessions: Dict[str, ChunkSessionWidget] = {}
        self._pill_wrappers: Dict[str, QWidget] = {}
        self._pill_buttons: Dict[str, QPushButton] = {}
        self._session_order: List[str] = []
        self._session_counter = 0
        self.init_ui()

    def init_ui(self):
        root = create_layout("v", (0, 2, 0, 0), spacing=8, parent=self)

        self.pill_bar = QWidget()
        self.pill_bar.setObjectName("no_back-pillBar")
        self.pill_layout = QHBoxLayout(self.pill_bar)
        self.pill_layout.setContentsMargins(0, 0, 0, 0)
        self.pill_layout.setSpacing(6)
        self.pill_layout.addStretch(1)

        self.pill_group = QButtonGroup(self)
        self.pill_group.setExclusive(True)
        root.addWidget(self.pill_bar)

        self.session_stack = QStackedWidget()
        self.session_stack.setObjectName("no_back-sessionStack")
        root.addWidget(self.session_stack, 1)

        self.empty_card = QFrame()
        self.empty_card.setObjectName("CardFrame_ui")
        empty_lay = create_layout("v", (20, 28, 20, 28), spacing=6, parent=self.empty_card)
        self.empty_lbl = create_label("번역 또는 AI 용어집 작업을 시작하면 작업별 청크 창이 생성됩니다.", "new_and_now")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lay.addWidget(self.empty_lbl)
        root.addWidget(self.empty_card, 1)

        self.pill_bar.setVisible(False)
        self.session_stack.setVisible(False)

    def _select_session(self, sid: str):
        w = self.sessions.get(sid)
        if w is not None:
            self.session_stack.setCurrentWidget(w)
        for s_id, wrap in self._pill_wrappers.items():
            is_active = (s_id == sid)
            wrap.setProperty("active", "true" if is_active else "false")
            wrap.style().unpolish(wrap)
            wrap.style().polish(wrap)
        btn = self._pill_buttons.get(sid)
        if btn is not None:
            btn.setChecked(True)

    def _add_session_pill(self, sid: str, tab_title: str):
        wrap = QFrame(self.pill_bar)
        wrap.setObjectName("floatingPillWrap")
        wrap.setProperty("active", "false")
        wlay = QHBoxLayout(wrap)
        wlay.setContentsMargins(0, 0, 0, 0)
        wlay.setSpacing(2)

        btn = QPushButton(tab_title)
        btn.setObjectName("floatingPillBtn")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _, s=sid: self._select_session(s))
        self.pill_group.addButton(btn)
        wlay.addWidget(btn)

        close_btn = QPushButton("×")
        close_btn.setObjectName("floatingPillClose")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(lambda _, s=sid: self.close_session(s))
        wlay.addWidget(close_btn)

        self._pill_wrappers[sid] = wrap
        self._pill_buttons[sid] = btn
        self._session_order.append(sid)
        self.pill_layout.insertWidget(self.pill_layout.count() - 1, wrap)

    def _extract_chunk_idx(self, text: str) -> Optional[int]:
        clean = re.sub(r"^\[AI\s*용어집\]\s*", "", text.strip())
        for pattern in (
            r"^\[(?:용어집\s+)?(\d+)/\d+\]",
            r"^\[(\d+)\s*-",
            r"\[(\d+)번\s*청크\]",
        ):
            m = re.search(pattern, clean)
            if m:
                return int(m.group(1))
        return None

    def handle_event(self, event: Dict[str, Any]):
        if not isinstance(event, dict):
            return
        etype = event.get("type")
        sid = str(event.get("session_id") or "").strip() or f"job_{self._session_counter + 1}"

        if etype == "init":
            kind = str(event.get("kind") or "번역")
            title = str(event.get("title") or kind)
            self._session_counter += 1
            tab_title = f"{kind} #{self._session_counter}"

            widget = self.sessions.get(sid)
            if widget is None:
                widget = ChunkSessionWidget(
                    session_id=sid,
                    kind=kind,
                    title=title,
                    session_context=event,
                    parent=self.session_stack,
                )
                self.sessions[sid] = widget
                self.session_stack.addWidget(widget)
                self._add_session_pill(sid, tab_title)
            else:
                widget.session_context = dict(event)

            self._select_session(sid)
            widget.set_chunks(event.get("chunks") or [])
            self.empty_card.setVisible(False)
            self.pill_bar.setVisible(True)
            self.session_stack.setVisible(True)
            return

        widget = self.sessions.get(sid)
        if widget is None:
            return

        if etype == "status":
            idx = int(event.get("idx", 0))
            if idx > 0:
                widget.update_chunk(
                    idx=idx,
                    status=str(event.get("status") or "대기중"),
                    result_text=event.get("result"),
                    source_text=event.get("source"),
                )

    def _find_target_session(self, raw_text: str) -> Optional[ChunkSessionWidget]:
        if "[AI 용어집]" in raw_text:
            for sid in reversed(self._session_order):
                w = self.sessions.get(sid)
                if w is not None and w.kind == "AI 용어집":
                    return w
        cur = self.session_stack.currentWidget()
        if isinstance(cur, ChunkSessionWidget):
            return cur
        return None

    def route_log(self, raw_text: str, formatted_html: str):
        target = self._find_target_session(raw_text)
        if target is None:
            return
        idx = self._extract_chunk_idx(raw_text)
        if idx is None:
            if any(k in raw_text for k in ("[2차 검증", "1차 분류 집계", "최종 용어집 확정", "추출 완료")):
                if target.cards:
                    idx = max(target.cards.keys())
        if idx is not None:
            target.append_chunk_log(idx, formatted_html)

    def close_session(self, sid: str):
        w = self.sessions.pop(sid, None)
        wrap = self._pill_wrappers.pop(sid, None)
        btn = self._pill_buttons.pop(sid, None)
        if sid in self._session_order:
            self._session_order.remove(sid)
        if btn is not None:
            self.pill_group.removeButton(btn)
        if wrap is not None:
            self.pill_layout.removeWidget(wrap)
            wrap.deleteLater()
        if w is not None:
            self.session_stack.removeWidget(w)
            w.deleteLater()
        if self._session_order:
            self._select_session(self._session_order[-1])
        else:
            self.pill_bar.setVisible(False)
            self.session_stack.setVisible(False)
            self.empty_card.setVisible(True)
