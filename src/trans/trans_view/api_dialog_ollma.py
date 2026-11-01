import json
import os
import shutil
import subprocess
import requests
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QWidget, QLineEdit, QFrame, QMessageBox,
    QComboBox, QProgressBar
)
from src.system.load_save import load_data, save_data
from .ui_factory import create_layout, create_button, create_label
from src.ai import AiRoute, AiTarget

OLLAMA_DOWNLOAD_URL = "https://ollama.com/download"

VERIFIED_OLLAMA_MODELS = AiRoute.get_popular_models(AiTarget.OLLAMA)


class OllamaStatusCheckThread(QThread):
    status_checked = Signal(bool, str, list)

    def __init__(self, host: str):
        super().__init__()
        self.host = host.rstrip("/")

    def run(self):
        try:
            r = requests.get(f"{self.host}/api/version", timeout=1.5)
            if r.status_code == 200:
                ver = r.json().get("version", "")
                tags_resp = requests.get(f"{self.host}/api/tags", timeout=1.5)
                installed_models = []
                if tags_resp.status_code == 200:
                    installed_models = [m.get("name", "") for m in tags_resp.json().get("models", [])]
                self.status_checked.emit(True, ver, installed_models)
                return
        except Exception:
            pass
        self.status_checked.emit(False, "", [])


class OllamaPullThread(QThread):
    progress_signal = Signal(int, str)
    finished_signal = Signal(bool, str)

    def __init__(self, host: str, model_name: str):
        super().__init__()
        self.host = host.rstrip("/")
        self.model_name = model_name

    def run(self):
        try:
            url = f"{self.host}/api/pull"
            resp = requests.post(
                url,
                json={"name": self.model_name, "stream": True},
                stream=True,
                timeout=7200
            )
            if resp.status_code != 200:
                self.finished_signal.emit(False, f"서버 오류 ({resp.status_code}): {resp.text}")
                return

            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                    status = data.get("status", "")
                    total = data.get("total", 0)
                    completed = data.get("completed", 0)

                    if total > 0 and completed > 0:
                        percent = int((completed / total) * 100)
                        gb_done = completed / (1024 ** 3)
                        gb_total = total / (1024 ** 3)
                        self.progress_signal.emit(percent, f"{status} {percent}% ({gb_done:.1f}GB / {gb_total:.1f}GB)")
                    else:
                        self.progress_signal.emit(0, status)

                    if status == "success":
                        self.finished_signal.emit(True, f"'{self.model_name}' 다운로드 완료!")
                        return
                except Exception:
                    pass

            self.finished_signal.emit(True, f"'{self.model_name}' 다운로드 완료")
        except Exception as e:
            self.finished_signal.emit(False, f"다운로드 실패: {e}")


class OllamaManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("로컬 AI (Ollama)")
        self.resize(580, 500)
        self.setMinimumSize(520, 440)

        self.pull_thread = None
        self.status_thread = None
        self.server_online = False
        self.installed_models = []
        self.init_ui()

    def init_ui(self):
        root = create_layout('v', (16, 16, 16, 16), spacing=12, parent=self)

        status_card = QFrame()
        status_card.setObjectName("CardFrame_ui")
        sc_lay = create_layout('v', (12, 10, 12, 10), spacing=8, parent=status_card)

        s_top = create_layout('h')
        self.server_status_lbl = create_label("서버 상태: 확인 중...", "subLabel")
        s_top.addWidget(self.server_status_lbl, 1)

        self.start_server_btn = create_button("서버 실행", self.start_ollama_server, "primaryBtn", h=32, w=80)
        self.refresh_server_btn = create_button("새로고침", self.check_server_status, "subtleBtn", h=32, w=70)
        s_top.addWidget(self.start_server_btn)
        s_top.addWidget(self.refresh_server_btn)
        sc_lay.addLayout(s_top)

        self.install_guide_row = create_layout('h')
        self.download_page_btn = create_button(
            "Ollama 공식 다운로드 페이지 열기 (미설치 시 클릭)",
            self.open_ollama_download_page,
            "subtleBtn",
            h=32
        )
        self.download_page_btn.setStyleSheet("font-weight: bold;")
        self.install_guide_row.addWidget(self.download_page_btn)
        sc_lay.addLayout(self.install_guide_row)

        h_row = create_layout('h', spacing=6)
        h_row.addWidget(create_label("엔드포인트:", width=75))
        self.ollama_url_edit = QLineEdit()
        self.ollama_url_edit.setFixedHeight(30)
        self.ollama_url_edit.setText(str(load_data().get("ollama_url", "http://localhost:11434")))
        h_row.addWidget(self.ollama_url_edit, 1)
        sc_lay.addLayout(h_row)

        root.addWidget(status_card)

        model_card = QFrame()
        model_card.setObjectName("CardFrame_ui")
        mc_lay = create_layout('v', (12, 10, 12, 10), spacing=10, parent=model_card)

        mc_lay.addWidget(create_label("로컬 모델 선택", "subLabel"))

        m_row = create_layout('h', spacing=8)
        self.local_model_combo = QComboBox()
        self.local_model_combo.setFixedHeight(34)
        self.local_model_combo.addItems(VERIFIED_OLLAMA_MODELS)
        self.local_model_combo.currentTextChanged.connect(self.update_model_status_display)
        m_row.addWidget(self.local_model_combo, 1)

        self.download_btn = create_button("다운로드", self.start_model_download, "primaryBtn", h=50, w=100)
        m_row.addWidget(self.download_btn)

        self.delete_model_btn = create_button("삭제", self.delete_local_model, "subtleBtn", h=50, w=54)
        m_row.addWidget(self.delete_model_btn)
        mc_lay.addLayout(m_row)

        self.model_installed_lbl = create_label("설치 여부: 확인 중...", "secondaryInfo")
        mc_lay.addWidget(self.model_installed_lbl)

        self.pull_progress = QProgressBar()
        self.pull_progress.setFixedHeight(16)
        self.pull_progress.setRange(0, 100)
        self.pull_progress.setValue(0)
        self.pull_progress.setVisible(False)
        mc_lay.addWidget(self.pull_progress)

        self.pull_status_lbl = create_label("", "secondaryInfo")
        self.pull_status_lbl.setVisible(False)
        mc_lay.addWidget(self.pull_status_lbl)

        root.addWidget(model_card)
        root.addStretch(1)

        bot_row = create_layout('h')
        bot_row.addStretch(1)
        save_btn = create_button("적용 및 닫기", self.save_and_close, "primaryBtn", h=36, w=100)
        bot_row.addWidget(save_btn)
        root.addLayout(bot_row)

        QTimer.singleShot(150, self.check_server_status)

    def get_ollama_host(self) -> str:
        return self.ollama_url_edit.text().strip().rstrip("/") or "http://localhost:11434"

    def find_ollama_executable(self) -> str:
        bin_path = shutil.which("ollama")
        if not bin_path and os.name == "nt":
            cand = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
            if os.path.exists(cand):
                bin_path = cand
        return bin_path or ""

    def open_ollama_download_page(self):
        QDesktopServices.openUrl(QUrl(OLLAMA_DOWNLOAD_URL))

    def check_server_status(self):
        if self.status_thread and self.status_thread.isRunning():
            return
        self.server_status_lbl.setText("서버 상태: 확인 중...")
        self.refresh_server_btn.setEnabled(False)
        host = self.get_ollama_host()
        self.status_thread = OllamaStatusCheckThread(host)
        self.status_thread.status_checked.connect(self._on_server_status_checked)
        self.status_thread.start()

    def _on_server_status_checked(self, is_online: bool, ver: str, installed_models: list):
        self.refresh_server_btn.setEnabled(True)
        self.server_online = is_online
        self.installed_models = installed_models
        installed_bin = self.find_ollama_executable()

        if is_online:
            self.server_status_lbl.setText(f"실행 중 (v{ver})")
            self.server_status_lbl.setStyleSheet("font-weight: bold;")
            self.start_server_btn.setEnabled(False)
            self.download_page_btn.setVisible(False)
            self._sync_installed_models_to_combo(installed_models)
            self.update_model_status_display()
        else:
            if not installed_bin:
                self.server_status_lbl.setText("Ollama 미설치")
                self.server_status_lbl.setStyleSheet("font-weight: bold;")
                self.start_server_btn.setText("설치하기")
                self.download_page_btn.setVisible(True)
            else:
                self.server_status_lbl.setText("중지됨")
                self.server_status_lbl.setStyleSheet("font-weight: bold;")
                self.start_server_btn.setText("서버 실행")
                self.download_page_btn.setVisible(False)

            self.start_server_btn.setEnabled(True)
            self.model_installed_lbl.setText("서버 오프라인")
            self.delete_model_btn.setEnabled(False)

    def _sync_installed_models_to_combo(self, installed_models: list):
        existing = [self.local_model_combo.itemText(i) for i in range(self.local_model_combo.count())]
        for name in reversed(installed_models):
            clean_name = name.replace(":latest", "")
            if clean_name and clean_name not in existing:
                self.local_model_combo.insertItem(0, clean_name)
                existing.insert(0, clean_name)

    def update_model_status_display(self):
        if not self.server_online:
            self.model_installed_lbl.setText("서버 오프라인")
            self.delete_model_btn.setEnabled(False)
            return

        target_model = self.local_model_combo.currentText().strip().lower()
        if not target_model:
            self.model_installed_lbl.setText("모델명을 입력하세요.")
            self.download_btn.setEnabled(False)
            self.delete_model_btn.setEnabled(False)
            return

        self.download_btn.setEnabled(True)
        models = [m.lower() for m in self.installed_models]
        installed = any(
            target_model == m or m.startswith(target_model) or target_model == m.replace(":latest", "")
            for m in models
        )
        if installed:
            self.model_installed_lbl.setText("로컬에 설치됨 (사용 가능)")
            self.model_installed_lbl.setStyleSheet("font-weight: bold;")
            self.download_btn.setText("재다운로드")
            self.delete_model_btn.setEnabled(True)
        else:
            self.model_installed_lbl.setText("미설치 (다운로드 필요)")
            self.model_installed_lbl.setStyleSheet("font-weight: bold;")
            self.download_btn.setText("다운로드")
            self.delete_model_btn.setEnabled(False)

    def check_local_model_installed(self):
        self.check_server_status()

    def start_ollama_server(self):
        bin_path = self.find_ollama_executable()
        if not bin_path:
            res = QMessageBox.question(
                self,
                "Ollama 설치 필요",
                "PC에 Ollama가 설치되어 있지 않습니다.\n공식 다운로드 페이지로 이동하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No
            )
            if res == QMessageBox.Yes:
                self.open_ollama_download_page()
            return

        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            subprocess.Popen([bin_path, "serve"], creationflags=flags)
            self.server_status_lbl.setText("서버 상태: 백그라운드 서버 가동 중...")
            QTimer.singleShot(2500, self.check_server_status)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"Ollama 실행 실패: {e}")

    def start_model_download(self):
        host = self.get_ollama_host()
        model_name = self.local_model_combo.currentText().strip()
        if not model_name:
            return

        if not self.server_online:
            bin_path = self.find_ollama_executable()
            if not bin_path:
                self.open_ollama_download_page()
            else:
                QMessageBox.warning(self, "알림", "먼저 [서버 실행] 버튼을 눌러 Ollama 서버를 가동하세요.")
            return

        self.download_btn.setEnabled(False)
        self.pull_progress.setVisible(True)
        self.pull_progress.setValue(0)
        self.pull_status_lbl.setVisible(True)
        self.pull_status_lbl.setText(f"'{model_name}' 다운로드 요청 중...")

        self.pull_thread = OllamaPullThread(host, model_name)
        self.pull_thread.progress_signal.connect(self.on_pull_progress)
        self.pull_thread.finished_signal.connect(self.on_pull_finished)
        self.pull_thread.start()

    def on_pull_progress(self, percent: int, msg: str):
        self.pull_progress.setValue(percent)
        self.pull_status_lbl.setText(msg)

    def on_pull_finished(self, success: bool, msg: str):
        self.download_btn.setEnabled(True)
        self.pull_status_lbl.setText(msg)
        if success:
            QMessageBox.information(self, "완료", msg)
            self.check_server_status()
        else:
            QMessageBox.critical(self, "다운로드 실패", msg)

    def delete_local_model(self):
        host = self.get_ollama_host()
        model_name = self.local_model_combo.currentText().strip()
        if not model_name:
            return

        res = QMessageBox.question(
            self,
            "모델 삭제",
            f"'{model_name}' 모델을 로컬 디스크에서 완전히 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        if res != QMessageBox.Yes:
            return

        try:
            r = requests.delete(f"{host}/api/delete", json={"name": model_name}, timeout=10)
            if r.status_code == 200:
                QMessageBox.information(self, "완료", f"'{model_name}' 모델이 삭제되었습니다.")
                self.check_server_status()
            else:
                QMessageBox.critical(self, "삭제 실패", f"서버 응답 오류: {r.text}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"삭제 실패: {e}")

    def save_and_close(self):
        url = self.get_ollama_host()
        data = load_data()
        data["ollama_url"] = url
        save_data(data)
        self.accept()

    def get_current_api_data(self):
        host = self.get_ollama_host()
        return host, [host], 0