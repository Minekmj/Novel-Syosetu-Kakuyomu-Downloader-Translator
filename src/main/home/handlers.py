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
    trans_view.trans_ai.CUSTOM_AI_PROMPT = data.get("AI_PROMPT", "")
    down.downin.base_data.EXPORT_TEXT = data.get("RAW_TEXT", False)
    down.downin.base_data.ORIGIN_NAME = data.get("origin_name", False)

    trans_view.trans_ai.USE_ADVANCED_CENSOR = data.get("CENSOR_ADVANCED", False)
    trans_view.trans_ai.CENSOR_SHUFFLE = data.get("CENSOR_SHUFFLE", True)
    trans_view.trans_ai.CENSOR_EXTRACT_MODE = data.get("CENSOR_MODE", "word")
    trans_view.trans_ai.CENSOR_PAPAGO = data.get("CENSOR_PAPAGO", False)

    if data.get("src"):
        down.downin.base_data.OUTFOLDER = data["src"]
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
    dialog = setting_ui.PathSettingsDialog(parent_window)

    if data.get("src"):
        dialog.path_edit.setText(data["src"])
    elif down.downin.base_data.OUTFOLDER:
        dialog.path_edit.setText(down.downin.base_data.OUTFOLDER)

    dialog.raw_text_toggle.setChecked(data.get("RAW_TEXT", False))
    dialog.origin_name_toggle.setChecked(data.get("origin_name", False))
    dialog.ai_prompt_edit.setPlainText(data.get("AI_PROMPT", ""))
    censor_adv = data.get("CENSOR_ADVANCED", False)
    dialog.censor_toggle.setChecked(censor_adv)
    dialog.censor_sub_widget.setVisible(censor_adv)
    dialog.shuffle_toggle.setChecked(data.get("CENSOR_SHUFFLE", True))
    saved_mode = data.get("CENSOR_MODE", "word")
    idx = dialog.mode_combo.findData(saved_mode)

    if idx >= 0:
        dialog.mode_combo.setCurrentIndex(idx)
    dialog.papago_toggle.setChecked(data.get("CENSOR_PAPAGO", False))

    if "epub_data" in data:
        dialog.set_epub_data(data["epub_data"])

    if dialog.exec():
        selected_path = dialog.path_edit.text().strip()
        selected_theme = data_iteam.THEME_DATA.get(dialog.theme_combo.currentText(), "DARK")

        raw_text = dialog.get_raw_text()
        origin_name = dialog.get_origin_name()
        ai_prompt = dialog.get_ai_prompt()
        censor_advanced = dialog.get_censor_advanced()
        censor_shuffle = dialog.get_censor_shuffle()
        censor_mode = dialog.get_censor_mode()
        censor_papago = dialog.get_censor_papago()
        epub_data = dialog.get_epub_data()

        if selected_path:
            down.downin.base_data.OUTFOLDER = selected_path
            trans_view.OUT = selected_path
            data["src"] = selected_path

        down.downin.base_data.EXPORT_TEXT = raw_text
        down.downin.base_data.ORIGIN_NAME = origin_name

        data["theme"] = selected_theme
        data["RAW_TEXT"] = raw_text
        data["origin_name"] = origin_name
        data["AI_PROMPT"] = ai_prompt
        data["CENSOR_ADVANCED"] = censor_advanced
        data["CENSOR_SHUFFLE"] = censor_shuffle
        data["CENSOR_MODE"] = censor_mode
        data["CENSOR_PAPAGO"] = censor_papago
        if not epub_data is None:
            data["epub_data"] = epub_data

        save_data(data)

        trans_view.trans_ai.CUSTOM_AI_PROMPT = ai_prompt
        trans_view.trans_ai.USE_ADVANCED_CENSOR = censor_advanced
        trans_view.trans_ai.CENSOR_SHUFFLE = censor_shuffle
        trans_view.trans_ai.CENSOR_EXTRACT_MODE = censor_mode
        trans_view.trans_ai.CENSOR_PAPAGO = censor_papago

        if data["theme"] != data_iteam.THEME_NAME:
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