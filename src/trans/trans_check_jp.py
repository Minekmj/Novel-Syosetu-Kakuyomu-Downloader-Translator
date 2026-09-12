import asyncio
import concurrent.futures
import re

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QTextEdit,
    QVBoxLayout, QWidget
)

from src.trans.trans import Translator

trans_ai = None  # 외부 삽입용

JP_RANGES = r'\u3040-\u309f\u30a0-\u30ff\u31f0-\u31ff\uff65-\uff9f\u4e00-\u9fff\uf900-\ufaff\u3005\u3006\u3007'
KO_RANGES = r'\uac00-\ud7af\u1100-\u11ff\u3130-\u318f'
PROLONGED_RANGES = r'ー〜~'
SMALL_KANA_RANGES = r'っッぁぃぅぇぉァィゥェォゎヵヶゃゅょャュョㇰ-ㇿ'

JP_PATTERN = re.compile(rf'[{JP_RANGES}]')
KO_PATTERN = re.compile(rf'[{KO_RANGES}]')
JP_BLOCK_PATTERN = re.compile(rf'[{JP_RANGES}]+')

PROLONGED_PATTERN = re.compile(rf'[{PROLONGED_RANGES}]+')
SMALL_KANA_PATTERN = re.compile(rf'[{SMALL_KANA_RANGES}]+')
RESIDUE_PATTERN = re.compile(rf'[{PROLONGED_RANGES}{SMALL_KANA_RANGES}]+')

KO_PROLONGED_KO_PATTERN = re.compile(
    rf'([{KO_RANGES}])\s*[{PROLONGED_RANGES}]+\s*([{KO_RANGES}])'
)

KO_YON_KO_PATTERN = re.compile(
    rf'([{KO_RANGES}])\s*[{SMALL_KANA_RANGES}]+\s*([{KO_RANGES}])'
)

BRACKET_PATTERN = re.compile(
    rf'([{JP_RANGES}]+)?\s*[\(（]([^\(\)（）]+)[\)）]'
)

WORD_TOKEN_PATTERN = re.compile(
    rf'[{KO_RANGES}{JP_RANGES}{PROLONGED_RANGES}{SMALL_KANA_RANGES}]+'
)

EXPLANATION_PATTERNS = [
    re.compile(r'[\'"]?[^\'"]*[\'"]?\s*는\s*일본어의\s*(가나|문자|히라가나|가타카나|발음|요음|촉음)[^\.\n]*[\.\n]?', re.IGNORECASE),
    re.compile(r'주로\s*(발음을\s*변화|감탄사|특수문자|글자\s*꾸미기)[^\.\n]*[\.\n]?', re.IGNORECASE),
    re.compile(r'\d+\.\s*(일본어에서의\s*)?(본래\s*의미|용법|발음)[^\.\n]*', re.IGNORECASE),
    re.compile(r'한국어에서는\s*(인터넷\s*유행어나|특수문자)[^\.\n]*[\.\n]?', re.IGNORECASE),
]

KO_PARTICLES = [
    '으로부터', '에서는', '에게서', '까지는', '부터는', '으로는',
    '에서', '으로', '에게', '한테', '까지', '부터', '보다', '처럼',
    '은', '는', '이', '가', '을', '를', '에', '와', '과', '도', '로', '의', '만', '랑'
]
PARTICLE_PATTERN = re.compile(rf'({"|".join(KO_PARTICLES)})$')

def clean_explanation_residue(text: str) -> str:
    if not text:
        return text
    for pat in EXPLANATION_PATTERNS:
        text = pat.sub('', text)
    return text.strip()


def strip_korean_particles(token: str) -> str:
    if not token:
        return token
    m = PARTICLE_PATTERN.search(token)
    if m:
        stem = token[:m.start()]
        if JP_PATTERN.search(stem):
            return stem
    return token


def sanitize_dot_addition(orig_text: str, trans_text: str) -> str:
    if not trans_text:
        return ""
    if '.' not in orig_text and '。' not in orig_text:
        trans_text = trans_text.replace('.', '').replace('。', '')
    return trans_text.strip()


