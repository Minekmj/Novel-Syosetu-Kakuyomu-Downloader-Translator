from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QWidget, QSizePolicy, QProgressBar, QMessageBox
)

from src.system.data import open_folder, load_data, save_data
from src.main.thread_pyqt import TranslateThread, trans_ai
from src.trans.trans_glossary import DictionaryDialog

from .elided_label import ElidedLabel
from .ui_factory import create_layout, create_button, create_label
from .log_panel import LogPanel
from .file_panel import FilePanel
from .model_panel import ModelPanel
from .settings_panel import SettingsPanel
from .settings_service import (
    load_app_settings, save_app_settings, save_app_preset, load_app_preset
)


class TranslateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_trans = False
        self.is_stop = False
        self.is_stop_i = False
        self.file_path = ''
        self.file_title = ''
        self.current_dictionary = {}
        self.thread = None

        self.setWindowTitle('AI 번역')
        self.resize(920, 750)
        self.setMinimumSize(720, 670)
        self.setAcceptDrops(True)

        self.init_ui()
        self.connect_signals()
        self.load_settings()

    def init_ui(self):
        root = create_layout('v', (14, 14, 14, 14), 10, self)

        self.file_panel = FilePanel(self)
        root.addWidget(self.file_panel)

        main = create_layout('h', spacing=14)

        left = QWidget()
        left.setObjectName('no_back-leftWidget')
        ll = create_layout('v', spacing=8, parent=left)

        self.model_panel = ModelPanel(left)
        ll.addWidget(self.model_panel)

        self.settings_panel = SettingsPanel(left)
        ll.addWidget(self.settings_panel, 1)
        ll.addWidget(create_button('설정 전체 저장', self.save_settings))

        right = QWidget()
        right.setObjectName('no_back-rightWidget')
        rl = create_layout('v', spacing=6, parent=right)

        row = create_layout('h')
        self.status_label = ElidedLabel('파일을 선택하세요.')
        self.status_label.setMaximumWidth(int(self.width() * 0.4))
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row.addWidget(self.status_label, 1)

        self.percent_label = create_label('0%')
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.percent_label)
        rl.addLayout(row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        rl.addWidget(self.progress_bar)

        self.log_panel = LogPanel(right)
        rl.addWidget(self.log_panel, 1)

        main.addWidget(left, 5)
        main.addWidget(right, 6)
        root.addLayout(main, 1)

        self.start_btn = create_button('번역 시작', self.start_translate, 'primaryBtn', 42)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        root.addWidget(self.start_btn)

        self.apply_ui_style()

    def connect_signals(self):
        self.model_panel.set_settings_panel(self.settings_panel)
        self.file_panel.file_selected.connect(self.on_file_selected)
        self.settings_panel.params_changed.connect(self.model_panel.update_active_model)

        self.model_panel.refresh_model_btn.clicked.connect(self.load_gemini_models)
        self.settings_panel.api_edit.textChanged.connect(lambda v: trans_ai.set_api_key(v) if v else None)
        self.settings_panel.dictionary_btn.clicked.connect(self.open_dictionary_dialog)
        self.settings_panel.preset_save_btn.clicked.connect(self.save_preset)
        self.settings_panel.preset_load_btn.clicked.connect(self.load_preset)

        self.model_panel.log_requested.connect(self.log_panel.add_log)
        self.settings_panel.log_requested.connect(self.log_panel.add_log)
        self.model_panel.status_requested.connect(self.status_label.setText)

    def apply_ui_style(self):
        self.setAutoFillBackground(False)
        self.settings_panel.setAutoFillBackground(False)
        for i in range(self.settings_panel.count()):
            page = self.settings_panel.widget(i)
            if page is not None:
                page.setAutoFillBackground(False)

        self.model_panel.model_list_container.setAutoFillBackground(False)
        self.model_panel.model_scroll.setAutoFillBackground(False)
        self.log_panel.log_edit.setAutoFillBackground(False)
        self.log_panel.log_edit.viewport().setAutoFillBackground(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'status_label'):
            self.status_label.setMaximumWidth(int(self.width() * 0.4))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile().lower()
            if path.endswith(('.txt', '.json')):
                event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.set_file(urls[0].toLocalFile())

    def set_file(self, path):
        self.file_panel.set_file(path)

    def on_file_selected(self, path, title, kind):
        self.file_path = path
        self.file_title = title

        if self.file_title:
            self.status_label.setText(f"{kind}  ·  {self.file_title}")
        else:
            self.status_label.setText(kind)

        self.log_panel.add_log(f"파일 선택: {path}")
        self.log_panel.add_log(f"작업 방식: {kind}")

        if self.file_title:
            self.log_panel.add_log(f"작품명 감지: {self.file_title}")
        else:
            self.log_panel.add_log('작품명을 찾지 못했습니다.')

        self.load_dictionary_for_title()

        if self.current_dictionary:
            self.log_panel.add_log(f"용어집 자동 선택: {len(self.current_dictionary)}개")
        else:
            self.log_panel.add_log('해당 작품에 등록된 용어집이 없습니다.')

    def load_dictionary_for_title(self):
        data = load_data()
        dictionary = data.get('dictionary', {}) if isinstance(data, dict) else {}
        self.current_dictionary = dictionary.get(self.file_title, {}) if isinstance(dictionary, dict) else {}
        if not isinstance(self.current_dictionary, dict):
            self.current_dictionary = {}

        if self.file_title:
            if self.current_dictionary:
                self.settings_panel.dictionary_status.setText(f"{self.file_title} ({len(self.current_dictionary)}개)")
            else:
                self.settings_panel.dictionary_status.setText(f"{self.file_title} (등록된 용어 없음)")
        else:
            self.settings_panel.dictionary_status.setText('작품명을 찾을 수 없습니다.')

    def open_dictionary_dialog(self):
        if not self.file_title:
            QMessageBox.warning(self, '알림', '먼저 번역할 파일을 선택하세요.\nTXT 파일은 첫 줄을 작품명으로 사용합니다.')
            return

        model_name = ''
        rpm = 15
        if 0 <= self.model_panel.active_model_index < len(self.model_panel.selected_models):
            m = self.model_panel.selected_models[self.model_panel.active_model_index]
            model_name = m.get('model', '')
            rpm = int(m.get('rpm', 15))

        try:
            dialog = DictionaryDialog(self, self.file_title, self.current_dictionary, model_name, rpm)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            self.current_dictionary = dict(dialog.dictionary)
            data = load_data()
            if not isinstance(data.get('dictionary'), dict):
                data['dictionary'] = {}
            data['dictionary'][self.file_title] = self.current_dictionary
            save_data(data)

            self.settings_panel.dictionary_status.setText(f"{self.file_title} ({len(self.current_dictionary)}개)")
            self.log_panel.add_log(f"용어집 저장 완료: {self.file_title} ({len(self.current_dictionary)}개)")
        except NameError:
            pass

    def load_gemini_models(self):
        api = self.settings_panel.api_edit.text().strip()
        if not self.model_panel.load_gemini_models(api):
            self.settings_panel.setCurrentIndex(3)
            self.settings_panel.api_edit.setFocus()

    def load_settings(self):
        load_app_settings(
            self.settings_panel, self.model_panel,
            self.status_label.setText, self.log_panel.add_log
        )

    def save_settings(self):
        if not save_app_settings(self.settings_panel, self.model_panel, self.log_panel.add_log):
            QMessageBox.warning(self, '알림', 'API 키와 Gemini 모델을 확인하세요.')
            return False
        return True

    def save_preset(self):
        if not save_app_preset(self.settings_panel, self.model_panel, self.log_panel.add_log):
            QMessageBox.warning(self, '알림', '프리셋 이름과 최소 하나의 모델을 확인하세요.')

    def load_preset(self):
        load_app_preset(self.settings_panel, self.model_panel, self, self.log_panel.add_log)

    def start_translate(self):
        if self.is_trans and not self.is_stop:
            self.stop_trans()
            return
        elif self.is_trans and not self.is_stop_i:
            self.stop_trans_i()
            return

        if not self.file_path:
            QMessageBox.warning(self, '알림', 'TXT 또는 JSON 파일을 선택하세요.')
            return

        api = self.settings_panel.api_edit.text().strip()
        if not api:
            QMessageBox.warning(self, '알림', 'Gemini API 키를 먼저 설정하세요.')
            self.settings_panel.setCurrentIndex(3)
            return

        model_configs = self.model_panel.get_model_configs()
        if not model_configs:
            QMessageBox.warning(self, '알림', '최소 하나의 모델을 추가하세요.')
            return

        try:
            max_chars = int(self.settings_panel.chars_combo.currentText())
        except ValueError:
            QMessageBox.warning(self, '알림', '설정 값이 올바르지 않습니다.')
            return

        if not self.save_settings():
            return

        model_names = ','.join(x['model'] for x in model_configs)
        rpms = tuple(x['rpm'] for x in model_configs)
        temperatures = tuple(x['temperature'] for x in model_configs)
        concurrencies = tuple(x['concurrency'] for x in model_configs)
        br_starts = tuple(x['br_start'] for x in model_configs)
        isno_xs = tuple(x['isno_x'] for x in model_configs)
        thinking_budgets = tuple(x.get('thinking_budget', '기본값') for x in model_configs)
        dict_data = dict(self.current_dictionary) if self.settings_panel.glossary_enabled else {}

        self.is_trans = True
        self.is_stop = False
        self.is_stop_i = False
        self.start_btn.setText('번역 중지')
        self.progress_bar.setValue(0)
        self.percent_label.setText('0%')
        
        self.log_panel.reset_time()

        self.log_panel.add_log('')
        self.log_panel.add_log('=' * 55)
        self.log_panel.add_log('번역 시작')

        for i, config in enumerate(model_configs, 1):
            censor_state = "건너뜀" if config['isno_x'] else "적용"
            self.log_panel.add_log(
                f"모델 {i}: {config['model']} / RPM {config['rpm']} / Temp {config['temperature']} / "
                f"동시 {config['concurrency']} / 분할시작 {config['br_start']} / 검열: {censor_state} / "
                f"추론: {config.get('thinking_budget', '기본값')}"
            )

        self.log_panel.add_log(f"작품명: {self.file_title}")
        self.log_panel.add_log(f"청크 글자수: {max_chars}")
        self.log_panel.add_log('용어집: ' + (f"활성 ({len(dict_data)}개)" if self.settings_panel.glossary_enabled else '비활성'))
        self.log_panel.add_log('=' * 55)

        try:
            self.thread = TranslateThread(
                self.file_path,
                model_names,
                rpms,
                temperatures,
                concurrencies,
                max_chars,
                dicts=dict_data,
                check=self.get_out,
                check_i=self.get_out_i,
                br_start=br_starts,
                isno_x=isno_xs,
                thinking_budget=thinking_budgets
            )
            self.thread.progress_changed.connect(self.update_progress)
            self.thread.log_changed.connect(self.log_panel.add_log)
            self.thread.finished_signal.connect(self.on_finished)
            self.thread.start()
        except NameError:
            self.log_panel.add_log('TranslateThread 실행 실패: 모듈을 찾을 수 없습니다.')
            self.is_trans = False
            self.start_btn.setText('번역 시작')

    def stop_trans(self):
        if not self.is_trans:
            return
        self.is_stop = True
        self.log_panel.add_log('중지: 번역 중지 요청 중... 작업 종료 후 중지')
        self.start_btn.setText('중지 중... (다시 눌를 시 강제 번역 종료)')

    def stop_trans_i(self):
        if not self.is_trans:
            return
        self.is_stop_i = True
        self.log_panel.add_log('중지: 번역 강제 중지 요청 중...')
        self.start_btn.setEnabled(False)
        self.start_btn.setText('중지 중...')

    def get_out(self):
        return self.is_stop

    def get_out_i(self):
        return self.is_stop_i

    def update_progress(self, done, total, message):
        total = max(int(total), 1)
        done = min(int(done), total)
        percent = int(done * 100 / total)

        self.progress_bar.setValue(percent)
        self.percent_label.setText(f"{percent}%")
        self.status_label.setText(str(message))

    def on_finished(self, success, message, output_dir):
        self.start_btn.setEnabled(True)
        self.start_btn.setText('번역 시작')
        self.is_trans = False
        self.is_stop = False
        self.is_stop_i = False

        if success:
            self.progress_bar.setValue(100)
            self.percent_label.setText('100%')
            self.status_label.setText(message)
            self.log_panel.add_log('번역이 정상적으로 완료되었습니다.')
            QMessageBox.information(self, '번역 완료', message)

            if output_dir:
                try:
                    open_folder(output_dir)
                except Exception:
                    pass
        else:
            self.status_label.setText('번역 실패')
            self.log_panel.add_log(f"번역 실패: {message}")
            QMessageBox.critical(self, '번역 오류', message)

    def closeEvent(self, event):
        if self.is_trans:
            QMessageBox.critical(
                self,
                '종료 거부',
                '현재 번역 작업 중 입니다.\n종료를 거부 합니다. 번역 중지 혹은 번역 완료 후 종료 해 주세요.'
            )
            event.ignore()
        else:
            super().closeEvent(event)