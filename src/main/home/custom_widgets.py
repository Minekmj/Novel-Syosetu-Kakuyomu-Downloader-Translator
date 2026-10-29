from PySide6.QtCore import QObject, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtWidgets import QScrollArea, QLabel
from PySide6.QtGui import QFontMetrics, QPainter

class ThreadProgressBridge(QObject):
    progress_updated = Signal(str)

    def setText(self, text):
        self.progress_updated.emit(str(text))

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

class MarqueeLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._offset = 0
        self._spacing = 40
        self._speed = 2

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._scroll_text)
        self._timer.start(30)

    def setText(self, text):
        super().setText(text)
        self._offset = 0
        self.update()

    def _scroll_text(self):
        fm = QFontMetrics(self.font())
        text_width = fm.horizontalAdvance(self.text())

        if text_width > self.width():
            self._offset += self._speed
            if self._offset >= text_width + self._spacing:
                self._offset = 0
            self.update()
        else:
            if self._offset != 0:
                self._offset = 0
                self.update()

    def paintEvent(self, event):
        if not self.text():
            super().paintEvent(event)
            return

        fm = QFontMetrics(self.font())
        text_width = fm.horizontalAdvance(self.text())

        if text_width <= self.width():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(self.foregroundRole()))

        y = (self.height() + fm.ascent() - fm.descent()) // 2

        x1 = -self._offset
        painter.drawText(x1, y, self.text())

        x2 = x1 + text_width + self._spacing
        painter.drawText(x2, y, self.text())