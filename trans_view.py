from PySide6.QtWidgets import (QVBoxLayout,
                            QHBoxLayout, QLineEdit, QPushButton, QLabel,
                            QFileDialog, QDialog, QMessageBox, QTextEdit,
                            QComboBox, QProgressBar)
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtCore import Qt
import html
import os
import json

from data import open_folder

from thread_pyqt import TranslateThread, ModelLoadThread, trans_ai

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

class TranslateDialog(QDialog):
    SETTINGS_FILE = "./data.json"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = ""
        self.thread = None
        self.model_load_thread = None

        self.setWindowTitle("AI 번역")
        self.resize(640, 800)
        self.setMinimumSize(640, 800)
        self.setFixedSize(640, 800)
        self.setAcceptDrops(True)

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

       
        self.drop_label = QLabel("TXT 또는 JSON 파일을 여기에 드래그하세요")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setObjectName("dropArea")
        self.drop_label.setMinimumHeight(90)
        layout.addWidget(self.drop_label)

       
        file_layout = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText("번역할 TXT 또는 JSON 파일 선택")
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
        self.model_combo.setPlaceholderText("Gemini 모델을 불러오세요")
        self.refresh_model_btn = QPushButton("새로고침")
        self.refresh_model_btn.setObjectName("secondaryBtn")
        self.refresh_model_btn.clicked.connect(self.load_gemini_models)
        model_layout.addWidget(self.model_combo, 1)
        model_layout.addWidget(self.refresh_model_btn)
        layout.addLayout(model_layout)
       
        label_width = 80 

       
        option_layout_1 = QHBoxLayout()
        
        lbl_rpm = QLabel("RPM")
        lbl_rpm.setFixedWidth(label_width)
        option_layout_1.addWidget(lbl_rpm)
        
        self.rpm_combo = QComboBox()
        self.rpm_combo.addItems(["5", "10", "15", "20", "30", "60"])
        self.rpm_combo.setCurrentText("15")
        option_layout_1.addWidget(self.rpm_combo)

       
        option_layout_1.addStretch(1)

        lbl_temp = QLabel("Temperature")
        lbl_temp.setFixedWidth(label_width)
        option_layout_1.addWidget(lbl_temp)
        
        self.temp_combo = QComboBox()
        self.temp_combo.addItems(["0.0", "0.1", "0.2", "0.3", "0.5", "0.7", "1.0"])
        self.temp_combo.setCurrentText("0.1")
        option_layout_1.addWidget(self.temp_combo)

       
        option_layout_2 = QHBoxLayout()
        
        lbl_conc = QLabel("동시 작업")
        lbl_conc.setFixedWidth(label_width)
        option_layout_2.addWidget(lbl_conc)
        
        self.concurrency_combo = QComboBox()
        self.concurrency_combo.addItems([str(i) for i in range(1, 16)])
        self.concurrency_combo.setCurrentText("4")
        option_layout_2.addWidget(self.concurrency_combo)

       
        option_layout_2.addStretch(1)

        lbl_chars = QLabel("청크 글자수")
        lbl_chars.setFixedWidth(label_width)
        option_layout_2.addWidget(lbl_chars)
        
        self.chars_combo = QComboBox()
        self.chars_combo.addItems(["2000", "3000", "4000", "5000", "7000", "10000"])
        self.chars_combo.setCurrentText("5000")
        option_layout_2.addWidget(self.chars_combo)

       
        layout.addLayout(option_layout_1)
        layout.addLayout(option_layout_2)

       
        api_layout = QHBoxLayout()
        self.api_edit = PasteOnlyLineEdit()
        self.api_edit.setPlaceholderText("Gemini API Key (붙여 넣기만 가능)")
        self.api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_show_btn = QPushButton("보기")
        self.api_show_btn.setObjectName("secondaryBtn")
        self.api_show_btn.setCheckable(True)
        self.api_show_btn.toggled.connect(self.toggle_api_visibility)
        save_api_btn = QPushButton("설정 저장")
        save_api_btn.setObjectName("secondaryBtn")
        save_api_btn.clicked.connect(self.save_settings)
        api_layout.addWidget(self.api_edit, 1)
        api_layout.addWidget(self.api_show_btn)
        api_layout.addWidget(save_api_btn)
        layout.addLayout(api_layout)

       
        self.status_label = QLabel("파일을 선택하세요.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self.log_filter_combo.addItems(["전체", "일반", "경고", "오류"])
        self.log_filter_combo.currentTextChanged.connect(self.filter_logs)
        log_title.addWidget(self.log_filter_combo)

        clear_log_btn = QPushButton("로그 지우기")
        clear_log_btn.setObjectName("secondaryBtn")
        clear_log_btn.clicked.connect(self.clear_logs)
        log_title.addWidget(clear_log_btn)
        layout.addLayout(log_title)

       
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(180)
        self.log_edit.setPlaceholderText("번역 로그가 여기에 표시됩니다.")
        layout.addWidget(self.log_edit, 1)

       
        self.log_history = []

       
        self.start_btn = QPushButton("번역 시작")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedHeight(42)
        self.start_btn.clicked.connect(self.start_translate)
        layout.addWidget(self.start_btn)

    def load_gemini_models(self):
        api = self.api_edit.text().strip()
        if not api:
            QMessageBox.warning(self, "알림", "Gemini API 키를 먼저 입력하세요.")
            return

        self.refresh_model_btn.setEnabled(False)
        self.status_label.setText("Gemini 모델 목록을 불러오는 중...")
        
       
        self.model_load_thread = ModelLoadThread(api)
        self.model_load_thread.finished.connect(self.on_models_loaded)
        self.model_load_thread.start()

    def on_models_loaded(self, model_names, error_msg):
        self.refresh_model_btn.setEnabled(True)
        
        if error_msg:
            self.add_log(f"모델 조회 실패: {error_msg}")
            QMessageBox.critical(self, "모델 조회 실패", error_msg)
            return

        current_model = self.model_combo.currentText()
        self.model_combo.clear()
        self.model_combo.addItems(model_names)

        index = self.model_combo.findText(current_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        elif model_names:
            self.model_combo.setCurrentIndex(0)

        if model_names:
            self.add_log(f"텍스트 생성이 가능한 Gemini 모델 {len(model_names)}개를 불러왔습니다.")
            self.status_label.setText("Gemini 모델 목록을 불러왔습니다.")
        else:
            self.add_log("사용 가능한 Gemini 텍스트 모델을 찾지 못했습니다.")
            self.status_label.setText("사용 가능한 모델이 없습니다.")

    def load_settings(self):
        data = {}
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                self.add_log(f"설정 불러오기 실패: {e}")

        api = data.get("api", "")
        model_name = data.get("translate_model", "")
        rpm = str(data.get("translate_rpm", 15))
        temperature = str(data.get("translate_temperature", 0.1))
        concurrency = str(data.get("translate_concurrency", 4))
        max_chars = str(data.get("translate_max_chars", 5000))

        self.api_edit.setText(api)
        def set_api(api):
            trans_ai.set_api_key(api)
            self.load_gemini_models()
            
        self.api_edit.textChanged.connect(set_api)

        if model_name:
            self.model_combo.addItem(model_name)
            self.model_combo.setCurrentText(model_name)

        if api:
            try:
                self.load_gemini_models()
            except Exception as e:
                self.add_log(f"자동 모델 조회 실패: {e}")

        for combo, val in [(self.rpm_combo, rpm), (self.temp_combo, temperature),
                           (self.concurrency_combo, concurrency), (self.chars_combo, max_chars)]:
            if combo.findText(val) < 0:
                combo.addItem(val)
            combo.setCurrentText(val)

        self.add_log("저장된 번역 설정을 불러왔습니다.")

    def save_settings(self):
        api = self.api_edit.text().strip()
        model_name = self.model_combo.currentText().strip()

        if not api or not model_name:
            QMessageBox.warning(self, "알림", "API 키와 Gemini 모델을 확인하세요.")
            return

        try:
            data = {}
            if os.path.exists(self.SETTINGS_FILE):
                try:
                    with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}

            data.update({
                "api": api,
                "translate_model": model_name,
                "translate_rpm": int(self.rpm_combo.currentText()),
                "translate_temperature": float(self.temp_combo.currentText()),
                "translate_concurrency": int(self.concurrency_combo.currentText()),
                "translate_max_chars": int(self.chars_combo.currentText())
            })

            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            self.add_log("번역 설정이 data.json에 저장되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", str(e))

    def toggle_api_visibility(self, checked):
        if checked:
            self.api_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.api_show_btn.setText("숨기기")
        else:
            self.api_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.api_show_btn.setText("보기")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            if event.mimeData().urls()[0].toLocalFile().lower().endswith((".txt", ".json")):
                event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.set_file(urls[0].toLocalFile())

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "번역할 파일 선택", OUT, "지원 파일 (*.txt *.json)")
        if path:
            self.set_file(path)

    def set_file(self, path):
        if not path.lower().endswith((".txt", ".json")):
            QMessageBox.warning(self, "알림", "TXT 또는 JSON 파일만 선택할 수 있습니다.")
            return

        self.file_path = path
        self.file_edit.setText(path)
        kind = "JSON 복원/재번역" if path.lower().endswith(".json") else "TXT 전체 번역"
        
        self.drop_label.setText(f"선택됨: {os.path.basename(path)}")
        self.status_label.setText(kind)
        self.add_log(f"파일 선택: {path}")
        self.add_log(f"작업 방식: {kind}")

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
        self.add_log("=" * 60)

        self.thread = TranslateThread(
            self.file_path,
            model_name,
            rpm,
            temperature,
            max_concurrent,
            max_chars
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
        percent = int(done * 100 / max(total, 1))
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def add_log(self, text):
        if not text:
            return

       
        log_type = "NORMAL"
        color = "#e0e0e0" 

        if "오류" in text or "실패" in text or "예외 발생" in text or "error" in text.lower():
            log_type = "ERROR"
            color = "#ff5555" 
        elif "경고" in text or "재시도" in text or "불일치" in text or "미설정" in text:
            log_type = "WARN"
            color = "#ffb86c" 
        elif "성공" in text or "완료" in text or "통과" in text:
            log_type = "SUCCESS"
            color = "#50fa7b" 
        elif "시작" in text or "로드" in text or "감지" in text:
            log_type = "INFO"
            color = "#8be9fd" 

       
        safe_text = html.escape(str(text)).replace("\n", "<br>")
        formatted_html = f'<span style="color: {color}; font-family: Consolas, monospace;">{safe_text}</span>'

       
        self.log_history.append((log_type, formatted_html))

       
        current_filter = self.log_filter_combo.currentText()
        if self._matches_filter(log_type, current_filter):
            self.log_edit.append(formatted_html)

    def _matches_filter(self, log_type, filter_text):
        if filter_text == "전체":
            return True
        elif filter_text == "일반" and log_type in ["NORMAL", "INFO", "SUCCESS"]:
            return True
        elif filter_text == "경고" and log_type == "WARN":
            return True
        elif filter_text == "오류" and log_type == "ERROR":
            return True
        return False

    def filter_logs(self, filter_text):
        self.log_edit.clear()
        for log_type, formatted_html in self.log_history:
            if self._matches_filter(log_type, filter_text):
                self.log_edit.append(formatted_html)

    def clear_logs(self):
        self.log_history.clear()
        self.log_edit.clear()

    def on_finished(self, success, message, output_dir):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("번역 시작")
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText(message)
            self.add_log("\n번역이 정상적으로 완료되었습니다.")
            QMessageBox.information(self, "번역 완료", message)
            if output_dir:
                open_folder(output_dir)
        else:
            self.status_label.setText("번역 실패")
            self.add_log(f"번역 실패: {message}")
            QMessageBox.critical(self, "번역 오류", message)