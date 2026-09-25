from PySide6.QtWidgets import (
    QWidget, QVBoxLayout,
    QPushButton,
    QScrollArea, QDialog, QTextBrowser,
    QSizePolicy
)
from PySide6.QtCore import QSize, Qt
import re

from src.system.src import resource_path

class DynamicTextBrowser(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def sizeHint(self):
        doc_height = int(self.document().size().height())
        return QSize(super().sizeHint().width(), doc_height + 40)


class CollapsibleSection(QWidget):
    def __init__(self, title, markdown_content, parent=None):
        super().__init__(parent)
        self.is_expanded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toggle_button = QPushButton(f"▼ {title}")
        self.toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                padding: 8px;
                border:None;
            }
        """)
        self.toggle_button.setObjectName("isCo")
        self.toggle_button.clicked.connect(self.toggle)
        layout.addWidget(self.toggle_button)

        self.text_browser = DynamicTextBrowser(self)
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setMarkdown(markdown_content)
        self.text_browser.setObjectName('detail_description')
        self.text_browser.viewport().setStyleSheet("background: transparent;")
        
        self.text_browser.setVisible(False)
        layout.addWidget(self.text_browser)

    def toggle(self):
        self.is_expanded = not self.is_expanded
        self.text_browser.setVisible(self.is_expanded)
        
        if self.is_expanded:
            self.text_browser.document().adjustSize()
            self.text_browser.updateGeometry()

        title_text = self.toggle_button.text()[2:]
        if self.is_expanded:
            self.toggle_button.setText(f"▲ {title_text}")
        else:
            self.toggle_button.setText(f"▼ {title_text}")


class UpdateView(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("업데이트")
        self.setFixedSize(600, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)

        try:
            with open(resource_path("MD/update.md"), "r", encoding="UTF-8") as f:
                md_content = f.read()
            
            sections = self.parse_markdown(md_content)
            for i, (title, content) in enumerate(sections):
                section_widget = CollapsibleSection(title, content)
                if i == 0:
                    section_widget.toggle()
                self.scroll_layout.addWidget(section_widget)

        except Exception as e:
            err_browser = QTextBrowser(self)
            err_browser.setText(f"업데이트 내역을 불러오는데 실패했습니다: {e}")
            self.scroll_layout.addWidget(err_browser)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

    def parse_markdown(self, md_text):
        clean_text = re.sub(r'<hr\s*/?>', '', md_text)
        raw_sections = clean_text.split("## ")
        parsed = []
        
        for section in raw_sections:
            if not section.strip():
                continue
            lines = section.strip().split("\n")
            title = lines[0].strip()
            content = "\n".join(lines[1:]).strip()
            parsed.append((title, content))
            
        return parsed