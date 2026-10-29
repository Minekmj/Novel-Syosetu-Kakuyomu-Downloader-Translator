from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QLabel


class ElidedLabel(QLabel):
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def setText(self, text):
        self._full_text = text
        self._update_elided_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_text()

    def _update_elided_text(self):
        width = self.width()
        if width <= 0:
            return
        metrics = QFontMetrics(self.font())
        super().setText(metrics.elidedText(self._full_text, Qt.ElideRight, width))