import re
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QTextEdit
from .constants import KO_RANGES, JP_RANGES, JP_PATTERN

SEMI_TRANS_BTN_STYLE = '''
    QPushButton#semiTransBtn {
        background-color: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 5px;
        color: palette(text);
        font-size: 11px;
        padding: 0px 6px;
    }
    QPushButton#semiTransBtn:hover {
        background-color: rgba(255, 255, 255, 0.15);
        border-color: rgba(255, 255, 255, 0.22);
    }
    QPushButton#semiTransBtn:pressed {
        background-color: rgba(255, 255, 255, 0.05);
        padding-top: 1px;
    }
    QPushButton#semiTransBtn:disabled {
        background-color: rgba(255, 255, 255, 0.02);
        border-color: rgba(255, 255, 255, 0.05);
        color: rgba(255, 255, 255, 0.25);
    }
'''


def bind_height_sync(*widgets):
    def sync():
        h = max(max(w.sizeHint().height(), w.height()) for w in widgets)
        for w in widgets:
            w.setFixedHeight(h)

    for w in widgets:
        if hasattr(w, 'document'):
            w.document().documentLayout().documentSizeChanged.connect(sync)
    sync()


class SuspiciousPatternHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.jp_format = QTextCharFormat()
        self.jp_format.setBackground(QColor("#ffff00"))
        self.jp_format.setForeground(QColor("#000000"))
        self.jp_format.setFontWeight(700)

        self.suspicious_format = QTextCharFormat()
        self.suspicious_format.setBackground(QColor("#ffaa00"))
        self.suspicious_format.setForeground(QColor("#000000"))
        self.suspicious_format.setFontWeight(700)

        self.suspicious_regexes = [
            re.compile(rf'[{KO_RANGES}{JP_RANGES}]+[\(（][^\(\)（）]+[\)）]'),
            re.compile(r'[-=]>\s*[^\n]+'),
            re.compile(r'\(Wait[^\)]*\)', re.IGNORECASE),
            re.compile(r'[-―~]ん'),
            re.compile(r'[っッｯー]{2,}')
        ]

    def highlightBlock(self, text):
        if not text:
            return

        for r in self.suspicious_regexes:
            for m in r.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), self.suspicious_format)

        for m in JP_PATTERN.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self.jp_format)


class AutoResizingTextEdit(QTextEdit):
    def __init__(self, is_orig=False, parent=None):
        super().__init__(parent)
        self.is_orig = is_orig
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.document().documentLayout().documentSizeChanged.connect(self.adjust_height)
        self.textChanged.connect(self.adjust_height)

        if self.is_orig:
            self.highlighter = SuspiciousPatternHighlighter(self.document())

    def adjust_height(self):
        doc_height = self.document().size().height()
        margins = self.contentsMargins()
        new_height = int(doc_height + margins.top() + margins.bottom() + 16)
        self.setFixedHeight(max(36, new_height))

    def setPlainText(self, text):
        super().setPlainText(text)
        self.adjust_height()