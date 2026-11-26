from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QCursor, QDesktopServices

from src.system.BasicUi import SmoothListWidget, SmoothScrollArea


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