def sanitize_translated_word(trans_text: str, orig_text: str = "") -> str:
    if not trans_text:
        return ""
    trans_text = clean_explanation_residue(trans_text)
    f = trans_text.find("： ")
    if (f > -1):
        trans_text = trans_text[f + 1:]
    parts = re.split(r'[,，/／\n]', trans_text)
    first_choice = parts[0].strip()
    res = first_choice if first_choice else trans_text.strip()

    if orig_text:
        res = sanitize_dot_addition(orig_text, res)
    return res

def step1_calculate_brackets(text: str) -> str:
    if not text:
        return text

    def _replace_match(m):
        before_jp = m.group(1)
        inside = m.group(2)

        has_ko = bool(KO_PATTERN.search(inside))
        has_jp = bool(JP_PATTERN.search(inside))

        if before_jp and has_ko:
            return inside

        if has_jp and not has_ko:
            return before_jp if before_jp else ""

        return m.group(0)

    cleaned = BRACKET_PATTERN.sub(_replace_match, text)
    cleaned = re.sub(r' +', ' ', cleaned)
    return cleaned.strip()

def step2_calculate_prolonged(text: str) -> str:
    if not text or not PROLONGED_PATTERN.search(text):
        return text
    prev = ""
    curr = text
    while prev != curr:
        prev = curr
        curr = KO_PROLONGED_KO_PATTERN.sub(r'\1 \2', curr)
    return curr


def step3_calculate_yon(text: str) -> str:
    if not text or not SMALL_KANA_PATTERN.search(text):
        return text
    prev = ""
    curr = text
    while prev != curr:
        prev = curr
        curr = KO_YON_KO_PATTERN.sub(r'\1 \2', curr)
    return curr

def has_japanese(text: str) -> bool:
    return bool(text and JP_PATTERN.search(text))

def smart_translate(text: str, glossary: dict = None, is_word_mode: bool = False) -> str:
    if not text or not text.strip():
        return text

    orig_input = text

    if glossary:
        sorted_glossary = sorted(glossary.items(), key=lambda x: len(x[0]), reverse=True)
        for jp_word, ko_word in sorted_glossary:
            if jp_word and ko_word and jp_word != ko_word and jp_word in text:
                text = text.replace(jp_word, ko_word)

    res = step1_calculate_brackets(text)

    res = step2_calculate_prolonged(res)

    res = step3_calculate_yon(res)

    if not has_japanese(res):
        res = clean_explanation_residue(res)
        res = re.sub(r' +', ' ', res).strip()
        if is_word_mode:
            res = sanitize_dot_addition(orig_input, res)
        return res

    try:
        translated = Translator(res)
        if is_word_mode:
            translated = sanitize_translated_word(translated, orig_text=res)
        res = translated
    except Exception:
        pass

    res = clean_explanation_residue(res)
    res = step1_calculate_brackets(res)
    res = step2_calculate_prolonged(res)
    res = step3_calculate_yon(res)

    if not has_japanese(res):
        res = RESIDUE_PATTERN.sub('', res)
        res = re.sub(r'~{2,}', '~', res)
        res = re.sub(r' +', ' ', res).strip()
        if is_word_mode:
            res = sanitize_dot_addition(orig_input, res)
        return res

    jp_matches = list(JP_BLOCK_PATTERN.finditer(res))
    if jp_matches:
        chars = list(res)
        for m in reversed(jp_matches):
            sub_jp = m.group()

            if RESIDUE_PATTERN.fullmatch(sub_jp):
                chars[m.start():m.end()] = []
                continue

            try:
                sub_trans = Translator(sub_jp)
                sub_trans = sanitize_translated_word(sub_trans, orig_text=sub_jp)
            except Exception:
                try:
                    sub_trans = Translator(sub_jp)
                    sub_trans = sanitize_translated_word(sub_trans, orig_text=sub_jp)
                except Exception:
                    sub_trans = sub_jp

            chars[m.start():m.end()] = list(sub_trans)
        res = "".join(chars)

    res = clean_explanation_residue(res)
    res = step1_calculate_brackets(res)
    res = RESIDUE_PATTERN.sub('', res)
    res = re.sub(r'~{2,}', '~', res)
    res = re.sub(r' +', ' ', res).strip()
    if is_word_mode:
        res = sanitize_translated_word(res, orig_text=orig_input)
    return res

class AutoResizingTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.document().documentLayout().documentSizeChanged.connect(self.adjust_height)
        self.textChanged.connect(self.adjust_height)

    def adjust_height(self):
        doc_height = self.document().size().height()
        margins = self.contentsMargins()
        new_height = int(doc_height + margins.top() + margins.bottom() + 16)
        self.setFixedHeight(max(36, new_height))

    def setPlainText(self, text):
        super().setPlainText(text)
        self.adjust_height()


class GlossaryExtractWorker(QThread):
    extracted_signal = Signal(list)

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items

    def run(self):
        word_freq = {}

        for item in self.items:
            text = item.get('original_text', '').strip()
            if not text:
                continue

            text = clean_explanation_residue(text)

            tokens = WORD_TOKEN_PATTERN.findall(text)
            for tok in tokens:
                tok = tok.strip()
                if not JP_PATTERN.search(tok):
                    continue

                tok = strip_korean_particles(tok)
                cleaned = RESIDUE_PATTERN.sub('', tok).strip()

                if len(cleaned) >= 2 and JP_PATTERN.search(cleaned):
                    word_freq[tok] = word_freq.get(tok, 0) + 1

        candidates = [
            word for word, count in word_freq.items()
            if count >= 2
        ]
        candidates.sort(key=lambda k: word_freq[k], reverse=True)

        self.extracted_signal.emit(candidates)


class JapaneseTranslateWorker(QThread):
    item_translated = Signal(int, str)
    progress_changed = Signal(int, int)
    finished_signal = Signal()

    def __init__(self, tasks, glossary=None, is_word_mode=False, parent=None):
        super().__init__(parent)
        self.tasks = tasks
        self.glossary = glossary or {}
        self.is_word_mode = is_word_mode
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        total = len(self.tasks)
        done = 0

        def worker_task(task_item):
            if self._is_cancelled:
                return task_item[0], None
            idx, text = task_item
            result = smart_translate(text, glossary=self.glossary, is_word_mode=self.is_word_mode)
            return idx, result

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_idx = {
                executor.submit(worker_task, task): task[0]
                for task in self.tasks
            }
            for future in concurrent.futures.as_completed(future_to_idx):
                if self._is_cancelled:
                    break
                try:
                    idx, res = future.result()
                    if res is not None and not self._is_cancelled:
                        self.item_translated.emit(idx, res)
                except Exception:
                    pass
                done += 1
                self.progress_changed.emit(done, total)

        self.finished_signal.emit()

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
        self.all_trans_btn.setToolTip("단어집의 모든 단어를 비동기로 동시 스마트 번역합니다.")
        self.all_trans_btn.clicked.connect(self.translate_all)
        header_layout.addWidget(self.all_trans_btn)

        count_lbl = QLabel(f"단어: {words_count}개")
        count_lbl.setObjectName("dictionaryCount")
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(count_lbl)
        layout.addLayout(header_layout)

        info_lbl = QLabel("수정하거나 번역한 내용은 자동으로 저장됩니다. [치환] 일괄 치환됩니다.")
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

            orig_edit = AutoResizingTextEdit()
            orig_edit.setReadOnly(True)
            orig_edit.setPlainText(word)
            orig_edit.viewport().setStyleSheet('background: transparent;')

            arrow_lbl = QLabel("→")
            arrow_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            arrow_lbl.setFixedWidth(16)
            arrow_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: rgba(255, 255, 255, 0.4);")

            replace_edit = AutoResizingTextEdit()
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

            def sync_heights(oe=orig_edit, re=replace_edit, b1=single_btn, b2=apply_btn):
                h = max(oe.sizeHint().height(), re.sizeHint().height(), oe.height(), re.height())
                oe.setFixedHeight(h)
                re.setFixedHeight(h)
                b1.setFixedHeight(h)
                b2.setFixedHeight(h)

            orig_edit.document().documentLayout().documentSizeChanged.connect(lambda: sync_heights(orig_edit, replace_edit, single_btn, apply_btn))
            replace_edit.document().documentLayout().documentSizeChanged.connect(lambda: sync_heights(orig_edit, replace_edit, single_btn, apply_btn))
            sync_heights(orig_edit, replace_edit, single_btn, apply_btn)

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
        self.setStyleSheet(self.styleSheet() + '''
            QPushButton#semiTransBtn {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                color: palette(text);
                font-size: 11px;
                padding: 0px 6px;
            }
            QPushButton#semiTransBtn:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.22);
            }
            QPushButton#semiTransBtn:pressed {
                background-color: rgba(255, 255, 255, 0.05);
                padding-top: 1px;
            }
            QPushButton#semiTransBtn:disabled {
                background-color: rgba(255, 255, 255, 0.02);
                border-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.25);
            }
        ''')

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
        count = self.parent_dialog.replace_in_all_editors(orig_word, ko_word)

    def apply_all_words(self):
        items_to_replace = []
        for orig_word, edit, _, _ in self.editors:
            ko_word = edit.toPlainText().strip()
            if ko_word and orig_word != ko_word:
                items_to_replace.append((orig_word, ko_word))

        items_to_replace.sort(key=lambda x: len(x[0]), reverse=True)

        total_count = 0
        for orig_word, ko_word in items_to_replace:
            total_count += self.parent_dialog.replace_in_all_editors(orig_word, ko_word)

    def closeEvent(self, event):
        if self.translate_worker and self.translate_worker.isRunning():
            self.translate_worker.cancel()
            self.translate_worker.wait()
        super().closeEvent(event)

