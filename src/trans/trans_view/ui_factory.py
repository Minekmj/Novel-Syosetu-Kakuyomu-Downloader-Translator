from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox
)


def create_layout(kind, margins=(0, 0, 0, 0), spacing=7, parent=None):
    layout = (QVBoxLayout if kind == 'v' else QHBoxLayout if kind == 'h' else QGridLayout)(parent)
    layout.setContentsMargins(*margins)
    if kind == 'g':
        layout.setHorizontalSpacing(spacing)
        layout.setVerticalSpacing(spacing)
    else:
        layout.setSpacing(spacing)
    return layout


def create_label(text, obj=None, width=None):
    w = QLabel(text)
    if obj:
        w.setObjectName(obj)
    if width:
        w.setFixedWidth(width)
    return w


def create_button(text, slot=None, obj='subtleBtn', h=35, w=None, checkable=False):
    b = QPushButton(text)
    if obj:
        b.setObjectName(obj)
    b.setFixedHeight(h)
    if w:
        b.setFixedWidth(w)
    b.setCheckable(checkable)
    if slot:
        (b.toggled if checkable else b.clicked).connect(slot)
    return b


def create_combo(items, current=None, slot=None, h=35):
    c = QComboBox()
    c.addItems([str(x) for x in items])
    if current is not None:
        c.setCurrentText(str(current))
    c.setMinimumHeight(h)
    if slot:
        c.currentTextChanged.connect(slot)
    return c


def set_combo_value(combo, value):
    value = str(value)
    combo.blockSignals(True)
    if combo.findText(value) < 0:
        combo.addItem(value)
    combo.setCurrentText(value)
    combo.blockSignals(False)


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()