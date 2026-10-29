from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame, QRadioButton,
    QButtonGroup, QMessageBox
)
from src.system.load_save import load_data, save_data
import src.trans.trans_ai as trans_ai
from .ui_factory import create_layout, create_button, create_label, clear_layout


class ApiManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gemini API 키 관리")
        self.resize(520, 480)
        self.setMinimumSize(460, 400)

        self.api_keys = []
        self.selected_index = 0

        self.load_keys()
        self.init_ui()
        self.rebuild_key_list()

    def load_keys(self):
        data = load_data()
        raw_keys = data.get("api_keys", [])
        if isinstance(raw_keys, list):
            self.api_keys = [str(k).strip() for k in raw_keys if str(k).strip()]
        else:
            self.api_keys = []

        single_api = str(data.get("api", "")).strip()
        if not self.api_keys and single_api:
            self.api_keys = [single_api]

        try:
            self.selected_index = int(data.get("api_index", 0))
        except (ValueError, TypeError):
            self.selected_index = 0

        if self.api_keys:
            self.selected_index = max(0, min(self.selected_index, len(self.api_keys) - 1))
        else:
            self.selected_index = 0

    def init_ui(self):
        root = create_layout('v', (16, 16, 16, 16), spacing=12, parent=self)

        add_group_label = create_label("추가 API", "optionLabel")
        root.addWidget(add_group_label)

        add_row = create_layout('h', spacing=8)
        self.new_key_edit = QLineEdit()
        self.new_key_edit.setPlaceholderText("새 Gemini API 키를 입력하세요")
        self.new_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_key_edit.setMinimumHeight(35)
        add_row.addWidget(self.new_key_edit, 1)

        self.add_key_btn = create_button("+", self.add_api_key, 'primaryBtn', h=35, w=48)
        add_row.addWidget(self.add_key_btn)
        root.addLayout(add_row)

        desc_lbl = create_label("인덱스 0이 메인 API이며 1 이상은 추가 API입니다.\nRate Limit 발생 시 순차적으로 다음 API 키로 자동 전환됩니다.", "secondaryInfo")
        desc_lbl.setWordWrap(True)
        root.addWidget(desc_lbl)

        list_title = create_label("등록된 API 키 목록", "subLabel")
        root.addWidget(list_title)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.list_container = QWidget()
        self.list_container.setObjectName("object_api")
        self.list_container.setStyleSheet("#object_api{background:Transparent;}")
        self.list_layout = create_layout('v', spacing=6, parent=self.list_container)
        self.scroll_area.setWidget(self.list_container)
        root.addWidget(self.scroll_area, 1)

        bottom_layout = create_layout('h', spacing=8)
        bottom_layout.addStretch(1)

        cancel_btn = create_button("취소", self.reject, 'secondaryBtn', h=38, w=70)
        save_btn = create_button("저장", self.save_and_close, 'primaryBtn', h=38, w=70)

        bottom_layout.addWidget(cancel_btn)
        bottom_layout.addWidget(save_btn)
        root.addLayout(bottom_layout)

    def rebuild_key_list(self):
        clear_layout(self.list_layout)
        self.button_group = QButtonGroup(self)

        if not self.api_keys:
            empty_lbl = create_label("등록된 API 키가 없습니다.", "secondaryInfo")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.addWidget(empty_lbl)
            self.list_layout.addStretch(1)
            return

        if self.selected_index >= len(self.api_keys):
            self.selected_index = max(0, len(self.api_keys) - 1)

        for i, key in enumerate(self.api_keys):
            row_widget = QWidget()
            row_widget.setObjectName("object_api")
            
            row_layout = create_layout('h', (4, 4, 4, 4), spacing=8, parent=row_widget)

            rb = QRadioButton()
            rb.setObjectName("object_api")
            
            rb.setChecked(i == self.selected_index)
            rb.toggled.connect(lambda checked, idx=i: self.on_radio_toggled(idx, checked))
            self.button_group.addButton(rb, i)
            row_layout.addWidget(rb)

            label_text = f"[{i}] 메인" if i == 0 else f"[{i}] 추가"
            idx_label = create_label(label_text, width=64)
            row_layout.addWidget(idx_label)

            masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else key
            key_display = QLineEdit(masked_key)
            key_display.setReadOnly(True)
            key_display.setMinimumHeight(32)
            row_layout.addWidget(key_display, 1)

            if i != 0:
                del_btn = create_button("✕", lambda _, idx=i: self.delete_key(idx), 'modelDeleteBtn', h=50, w=36)
                row_layout.addWidget(del_btn)

            self.list_layout.addWidget(row_widget)

        self.list_layout.addStretch(1)

    def on_radio_toggled(self, idx, checked):
        if checked:
            self.selected_index = idx

    def add_api_key(self):
        new_key = self.new_key_edit.text().strip()
        if not new_key:
            QMessageBox.warning(self, "알림", "추가할 API 키를 입력하세요.")
            return

        if new_key in self.api_keys:
            QMessageBox.warning(self, "알림", "이미 등록된 API 키입니다.")
            return

        self.api_keys.append(new_key)
        self.new_key_edit.clear()
        self.rebuild_key_list()

    def delete_key(self, idx):
        if not (0 <= idx < len(self.api_keys)):
            return

        self.api_keys.pop(idx)
        if self.selected_index >= len(self.api_keys):
            self.selected_index = max(0, len(self.api_keys) - 1)
        elif self.selected_index == idx:
            self.selected_index = min(idx, max(0, len(self.api_keys) - 1))

        self.rebuild_key_list()

    def save_and_close(self):
        trans_ai.set_api_keys(self.api_keys, self.selected_index)
        data = load_data()
        data["api_keys"] = self.api_keys
        data["api_index"] = self.selected_index
        data["api"] = self.api_keys[self.selected_index] if self.api_keys else ""
        save_data(data)
        self.accept()

    def get_current_api_data(self):
        active_key = self.api_keys[self.selected_index] if 0 <= self.selected_index < len(self.api_keys) else ""
        return active_key, self.api_keys, self.selected_index