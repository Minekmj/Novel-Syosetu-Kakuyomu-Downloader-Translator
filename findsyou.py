import requests

from PySide6.QtCore import QThread, Signal, Qt, QSize, QRect, QPoint, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QComboBox, QCheckBox, QSpinBox, QGroupBox, QDialog,
    QScrollArea, QSizePolicy, QFormLayout, QSplitter,
    QLayout, QFrame, QApplication
)

from trans import Translator
from data import TAG_CATEGORIES, NaroSearch, KakuyomuSearch
import data as data_iteam

click = False
click_plus_url = ''
IS_KAKU = False
istaiain = []

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=4):
        super().__init__(parent)

        self.itemList = []
        self.m_hSpace = spacing
        self.m_vSpace = spacing

        self.setContentsMargins(
            margin,
            margin,
            margin,
            margin
        )

    def __del__(self):
        item = self.takeAt(0)

        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(
            QRect(0, 0, width, 0),
            True
        )

    def setGeometry(self, rect):
        super().setGeometry(rect)

        self.doLayout(
            rect,
            False
        )

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self.itemList:
            size = size.expandedTo(
                item.minimumSize()
            )

        margins = self.contentsMargins()

        size += QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom()
        )

        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            spaceX = self.m_hSpace
            spaceY = self.m_vSpace

            nextX = (
                x
                + item.sizeHint().width()
                + spaceX
            )

            if (
                nextX - spaceX > rect.right()
                and lineHeight > 0
            ):
                x = rect.x()

                y += lineHeight + spaceY

                nextX = (
                    x
                    + item.sizeHint().width()
                    + spaceX
                )

                lineHeight = 0

            if not testOnly:
                item.setGeometry(
                    QRect(
                        QPoint(x, y),
                        item.sizeHint()
                    )
                )

            x = nextX

            lineHeight = max(
                lineHeight,
                item.sizeHint().height()
            )

        return (
            y
            + lineHeight
            - rect.y()
        )

class TagFlowWidget(QWidget):
    def __init__(
        self,
        target_line_edit,
        categories_data,
        parent=None
    ):
        super().__init__(parent)

        self.target_line_edit = target_line_edit
        self.categories_data = categories_data
        self.buttons = {}

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(260)

        container = QWidget()
        container.setObjectName("tag_container")
        
        container_layout = QVBoxLayout(container)
        

        container_layout.setSpacing(12)

        container_layout.setContentsMargins(
            8,
            8,
            8,
            8
        )

        for category_name, tag_map in self.categories_data.items():
            cat_label = QLabel(category_name)

            cat_label.setObjectName('cat_label')

            container_layout.addWidget(
                cat_label
            )

            tag_container = QWidget()
            tag_container.setObjectName("tag_container")

            flow_layout = FlowLayout(
                tag_container,
                margin=0,
                spacing=5
            )

            for ko_name, jp_word in tag_map.items():
                btn = QPushButton(
                    f'+ {ko_name}'
                )

                btn.setCheckable(True)

                btn.setCursor(
                    Qt.CursorShape.PointingHandCursor
                )

                btn.setObjectName('btn')

                btn.clicked.connect(
                    lambda checked,
                    j=jp_word,
                    b=btn,
                    k=ko_name:
                    self.toggle_tag(
                        j,
                        b,
                        k
                    )
                )

                flow_layout.addWidget(btn)

                self.buttons[jp_word] = (
                    btn,
                    ko_name
                )

            container_layout.addWidget(
                tag_container
            )

        container_layout.addStretch()

        scroll.setWidget(container)

        main_layout.addWidget(scroll)

        self.target_line_edit.textChanged.connect(
            self.sync_buttons_from_text
        )

        self.sync_buttons_from_text(
            self.target_line_edit.text()
        )

    def toggle_tag(
        self,
        jp_word,
        button,
        ko_name
    ):
        current_text = (
            self.target_line_edit.text()
            .strip()
        )

        words = (
            current_text.split()
            if current_text
            else []
        )

        if jp_word in words:
            words.remove(jp_word)

            button.setChecked(False)

            button.setText(
                f'+ {ko_name}'
            )

        else:
            words.append(jp_word)

            button.setChecked(True)

            button.setText(
                f'✓ {ko_name}'
            )

        self.target_line_edit.setText(
            ' '.join(words)
        )

    def sync_buttons_from_text(self, text):
        words = text.strip().split()

        for jp_word, data in self.buttons.items():
            btn, ko_name = data

            if jp_word in words:
                btn.setChecked(True)

                btn.setText(
                    f'✓ {ko_name}'
                )

            else:
                btn.setChecked(False)

                btn.setText(
                    f'+ {ko_name}'
                )

