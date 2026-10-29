import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QLineEdit, QFileDialog, QMessageBox
from .ui_factory import create_layout, create_label, create_button
from .file_utils import extract_title


class FilePanel(QWidget):
    file_selected = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = ''
        self.file_title = ''
        self.init_ui()

    def init_ui(self):
        layout = create_layout('v', spacing=5, parent=self)

        self.drop_label = create_label('TXT 또는 JSON 파일을 여기에 드래그하세요', 'dropArea')
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumHeight(48)
        self.drop_label.setMaximumHeight(54)
        layout.addWidget(self.drop_label)

        file_row = create_layout('h')
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText('번역할 TXT 또는 JSON 파일 선택')
        self.file_edit.setMinimumHeight(35)
        file_row.addWidget(self.file_edit, 1)
        file_row.addWidget(create_button('파일 찾기', self.browse_file, w=90))
        layout.addLayout(file_row)

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, '번역할 파일 선택', './out/', '지원 파일 (*.txt *.json)')
        if path:
            self.set_file(path)

    def set_file(self, path):
        if not path.lower().endswith(('.txt', '.json')):
            QMessageBox.warning(self, '알림', 'TXT 또는 JSON 파일만 선택할 수 있습니다.')
            return

        self.file_path = path
        self.file_edit.setText(path)
        self.file_title = extract_title(path)
        kind = 'JSON 복원/재번역' if path.lower().endswith('.json') else 'TXT 전체 번역'
        self.drop_label.setText(f"선택됨: {os.path.basename(path)}")
        self.file_selected.emit(path, self.file_title, kind)