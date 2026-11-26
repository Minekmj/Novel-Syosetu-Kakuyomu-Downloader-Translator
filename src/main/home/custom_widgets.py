from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QFontMetrics, QPainter

from src.system.BasicUi import SmoothScrollArea


class ThreadProgressBridge(QObject):
    progress_updated = Signal(str)

    def setText(self, text):
        self.progress_updated.emit(str(text))


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