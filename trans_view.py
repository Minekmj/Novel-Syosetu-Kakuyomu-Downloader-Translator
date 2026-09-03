from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QFileDialog, QDialog, QMessageBox, QTextEdit, QComboBox,
    QProgressBar, QSpinBox, QScrollArea, QWidget
)
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtCore import Qt


import html
import os
import json

import re

from data import open_folder, return_theme, load_data, save_data
from thread_pyqt import TranslateThread, ModelLoadThread, trans_ai, GlossaryExtractThread

OUT = "./out/"


class PasteOnlyLineEdit(QLineEdit):
    def keyPressEvent(self, event: QKeyEvent):
        if (
            event.matches(QKeySequence.StandardKey.Paste)
            or event.matches(QKeySequence.StandardKey.Copy)
            or event.matches(QKeySequence.StandardKey.SelectAll)
        ):
            super().keyPressEvent(event)
        else:
            event.ignore()
            
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

        info = QLabel(
            "전체 원문을 분석하여 일본어 → 한국어 용어집을 자동으로 추출합니다."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        percent_layout = QHBoxLayout()
        percent_label = QLabel("분석 비율")
        percent_label.setFixedWidth(100)

        self.percent_spin = QSpinBox()
        self.percent_spin.setRange(1, 100)
        self.percent_spin.setValue(20)
        self.percent_spin.setSuffix("%")

        percent_layout.addWidget(percent_label)
        percent_layout.addWidget(self.percent_spin, 1)
        layout.addLayout(percent_layout)

        chunk_layout = QHBoxLayout()
        chunk_label = QLabel("청크 글자수")
        chunk_label.setFixedWidth(100)

        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(500, 50000)
        self.chunk_spin.setSingleStep(500)
        self.chunk_spin.setValue(5000)
        self.chunk_spin.setSuffix("자")

        chunk_layout.addWidget(chunk_label)
        chunk_layout.addWidget(self.chunk_spin, 1)
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
            self.percent_spin.value(),
            self.chunk_spin.value()
        )