class TagSelectDialog(QDialog):
    def __init__(
        self,
        target_line_edit,
        categories_data,
        title='태그 선택',
        parent=None
    ):
        super().__init__(parent)

        self.setWindowTitle(title)

        self.resize(560, 520)

        self.setMinimumSize(
            460,
            400
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            14,
            14,
            14,
            14
        )

        layout.setSpacing(10)

        title_label = QLabel(title)

        title_label.setObjectName(
            'title_label'
        )

        layout.addWidget(
            title_label
        )

        desc = QLabel(
            '태그를 클릭하면 선택 또는 해제됩니다.'
        )

        desc.setObjectName(
            'new_and_now'
        )

        layout.addWidget(desc)

        self.tag_panel = TagFlowWidget(
            target_line_edit,
            categories_data
        )

        layout.addWidget(
            self.tag_panel,
            stretch=1
        )

        bottom_layout = QHBoxLayout()

        bottom_layout.addStretch()

        btn_close = QPushButton('완료')

        btn_close.setObjectName(
            'primaryBtn'
        )

        btn_close.clicked.connect(
            self.accept
        )

        bottom_layout.addWidget(
            btn_close
        )

        layout.addLayout(
            bottom_layout
        )

class SearchWorker(QThread):
    finished = Signal(dict)

    def __init__(
        self,
        search_params,
        is_k
    ):
        super().__init__()

        self.params = search_params
        self.is_k = is_k

    def run(self):
        try:
            if self.is_k:
                url = KakuyomuSearch.build_search_url(
                    **self.params
                )

                response = requests.get(
                    url,
                    headers=KakuyomuSearch.HEADERS,
                    timeout=10
                )

                if response.status_code == 200:
                    result = (
                        KakuyomuSearch
                        .parse_search_results(
                            response.text
                        )
                    )

                    self.finished.emit(result)

                else:
                    self.finished.emit({
                        'is_last_page': True,
                        'items': []
                    })

            else:
                result = (
                    NaroSearch
                    .fetch_search_results(
                        self.params
                    )
                )

                self.finished.emit(result)

        except Exception as e:
            print(
                f'검색 오류: {e}'
            )

            self.finished.emit({
                'is_last_page': True,
                'items': []
            })

class TranserWorker(QThread):
    finished = Signal(str)

    def __init__(self, text):
        super().__init__()

        self.text = text

    def run(self):
        try:
            result = Translator(
                self.text
            )

            self.finished.emit(result)

        except Exception as e:
            print(
                f'번역 오류: {e}'
            )

class DetailWorker(QThread):
    finished = Signal(str, str)

    def __init__(
        self,
        work_url,
        auto_translate,
        is_k
    ):
        super().__init__()

        self.work_url = work_url
        self.auto_translate = auto_translate
        self.is_k = is_k

    def run(self):
        search_class = (
            KakuyomuSearch
            if self.is_k
            else NaroSearch
        )

        description = (
            search_class
            .fetch_detail_description(
                self.work_url
            )
        )

        translated_desc = description

        if (
            self.auto_translate
            and description
        ):
            try:
                translated_desc = Translator(
                    description
                )

            except Exception as e:
                translated_desc = (
                    f'[번역 오류: {e}]\n\n'
                    f'{description}'
                )

        self.finished.emit(
            description,
            translated_desc
        )

