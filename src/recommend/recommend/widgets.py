from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QUrl
from PySide6.QtWidgets import QLabel, QListWidget, QScrollArea
from PySide6.QtGui import QCursor, QDesktopServices

class SmoothScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.anim = QPropertyAnimation(self.verticalScrollBar(), b"value")
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setDuration(250)
        self.target_scroll_value = 0

    def wheelEvent(self, event):
        num_degrees = event.angleDelta().y()
        if num_degrees == 0:
            super().wheelEvent(event)
            return

        bar = self.verticalScrollBar()
        step = -int(num_degrees * 0.9)

        if self.anim.state() == QPropertyAnimation.State.Running:
            start_val = self.anim.currentValue()
            target_val = self.target_scroll_value + step
        else:
            start_val = bar.value()
            target_val = bar.value() + step

        target_val = max(0, min(bar.maximum(), target_val))
        self.target_scroll_value = target_val

        self.anim.stop()
        self.anim.setStartValue(start_val)
        self.anim.setEndValue(target_val)
        self.anim.start()

        event.accept()


class SmoothListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.anim = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setDuration(250)
        self.target_scroll_value = 0

    def wheelEvent(self, event):
        num_degrees = event.angleDelta().y()
        if num_degrees == 0:
            super().wheelEvent(event)
            return

        bar = self.verticalScrollBar()
        step = -int(num_degrees * 0.9)

        if self.anim.state() == QPropertyAnimation.State.Running:
            start_val = self.anim.currentValue()
            target_val = self.target_scroll_value + step
        else:
            start_val = bar.value()
            target_val = bar.value() + step

        target_val = max(bar.minimum(), min(bar.maximum(), target_val))
        self.target_scroll_value = target_val

        self.anim.stop()
        self.anim.setStartValue(int(start_val))
        self.anim.setEndValue(target_val)
        self.anim.start()
        event.accept()


class ClickableTitleLabel(QLabel):
    def __init__(self, title_text: str, url_string: str = "", parent=None):
        super().__init__(title_text, parent)
        self.url_string = url_string
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setWordWrap(True)
        self.setObjectName("lbl_title")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.url_string:
            QDesktopServices.openUrl(QUrl(self.url_string))
        super().mousePressEvent(event)