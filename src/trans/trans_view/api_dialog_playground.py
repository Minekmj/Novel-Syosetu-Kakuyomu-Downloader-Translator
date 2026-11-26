import shutil
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog, QWidget, QLineEdit, QFrame, QMessageBox, QComboBox
)
from src.ai import AiRoute, AiTarget
from src.system.load_save import load_data, save_data
from .ui_factory import create_layout, create_button, create_label


class PlaygroundLoginThread(QThread):
    finished_signal = Signal(bool, str)

    def __init__(self, profile_key: str = "default", force: bool = False, parent=None):
        super().__init__(parent)
        self.profile_key = (profile_key or "default").strip() or "default"
        self.force = force

    def run(self):
        try:
            route = AiRoute(ai_target=AiTarget.PLAYGROUND, api=self.profile_key)
            ok = route.SetLogin(api_key=self.profile_key, target=AiTarget.PLAYGROUND, force=self.force)
            if ok:
                self.finished_signal.emit(True, f"Playground 로그인 완료 (프로필: {self.profile_key})")
            else:
                self.finished_signal.emit(False, "Playground 로그인에 실패했습니다.")
        except Exception as e:
            self.finished_signal.emit(False, f"로그인 오류: {e}")


class PlaygroundStatusThread(QThread):
    status_checked = Signal(bool, list, str)

    def __init__(self, profile_key: str = "default", verify: bool = False, parent=None):
        super().__init__(parent)
        self.profile_key = (profile_key or "default").strip() or "default"
        self.verify = verify

    def run(self):
        try:
            route = AiRoute(ai_target=AiTarget.PLAYGROUND, api=self.profile_key)
            logged_in = route.check_login(api_key=self.profile_key, target=AiTarget.PLAYGROUND, verify=self.verify)
            models = []
            if logged_in:
                try:
                    models = route.get_model(AiTarget.PLAYGROUND).list_models(self.profile_key)
                except Exception:
                    models = []
            self.status_checked.emit(bool(logged_in), list(models), "")
        except Exception as e:
            self.status_checked.emit(False, [], str(e))


class PlaygroundManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Playground 관리")
        self.resize(560, 460)
        self.setMinimumSize(500, 400)

        self.profiles = []
        self.selected_index = 0
        self.login_thread = None
        self.status_thread = None
        self._is_closed = False

        self.load_profiles()
        self.init_ui()
        QTimer.singleShot(100, lambda: self.refresh_status(verify=False))

    def load_profiles(self):
        data = load_data()
        single_k, list_k, idx_k = AiRoute.get_storage_keys(AiTarget.PLAYGROUND)

        raw_list = data.get(list_k, [])
        if isinstance(raw_list, list):
            self.profiles = [str(p).strip() for p in raw_list if str(p).strip()]
        else:
            self.profiles = []

        single_val = str(data.get(single_k, "")).strip()
        if single_val and single_val not in self.profiles:
            self.profiles.insert(0, single_val)
        if not self.profiles:
            self.profiles = ["default"]

        try:
            self.selected_index = int(data.get(idx_k, 0))
        except (ValueError, TypeError):
            self.selected_index = 0
        self.selected_index = max(0, min(self.selected_index, len(self.profiles) - 1))

    def init_ui(self):
        root = create_layout('v', (16, 16, 16, 16), spacing=12, parent=self)

        profile_card = QFrame()
        profile_card.setObjectName("CardFrame_ui")
        pc_lay = create_layout('v', (12, 10, 12, 10), spacing=8, parent=profile_card)

        pc_lay.addWidget(create_label("Playground 프로필", "subLabel"))

        p_row = create_layout('h', spacing=8)
        self.profile_combo = QComboBox()
        self.profile_combo.setFixedHeight(34)
        self.profile_combo.addItems(self.profiles)
        self.profile_combo.setCurrentIndex(self.selected_index)
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
        p_row.addWidget(self.profile_combo, 1)

        self.new_profile_edit = QLineEdit()
        self.new_profile_edit.setPlaceholderText("새 프로필 이름")
        self.new_profile_edit.setFixedHeight(34)
        p_row.addWidget(self.new_profile_edit, 1)

        self.add_profile_btn = create_button("추가", self.add_profile, "subtleBtn", h=34, w=58)
        self.del_profile_btn = create_button("삭제", self.delete_profile, "subtleBtn", h=34, w=58)
        p_row.addWidget(self.add_profile_btn)
        p_row.addWidget(self.del_profile_btn)
        pc_lay.addLayout(p_row)

        save_dir_str = ""
        try:
            model = AiRoute(ai_target=AiTarget.PLAYGROUND).get_model(AiTarget.PLAYGROUND)
            save_dir_str = str(model._get_save_dir())
        except Exception:
            save_dir_str = ""

        path_lbl = create_label(f"세션 저장 경로: {save_dir_str}", "secondaryInfo")
        path_lbl.setWordWrap(True)
        pc_lay.addWidget(path_lbl)

        root.addWidget(profile_card)

        status_card = QFrame()
        status_card.setObjectName("CardFrame_ui")
        sc_lay = create_layout('v', (12, 10, 12, 10), spacing=10, parent=status_card)

        s_top = create_layout('h', spacing=8)
        self.status_lbl = create_label("확인 중...", "subLabel")
        s_top.addWidget(self.status_lbl, 1)

        self.verify_btn = create_button("검증", lambda: self.refresh_status(verify=True), "subtleBtn", h=32, w=82)
        s_top.addWidget(self.verify_btn)
        sc_lay.addLayout(s_top)

        self.model_count_lbl = create_label("조회된 모델: -", "secondaryInfo")
        sc_lay.addWidget(self.model_count_lbl)

        btn_row = create_layout('h', spacing=8)
        self.login_btn = create_button("로그인", lambda: self.start_login(force=False), "primaryBtn", h=38)
        self.relogin_btn = create_button("계정 변경", lambda: self.start_login(force=True), "subtleBtn", h=38)
        self.clear_session_btn = create_button("세션 삭제", self.clear_session, "subtleBtn", h=38, w=90)
        btn_row.addWidget(self.login_btn, 1)
        btn_row.addWidget(self.relogin_btn, 1)
        btn_row.addWidget(self.clear_session_btn)
        sc_lay.addLayout(btn_row)

        guide_lbl = create_label(
            "로그인 버튼을 누르면 Chrome 창이 열립니다. Google 로그인을 완료하세요.",
            "secondaryInfo"
        )
        guide_lbl.setWordWrap(True)
        sc_lay.addWidget(guide_lbl)

        root.addWidget(status_card)
        root.addStretch(1)

        bot_row = create_layout('h', spacing=8)
        bot_row.addStretch(1)
        cancel_btn = create_button("취소", self.reject, "secondaryBtn", h=36, w=72)
        save_btn = create_button("적용 및 닫기", self.save_and_close, "primaryBtn", h=36, w=104)
        bot_row.addWidget(cancel_btn)
        bot_row.addWidget(save_btn)
        root.addLayout(bot_row)

    def get_current_profile(self) -> str:
        text = self.profile_combo.currentText().strip()
        return text or "default"

    def on_profile_changed(self, idx: int):
        if 0 <= idx < len(self.profiles):
            self.selected_index = idx
        self.refresh_status(verify=False)

    def add_profile(self):
        name = self.new_profile_edit.text().strip()
        if not name:
            return
        if name not in self.profiles:
            self.profiles.append(name)
            self.profile_combo.addItem(name)
        idx = self.profiles.index(name)
        self.selected_index = idx
        self.profile_combo.setCurrentIndex(idx)
        self.new_profile_edit.clear()
        self.refresh_status(verify=False)

    def delete_profile(self):
        if len(self.profiles) <= 1:
            QMessageBox.warning(self, "알림", "최소 하나의 프로필은 필요합니다.")
            return
        idx = self.profile_combo.currentIndex()
        if not (0 <= idx < len(self.profiles)):
            return
        if self.profiles[idx] == "default":
            QMessageBox.warning(self, "알림", "기본(default) 프로필은 삭제할 수 없습니다.")
            return
        self.profiles.pop(idx)
        self.profile_combo.removeItem(idx)
        self.selected_index = max(0, min(idx, len(self.profiles) - 1))
        self.profile_combo.setCurrentIndex(self.selected_index)
        self.refresh_status(verify=False)

    def _set_busy(self, busy: bool):
        self.login_btn.setEnabled(not busy)
        self.relogin_btn.setEnabled(not busy)
        self.verify_btn.setEnabled(not busy)
        self.clear_session_btn.setEnabled(not busy)
        self.profile_combo.setEnabled(not busy)

    def refresh_status(self, verify: bool = False):
        if self._is_closed:
            return
        if self.status_thread and self.status_thread.isRunning():
            return
        if self.login_thread and self.login_thread.isRunning():
            return

        profile = self.get_current_profile()
        self.status_lbl.setText("검증 중..." if verify else "확인 중...")
        self.verify_btn.setEnabled(False)

        self.status_thread = PlaygroundStatusThread(profile, verify=verify, parent=self)
        self.status_thread.status_checked.connect(self._on_status_checked)
        self.status_thread.start()

    def _on_status_checked(self, logged_in: bool, models: list, err: str):
        if self._is_closed:
            return
        self.verify_btn.setEnabled(True)
        if err:
            self.status_lbl.setText("확인 오류")
            self.model_count_lbl.setText(f"오류: {err}")
            return

        if logged_in:
            self.status_lbl.setText("로그인됨")
            if models:
                self.model_count_lbl.setText(f"조회된 모델: {len(models)}개")
            else:
                self.model_count_lbl.setText("조회된 모델: 세션 검증 시 조회 가능")
        else:
            self.status_lbl.setText("로그인 필요")
            self.model_count_lbl.setText("조회된 모델: 0개")

    def start_login(self, force: bool = False):
        if self._is_closed:
            return
        if self.login_thread and self.login_thread.isRunning():
            return

        profile = self.get_current_profile()
        self._set_busy(True)
        self.status_lbl.setText("로그인 진행 중... 브라우저에서 Google 로그인을 완료하세요.")

        self.login_thread = PlaygroundLoginThread(profile, force=force, parent=self)
        self.login_thread.finished_signal.connect(self._on_login_finished)
        self.login_thread.start()

    def _on_login_finished(self, success: bool, msg: str):
        if self._is_closed:
            return
        self._set_busy(False)
        if success:
            QMessageBox.information(self, "로그인 완료", msg)
            self.refresh_status(verify=True)
        else:
            self.status_lbl.setText("로그인 상태: 로그인 실패")
            QMessageBox.critical(self, "로그인 실패", msg)

    def clear_session(self):
        profile = self.get_current_profile()
        res = QMessageBox.question(
            self,
            "세션 삭제",
            f"'{profile}' 프로필의 저장된 로그인 세션을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        if res != QMessageBox.Yes:
            return

        try:
            model = AiRoute(ai_target=AiTarget.PLAYGROUND, api=profile).get_model(AiTarget.PLAYGROUND)
            model.close(profile)
            model._verified_profiles.discard(profile)
            save_dir = model._get_save_dir()

            profile_json = save_dir / f"{profile}.json"
            if profile_json.is_file():
                profile_json.unlink()

            for target_dir in (save_dir / f"{profile}_runtime", save_dir / profile, *save_dir.glob(f"{profile}_worker_*")):
                if target_dir.exists():
                    shutil.rmtree(target_dir, ignore_errors=True)

            for enc_file in save_dir.rglob("*.enc"):
                if profile == "default" or profile in enc_file.stem or profile in str(enc_file.parent):
                    try:
                        enc_file.unlink()
                    except Exception:
                        pass

            self.refresh_status(verify=False)
            QMessageBox.information(self, "완료", "세션이 삭제되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"세션 삭제 실패: {e}")

    def save_and_close(self):
        single_k, list_k, idx_k = AiRoute.get_storage_keys(AiTarget.PLAYGROUND)
        idx = self.profile_combo.currentIndex()
        if not (0 <= idx < len(self.profiles)):
            idx = 0
        self.selected_index = idx

        data = load_data()
        data[list_k] = self.profiles
        data[idx_k] = self.selected_index
        data[single_k] = self.profiles[self.selected_index]
        save_data(data)
        self.accept()

    def get_current_api_data(self):
        active_profile = self.get_current_profile()
        return active_profile, list(self.profiles), self.selected_index

    def closeEvent(self, event):
        self._safe_cleanup()
        super().closeEvent(event)

    def reject(self):
        self._safe_cleanup()
        super().reject()

    def accept(self):
        self._safe_cleanup()
        super().accept()

    def _safe_cleanup(self):
        if self._is_closed:
            return
        self._is_closed = True
        for th in (self.status_thread, self.login_thread):
            if th is not None and th.isRunning():
                try:
                    th.disconnect()
                except Exception:
                    pass
                th.quit()
                th.wait(2000)
        self.status_thread = None
        self.login_thread = None