class WorkCardWidget(QWidget):
    def __init__(
        self,
        item_data,
        auto_translate,
        data_setter,
        is_k,
        parent=None
    ):
        super().__init__(parent)

        self.item_data = item_data
        self.auto_translate = auto_translate
        self.data_setter = data_setter
        self.is_k = is_k

        self.trans_worker = None

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            0,
            5,
            10,
            5
        )

        card = QFrame()

        card.setObjectName(
            'CardFrame'
        )

        card.setMinimumHeight(112)

        layout = QVBoxLayout(card)

        layout.setContentsMargins(
            16,
            13,
            16,
            13
        )

        layout.setSpacing(7)

        display_title = (
            self.item_data.get(
                'title_ko',
                self.item_data.get(
                    'title',
                    ''
                )
            )
        )

        title_row = QHBoxLayout()

        self.lbl_title = QLabel(
            display_title
        )

        self.lbl_title.setObjectName(
            'lbl_title'
        )

        self.lbl_title.setWordWrap(True)

        title_row.addWidget(
            self.lbl_title,
            stretch=1
        )

        stars = str(
            self.item_data.get(
                'stars',
                '0'
            )
        )

        self.lbl_stars = QLabel(
            f'{"★" if self.is_k else "pt"} {stars}'
        )

        self.lbl_stars.setObjectName(
            'lbl_stars'
        )

        title_row.addWidget(
            self.lbl_stars
        )

        layout.addLayout(
            title_row
        )

        original_title = (
            self.item_data.get(
                'title',
                ''
            )
        )

        if (
            original_title
            and original_title != display_title
        ):
            original_label = QLabel(
                original_title
            )

            original_label.setObjectName(
                'lbl_url'
            )

            layout.addWidget(
                original_label
            )

        meta_row = QHBoxLayout()

        status = str(
            self.item_data.get(
                'status_episodes',
                ''
            )
        )

        updated = str(
            self.item_data.get(
                'updated_at',
                ''
            )
        )

        if status:
            status_label = QLabel(
                status
            )

            status_label.setObjectName(
                'lbl_episodes'
            )

            meta_row.addWidget(
                status_label
            )

        if updated:
            updated_label = QLabel(
                f'최근 갱신 {updated}'
            )

            updated_label.setObjectName(
                'new_and_now'
            )

            meta_row.addWidget(
                updated_label
            )

        meta_row.addStretch()

        layout.addLayout(
            meta_row
        )

        url = str(
            self.item_data.get(
                'url',
                ''
            )
        )

        if url:
            url_label = QLabel(url)

            url_label.setObjectName(
                'lbl_url'
            )

            layout.addWidget(
                url_label
            )

        main_layout.addWidget(card)

        if (
            self.auto_translate
            and display_title
        ):
            self.trans_worker = TranserWorker(
                display_title
            )

            self.trans_worker.finished.connect(
                self.set_text
            )

            self.trans_worker.start()

    def set_text(self, text):
        if not text:
            return

        self.lbl_title.setText(text)

        self.item_data[
            'title_ko'
        ] = text

        if self.data_setter:
            self.data_setter(
                Qt.ItemDataRole.UserRole,
                self.item_data
            )

class CopyTagButton(QPushButton):
    def __init__(
        self,
        display_text,
        original_text,
        parent=None
    ):
        super().__init__(
            display_text,
            parent
        )

        self.display_text = display_text
        self.original_text = original_text

        self.setObjectName('btn')

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.clicked.connect(
            self.copy_original_tag
        )

    def copy_original_tag(self):
        QApplication.clipboard().setText(
            self.original_text
        )

        self.setText('✓ 복사됨')

        QTimer.singleShot(
            800,
            lambda:
            self.setText(
                self.display_text
            )
        )

