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

# 일본어 / 한국어 문자 범위 정의
JP_CHAR = r'[\u3040-\u309f\u30a0-\u30ff\u31f0-\u31ff\uff65-\uff9f\u4e00-\u9fff\uf900-\ufaff\u3005\u3006\u3007]'
KO_CHAR = r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]'

JP_BLOCK_PATTERN = re.compile(rf'{JP_CHAR}+')

JP_PATTERN = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u31f0-\u31ff\uff65-\uff9f\u4e00-\u9fff\uf900-\ufaff\u3005\u3006\u3007]')
KO_PATTERN = re.compile(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]')

# 패턴: [앞의 일본어(선택)] + [공백(선택)] + [(괄호 안 내용)] (반각 (), 전각 （） 모두 대응)
BRACKET_PATTERN = re.compile(
    r'([\u3040-\u309f\u30a0-\u30ff\u31f0-\u31ff\uff65-\uff9f\u4e00-\u9fff\uf900-\ufaff\u3005\u3006\u3007]+)?\s*[\(（]([^\(\)（）]+)[\)）]'
)

SMALL_KANA_PATTERN = re.compile(r'[っッぁぃぅぇぉァィゥェォゎヵヶ]+')

def clean_japanese_residue(text: str) -> str:
    if not text:
        return text

    # 덜렁 남은 촉음(っ, ッ) 및 소형 가나는 깔끔하게 제거
    text = SMALL_KANA_PATTERN.sub('', text)

    # 연속된 물결표 정리 (예: ~~~ -> ~)
    text = re.sub(r'~{2,}', '~', text)
    
    # 찌꺼기가 빠지면서 생긴 불필요한 공백 정리
    text = re.sub(r' +', ' ', text)

    return text.strip()

def clean_brackets(text: str) -> str:
    if not text:
        return text

    def _replace_match(m):
        before_jp = m.group(1)  # 괄호 바로 앞의 일본어 (있을 경우)
        inside = m.group(2)     # 괄호 안 내용

        has_ko = bool(KO_PATTERN.search(inside))
        has_jp = bool(JP_PATTERN.search(inside))

        # 1. 일본어(한국어) 형태 -> 한국어로 대체
        if before_jp and has_ko:
            return inside

        # 2. 뭐라뭐라(일본어) 형태 -> (일본어) 부분 삭제
        #    (괄호 안에 일본어가 있고 한글은 없는 경우)
        if has_jp and not has_ko:
            return before_jp if before_jp else ""

        # 그 외 일반 괄호(예: 공격력(ATK), 레벨(10) 등)는 원본 유지
        return m.group(0)

    # 괄호 패턴 치환 적용
    cleaned = BRACKET_PATTERN.sub(_replace_match, text)
    # 불필요한 연속 공백 정리
    cleaned = re.sub(r' +', ' ', cleaned)
    return cleaned.strip()


def smart_translate(text: str) -> str:
    if not text or not text.strip():
        return text

    # 번역 전 괄호 정리
    text = clean_brackets(text)

    try:
        res = Translator(text)
    except Exception:
        res = text

    # 1차 괄호 및 촉음/장음 찌꺼기 정리
    res = clean_brackets(res)
    res = clean_japanese_residue(res)

    # 번역 후에도 남아있는 일본어 일반 단어 블록 처리
    jp_matches = list(JP_BLOCK_PATTERN.finditer(res))
    if jp_matches:
        chars = list(res)
        for m in reversed(jp_matches):
            sub_jp = m.group()
            
            # 남은 게 순수 촉음/장음뿐이면 번역기를 다시 호출하지 않고 건너뜀
            if SMALL_KANA_PATTERN.fullmatch(sub_jp):
                chars[m.start():m.end()] = []
                continue

            try:
                sub_trans = Translator(sub_jp)
            except Exception:
                sub_trans = sub_jp
            chars[m.start():m.end()] = list(sub_trans)
        res = "".join(chars)

    # 최종 괄호 및 찌꺼기 정리
    res = clean_brackets(res)
    return clean_japanese_residue(res)


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


class JapaneseTranslateWorker(QThread):
    item_translated = Signal(int, str)
    progress_changed = Signal(int, int)
    finished_signal = Signal()

    def __init__(self, tasks, parent=None):
        super().__init__(parent)
        self.tasks = tasks
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
            result = smart_translate(text)
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

        self.setWindowTitle(f"일본어 검사 - {self.title}")
        self.resize(880, 680)
        self.setMinimumSize(640, 500)
        self.init_ui()
        self.apply_custom_styles()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # 상단 헤더
        header_layout = QHBoxLayout()
        header_title = QLabel(f"일본어 검출 항목  |  {self.title}")
        header_title.setObjectName("dictionaryTitle")
        header_layout.addWidget(header_title, 1)

        self.all_trans_btn = QPushButton("전체 번역")
        self.all_trans_btn.setObjectName("semiTransBtn")
        self.all_trans_btn.setFixedHeight(28)
        self.all_trans_btn.setToolTip("검출된 모든 항목을 최대 10개씩 동시 번역합니다.")
        self.all_trans_btn.clicked.connect(self.translate_all)
        header_layout.addWidget(self.all_trans_btn)

        count_lbl = QLabel(f"검출: {len(self.items)}개 블록")
        count_lbl.setObjectName("dictionaryCount")
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(count_lbl)
        layout.addLayout(header_layout)

        info_lbl = QLabel("일본어 잔존 문장입니다. [번역]을 누르면 스마트 번역이 실행되며, 직접 수정 후 [바꾸기]를 누르면 저장됩니다.")
        info_lbl.setObjectName("secondaryInfo")
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        # 진행 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 스크롤 영역
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

            # 청크 헤더 박스
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

            # 내용 행 위젯
            row_widget = QWidget()
            row_widget.setObjectName("Fs")
            row_widget.setStyleSheet("QWidget#Fs{background:transparent;}")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 1, 4, 1)
            row_layout.setSpacing(8)

            # 왼쪽: 원문 창
            orig_edit = AutoResizingTextEdit()
            orig_edit.setReadOnly(True)
            orig_edit.setPlainText(item.get('original_text', '').rstrip('\n'))
            orig_edit.viewport().setStyleSheet('background: transparent;')

            arrow_lbl = QLabel("→")
            arrow_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            arrow_lbl.setFixedWidth(16)
            arrow_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: rgba(255, 255, 255, 0.4);")

            # 오른쪽: 번역/수정 창
            replace_edit = AutoResizingTextEdit()
            replace_edit.setPlainText(item.get('original_text', '').rstrip('\n'))
            replace_edit.viewport().setStyleSheet('background: transparent;')

            # 개별 번역 버튼
            single_btn = QPushButton("번역")
            single_btn.setObjectName("semiTransBtn")
            single_btn.setFixedWidth(48)
            single_btn.clicked.connect(lambda chk=False, i=idx: self.translate_single(i))

            # 세로 높이 동기화
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

        # 하단 버튼
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

        self.translate_worker = JapaneseTranslateWorker(tasks, self)
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