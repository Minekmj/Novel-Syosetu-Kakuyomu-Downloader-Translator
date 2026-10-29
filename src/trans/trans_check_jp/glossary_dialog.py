from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget
)
from .widgets import AutoResizingTextEdit, SEMI_TRANS_BTN_STYLE, bind_height_sync
from .workers import JapaneseTranslateWorker


class JapaneseGlossaryDialog(QDialog):
    def __init__(self, parent_dialog):
        super().__init__(parent_dialog)
        self.parent_dialog = parent_dialog
        self.editors = []
        self.translate_worker = None

        self.setWindowTitle("단어집 및 일괄 치환")
        self.resize(880, 640)
        self.setMinimumSize(680, 480)
        self.init_ui()
        self.apply_custom_styles()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        words_count = len(self.parent_dialog.glossary_candidates)

        header_layout = QHBoxLayout()
        header_title = QLabel("자동 검출 단어집")
        header_title.setObjectName("dictionaryTitle")
        header_layout.addWidget(header_title, 1)

        self.all_trans_btn = QPushButton("전체 번역")
        self.all_trans_btn.setObjectName("semiTransBtn")
        self.all_trans_btn.setFixedHeight(28)
        self.all_trans_btn.setToolTip("단어집의 모든 단어를 비동기로 동시 번역합니다.")
        self.all_trans_btn.clicked.connect(self.translate_all)
        header_layout.addWidget(self.all_trans_btn)

        count_lbl = QLabel(f"단어: {words_count}개")
        count_lbl.setObjectName("dictionaryCount")
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(count_lbl)
        layout.addLayout(header_layout)

        info_lbl = QLabel("수정하거나 번역한 내용은 자동으로 저장됩니다. [치환]을 누르면 일괄 치환됩니다.")
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

        for idx, word in enumerate(self.parent_dialog.glossary_candidates):
            current_val = self.parent_dialog.glossary_dict.get(word, word)

            row_widget = QWidget()
            row_widget.setObjectName("Fs")
            row_widget.setStyleSheet("QWidget#Fs{background:transparent;}")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 1, 4, 1)
            row_layout.setSpacing(8)

            orig_edit = AutoResizingTextEdit(is_orig=True)
            orig_edit.setReadOnly(True)
            orig_edit.setPlainText(word)
            orig_edit.viewport().setStyleSheet('background: transparent;')

            arrow_lbl = QLabel("→")
            arrow_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            arrow_lbl.setFixedWidth(16)
            arrow_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: rgba(255, 255, 255, 0.4);")

            replace_edit = AutoResizingTextEdit(is_orig=False)
            replace_edit.setPlainText(current_val)
            replace_edit.viewport().setStyleSheet('background: transparent;')

            replace_edit.textChanged.connect(
                lambda w=word, ed=replace_edit: self.parent_dialog.update_glossary_entry(w, ed.toPlainText())
            )

            single_btn = QPushButton("번역")
            single_btn.setObjectName("semiTransBtn")
            single_btn.setFixedWidth(48)
            single_btn.clicked.connect(lambda chk=False, i=idx: self.translate_single(i))

            apply_btn = QPushButton("치환")
            apply_btn.setObjectName("semiTransBtn")
            apply_btn.setFixedWidth(48)
            apply_btn.clicked.connect(lambda chk=False, i=idx: self.apply_single_word(i))

            bind_height_sync(orig_edit, replace_edit, single_btn, apply_btn)

            row_layout.addWidget(orig_edit, 1)
            row_layout.addWidget(arrow_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
            row_layout.addWidget(replace_edit, 1)
            row_layout.addWidget(single_btn)
            row_layout.addWidget(apply_btn)

            container_layout.addWidget(row_widget)
            self.editors.append((word, replace_edit, single_btn, apply_btn))

        container_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        close_btn = QPushButton("닫기")
        close_btn.setObjectName("secondaryBtn")
        close_btn.setFixedHeight(40)
        close_btn.clicked.connect(self.close)

        apply_all_btn = QPushButton("단어집 전체 본문에 치환")
        apply_all_btn.setObjectName("primaryBtn")
        apply_all_btn.setFixedHeight(40)
        apply_all_btn.clicked.connect(self.apply_all_words)

        bottom_layout.addWidget(close_btn)
        bottom_layout.addWidget(apply_all_btn)
        layout.addLayout(bottom_layout)

    def apply_custom_styles(self):
        self.setStyleSheet(self.styleSheet() + SEMI_TRANS_BTN_STYLE)

    def _set_buttons_enabled(self, enabled: bool):
        self.all_trans_btn.setEnabled(enabled)
        for _, _, s_btn, a_btn in self.editors:
            s_btn.setEnabled(enabled)
            a_btn.setEnabled(enabled)

    def _start_batch_translate(self, indices):
        if not indices:
            return

        if self.translate_worker and self.translate_worker.isRunning():
            QMessageBox.warning(self, "알림", "현재 단어 번역 작업이 진행 중입니다.")
            return

        tasks = []
        for i in indices:
            orig_word, replace_edit, _, _ = self.editors[i]
            txt = replace_edit.toPlainText().strip() or orig_word
            tasks.append((i, txt))

        self._set_buttons_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(tasks))
        self.progress_bar.setValue(0)

        self.translate_worker = JapaneseTranslateWorker(tasks, is_word_mode=True, parent=self)
        self.translate_worker.item_translated.connect(self.on_item_translated)
        self.translate_worker.progress_changed.connect(self.on_progress_changed)
        self.translate_worker.finished_signal.connect(self.on_translate_finished)
        self.translate_worker.start()

    def translate_single(self, index: int):
        self._start_batch_translate([index])

    def translate_all(self):
        all_indices = list(range(len(self.editors)))
        self._start_batch_translate(all_indices)

    def on_item_translated(self, idx: int, result_text: str):
        if 0 <= idx < len(self.editors):
            orig_word = self.editors[idx][0]
            self.editors[idx][1].setPlainText(result_text)
            self.parent_dialog.update_glossary_entry(orig_word, result_text)

    def on_progress_changed(self, done: int, total: int):
        self.progress_bar.setValue(done)

    def on_translate_finished(self):
        self._set_buttons_enabled(True)
        self.progress_bar.setVisible(False)

    def apply_single_word(self, index: int):
        orig_word, edit, _, _ = self.editors[index]
        ko_word = edit.toPlainText().strip()
        self.parent_dialog.replace_in_all_editors(orig_word, ko_word)

    def apply_all_words(self):
        items_to_replace = []
        for orig_word, edit, _, _ in self.editors:
            ko_word = edit.toPlainText().strip()
            if ko_word and orig_word != ko_word:
                items_to_replace.append((orig_word, ko_word))

        items_to_replace.sort(key=lambda x: len(x[0]), reverse=True)
        for orig_word, ko_word in items_to_replace:
            self.parent_dialog.replace_in_all_editors(orig_word, ko_word)

    def closeEvent(self, event):
        if self.translate_worker and self.translate_worker.isRunning():
            self.translate_worker.cancel()
            self.translate_worker.wait()
        super().closeEvent(event)