class DetailDialog(QDialog):
    def __init__(
        self,
        item_data,
        auto_translate,
        is_k,
        parent=None
    ):
        super().__init__(parent)

        self.item_data = item_data
        self.auto_translate = auto_translate
        self.is_k = is_k

        self.setWindowTitle('상세 정보')

        self.resize(700, 720)

        self.setMinimumSize(
            560,
            600
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            20,
            20,
            20,
            20
        )

        layout.setSpacing(12)

        title = self.item_data.get(
            'title_ko',
            self.item_data.get(
                'title',
                ''
            )
        )

        title_label = QLabel(title)

        title_label.setObjectName(
            'label_title'
        )

        title_label.setWordWrap(True)

        layout.addWidget(
            title_label
        )

        meta = QFormLayout()

        original_title = QLabel(
            self.item_data.get(
                'title',
                ''
            )
        )

        original_title.setWordWrap(True)

        stars = QLabel(
            f"{'★' if self.is_k else 'pt'} {self.item_data.get('stars', '')}"
        )

        stars.setObjectName(
            'lbl_stars'
        )

        status = QLabel(
            self.item_data.get(
                'status_episodes',
                ''
            )
        )

        updated = QLabel(
            self.item_data.get(
                'updated_at',
                ''
            )
        )

        url = self.item_data.get(
            'url',
            ''
        )

        url_label = QLabel(
            f"<a href='{url}'>{url}</a>"
        )

        url_label.setOpenExternalLinks(True)

        url_label.setWordWrap(True)

        meta.addRow(
            '원제:',
            original_title
        )

        meta.addRow(
            '평점:',
            stars
        )

        meta.addRow(
            '상태:',
            status
        )

        meta.addRow(
            '업데이트:',
            updated
        )

        meta.addRow(
            'URL:',
            url_label
        )

        layout.addLayout(meta)

        self.text_detail = QTextEdit()

        self.text_detail.setReadOnly(True)

        self.text_detail.setText(
            '상세 정보를 불러오는 중입니다...'
        )

        layout.addWidget(
            self.text_detail,
            stretch=1
        )

        tag_title = QLabel(
            '태그 · 클릭하면 일본어 원문이 복사됩니다'
        )

        tag_title.setObjectName(
            'cat_label'
        )

        layout.addWidget(
            tag_title
        )

        self.tags_widget = QWidget()
        self.tags_widget.setObjectName("tag_container")

        self.tags_layout = FlowLayout(
            self.tags_widget,
            margin=0,
            spacing=6
        )

        layout.addWidget(
            self.tags_widget
        )

        bottom = QHBoxLayout()

        bottom.addStretch()

        add_button = QPushButton('추가')

        add_button.setObjectName(
            'primaryBtn'
        )

        add_button.clicked.connect(
            self.on_add_clicked
        )

        bottom.addWidget(
            add_button
        )

        layout.addLayout(bottom)

        self.load_detail()

    def load_detail(self):
        target_url = (
            self.item_data['url']
            if self.is_k
            else self.item_data['story']
        )

        self.worker = DetailWorker(
            target_url,
            self.auto_translate,
            self.is_k
        )

        self.worker.finished.connect(
            self.on_finished
        )

        self.worker.start()

    def on_finished(
        self,
        raw_desc,
        translated_desc
    ):
        raw_data = (
            str(raw_desc)
            .split('_____tags_____')
        )

        translated_data = (
            str(translated_desc)
            .split('_____tags_____')
        )

        self.text_detail.setText(
            translated_data[0].strip()
        )

        original_tags = []
        translated_tags = []

        if (
            len(raw_data) > 1
            and raw_data[1].strip()
        ):
            original_tags = [
                tag.strip()
                for tag in raw_data[1]
                .strip()
                .split(',')
                if tag.strip()
            ]

        if (
            len(translated_data) > 1
            and translated_data[1].strip()
        ):
            translated_tags = [
                tag.strip()
                for tag in translated_data[1]
                .strip()
                .split(',')
                if tag.strip()
            ]

        if original_tags:
            self.display_tags(
                original_tags,
                translated_tags
            )

    def display_tags(
        self,
        original_tags,
        translated_tags=None
    ):
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        translated_tags = (
            translated_tags
            or []
        )

        for index, original_tag in enumerate(
            original_tags
        ):
            if index < len(translated_tags):
                display_text = (
                    translated_tags[index]
                )

            else:
                display_text = original_tag

            button = CopyTagButton(
                display_text,
                original_tag
            )

            self.tags_layout.addWidget(
                button
            )

    def on_add_clicked(self):
        global click_plus_url
        global click

        click_plus_url = (
            self.item_data.get(
                'url',
                ''
            )
        )

        click = True

class MyListWidget(QListWidget):
    nearBottom = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.verticalScrollBar().valueChanged.connect(
            self.check_scroll
        )

    def check_scroll(self, value):
        bar = self.verticalScrollBar()

        if bar.maximum() <= 0:
            return

        if value >= bar.maximum() - 5:
            self.nearBottom.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        for index in range(self.count()):
            item = self.item(index)

            widget = self.itemWidget(item)

            if widget:
                item.setSizeHint(
                    widget.sizeHint()
                )

