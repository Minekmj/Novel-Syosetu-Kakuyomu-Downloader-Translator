from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QDialog, QMessageBox, QComboBox,QScrollArea, QWidget
)
from PySide6.QtCore import Qt

import os
import json

from src.main.thread_pyqt import GlossaryExtractThread

class GlossaryAiDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 용어집 추가")
        self.resize(420, 260)
        self.setMinimumSize(380, 230)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("AI 용어집 자동 추출")
        title.setObjectName("dictionaryTitle")
        layout.addWidget(title)

        info = QLabel("전체 원문을 분석하여 일본어 → 한국어 용어집을 자동으로 추출합니다.")
        info.setWordWrap(True)
        layout.addWidget(info)

        percent_layout = QHBoxLayout()
        percent_label = QLabel("분석 비율")
        percent_label.setFixedWidth(100)

        self.percent_combo = QComboBox()
        for value in range(10, 101, 10):
            self.percent_combo.addItem(f"{value}%", value)
        self.percent_combo.setCurrentIndex(1)

        percent_layout.addWidget(percent_label)
        percent_layout.addWidget(self.percent_combo, 1)
        layout.addLayout(percent_layout)

        chunk_layout = QHBoxLayout()
        chunk_label = QLabel("청크 글자수")
        chunk_label.setFixedWidth(100)

        self.chunk_combo = QComboBox()
        for value in range(3000, 35001, 2000):
            self.chunk_combo.addItem(f"{value:,}자", value)

        if self.chunk_combo.itemData(self.chunk_combo.count() - 1) != 35000:
            self.chunk_combo.addItem("35,000자", 35000)

        self.chunk_combo.setCurrentIndex(1)

        chunk_layout.addWidget(chunk_label)
        chunk_layout.addWidget(self.chunk_combo, 1)
        layout.addLayout(chunk_layout)

        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        cancel_btn = QPushButton("취소")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setFixedHeight(40)
        cancel_btn.clicked.connect(self.reject)

        start_btn = QPushButton("AI 용어집 추출")
        start_btn.setObjectName("primaryBtn")
        start_btn.setFixedHeight(40)
        start_btn.clicked.connect(self.accept)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(start_btn)
        layout.addLayout(button_layout)

    def get_values(self):
        return (
            self.percent_combo.currentData(),
            self.chunk_combo.currentData()
        )


