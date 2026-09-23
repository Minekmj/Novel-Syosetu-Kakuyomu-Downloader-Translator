from PySide6.QtCore import QThread, QUrl, Signal, Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit,
    QDialog,
    QFrame, QApplication
)
from PySide6.QtGui import QCursor, QDesktopServices

from src.find.site_list import Sites, get_search_class, site_point_text
from src.trans.trans import Translator

import src.find.tag as tag_ui

class ClickableUrlLabel(QLabel):
    def __init__(self, url_string, parent=None):
        super().__init__(url_string, parent)
        self.url_string = url_string
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setWordWrap(True)
        self.setObjectName('lbl_url')

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl(self.url_string))
        super().mousePressEvent(event)

class DetailWorker(QThread):
    finished = Signal(str, str)

    def __init__(self, work_url, auto_translate, site):
        super().__init__()
        self.work_url = work_url
        self.auto_translate = auto_translate
        self.site = site

    def run(self):
        try:
            search_class = get_search_class(self.site)
            description = search_class.fetch_detail_description(self.work_url)
            translated_desc = description

            if self.auto_translate and description:
                try:
                    translated_desc = Translator(description, True)
                except Exception as e:
                    translated_desc = f'[번역 오류: {e}]\n\n{description}'

            self.finished.emit(description, translated_desc)
        except Exception as e:
            print(f'상세 정보 오류: {e}')
            self.finished.emit('', '')


class CopyTagButton(QPushButton):
    def __init__(self, display_text, original_text, parent=None):
        super().__init__(display_text, parent)
        self.display_text = display_text
        self.original_text = original_text
        self.setObjectName('btn')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self.copy_original_tag)

    def copy_original_tag(self):
        QApplication.clipboard().setText(self.original_text)
        self.setText('✓ 복사됨')
        QTimer.singleShot(800, lambda: self.setText(self.display_text))


class DetailDialog(QDialog):
    def __init__(self, item_data, auto_translate, site, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.auto_translate = auto_translate
        self.site = site

        self.setWindowTitle('작품 상세 정보')
        self.resize(760, 760)
        self.setMinimumSize(620, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 20)
        layout.setSpacing(12)

        title = self.item_data.get(
            'title_ko',
            self.item_data.get('title', '')
        )
        original_title = self.item_data.get('title', '')
        stars_value = self.item_data.get('stars', '')
        status_value = self.item_data.get('status_episodes', '')
        updated_value = self.item_data.get('updated_at', '')
        url = self.item_data.get('url', '')

        title_label = QLabel(title)
        title_label.setObjectName('detail_dialog_title')
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        if original_title and original_title != title:
            original_label = QLabel(original_title)
            original_label.setObjectName('detail_original_title')
            original_label.setWordWrap(True)
            layout.addWidget(original_label)

        meta_frame = QFrame()
        meta_frame.setObjectName('detail_meta')

        meta_layout = QHBoxLayout(meta_frame)
        meta_layout.setContentsMargins(13, 10, 13, 10)
        meta_layout.setSpacing(18)

        rating_label = QLabel(site_point_text(self.site, stars_value))
        rating_label.setObjectName('detail_rating')
        meta_layout.addWidget(rating_label)

        if status_value:
            status_label = QLabel(str(status_value))
            status_label.setObjectName('detail_meta_text')
            meta_layout.addWidget(status_label)

        if updated_value:
            updated_label = QLabel(f'최근 갱신  ·  {updated_value}')
            updated_label.setObjectName('detail_meta_text')
            meta_layout.addWidget(updated_label)

        meta_layout.addStretch()
        layout.addWidget(meta_frame)

        if url:
            url_title = QLabel('작품 주소')
            url_title.setObjectName('detail_section_title')
            layout.addWidget(url_title)

            url_label = ClickableUrlLabel(str(url))
            url_label.setObjectName('detail_url')
            layout.addWidget(url_label)

        description_title = QLabel('작품 소개')
        description_title.setObjectName('detail_section_title')
        layout.addWidget(description_title)

        self.text_detail = QTextEdit()
        self.text_detail.setObjectName('detail_description')
        self.text_detail.setReadOnly(True)
        self.text_detail.setPlaceholderText('작품 소개가 없습니다.')
        self.text_detail.setText('상세 정보를 불러오는 중입니다...')
        self.text_detail.viewport().setStyleSheet('background: transparent;')
        layout.addWidget(self.text_detail, 1)

        tag_title = QLabel('태그')
        tag_title.setObjectName('detail_section_title')
        layout.addWidget(tag_title)

        tag_desc = QLabel('태그를 클릭하면 일본어 원문이 클립보드에 복사됩니다.')
        tag_desc.setObjectName('dialog_hint')
        layout.addWidget(tag_desc)

        self.tags_widget = QWidget()
        self.tags_widget.setObjectName('detail_tags')
        self.tags_layout = tag_ui.FlowLayout(self.tags_widget, margin=0, spacing=6)
        layout.addWidget(self.tags_widget)

        bottom_line = QFrame()
        bottom_line.setObjectName('dialog_separator')
        bottom_line.setFixedHeight(1)
        layout.addWidget(bottom_line)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 5, 0, 0)
        bottom.addStretch()

        close_button = QPushButton('닫기')
        close_button.setObjectName('secondaryBtn')
        close_button.setMinimumWidth(100)
        close_button.setStyleSheet(
            'QPushButton#secondaryBtn { min-height: 22px; padding: 8px 16px; font-weight: 650; }'
        )
        close_button.clicked.connect(self.accept)
        bottom.addWidget(close_button)

        add_button = QPushButton('작품 추가')
        add_button.setObjectName('primaryBtn')
        add_button.setMinimumWidth(100)
        add_button.clicked.connect(self.on_add_clicked)
        bottom.addWidget(add_button)

        layout.addLayout(bottom)
        self.load_detail()

    def load_detail(self):
        target_url = self.item_data.get(
            'url' if (self.site == Sites.KAKUYOMU or self.site == Sites.HAMELLEUN or self.site == Sites.HAMELLEUN18) else 'story',
            ''
        )

        self.worker = DetailWorker(
            target_url,
            self.auto_translate,
            self.site
        )

        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, raw_desc, translated_desc):
        raw_data = str(raw_desc).split('_____1234_____')
        translated_data = str(translated_desc).split('_____1234_____')

        description = translated_data[0].strip()

        self.text_detail.setText(
            description if (description and description != "error") else '작품 소개가 없습니다.'
        )

        original_tags = []
        translated_tags = []

        if len(raw_data) > 1 and raw_data[1].strip():
            original_tags = [
                tag.strip() for tag in raw_data[1].strip().split(',')
                if tag.strip()
            ]

        if len(translated_data) > 1 and translated_data[1].strip():
            translated_tags = [
                tag.strip() for tag in translated_data[1].strip().split(',')
                if tag.strip()
            ]

        if original_tags:
            self.display_tags(original_tags, translated_tags)

    def display_tags(self, original_tags, translated_tags=None):
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        translated_tags = translated_tags or []

        for index, original_tag in enumerate(original_tags):
            display_text = (
                translated_tags[index]
                if index < len(translated_tags)
                else original_tag
            )

            button = CopyTagButton(display_text, original_tag)
            button.setObjectName('detail_tag_btn')
            self.tags_layout.addWidget(button)

    def on_add_clicked(self):
        global click_plus_url, click

        click_plus_url = self.item_data.get('url', '')
        click = True
        self.accept()
        
click = False
click_plus_url = ''