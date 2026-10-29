from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget
)
from .text_cleaner import has_japanese
from .widgets import AutoResizingTextEdit, SEMI_TRANS_BTN_STYLE, bind_height_sync
from .workers import GlossaryExtractWorker, JapaneseTranslateWorker
from .glossary_dialog import JapaneseGlossaryDialog
from src.trans.trans_ai_utils import apply_japanese_corrections


class JapaneseCheckDialog(QDialog):
    def __init__(self, inspection_data, parent=None):
        super().__init__(parent)
        self.inspection_data = inspection_data
        self.json_path = inspection_data.get('json_path', '')
        self.title = inspection_data.get('title', '작품')

        raw_items = inspection_data.get('items', [])
        self.items = [
            item for item in raw_items
            if has_japanese(item.get('original_text', ''))
        ]

        self.editors = []
        self.chunk_button_map = {}
        self.translate_worker = None
        self.extract_worker = None
        self.glossary_dialog = None

        self.glossary_dict = {}
        self.glossary_candidates = []
        self.is_extracting_glossary = True

        self.setWindowTitle(f"일본어 검사 - {self.title}")
        self.resize(880, 680)
        self.setMinimumSize(640, 500)
        self.init_ui()
        self.apply_custom_styles()

        self._start_initial_glossary_extraction()

    def _start_initial_glossary_extraction(self):
        self.glossary_btn.setText("단어집 준비 중...")
        self.extract_worker = GlossaryExtractWorker(self.items, self)
        self.extract_worker.extracted_signal.connect(self._on_glossary_extracted)
        self.extract_worker.start()

    def _on_glossary_extracted(self, candidates):
        self.is_extracting_glossary = False
        self.glossary_candidates = candidates
        for word in candidates:
            if word not in self.glossary_dict:
                self.glossary_dict[word] = word
        self.glossary_btn.setText(f"단어집 ({len(candidates)})")

    def update_glossary_entry(self, jp_word: str, ko_word: str):
        self.glossary_dict[jp_word] = ko_word.strip()

    def open_glossary_window(self):
        if self.is_extracting_glossary:
            QMessageBox.information(self, "단어집", "단어집을 분석 중입니다. 잠시 후 다시 눌러주세요.")
            return
        if not self.glossary_candidates:
            QMessageBox.information(self, "단어집", "2회 이상 반복 검출된 일본어 단어가 없습니다.")
            return
        if self.glossary_dialog is not None and self.glossary_dialog.isVisible():
            self.glossary_dialog.raise_()
            self.glossary_dialog.activateWindow()
            return
        self.glossary_dialog = JapaneseGlossaryDialog(parent_dialog=self)
        self.glossary_dialog.show()

    def replace_in_all_editors(self, orig_word: str, ko_word: str) -> int:
        if not ko_word or orig_word == ko_word:
            return 0
        count = 0
        for _, edit, _ in self.editors:
            cur = edit.toPlainText()
            if orig_word in cur:
                edit.setPlainText(cur.replace(orig_word, ko_word))
                count += 1
        return count

    def get_active_glossary_dict(self) -> dict:
        valid_items = [
            (jp, ko) for jp, ko in self.glossary_dict.items()
            if ko and jp != ko
        ]
        valid_items.sort(key=lambda x: len(x[0]), reverse=True)
        return dict(valid_items)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_title = QLabel(f"일본어 검출 항목  |  {self.title}")
        header_title.setObjectName("dictionaryTitle")
        header_layout.addWidget(header_title, 1)

        self.glossary_btn = QPushButton("단어집")
        self.glossary_btn.setObjectName("semiTransBtn")
        self.glossary_btn.setFixedHeight(28)
        self.glossary_btn.setToolTip("검출된 일본어 단어를 모아보고 일괄 치환합니다.")
        self.glossary_btn.clicked.connect(self.open_glossary_window)
        header_layout.addWidget(self.glossary_btn)

        self.all_trans_btn = QPushButton("전체 번역")
        self.all_trans_btn.setObjectName("semiTransBtn")
        self.all_trans_btn.setFixedHeight(28)
        self.all_trans_btn.setToolTip("검출된 모든 항목을 비동기로 동시 번역합니다.")
        self.all_trans_btn.clicked.connect(self.translate_all)
        header_layout.addWidget(self.all_trans_btn)

        count_lbl = QLabel(f"검출: {len(self.items)}개 항목")
        count_lbl.setObjectName("dictionaryCount")
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(count_lbl)
        layout.addLayout(header_layout)

        info_lbl = QLabel("[번역]을 누르면 번역이 실행됩니다. 원문 칸에 의심/검출 구간이 형광펜으로 표시됩니다.")
        info_lbl.setObjectName("secondaryInfo")
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        container = QWidget()
        container.setObjectName("Fcon")
        container.setStyleSheet("QWidget#Fcon{background:transparent;}")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(4, 4, 4, 4)
        container_layout.setSpacing(8)

        last_chunk_key = None
        current_chunk_indices = []

        for idx, item in enumerate(self.items):
            chunk_display = item.get('chunk_display', 1)
            chunk_key = item.get('chunk_key', '0')

            if chunk_key != last_chunk_key:
                if last_chunk_key is not None and last_chunk_key in self.chunk_button_map:
                    self.chunk_button_map[last_chunk_key][1] = list(current_chunk_indices)
                    current_chunk_indices.clear()

                last_chunk_key = chunk_key

                chunk_sep_box = QFrame()
                chunk_sep_box.setObjectName("chunkSepBox")
                chunk_sep_box.setStyleSheet("QFrame{background:transparent;}")
                sep_layout = QHBoxLayout(chunk_sep_box)
                sep_layout.setContentsMargins(10, 5, 10, 5)

                chunk_lbl = QLabel(f"[{self.title} - 청크 {chunk_display}]")
                chunk_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #4da6ff;")
                sep_layout.addWidget(chunk_lbl, 1)

                chunk_trans_btn = QPushButton("이 청크 번역")
                chunk_trans_btn.setObjectName("semiTransBtn")
                chunk_trans_btn.setFixedHeight(28)
                chunk_trans_btn.clicked.connect(lambda chk=False, ck=chunk_key: self.translate_chunk(ck))
                sep_layout.addWidget(chunk_trans_btn)

                container_layout.addWidget(chunk_sep_box)
                self.chunk_button_map[chunk_key] = [chunk_trans_btn, []]

            current_chunk_indices.append(idx)

            row_widget = QWidget()
            row_widget.setObjectName("Fs")
            row_widget.setStyleSheet("QWidget#Fs{background:transparent;}")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 1, 4, 1)
            row_layout.setSpacing(8)

            orig_edit = AutoResizingTextEdit(is_orig=True)
            orig_edit.setReadOnly(True)
            orig_edit.setPlainText(item.get('original_text', '').rstrip('\n'))
            orig_edit.viewport().setStyleSheet('background: transparent;')

            arrow_lbl = QLabel("→")
            arrow_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            arrow_lbl.setFixedWidth(16)
            arrow_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: rgba(255, 255, 255, 0.4);")

            replace_edit = AutoResizingTextEdit(is_orig=False)
            replace_edit.setPlainText(item.get('original_text', '').rstrip('\n'))
            replace_edit.viewport().setStyleSheet('background: transparent;')

            single_btn = QPushButton("번역")
            single_btn.setObjectName("semiTransBtn")
            single_btn.setFixedWidth(48)
            single_btn.clicked.connect(lambda chk=False, i=idx: self.translate_single(i))

            bind_height_sync(orig_edit, replace_edit, single_btn)

            row_layout.addWidget(orig_edit, 1)
            row_layout.addWidget(arrow_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
            row_layout.addWidget(replace_edit, 1)
            row_layout.addWidget(single_btn)

            container_layout.addWidget(row_widget)
            self.editors.append((item, replace_edit, single_btn))

        if last_chunk_key is not None and last_chunk_key in self.chunk_button_map:
            self.chunk_button_map[last_chunk_key][1] = list(current_chunk_indices)

        container_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        cancel_btn = QPushButton("취소")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setFixedHeight(40)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("바꾸기")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.apply_changes)

        bottom_layout.addWidget(cancel_btn)
        bottom_layout.addWidget(save_btn)
        layout.addLayout(bottom_layout)

    def apply_custom_styles(self):
        self.setStyleSheet(self.styleSheet() + SEMI_TRANS_BTN_STYLE)

    def _set_buttons_enabled(self, enabled: bool):
        self.all_trans_btn.setEnabled(enabled)
        for chunk_btn, _ in self.chunk_button_map.values():
            chunk_btn.setEnabled(enabled)
        for _, _, single_btn in self.editors:
            single_btn.setEnabled(enabled)

    def _start_batch_translate(self, indices):
        if not indices:
            return

        if self.translate_worker and self.translate_worker.isRunning():
            QMessageBox.warning(self, "알림", "현재 번역 작업이 진행 중입니다.")
            return

        tasks = []
        for i in indices:
            item, replace_edit, _ = self.editors[i]
            txt = replace_edit.toPlainText().strip() or item.get('original_text', '').strip()
            tasks.append((i, txt))

        self._set_buttons_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(tasks))
        self.progress_bar.setValue(0)

        glossary = self.get_active_glossary_dict()

        self.translate_worker = JapaneseTranslateWorker(tasks, glossary=glossary, is_word_mode=False, parent=self)
        self.translate_worker.item_translated.connect(self.on_item_translated)
        self.translate_worker.progress_changed.connect(self.on_progress_changed)
        self.translate_worker.finished_signal.connect(self.on_translate_finished)
        self.translate_worker.start()

    def translate_single(self, index: int):
        self._start_batch_translate([index])

    def translate_chunk(self, chunk_key: str):
        if chunk_key in self.chunk_button_map:
            indices = self.chunk_button_map[chunk_key][1]
            self._start_batch_translate(indices)

    def translate_all(self):
        all_indices = list(range(len(self.editors)))
        self._start_batch_translate(all_indices)

    def on_item_translated(self, idx: int, result_text: str):
        if 0 <= idx < len(self.editors):
            self.editors[idx][1].setPlainText(result_text)

    def on_progress_changed(self, done: int, total: int):
        self.progress_bar.setValue(done)

    def on_translate_finished(self):
        self._set_buttons_enabled(True)
        self.progress_bar.setVisible(False)

    def closeEvent(self, event):
        if self.translate_worker and self.translate_worker.isRunning():
            self.translate_worker.cancel()
            self.translate_worker.wait()
        if self.extract_worker and self.extract_worker.isRunning():
            self.extract_worker.wait()
        if self.glossary_dialog and self.glossary_dialog.isVisible():
            self.glossary_dialog.close()
        super().closeEvent(event)

    def apply_changes(self):
        corrections = []
        for item, edit, _ in self.editors:
            new_text = edit.toPlainText()
            if item.get('original_text', '').endswith('\n') and not new_text.endswith('\n'):
                new_text += '\n'
            corrections.append({
                'chunk_key': item['chunk_key'],
                'start_line': item['start_line'],
                'end_line': item['end_line'],
                'new_text': new_text
            })

        try:
            success, count, err = apply_japanese_corrections(self.json_path, corrections)
            if success:
                QMessageBox.information(
                    self,
                    "일본어 검사 완료",
                    f"총 {count}개의 검출 블록이 성공적으로 수정 및 저장되었습니다.\n\nJSON 파일과 청크 파일이 갱신되었습니다."
                )
                self.accept()
            else:
                QMessageBox.critical(self, "저장 오류", f"수정 사항 저장 중 오류가 발생했습니다: {err}")
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", str(e))