class DictionaryDialog(QDialog):
    def __init__(self, parent=None, title='', dictionary=None, model='gemini-3.5-flash-lite', rpm=5):
        super().__init__(parent)
        self.title = title
        self.dictionary = dictionary if isinstance(dictionary, dict) else {}
        self.rows = []
        self.model = model
        self.rpm = rpm
        self.setWindowTitle('용어집 설정')
        self.resize(620, 560)
        self.setMinimumSize(500, 450)
        self.setObjectName('dictionaryDialog')
        self.init_ui()
        self.load_dictionary()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        title_label = QLabel(f"용어집  |  {self.title}")
        title_label.setObjectName('dictionaryTitle')
        title_label.setWordWrap(True)
        header_layout.addWidget(title_label, 1)

        self.count_label = QLabel('0개')
        self.count_label.setObjectName('dictionaryCount')
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.count_label)

        layout.addLayout(header_layout)

        self.scroll = QScrollArea()
        self.scroll.setObjectName('dictionaryScroll')
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.container = QWidget()
        self.container.setObjectName('dictionaryContainer')
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(2, 4, 2, 4)
        self.container_layout.setSpacing(7)
        self.container_layout.addStretch()

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(7)

        add_btn = QPushButton('+ 용어 추가')
        add_btn.setObjectName('dictionaryAdd')
        add_btn.setMinimumHeight(36)
        add_btn.clicked.connect(lambda: self.add_row('', ''))

        ai_add_btn = QPushButton('AI 용어집 추가')
        ai_add_btn.setObjectName('dictionaryAdd')
        ai_add_btn.setMinimumHeight(36)
        ai_add_btn.clicked.connect(self.open_ai_glossary_dialog)

        clear_btn = QPushButton('전체 삭제')
        clear_btn.setObjectName('dictionaryAdd')
        clear_btn.setMinimumHeight(36)
        clear_btn.clicked.connect(self.clear_all_rows)

        action_layout.addWidget(add_btn, 1)
        action_layout.addWidget(ai_add_btn, 1)
        action_layout.addWidget(clear_btn, 1)
        layout.addLayout(action_layout)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        cancel_btn = QPushButton('취소')
        cancel_btn.setObjectName('secondaryBtn')
        cancel_btn.setFixedHeight(40)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton('저장')
        save_btn.setObjectName('primaryBtn')
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.save_dictionary)

        bottom_layout.addWidget(cancel_btn)
        bottom_layout.addWidget(save_btn)
        layout.addLayout(bottom_layout)

        self.update_count()

    def load_dictionary(self):
        for src, dst in self.dictionary.items():
            self.add_row(src, dst)

    def add_row(self, src='', dst=''):
        row_widget = QWidget()
        row_widget.setObjectName('dictionaryItem')

        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(10, 4, 6, 4)
        row_layout.setSpacing(4)

        source_edit = QLineEdit()
        source_edit.setObjectName('dictionarySource')
        source_edit.setPlaceholderText('일본어')
        source_edit.setText(str(src))

        arrow = QLabel('→')
        arrow.setObjectName('dictionaryArrow')
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)

        target_edit = QLineEdit()
        target_edit.setObjectName('dictionaryTarget')
        target_edit.setPlaceholderText('한국어')
        target_edit.setText(str(dst))

        remove_btn = QPushButton('×')
        remove_btn.setObjectName('dictionaryRemove')
        remove_btn.setFixedSize(30, 30)
        remove_btn.clicked.connect(lambda checked=False, widget=row_widget: self.remove_row(widget))

        row_layout.addWidget(source_edit, 1)
        row_layout.addWidget(arrow)
        row_layout.addWidget(target_edit, 1)
        row_layout.addWidget(remove_btn)

        self.container_layout.insertWidget(self.container_layout.count() - 1, row_widget)
        self.rows.append((row_widget, source_edit, target_edit))

        self.update_count()

        if not src and not dst:
            source_edit.setFocus()

    def remove_row(self, widget):
        for index, row in enumerate(self.rows):
            if row[0] is widget:
                self.rows.pop(index)
                widget.deleteLater()
                self.update_count()
                return

    def clear_all_rows(self):
        if not self.rows:
            return

        result = QMessageBox.question(
            self,
            '전체 삭제',
            f'현재 등록된 용어 {len(self.rows)}개를 모두 삭제하시겠습니까?\n\n이 작업은 저장하기 전까지 실제로 저장되지 않습니다.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        for widget, source_edit, target_edit in self.rows:
            widget.deleteLater()

        self.rows.clear()
        self.update_count()

    def update_count(self):
        count = len(self.rows)
        self.count_label.setText(f'{count}개')

    def read_source_text(self):
        parent = self.parent()
        if parent is None:
            return ''

        path = parent.file_path
        if not path or not os.path.exists(path):
            return ''

        try:
            if path.lower().endswith('.txt'):
                with open(path, 'r', encoding='utf-8-sig') as f:
                    return f.read()

            if path.lower().endswith('.json'):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return self.extract_json_source_text(data)

        except Exception as e:
            if hasattr(parent, 'add_log'):
                parent.add_log(f"AI 용어집 원문 읽기 실패: {e}")

        return ''

    def extract_json_source_text(self, data):
        texts = []
        source_keys = {'original', 'source', 'japanese', 'jp', 'raw', 'raw_text', 'source_text', 'original_text', 'text'}

        def walk(value, key_name=''):
            if isinstance(value, dict):
                for key, child in value.items():
                    key_lower = str(key).lower()

                    if key_lower in source_keys and isinstance(child, str):
                        if child.strip():
                            texts.append(child)

                    elif isinstance(child, (dict, list)):
                        walk(child, key_lower)

            elif isinstance(value, list):
                for child in value:
                    if isinstance(child, (dict, list)):
                        walk(child)

        walk(data)

        if texts:
            return '\n'.join(texts)

        return ''

    def save_dictionary(self):
        result = {}

        for widget, source_edit, target_edit in self.rows:
            source = source_edit.text().strip()
            target = target_edit.text().strip()

            if not source and not target:
                continue

            if source and not target:
                QMessageBox.warning(self, '알림', f"'{source}'의 한국어 번역을 입력하세요.")
                source_edit.setFocus()
                return

            if not source:
                QMessageBox.warning(self, '알림', '일본어 용어를 입력하세요.')
                source_edit.setFocus()
                return

            result[source] = target

        self.dictionary = result
        self.accept()

    def open_ai_glossary_dialog(self):
        all_text = self.read_source_text()

        if not all_text.strip():
            QMessageBox.warning(self, '알림', '분석할 원문을 찾을 수 없습니다.')
            return

        dialog = GlossaryAiDialog(self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        percent, chunk = dialog.get_values()

        self.ai_glossary_thread = GlossaryExtractThread(
            all_text,
            percent,
            chunk,
            self.model,
            self.rpm,
            self
        )

        self.ai_glossary_thread.log_signal.connect(self.on_ai_glossary_log)
        self.ai_glossary_thread.finished_signal.connect(self.on_ai_glossary_finished)
        self.ai_glossary_thread.start()

    def on_ai_glossary_log(self, text):
        parent = self.parent()

        if parent is not None and hasattr(parent, 'add_log'):
            parent.add_log(f"[AI 용어집] {text}")

    def on_ai_glossary_finished(self, glossary, error):
        if error:
            parent = self.parent()

            if parent is not None and hasattr(parent, 'add_log'):
                parent.add_log(f"[AI 용어집] 추출 실패: {error}")

            QMessageBox.critical(self, 'AI 용어집 오류', error)
            return

        if not glossary:
            parent = self.parent()

            if parent is not None and hasattr(parent, 'add_log'):
                parent.add_log('[AI 용어집] 추출된 용어가 없습니다.')

            QMessageBox.information(self, 'AI 용어집', '추출된 용어가 없습니다.')
            return

        added = 0
        skipped = 0

        for source, target in glossary.items():
            source = str(source).strip()
            target = str(target).strip()

            if not source or not target:
                continue

            if source in self.dictionary:
                skipped += 1
                continue

            self.dictionary[source] = target
            self.add_row(source, target)
            added += 1

        parent = self.parent()

        if parent is not None and hasattr(parent, 'add_log'):
            parent.add_log(f"[AI 용어집] 추출 완료: {len(glossary)}개 / 추가: {added}개 / 기존 용어: {skipped}개")

        QMessageBox.information(
            self,
            'AI 용어집 완료',
            f"AI 용어집 추출이 완료되었습니다.\n\n추출: {len(glossary)}개\n새로 추가: {added}개\n기존 용어: {skipped}개"
        )