class DictionaryDialog(QDialog):
    def __init__(self, parent=None, title="", dictionary=None):
        super().__init__(parent)

        self.title = title
        self.dictionary = dictionary if isinstance(dictionary, dict) else {}
        self.rows = []

        self.setWindowTitle("용어집 설정")
        self.resize(620, 560)
        self.setMinimumSize(500, 450)
        self.setObjectName("dictionaryDialog")

        self.init_ui()
        self.load_dictionary()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title_label = QLabel(f"용어집  |  {self.title}")
        title_label.setObjectName("dictionaryTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("dictionaryScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.container = QWidget()
        self.container.setObjectName("dictionaryContainer")

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(2, 2, 2, 2)
        self.container_layout.setSpacing(7)
        self.container_layout.addStretch()

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)

        add_btn = QPushButton("+ 용어 추가")
        add_btn.setObjectName("dictionaryAdd")
        
        def add():
            self.add_row("","")
        add_btn.clicked.connect(add)
        layout.addWidget(add_btn)

        ai_add_btn = QPushButton("AI 용어집 추가")
        ai_add_btn.setObjectName("dictionaryAdd")
        ai_add_btn.clicked.connect(self.open_ai_glossary_dialog)
        layout.addWidget(ai_add_btn)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        cancel_btn = QPushButton("취소")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setFixedHeight(40)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("저장")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.save_dictionary)

        bottom_layout.addWidget(cancel_btn)
        bottom_layout.addWidget(save_btn)
        layout.addLayout(bottom_layout)

    def load_dictionary(self):
        for src, dst in self.dictionary.items():
            self.add_row(src, dst)

    def add_row(self, src="", dst=""):
        row_widget = QWidget()
        row_widget.setObjectName("dictionaryItem")

        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(10, 4, 6, 4)
        row_layout.setSpacing(4)

        source_edit = QLineEdit()
        source_edit.setObjectName("dictionarySource")
        source_edit.setPlaceholderText("일본어")
        source_edit.setText(str(src))

        arrow = QLabel("→")
        arrow.setObjectName("dictionaryArrow")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)

        target_edit = QLineEdit()
        target_edit.setObjectName("dictionaryTarget")
        target_edit.setPlaceholderText("한국어")
        target_edit.setText(str(dst))

        remove_btn = QPushButton("×")
        remove_btn.setObjectName("dictionaryRemove")
        remove_btn.setFixedSize(30, 30)
        remove_btn.clicked.connect(
            lambda checked=False, widget=row_widget: self.remove_row(widget)
        )

        row_layout.addWidget(source_edit, 1)
        row_layout.addWidget(arrow)
        row_layout.addWidget(target_edit, 1)
        row_layout.addWidget(remove_btn)

        self.container_layout.insertWidget(
            self.container_layout.count() - 1,
            row_widget
        )

        self.rows.append((row_widget, source_edit, target_edit))

        if not src and not dst:
            source_edit.setFocus()
            
    def read_source_text(self):
        parent = self.parent()

        if parent is None:
            return ""

        path = getattr(parent, "file_path", "")

        if not path or not os.path.exists(path):
            return ""

        try:
            if path.lower().endswith(".txt"):
                with open(
                    path,
                    "r",
                    encoding="utf-8-sig"
                ) as f:
                    return f.read()

            if path.lower().endswith(".json"):
                with open(
                    path,
                    "r",
                    encoding="utf-8"
                ) as f:
                    data = json.load(f)

                return self.extract_json_source_text(data)

        except Exception as e:
            if hasattr(parent, "add_log"):
                parent.add_log(
                    f"AI 용어집 원문 읽기 실패: {e}"
                )

        return ""

    def extract_json_source_text(self, data):
        texts = []

        source_keys = {
            "original",
            "source",
            "japanese",
            "jp",
            "raw",
            "raw_text",
            "source_text",
            "original_text",
            "text"
        }

        def walk(value, key_name=""):
            if isinstance(value, dict):
                for key, child in value.items():
                    key_lower = str(key).lower()

                    if (
                        key_lower in source_keys
                        and isinstance(child, str)
                    ):
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
            return "\n".join(texts)

        return ""

    def remove_row(self, widget):
        for index, row in enumerate(self.rows):
            if row[0] is widget:
                self.rows.pop(index)
                widget.deleteLater()
                return

    def save_dictionary(self):
        result = {}

        for widget, source_edit, target_edit in self.rows:
            source = source_edit.text().strip()
            target = target_edit.text().strip()

            if not source and not target:
                continue

            if source and not target:
                QMessageBox.warning(
                    self,
                    "알림",
                    f"'{source}'의 한국어 번역을 입력하세요."
                )
                source_edit.setFocus()
                return

            if not source:
                QMessageBox.warning(
                    self,
                    "알림",
                    "일본어 용어를 입력하세요."
                )
                source_edit.setFocus()
                return

            result[source] = target

        self.dictionary = result
        self.accept()
        
    def open_ai_glossary_dialog(self):
        all_text = self.read_source_text()

        if not all_text.strip():
            QMessageBox.warning(
                self,
                "알림",
                "분석할 원문을 찾을 수 없습니다."
            )
            return

        dialog = GlossaryAiDialog(self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        paserent, chunk = dialog.get_values()

        self.ai_glossary_thread = GlossaryExtractThread(
            all_text,
            paserent,
            chunk,
            self
        )

        self.ai_glossary_thread.log_signal.connect(
            self.on_ai_glossary_log
        )

        self.ai_glossary_thread.finished_signal.connect(
            self.on_ai_glossary_finished
        )

        self.ai_glossary_thread.start()
        
    def on_ai_glossary_log(self, text):
        parent = self.parent()

        if parent is not None and hasattr(parent, "add_log"):
            parent.add_log(
                f"[AI 용어집] {text}"
            )
            
    def on_ai_glossary_finished(self, glossary, error):
        if error:
            parent = self.parent()

            if parent is not None and hasattr(parent, "add_log"):
                parent.add_log(
                    f"[AI 용어집] 추출 실패: {error}"
                )

            QMessageBox.critical(
                self,
                "AI 용어집 오류",
                error
            )
            return

        if not glossary:
            parent = self.parent()

            if parent is not None and hasattr(parent, "add_log"):
                parent.add_log(
                    "[AI 용어집] 추출된 용어가 없습니다."
                )

            QMessageBox.information(
                self,
                "AI 용어집",
                "추출된 용어가 없습니다."
            )
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

        if parent is not None and hasattr(parent, "add_log"):
            parent.add_log(
                f"[AI 용어집] 추출 완료: "
                f"{len(glossary)}개 / "
                f"추가: {added}개 / "
                f"기존 용어: {skipped}개"
            )

        QMessageBox.information(
            self,
            "AI 용어집 완료",
            f"AI 용어집 추출이 완료되었습니다.\n\n"
            f"추출: {len(glossary)}개\n"
            f"새로 추가: {added}개\n"
            f"기존 용어: {skipped}개"
        )

class TranslateDialog(QDialog):
    SETTINGS_FILE = "./data.json"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.file_path = ""
        self.file_title = ""
        self.current_dictionary = {}

        self.thread = None
        self.model_load_thread = None

        self.setWindowTitle("AI 번역")
        self.resize(640, 800)
        self.setMinimumSize(450, 730)
        self.setAcceptDrops(True)

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.drop_label = QLabel(
            "TXT 또는 JSON 파일을 여기에 드래그하세요"
        )
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setObjectName("dropArea")
        self.drop_label.setMinimumHeight(90)
        layout.addWidget(self.drop_label)

        file_layout = QHBoxLayout()

        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText(
            "번역할 TXT 또는 JSON 파일 선택"
        )

        browse_btn = QPushButton("파일 찾기")
        browse_btn.setObjectName("secondaryBtn")
        browse_btn.clicked.connect(self.browse_file)

        file_layout.addWidget(self.file_edit, 1)
        file_layout.addWidget(browse_btn)

        layout.addLayout(file_layout)

        model_layout = QHBoxLayout()

        model_layout.addWidget(QLabel("모델"))

        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(250)
        self.model_combo.setPlaceholderText(
            "Gemini 모델을 불러오세요"
        )

        self.refresh_model_btn = QPushButton("새로고침")
        self.refresh_model_btn.setObjectName("secondaryBtn")
        self.refresh_model_btn.clicked.connect(
            self.load_gemini_models
        )

        model_layout.addWidget(self.model_combo, 1)
        model_layout.addWidget(self.refresh_model_btn)

        layout.addLayout(model_layout)

        label_width = 80

        option_layout_1 = QHBoxLayout()

        lbl_rpm = QLabel("RPM")
        lbl_rpm.setFixedWidth(label_width)
        option_layout_1.addWidget(lbl_rpm)

        self.rpm_combo = QComboBox()
        self.rpm_combo.addItems(
            ["5", "10", "15", "20", "30", "60"]
        )
        self.rpm_combo.setCurrentText("15")

        option_layout_1.addWidget(self.rpm_combo)
        option_layout_1.addStretch(1)

        lbl_temp = QLabel("Temperature")
        lbl_temp.setFixedWidth(label_width)
        option_layout_1.addWidget(lbl_temp)

        self.temp_combo = QComboBox()
        self.temp_combo.addItems(
            ["0.0", "0.1", "0.2", "0.3", "0.5", "0.7", "1.0"]
        )
        self.temp_combo.setCurrentText("0.1")

        option_layout_1.addWidget(self.temp_combo)

        option_layout_2 = QHBoxLayout()

        lbl_conc = QLabel("동시 작업")
        lbl_conc.setFixedWidth(label_width)
        option_layout_2.addWidget(lbl_conc)

        self.concurrency_combo = QComboBox()
        self.concurrency_combo.addItems(
            [str(i) for i in range(1, 16)]
        )
        self.concurrency_combo.setCurrentText("4")

        option_layout_2.addWidget(self.concurrency_combo)
        option_layout_2.addStretch(1)

        lbl_chars = QLabel("청크 글자수")
        lbl_chars.setFixedWidth(label_width)
        option_layout_2.addWidget(lbl_chars)

        self.chars_combo = QComboBox()
        self.chars_combo.addItems(
            ["2000", "3000", "4000", "5000", "7000", "10000"]
        )
        self.chars_combo.setCurrentText("5000")

        option_layout_2.addWidget(self.chars_combo)

        layout.addLayout(option_layout_1)
        layout.addLayout(option_layout_2)

        api_layout = QHBoxLayout()

        self.api_edit = PasteOnlyLineEdit()
        self.api_edit.setPlaceholderText(
            "Gemini API Key (붙여 넣기만 가능)"
        )
        self.api_edit.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        self.api_show_btn = QPushButton("보기")
        self.api_show_btn.setObjectName("secondaryBtn")
        self.api_show_btn.setCheckable(True)
        self.api_show_btn.toggled.connect(
            self.toggle_api_visibility
        )

        save_api_btn = QPushButton("설정 저장")
        save_api_btn.setObjectName("secondaryBtn")
        save_api_btn.clicked.connect(self.save_settings)

        api_layout.addWidget(self.api_edit, 1)
        api_layout.addWidget(self.api_show_btn)
        api_layout.addWidget(save_api_btn)

        layout.addLayout(api_layout)

        # 용어집 영역
        dictionary_layout = QHBoxLayout()

        self.dictionary_status = QLabel("용어집: 선택된 작품 없음")
        self.dictionary_status.setWordWrap(True)

        self.dictionary_btn = QPushButton("용어집 설정")
        self.dictionary_btn.setObjectName("secondaryBtn")
        self.dictionary_btn.clicked.connect(
            self.open_dictionary_dialog
        )

        dictionary_layout.addWidget(
            self.dictionary_status, 1
        )
        dictionary_layout.addWidget(
            self.dictionary_btn
        )

        layout.addLayout(dictionary_layout)

        self.status_label = QLabel("파일을 선택하세요.")
        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        layout.addWidget(self.progress_bar)

        log_title = QHBoxLayout()

        log_title.addWidget(QLabel("번역 로그"))
        log_title.addStretch()

        log_title.addWidget(QLabel("필터:"))

        self.log_filter_combo = QComboBox()
        self.log_filter_combo.addItems(
            ["전체", "일반", "경고", "오류"]
        )
        self.log_filter_combo.currentTextChanged.connect(
            self.filter_logs
        )

        log_title.addWidget(
            self.log_filter_combo
        )

        clear_log_btn = QPushButton("로그 지우기")
        clear_log_btn.setObjectName("secondaryBtn")
        clear_log_btn.clicked.connect(
            self.clear_logs
        )

        log_title.addWidget(clear_log_btn)

        layout.addLayout(log_title)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(180)
        self.log_edit.setPlaceholderText(
            "번역 로그가 여기에 표시됩니다."
        )
        self.log_edit.setObjectName(
            "detail_description"
        )
        self.log_edit.viewport().setStyleSheet(
            "background: transparent;"
        )

        layout.addWidget(
            self.log_edit, 1
        )

        self.log_history = []

        self.start_btn = QPushButton("번역 시작")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedHeight(42)
        self.start_btn.clicked.connect(
            self.start_translate
        )

        layout.addWidget(self.start_btn)

    def load_gemini_models(self):
        api = self.api_edit.text().strip()

        if not api:
            QMessageBox.warning(
                self,
                "알림",
                "Gemini API 키를 먼저 입력하세요."
            )
            return

        self.refresh_model_btn.setEnabled(False)
        self.status_label.setText(
            "Gemini 모델 목록을 불러오는 중..."
        )

        self.model_load_thread = ModelLoadThread(api)
        self.model_load_thread.finished.connect(
            self.on_models_loaded
        )
        self.model_load_thread.start()

    def on_models_loaded(self, model_names, error_msg):
        self.refresh_model_btn.setEnabled(True)

        if error_msg:
            self.add_log(
                f"모델 조회 실패: {error_msg}"
            )
            QMessageBox.critical(
                self,
                "모델 조회 실패",
                error_msg
            )
            return

        current_model = self.model_combo.currentText()

        self.model_combo.clear()
        self.model_combo.addItems(model_names)

        index = self.model_combo.findText(
            current_model
        )

        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        elif model_names:
            self.model_combo.setCurrentIndex(0)

        if model_names:
            self.add_log(
                f"텍스트 생성이 가능한 Gemini 모델 "
                f"{len(model_names)}개를 불러왔습니다."
            )
            self.status_label.setText(
                "Gemini 모델 목록을 불러왔습니다."
            )
        else:
            self.add_log(
                "사용 가능한 Gemini 텍스트 모델을 찾지 못했습니다."
            )
            self.status_label.setText(
                "사용 가능한 모델이 없습니다."
            )

    def load_settings(self):
        data = {}

        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(
                    self.SETTINGS_FILE,
                    "r",
                    encoding="utf-8"
                ) as f:
                    data = json.load(f)
            except Exception as e:
                self.add_log(
                    f"설정 불러오기 실패: {e}"
                )

        api = data.get("api", "")
        model_name = data.get(
            "translate_model", ""
        )
        rpm = str(
            data.get("translate_rpm", 15)
        )
        temperature = str(
            data.get("translate_temperature", 0.1)
        )
        concurrency = str(
            data.get("translate_concurrency", 4)
        )
        max_chars = str(
            data.get("translate_max_chars", 5000)
        )

        self.api_edit.setText(api)

        def set_api(api):
            trans_ai.set_api_key(api)

        self.api_edit.textChanged.connect(
            set_api
        )

        if model_name:
            self.model_combo.addItem(model_name)
            self.model_combo.setCurrentText(
                model_name
            )

        if api:
            try:
                self.load_gemini_models()
            except Exception as e:
                self.add_log(
                    f"자동 모델 조회 실패: {e}"
                )

        for combo, val in [
            (self.rpm_combo, rpm),
            (self.temp_combo, temperature),
            (self.concurrency_combo, concurrency),
            (self.chars_combo, max_chars)
        ]:
            if combo.findText(val) < 0:
                combo.addItem(val)

            combo.setCurrentText(val)

        self.add_log(
            "저장된 번역 설정을 불러왔습니다."
        )

    def save_settings(self):
        api = self.api_edit.text().strip()
        model_name = self.model_combo.currentText().strip()

        if not api or not model_name:
            QMessageBox.warning(
                self,
                "알림",
                "API 키와 Gemini 모델을 확인하세요."
            )
            return

        try:
            data = {}

            if os.path.exists(
                self.SETTINGS_FILE
            ):
                try:
                    with open(
                        self.SETTINGS_FILE,
                        "r",
                        encoding="utf-8"
                    ) as f:
                        data = json.load(f)
                except Exception:
                    data = {}

            data.update({
                "api": api,
                "translate_model": model_name,
                "translate_rpm": int(
                    self.rpm_combo.currentText()
                ),
                "translate_temperature": float(
                    self.temp_combo.currentText()
                ),
                "translate_concurrency": int(
                    self.concurrency_combo.currentText()
                ),
                "translate_max_chars": int(
                    self.chars_combo.currentText()
                )
            })

            # dictionary가 없으면 생성
            if not isinstance(
                data.get("dictionary"),
                dict
            ):
                data["dictionary"] = {}

            with open(
                self.SETTINGS_FILE,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    data,
                    f,
                    ensure_ascii=False,
                    indent=4
                )

            self.add_log(
                "번역 설정이 data.json에 저장되었습니다."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "오류",
                str(e)
            )

    def toggle_api_visibility(self, checked):
        if checked:
            self.api_edit.setEchoMode(
                QLineEdit.EchoMode.Normal
            )
            self.api_show_btn.setText("숨기기")
        else:
            self.api_edit.setEchoMode(
                QLineEdit.EchoMode.Password
            )
            self.api_show_btn.setText("보기")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            if event.mimeData().urls()[0].toLocalFile().lower().endswith(
                (".txt", ".json")
            ):
                event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()

        if urls:
            self.set_file(
                urls[0].toLocalFile()
            )

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "번역할 파일 선택",
            OUT,
            "지원 파일 (*.txt *.json)"
        )

        if path:
            self.set_file(path)

    def extract_title(self, path):
        try:
            if path.lower().endswith(".txt"):
                with open(
                    path,
                    "r",
                    encoding="utf-8-sig"
                ) as f:
                    first_line = f.readline().strip()

                return first_line

            if path.lower().endswith(".json"):
                with open(
                    path,
                    "r",
                    encoding="utf-8"
                ) as f:
                    data = json.load(f)

                if isinstance(data, dict):
                    for key in [
                        "title",
                        "name",
                        "novel_title",
                        "work_title"
                    ]:
                        value = data.get(key)

                        if not isinstance(value, str):
                            continue

                        value = value.strip()

                        if not value:
                            continue

                        # -----------------------------
                        # 뒤에서부터 _복원 제거
                        # -----------------------------
                        while value.endswith("_복원"):
                            value = value[:-len("_복원")].rstrip()

                        # -----------------------------
                        # 뒤에서부터 _숫자 ~ 숫자 제거
                        #
                        # 예:
                        # _1 ~ 5
                        # _10~20
                        # _001 ~ 005
                        # -----------------------------
                        match = re.search(
                            r"_\d+\s*~\s*\d+$",
                            value
                        )

                        if match:
                            value = value[:match.start()].rstrip()

                        return value

        except Exception as e:
            self.add_log(
                f"작품명 추출 실패: {e}"
            )

        return ""

    def load_dictionary_for_title(self):
        data = load_data()

        dictionary = data.get(
            "dictionary",
            {}
        )

        if not isinstance(dictionary, dict):
            dictionary = {}

        self.current_dictionary = dictionary.get(
            self.file_title,
            {}
        )

        if not isinstance(
            self.current_dictionary,
            dict
        ):
            self.current_dictionary = {}

        if self.file_title:
            if self.current_dictionary:
                self.dictionary_status.setText(
                    f"용어집: {self.file_title} "
                    f"({len(self.current_dictionary)}개)"
                )
            else:
                self.dictionary_status.setText(
                    f"용어집: {self.file_title} "
                    "(등록된 용어 없음)"
                )
        else:
            self.dictionary_status.setText(
                "용어집: 작품명을 찾을 수 없습니다."
            )

    def open_dictionary_dialog(self):
        if not self.file_title:
            QMessageBox.warning(
                self,
                "알림",
                "먼저 번역할 파일을 선택하세요.\n"
                "TXT 파일은 첫 줄을 작품명으로 사용합니다."
            )
            return

        dialog = DictionaryDialog(
            self,
            self.file_title,
            self.current_dictionary
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.current_dictionary = dict(
            dialog.dictionary
        )

        data = load_data()

        if not isinstance(
            data.get("dictionary"),
            dict
        ):
            data["dictionary"] = {}

        data["dictionary"][
            self.file_title
        ] = self.current_dictionary

        save_data(data)

        self.dictionary_status.setText(
            f"용어집: {self.file_title} "
            f"({len(self.current_dictionary)}개)"
        )

        self.add_log(
            f"용어집 저장 완료: "
            f"{self.file_title} "
            f"({len(self.current_dictionary)}개)"
        )

    def set_file(self, path):
        if not path.lower().endswith(
            (".txt", ".json")
        ):
            QMessageBox.warning(
                self,
                "알림",
                "TXT 또는 JSON 파일만 선택할 수 있습니다."
            )
            return

        self.file_path = path
        self.file_edit.setText(path)

        kind = (
            "JSON 복원/재번역"
            if path.lower().endswith(".json")
            else "TXT 전체 번역"
        )

        self.file_title = self.extract_title(
            path
        )

        self.drop_label.setText(
            f"선택됨: {os.path.basename(path)}"
        )

        if self.file_title:
            self.status_label.setText(
                f"{kind} / 작품: {self.file_title}"
            )
        else:
            self.status_label.setText(
                kind
            )

        self.add_log(
            f"파일 선택: {path}"
        )

        self.add_log(
            f"작업 방식: {kind}"
        )

        if self.file_title:
            self.add_log(
                f"작품명 감지: {self.file_title}"
            )
        else:
            self.add_log(
                "작품명을 찾지 못했습니다."
            )

        # 작품명을 기준으로 용어집 자동 선택
        self.load_dictionary_for_title()

        if self.current_dictionary:
            self.add_log(
                f"용어집 자동 선택: "
                f"{len(self.current_dictionary)}개"
            )
        else:
            self.add_log(
                "해당 작품에 등록된 용어집이 없습니다."
            )

    def start_translate(self):
        if not self.file_path:
            QMessageBox.warning(
                self,
                "알림",
                "TXT 또는 JSON 파일을 선택하세요."
            )
            return

        api = self.api_edit.text().strip()
        model_name = self.model_combo.currentText()

        if not api:
            QMessageBox.warning(
                self,
                "알림",
                "Gemini API 키를 먼저 설정하세요."
            )
            return

        if not model_name:
            QMessageBox.warning(
                self,
                "알림",
                "모델 이름을 입력하세요."
            )
            return

        try:
            rpm = int(
                self.rpm_combo.currentText()
            )

            temperature = float(
                self.temp_combo.currentText()
            )

            max_concurrent = int(
                self.concurrency_combo.currentText()
            )

            max_chars = int(
                self.chars_combo.currentText()
            )

        except ValueError:
            QMessageBox.warning(
                self,
                "알림",
                "설정 값이 올바르지 않습니다."
            )
            return

        try:
            self.save_settings()
        except Exception as e:
            QMessageBox.critical(
                self,
                "오류",
                str(e)
            )
            return

        # 현재 작품의 용어집
        dict_data = dict(
            self.current_dictionary
        )

        self.start_btn.setEnabled(False)
        self.start_btn.setText("번역 중...")

        self.progress_bar.setValue(0)

        self.add_log("")
        self.add_log("=" * 60)
        self.add_log("번역 시작")
        self.add_log(
            f"모델: {model_name}"
        )
        self.add_log(
            f"작품명: {self.file_title}"
        )
        self.add_log(
            f"청크 글자수: {max_chars}"
        )
        self.add_log(
            f"RPM: {rpm}"
        )
        self.add_log(
            f"Temperature: {temperature}"
        )
        self.add_log(
            f"동시 작업수: {max_concurrent}"
        )
        self.add_log(
            f"용어집: {len(dict_data)}개"
        )
        self.add_log("=" * 60)

        self.thread = TranslateThread(
            self.file_path,
            model_name,
            rpm,
            temperature,
            max_concurrent,
            max_chars,
            dicts=dict_data
        )

        self.thread.progress_changed.connect(
            self.update_progress
        )

        self.thread.log_changed.connect(
            self.add_log
        )

        self.thread.finished_signal.connect(
            self.on_finished
        )

        self.thread.start()

    def update_progress(self, done, total, message):
        percent = int(
            done * 100 / max(total, 1)
        )

        self.progress_bar.setValue(
            percent
        )

        self.status_label.setText(
            message
        )

    def get_brightness(self, hex_color):
        hex_color = hex_color.lstrip("#")

        r = int(
            hex_color[0:2],
            16
        )
        g = int(
            hex_color[2:4],
            16
        )
        b = int(
            hex_color[4:6],
            16
        )

        return (
            r * 299 +
            g * 587 +
            b * 114
        ) / 1000

    def add_log(self, text):
        if not text:
            return

        text_i = text
        log_type = "NORMAL"

        if (
            "오류" in text
            or "실패" in text
            or "에러" in text
        ):
            log_type = "ERROR"
        elif "경고" in text:
            log_type = "WARN"
        elif (
            "성공" in text
            or "완료" in text
            or "통과" in text
        ):
            log_type = "SUCCESS"
        elif (
            "시작" in text
            or "로드" in text
            or "감지" in text
        ):
            log_type = "INFO"

        bg_color = return_theme()
        is_dark = (
            self.get_brightness(bg_color) < 128
        )

        color_map = {
            "DARK": {
                "NORMAL": "#e0e0e0",
                "ERROR": "#ff5555",
                "WARN": "#ffb86c",
                "SUCCESS": "#50fa7b",
                "INFO": "#8be9fd"
            },
            "LIGHT": {
                "NORMAL": "#222222",
                "ERROR": "#d32f2f",
                "WARN": "#e65100",
                "SUCCESS": "#2e7d32",
                "INFO": "#0288d1"
            }
        }

        mode = (
            "DARK"
            if is_dark
            else "LIGHT"
        )

        color = color_map[
            mode
        ][log_type]

        text = text_i

        safe_text = (
            html.escape(str(text))
            .replace("\n", "<br>")
        )

        formatted_html = (
            f'<span style="color: {color}; '
            f'font-family: Consolas, monospace;">'
            f'{safe_text}'
            f'</span>'
        )

        self.log_history.append(
            (
                log_type,
                formatted_html
            )
        )

        current_filter = (
            self.log_filter_combo.currentText()
        )

        if self._matches_filter(
            log_type,
            current_filter
        ):
            self.log_edit.append(
                formatted_html
            )

    def _matches_filter(
        self,
        log_type,
        filter_text
    ):
        if filter_text == "전체":
            return True

        elif (
            filter_text == "일반"
            and log_type in [
                "NORMAL",
                "INFO",
                "SUCCESS"
            ]
        ):
            return True

        elif (
            filter_text == "경고"
            and log_type == "WARN"
        ):
            return True

        elif (
            filter_text == "오류"
            and log_type == "ERROR"
        ):
            return True

        return False

    def filter_logs(self, filter_text):
        self.log_edit.clear()

        for log_type, formatted_html in self.log_history:
            if self._matches_filter(
                log_type,
                filter_text
            ):
                self.log_edit.append(
                    formatted_html
                )

    def clear_logs(self):
        self.log_history.clear()
        self.log_edit.clear()

    def on_finished(
        self,
        success,
        message,
        output_dir
    ):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("번역 시작")

        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText(
                message
            )

            self.add_log(
                "\n번역이 정상적으로 완료되었습니다."
            )

            QMessageBox.information(
                self,
                "번역 완료",
                message
            )

            if output_dir:
                open_folder(output_dir)

        else:
            self.status_label.setText(
                "번역 실패"
            )

            self.add_log(
                f"번역 실패: {message}"
            )

            QMessageBox.critical(
                self,
                "번역 오류",
                message
            )