class JapaneseCheckDialog(QDialog):
    def __init__(self, inspection_data, parent=None):
        super().__init__(parent)
        self.inspection_data = inspection_data
        self.json_path = inspection_data.get('json_path', '')
        self.title = inspection_data.get('title', '작품')
        self.items = inspection_data.get('items', [])

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
        self.all_trans_btn.setToolTip("검출된 모든 항목을 최대 10개씩 동시 번역합니다.")
        self.all_trans_btn.clicked.connect(self.translate_all)
        header_layout.addWidget(self.all_trans_btn)

        count_lbl = QLabel(f"검출: {len(self.items)}개 항목")
        count_lbl.setObjectName("dictionaryCount")
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(count_lbl)
        layout.addLayout(header_layout)

        info_lbl = QLabel("[번역]을 누르면 번역이 실행되며, 직접 수정 후 [바꾸기]를 누르면 저장됩니다.")
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

            orig_edit = AutoResizingTextEdit()
            orig_edit.setReadOnly(True)
            orig_edit.setPlainText(item.get('original_text', '').rstrip('\n'))
            orig_edit.viewport().setStyleSheet('background: transparent;')

            arrow_lbl = QLabel("→")
            arrow_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            arrow_lbl.setFixedWidth(16)
            arrow_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: rgba(255, 255, 255, 0.4);")

            replace_edit = AutoResizingTextEdit()
            replace_edit.setPlainText(item.get('original_text', '').rstrip('\n'))
            replace_edit.viewport().setStyleSheet('background: transparent;')

            single_btn = QPushButton("번역")
            single_btn.setObjectName("semiTransBtn")
            single_btn.setFixedWidth(48)
            single_btn.clicked.connect(lambda chk=False, i=idx: self.translate_single(i))

            def sync_heights(oe=orig_edit, re=replace_edit, sb=single_btn):
                h = max(oe.sizeHint().height(), re.sizeHint().height(), oe.height(), re.height())
                oe.setFixedHeight(h)
                re.setFixedHeight(h)
                sb.setFixedHeight(h)

            orig_edit.document().documentLayout().documentSizeChanged.connect(lambda: sync_heights(orig_edit, replace_edit, single_btn))
            replace_edit.document().documentLayout().documentSizeChanged.connect(lambda: sync_heights(orig_edit, replace_edit, single_btn))
            sync_heights(orig_edit, replace_edit, single_btn)

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
        self.setStyleSheet(self.styleSheet() + '''
            QPushButton#semiTransBtn {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                color: palette(text);
                font-size: 11px;
                padding: 0px 6px;
            }
            QPushButton#semiTransBtn:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.22);
            }
            QPushButton#semiTransBtn:pressed {
                background-color: rgba(255, 255, 255, 0.05);
                padding-top: 1px;
            }
            QPushButton#semiTransBtn:disabled {
                background-color: rgba(255, 255, 255, 0.02);
                border-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.25);
            }
        ''')

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
            success, count, err = trans_ai.apply_japanese_corrections(self.json_path, corrections)
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