class MainWindow_Find(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.is_k = IS_KAKU

        site_name = (
            '카쿠요무'
            if self.is_k
            else '나로우'
        )

        self.setWindowTitle(
            f'{site_name} 작품 검색기'
        )

        self.resize(1200, 850)

        self.setMinimumSize(
            1200,
            800
        )

        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
        )

        self.setStyleSheet(
            data_iteam.MINIMAL_DARK_THEME
        )

        self.current_page = 1

        self.search_results = []

        self.active_search_params = None

        self.is_loading = False
        self.has_searched = False
        self.is_searching_new = False
        self.is_end = False

        self.kaku_include_values = []
        self.kaku_exclude_values = []

        self.naro_include_values = []
        self.naro_exclude_values = []
        self.naro_find_area_values = []

        self.init_ui()

        istaiain.append(self)

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            16,
            16,
            16,
            16
        )

        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        splitter.setHandleWidth(12)

        sidebar = self.build_sidebar()

        content = self.build_content()

        splitter.addWidget(sidebar)

        splitter.addWidget(content)

        splitter.setSizes([
            390,
            810
        ])

        main_layout.addWidget(
            splitter
        )

    def build_sidebar(self):
        sidebar = QWidget()

        layout = QVBoxLayout(sidebar)

        layout.setContentsMargins(
            4,
            4,
            4,
            4
        )

        layout.setSpacing(8)

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        inner = QWidget()

        inner_layout = QVBoxLayout(inner)

        inner_layout.setContentsMargins(
            0,
            0,
            8,
            0
        )

        inner_layout.setSpacing(12)

        self.build_keyword_group(
            inner_layout
        )

        self.build_basic_filter_group(
            inner_layout
        )

        self.check_translate = QCheckBox(
            '제목 / 줄거리 자동 번역'
        )

        self.check_translate.setChecked(True)

        inner_layout.addWidget(
            self.check_translate
        )

        inner_layout.addStretch()

        scroll.setWidget(inner)

        layout.addWidget(
            scroll,
            stretch=1
        )

        self.btn_search = QPushButton(
            '검색 실행'
        )

        self.btn_search.setObjectName(
            'primaryBtn'
        )

        self.btn_search.clicked.connect(
            self.start_new_search
        )

        layout.addWidget(
            self.btn_search
        )

        return sidebar

    def build_keyword_group(
        self,
        parent_layout
    ):
        group = QGroupBox(
            '키워드 설정'
        )
        
        group.setObjectName("group_box")

        layout = QVBoxLayout(group)

        layout.setSpacing(8)

        header = QHBoxLayout()

        header.addWidget(
            QLabel('검색 키워드')
        )

        header.addStretch()

        include_button = QPushButton(
            '태그 선택'
        )

        include_button.setObjectName(
            'secondaryBtn'
        )

        include_button.clicked.connect(
            self.open_include_tag_dialog
        )

        header.addWidget(
            include_button
        )

        layout.addLayout(header)

        self.input_query = QLineEdit()

        self.input_query.setPlaceholderText(
            '포함할 검색어 또는 태그'
        )

        layout.addWidget(
            self.input_query
        )

        exclude_header = QHBoxLayout()

        exclude_header.addWidget(
            QLabel('제외 키워드')
        )

        exclude_header.addStretch()

        exclude_button = QPushButton(
            '태그 선택'
        )

        exclude_button.setObjectName(
            'secondaryBtn'
        )

        exclude_button.clicked.connect(
            self.open_exclude_tag_dialog
        )

        exclude_header.addWidget(
            exclude_button
        )

        layout.addLayout(
            exclude_header
        )

        self.input_exclude = QLineEdit()

        self.input_exclude.setPlaceholderText(
            '제외할 검색어 또는 태그'
        )

        layout.addWidget(
            self.input_exclude
        )

        parent_layout.addWidget(group)

    def create_multi_select_section(
        self,
        layout,
        title,
        options,
        selected_list
    ):
        title_label = QLabel(title)

        title_label.setObjectName(
            'cat_label'
        )

        layout.addWidget(
            title_label
        )

        container = QWidget()
        container.setObjectName("tag_container")

        flow = FlowLayout(
            container,
            margin=0,
            spacing=5
        )

        button_map = {}

        for display_name, value in options.items():
            btn = QPushButton(
                display_name
            )

            btn.setObjectName('btn')

            btn.setCheckable(True)

            btn.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            btn.setChecked(
                value in selected_list
            )

            btn.clicked.connect(
                lambda checked,
                v=value,
                target=selected_list:
                self.toggle_multi_value(
                    checked,
                    v,
                    target
                )
            )

            flow.addWidget(btn)

            button_map[value] = btn

        layout.addWidget(container)

        return button_map

    def toggle_multi_value(
        self,
        checked,
        value,
        selected_list
    ):
        if checked:
            if value not in selected_list:
                selected_list.append(value)

        else:
            if value in selected_list:
                selected_list.remove(value)

    def build_basic_filter_group(
        self,
        parent_layout
    ):
        search_cls = (
            KakuyomuSearch
            if self.is_k
            else NaroSearch
        )

        group = QGroupBox(
            '검색 조건'
        )
        
        group.setObjectName("group_box")

        layout = QVBoxLayout(group)

        layout.setSpacing(10)

        form = QFormLayout()

        form.setSpacing(10)

        self.combo_genre = QComboBox()

        self.combo_genre.addItems(
            list(
                search_cls.GENRES.keys()
            )
        )

        self.combo_serial_status = QComboBox()

        self.combo_serial_status.addItems(
            list(
                search_cls
                .SERIAL_STATUSES
                .keys()
            )
        )

        self.combo_last_published = QComboBox()

        self.combo_last_published.addItems(
            list(
                search_cls
                .LAST_PUBLISHED_PERIODS
                .keys()
            )
        )

        self.spin_min_chars = QSpinBox()

        self.spin_min_chars.setRange(
            0,
            100000000
        )

        self.spin_min_chars.setSingleStep(
            10000
        )

        self.spin_min_chars.setSuffix(
            ' 자'
        )

        self.combo_order = QComboBox()

        self.combo_order.addItems(
            list(
                search_cls
                .SORT_ORDERS
                .keys()
            )
        )

        form.addRow(
            '장르:',
            self.combo_genre
        )

        form.addRow(
            '연재 상태:',
            self.combo_serial_status
        )

        form.addRow(
            '최근 갱신:',
            self.combo_last_published
        )

        form.addRow(
            '최소 글자수:',
            self.spin_min_chars
        )

        self.spin_min_start = QSpinBox()

        self.spin_min_start.setRange(
            0,
            100000000
        )

        self.spin_min_start.setSingleStep(
            100
        )

        self.spin_min_start.setSuffix(
            ' ★' if self.is_k else ' pt'
        )

        form.addRow(
            '최소 포인트:',
            self.spin_min_start
        )

        form.addRow(
            '정렬:',
            self.combo_order
        )

        layout.addLayout(form)

        if self.is_k:
            self.kaku_include_buttons = (
                self.create_multi_select_section(
                    layout,
                    '포함 조건',
                    KakuyomuSearch
                    .FLAG_INCLUSION_AND_EXLUSION,
                    self.kaku_include_values
                )
            )

            self.kaku_exclude_buttons = (
                self.create_multi_select_section(
                    layout,
                    '제외 조건',
                    KakuyomuSearch
                    .FLAG_INCLUSION_AND_EXLUSION,
                    self.kaku_exclude_values
                )
            )

        else:
            data = {}
            for k, v in NaroSearch.FLAG_INCLUSION_AND_EXLUSION.items():
                if v == "stop": continue
                data[k] = v
            self.naro_include_buttons = (
                self.create_multi_select_section(
                    layout,
                    '포함 조건',
                    data,
                    self.naro_include_values
                )
            )

            self.naro_exclude_buttons = (
                self.create_multi_select_section(
                    layout,
                    '제외 조건',
                    NaroSearch
                    .FLAG_INCLUSION_AND_EXLUSION,
                    self.naro_exclude_values
                )
            )

            self.naro_find_area_buttons = (
                self.create_multi_select_section(
                    layout,
                    '검색 범위',
                    NaroSearch.FIND_AREA,
                    self.naro_find_area_values
                )
            )

        parent_layout.addWidget(group)

    def build_content(self):
        content = QWidget()

        layout = QVBoxLayout(content)

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        layout.setSpacing(10)

        header = QFrame()

        header.setObjectName(
            'CardFrame'
        )

        header_layout = QHBoxLayout(
            header
        )

        header_layout.setContentsMargins(
            16,
            10,
            16,
            10
        )

        title = QLabel(
            '검색 결과'
        )

        title.setObjectName(
            'title_label'
        )

        self.result_count_label = QLabel('')

        self.result_count_label.setObjectName(
            'new_and_now'
        )

        header_layout.addWidget(title)

        header_layout.addStretch()

        header_layout.addWidget(
            self.result_count_label
        )

        layout.addWidget(header)

        self.list_widget = MyListWidget()

        self.list_widget.itemClicked.connect(
            self.on_item_clicked
        )

        self.list_widget.nearBottom.connect(
            self.load_next_page_if_needed
        )

        self.list_widget.setSpacing(2)

        self.list_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy
            .ScrollBarAlwaysOff
        )

        layout.addWidget(
            self.list_widget,
            stretch=1
        )

        self.show_panel_message(
            '검색 조건을 설정한 뒤 검색을 실행하세요.'
        )

        return content

    def show_panel_message(self, text):
        self.list_widget.clear()

        item = QListWidgetItem()

        label = QLabel(text)

        label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        label.setObjectName(
            'new_and_now'
        )

        label.setContentsMargins(
            0,
            50,
            0,
            50
        )

        item.setFlags(
            Qt.ItemFlag.NoItemFlags
        )

        item.setSizeHint(
            QSize(
                0,
                180
            )
        )

        self.list_widget.addItem(item)

        self.list_widget.setItemWidget(
            item,
            label
        )

    def open_include_tag_dialog(self):
        dialog = TagSelectDialog(
            self.input_query,
            TAG_CATEGORIES,
            '검색 태그 선택',
            self
        )

        dialog.setStyleSheet(
            data_iteam.MINIMAL_DARK_THEME
        )

        dialog.show()

    def open_exclude_tag_dialog(self):
        dialog = TagSelectDialog(
            self.input_exclude,
            TAG_CATEGORIES,
            '제외 태그 선택',
            self
        )

        dialog.setStyleSheet(
            data_iteam.MINIMAL_DARK_THEME
        )

        dialog.show()

    def start_new_search(self):
        if self.is_loading:
            return

        self.current_page = 1

        self.search_results = []

        self.active_search_params = None

        self.has_searched = False

        self.is_searching_new = True

        self.is_end = False

        self.execute_search(
            True
        )

    def load_next_page_if_needed(self):
        if not self.has_searched:
            return

        if self.is_end:
            return

        if self.is_loading:
            return

        self.current_page += 1

        self.is_searching_new = False

        self.execute_search(
            False
        )

    def execute_search(self, is_new=True):
        if self.is_k:
            self.execute_search_k(
                is_new
            )

        else:
            self.execute_search_n(
                is_new
            )

    def execute_search_n(self, is_new=True):
        if self.is_loading:
            return

        self.is_loading = True

        self.btn_search.setEnabled(False)

        if is_new:
            self.list_widget.clear()

            self.is_end = False

            genre_val = (
                NaroSearch.GENRES.get(
                    self.combo_genre
                    .currentText(),
                    0
                )
            )

            order_val = (
                NaroSearch.SORT_ORDERS.get(
                    self.combo_order
                    .currentText(),
                    'hyoka'
                )
            )

            last_published = (
                NaroSearch
                .LAST_PUBLISHED_PERIODS
                .get(
                    self.combo_last_published
                    .currentText()
                )
            )

            serial_status = (
                NaroSearch
                .SERIAL_STATUSES
                .get(
                    self.combo_serial_status
                    .currentText(),
                    ''
                )
            )

            self.active_search_params = {
                'query':
                    self.input_query
                    .text()
                    .strip(),

                'genre_val':
                    genre_val,

                'exclude_words':
                    self.input_exclude
                    .text()
                    .strip()
                    .split(),

                'min_chars':
                    self.spin_min_chars
                    .value(),
                    
                'min_pt':
                    self.spin_min_start
                    .value(),

                'last_published':
                    last_published,

                'serial_status':
                    serial_status,

                'order':
                    order_val,

                'inclusion_flags':
                    self.naro_include_values
                    .copy(),

                'exlusion_flags':
                    self.naro_exclude_values
                    .copy(),

                'find_areas':
                    self.naro_find_area_values
                    .copy()
            }

        params = (
            self.active_search_params
            .copy()
        )

        params['page'] = (
            self.current_page
        )

        self.search_worker = SearchWorker(
            params,
            False
        )

        self.search_worker.finished.connect(
            self.on_search_finished
        )

        self.search_worker.start()

    def execute_search_k(self, is_new=True):
        if self.is_loading:
            return

        self.is_loading = True

        self.btn_search.setEnabled(False)

        if is_new:
            self.list_widget.clear()

            self.is_end = False

            genre_val = (
                KakuyomuSearch.GENRES.get(
                    self.combo_genre
                    .currentText(),
                    ''
                )
            )

            order_val = (
                KakuyomuSearch.SORT_ORDERS.get(
                    self.combo_order
                    .currentText(),
                    'popular'
                )
            )

            last_published = (
                KakuyomuSearch
                .LAST_PUBLISHED_PERIODS
                .get(
                    self.combo_last_published
                    .currentText(),
                    ''
                )
            )

            serial_status = (
                KakuyomuSearch
                .SERIAL_STATUSES
                .get(
                    self.combo_serial_status
                    .currentText(),
                    ''
                )
            )

            self.active_search_params = {
                'query':
                    self.input_query
                    .text()
                    .strip(),

                'genre_name':
                    genre_val,

                'exclude_words':
                    self.input_exclude
                    .text()
                    .strip()
                    .split(),

                'min_chars':
                    self.spin_min_chars
                    .value(),

                'last_published':
                    last_published,

                'min_start':
                    self.spin_min_start
                    .value(),

                'serial_status':
                    serial_status,

                'order':
                    order_val,

                'inclusion_flag':
                    self.kaku_include_values
                    .copy(),

                'exclusion_flag':
                    self.kaku_exclude_values
                    .copy()
            }

        params = (
            self.active_search_params
            .copy()
        )

        params['page'] = (
            self.current_page
        )

        self.search_worker = SearchWorker(
            params,
            True
        )

        self.search_worker.finished.connect(
            self.on_search_finished
        )

        self.search_worker.start()

    def on_search_finished(self, result):
        self.is_loading = False

        self.btn_search.setEnabled(True)

        items = result.get(
            'items',
            []
        )

        is_last_page = result.get(
            'is_last_page',
            False
        )

        if self.is_searching_new:
            self.has_searched = True

            self.is_searching_new = False

            if not items:
                self.is_end = True

                self.result_count_label.setText(
                    '0개'
                )

                self.show_panel_message(
                    '검색 결과가 없습니다.'
                )

                return

        elif not items:
            self.is_end = True

            self.add_end_message()

            return

        self.search_results.extend(
            items
        )

        for item_data in items:
            list_item = QListWidgetItem()

            card = WorkCardWidget(
                item_data,
                self.check_translate
                .isChecked(),
                list_item.setData,
                self.is_k
            )

            list_item.setSizeHint(
                card.sizeHint()
            )

            list_item.setData(
                Qt.ItemDataRole.UserRole,
                item_data
            )

            self.list_widget.addItem(
                list_item
            )

            self.list_widget.setItemWidget(
                list_item,
                card
            )

        self.result_count_label.setText(
            f'{len(self.search_results)}개 표시'
        )

        if is_last_page:
            self.is_end = True

            self.add_end_message()

        else:
            self.is_end = False

    def add_end_message(self):
        item = QListWidgetItem()

        item.setFlags(
            Qt.ItemFlag.NoItemFlags
        )

        label = QLabel(
            '더 이상 검색 결과가 없습니다'
        )

        label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        label.setObjectName(
            'new_and_now'
        )

        label.setContentsMargins(
            0,
            25,
            0,
            25
        )

        item.setSizeHint(
            QSize(
                0,
                70
            )
        )

        self.list_widget.addItem(
            item
        )

        self.list_widget.setItemWidget(
            item,
            label
        )

    def on_item_clicked(self, list_item):
        item_data = list_item.data(
            Qt.ItemDataRole.UserRole
        )

        if (
            not item_data
            or not isinstance(
                item_data,
                dict
            )
        ):
            return

        dialog = DetailDialog(
            item_data,
            self.check_translate
            .isChecked(),
            self.is_k,
            self
        )

        dialog.setStyleSheet(
            data_iteam.MINIMAL_DARK_THEME
        )

        dialog.show()

    def closeEvent(self, event):
        if self in istaiain:
            istaiain.remove(self)

        super().closeEvent(event)

def rest():
    data_iteam.rest()

    for window in istaiain:
        window.setStyleSheet(
            data_iteam.MINIMAL_DARK_THEME
        )