import os

from PySide6.QtWidgets import QFileDialog, QMessageBox
import src.down.down as down
import src.trans.trans_view as trans_view
import src.system.data as data_iteam
from src.system.data import load_data, save_data, open_folder
import src.main.setting as setting_ui
import src.main.update as update_ui
import src.main.thread_pyqt as thread_pyqt
from src.system.v import V

def init_system_config():
    data = load_data()
    setting_ui.export_env_settings(data)

    trans_view.trans_ai.CUSTOM_AI_PROMPT = data.get("AI_PROMPT", "")
    down.downin.base_data.EXPORT_TEXT = data.get("RAW_TEXT", False)
    down.downin.base_data.ORIGIN_NAME = data.get("origin_name", False)

    trans_view.trans_ai.USE_ADVANCED_CENSOR = data.get("CENSOR_ADVANCED", False)
    trans_view.trans_ai.CENSOR_SHUFFLE = data.get("CENSOR_SHUFFLE", True)
    trans_view.trans_ai.CENSOR_EXTRACT_MODE = data.get("CENSOR_MODE", "word")
    trans_view.trans_ai.CENSOR_PAPAGO = data.get("CENSOR_PAPAGO", False)

    if data.get("src"):
        down.downin.base_data.OUTFOLDER = data["src"]
        os.environ["minedown_setting_src"] = data["src"]
        trans_view.OUT = data["src"]

def check_app_version(parent_window):
    data = load_data()
    vn = data.get("V", "")
    if vn == "" or vn != V:
        data["V"] = V
        save_data(data)
        update = update_ui.UpdateView(parent_window)
        update.show()

def handle_settings_dialog(parent_window):
    data = load_data()
    if data.get("theme"):
        data_iteam.THEME_NAME = data["theme"]
    if not data.get("src") and down.downin.base_data.OUTFOLDER:
        data["src"] = down.downin.base_data.OUTFOLDER

    dialog = setting_ui.PathSettingsDialog(data, parent_window)

    if dialog.exec():
        new_settings = dialog.get_data()
        data.update(new_settings)
        setting_ui.export_env_settings(new_settings)

        selected_path = new_settings.get("src", "").strip()
        if selected_path:
            down.downin.base_data.OUTFOLDER = selected_path
            os.environ["minedown_setting_src"] = selected_path
            trans_view.OUT = selected_path

        down.downin.base_data.EXPORT_TEXT = new_settings.get("RAW_TEXT", False)
        down.downin.base_data.ORIGIN_NAME = new_settings.get("origin_name", False)

        save_data(data)

        trans_view.trans_ai.CUSTOM_AI_PROMPT = new_settings.get("AI_PROMPT", "")
        trans_view.trans_ai.USE_ADVANCED_CENSOR = new_settings.get("CENSOR_ADVANCED", False)
        trans_view.trans_ai.CENSOR_SHUFFLE = new_settings.get("CENSOR_SHUFFLE", True)
        trans_view.trans_ai.CENSOR_EXTRACT_MODE = new_settings.get("CENSOR_MODE", "word")
        trans_view.trans_ai.CENSOR_PAPAGO = new_settings.get("CENSOR_PAPAGO", False)

        if data.get("theme") and data["theme"] != data_iteam.THEME_NAME:
            data_iteam.THEME_NAME = data["theme"]
            data_iteam.rest()

            parent_window.setUpdatesEnabled(False)
            parent_window.app.setStyleSheet(data_iteam.MINIMAL_DARK_THEME)
            parent_window.setUpdatesEnabled(True)

def convert_txt_to_epub_flow(parent_window, epub_btn):
    file_paths, _ = QFileDialog.getOpenFileNames(
        parent_window,
        "EPUB으로 변환할 TXT 파일 선택",
        down.downin.base_data.OUTFOLDER,
        "Text Files (*.txt)"
    )

    if not file_paths:
        return

    epub_btn.setEnabled(False)
    epub_btn.setText("변환 중...")

    def on_finished(success, message, output_dir):
        epub_btn.setEnabled(True)
        epub_btn.setText("EPUB 변환")
        if success:
            if output_dir:
                open_folder(output_dir)
        else:
            QMessageBox.critical(parent_window, "오류", f"EPUB 변환 도중 오류가 발생했습니다:\n{message}")

    thread = thread_pyqt.EpubConvertThread(file_paths)
    thread.finished_signal.connect(on_finished)
    thread.start()
    parent_window._active_epub_thread = thread