from PySide6.QtWidgets import (
    QListWidget, QListWidgetItem, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QDialog, QMessageBox
)
from PySide6.QtGui import QKeyEvent, QKeySequence

import os
import json

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


class PresetLoadDialog(QDialog):
    def __init__(self, presets, parent=None):
        super().__init__(parent)
        self.setWindowTitle('프리셋 불러오기')
        self.resize(560, 400)
        self.setMinimumSize(500, 360)
        self.presets = presets
        self.selected_name = ''

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel('프리셋 불러오기')
        title.setObjectName('dialogTitle')
        layout.addWidget(title)

        subtitle = QLabel('저장된 프리셋을 선택하세요.')
        subtitle.setObjectName('secondaryInfo')
        layout.addWidget(subtitle)

        content = QHBoxLayout()
        content.setSpacing(10)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName('presetList')
        self.list_widget.setMinimumWidth(230)
        self.list_widget.setSpacing(2)
        self.list_widget.addItems(sorted(self.presets.keys()))
        self.list_widget.currentItemChanged.connect(self.on_preset_selected)
        self.list_widget.itemDoubleClicked.connect(self.accept_selected)
        content.addWidget(self.list_widget, 1)

        self.model_list = QListWidget()
        self.model_list.setObjectName('presetModelList')
        self.model_list.setMinimumWidth(230)
        self.model_list.setSpacing(2)
        self.model_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        content.addWidget(self.model_list, 1)

        layout.addLayout(content, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(7)

        self.delete_btn = QPushButton('삭제')
        self.delete_btn.setObjectName('subtleBtn')
        self.delete_btn.setMinimumHeight(34)
        self.delete_btn.setEnabled(False)

        cancel_btn = QPushButton('취소')
        cancel_btn.setMinimumHeight(34)

        load_btn = QPushButton('불러오기')
        load_btn.setObjectName('primaryBtn')
        load_btn.setMinimumHeight(36)
        load_btn.setMinimumWidth(90)

        self.delete_btn.clicked.connect(self.delete_selected)
        cancel_btn.clicked.connect(self.reject)
        load_btn.clicked.connect(self.accept_selected)

        buttons.addWidget(self.delete_btn)
        buttons.addStretch(1)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(load_btn)
        layout.addLayout(buttons)

        self.setStyleSheet('''
            QListWidget#presetList,
            QListWidget#presetModelList {
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                background: transparent;
                outline: none;
                padding: 4px;
            }

            QListWidget#presetList::item,
            QListWidget#presetModelList::item {
                min-height: 34px;
                padding: 5px 9px;
                border-radius: 6px;
            }

            QListWidget#presetList::item:hover {
                background: rgba(255, 255, 255, 0.05);
            }

            QListWidget#presetList::item:selected {
                background: rgba(255, 255, 255, 0.09);
            }

            QListWidget#presetModelList::item {
                color: palette(text);
            }

            QPushButton {
                min-height: 34px;
                padding-left: 11px;
                padding-right: 11px;
            }
        ''')

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def on_preset_selected(self, current, previous=None):
        self.model_list.clear()
        if current is None:
            self.delete_btn.setEnabled(False)
            return

        name = current.text()
        if name not in self.presets:
            self.delete_btn.setEnabled(False)
            return

        self.delete_btn.setEnabled(True)
        preset = self.presets.get(name)
        if not isinstance(preset, dict):
            return

        models = preset.get('selected_models') or preset.get('models') or []
        if isinstance(models, dict):
            models = [models]

        model_names = []
        for model in models:
            if isinstance(model, dict):
                model_name = model.get('model') or model.get('name') or ''
            else:
                model_name = str(model)
            model_name = str(model_name).strip()
            if model_name and model_name.casefold() not in {x.casefold() for x in model_names}:
                model_names.append(model_name)

        if not model_names:
            model_name = preset.get('model') or preset.get('model_name') or ''
            if model_name:
                model_names.append(str(model_name).strip())

        for model_name in model_names:
            item = QListWidgetItem(model_name)
            self.model_list.addItem(item)

    def accept_selected(self, *args):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, '알림', '프리셋을 선택하세요.')
            return

        name = item.text()
        if name not in self.presets:
            QMessageBox.warning(self, '알림', '선택한 프리셋을 찾을 수 없습니다.')
            return

        self.selected_name = name
        self.accept()

    def delete_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return

        name = item.text()
        if name not in self.presets:
            return

        result = QMessageBox.question(
            self,
            '프리셋 삭제',
            f"「{name}」 프리셋을 삭제하시겠습니까?\n삭제한 프리셋은 복구할 수 없습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        if name in self.presets:
            del self.presets[name]

        parent = self.parent()
        settings_file = parent.SETTINGS_FILE
        try:
            data = {}
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            if 'pre' in data and isinstance(data['pre'], dict):
                if name in data['pre']:
                    del data['pre'][name]
                with open(settings_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.critical(self, '저장 오류', f'프리셋 삭제 저장 중 오류가 발생했습니다: {e}')

        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
        self.model_list.clear()

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(min(row, self.list_widget.count() - 1))
        else:
            self.delete_btn.setEnabled(False)

        self.selected_name = ''

        if parent is not None:
            if hasattr(parent, 'preset_status') and hasattr(parent, 'preset_name_edit'):
                if parent.preset_name_edit.text().strip() == name:
                    parent.preset_name_edit.clear()
                    parent.preset_status.setText('현재 프리셋 없음')
            if hasattr(parent, 'add_log'):
                parent.add_log(f"프리셋 삭제 완료: {name}")