import requests
from PySide6.QtCore import QThread, Signal, Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem,
    QComboBox, QCheckBox, QSpinBox, QGroupBox, QDialog,
    QScrollArea, QFormLayout, QSplitter,  QFrame
)
from src.trans.trans import Translator
from src.system.data import TAG_CATEGORIES
import src.system.data as data_iteam
from src.system.data import load_data

import src.find.tag as tag_ui
import src.find.detail as detail_ui
import src.find.site_list as sl

click = False
click_plus_url = ''
istaiain = []

class SearchWorker(QThread):
    finished = Signal(dict)

    def __init__(self, search_params, site):
        super().__init__()
        self.params = search_params
        self.site = site

    def run(self):
        try:
            config = sl.get_site(self.site)
            search_class = config['search_class']

            if self.site == sl.Sites.KAKUYOMU:
                url = search_class.build_search_url(**self.params)
                response = requests.get(
                    url,
                    headers=search_class.HEADERS,
                    timeout=10
                )

                if response.status_code == 200:
                    result = search_class.parse_search_results(response.text)
                    self.finished.emit(result)
                else:
                    self.finished.emit({'is_last_page': True, 'items': []})
            else:
                result = search_class.fetch_search_results(self.params)
                self.finished.emit(result)

        except Exception as e:
            print(f'검색 오류: {e}')
            self.finished.emit({'is_last_page': True, 'items': []})


class TranserWorker(QThread):
    finished = Signal(str)

    def __init__(self, text):
        super().__init__()
        self.text = text

    def run(self):
        try:
            result = Translator(self.text, True)
            self.finished.emit(result)
        except Exception as e:
            print(f'번역 오류: {e}')

class WorkCardWidget(QWidget):
    def __init__(self, item_data, auto_translate, data_setter, site, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.auto_translate = auto_translate
        self.data_setter = data_setter
        self.site = site
        self.trans_worker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 10, 5)

        card = QFrame()
        card.setObjectName('CardFrame')
        card.setMinimumHeight(112)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(7)

        display_title = self.item_data.get(
            'title_ko',
            self.item_data.get('title', '')
        )

        title_row = QHBoxLayout()

        self.lbl_title = QLabel(display_title)
        self.lbl_title.setObjectName('lbl_title')
        self.lbl_title.setWordWrap(True)
        title_row.addWidget(self.lbl_title, stretch=1)

        stars = str(self.item_data.get('stars', '0'))
        self.lbl_stars = QLabel(sl.site_point_text(self.site, stars))
        self.lbl_stars.setObjectName('lbl_stars')
        title_row.addWidget(self.lbl_stars)

        layout.addLayout(title_row)

        original_title = self.item_data.get('title', '')

        if original_title and original_title != display_title:
            original_label = QLabel(original_title)
            original_label.setObjectName('lbl_url')
            layout.addWidget(original_label)

        meta_row = QHBoxLayout()

        status = str(self.item_data.get('status_episodes', ''))
        updated = str(self.item_data.get('updated_at', ''))

        if status:
            status_label = QLabel(status)
            status_label.setObjectName('lbl_episodes')
            meta_row.addWidget(status_label)

        if updated:
            updated_label = QLabel(f'최근 갱신 {updated}')
            updated_label.setObjectName('new_and_now')
            meta_row.addWidget(updated_label)

        meta_row.addStretch()
        layout.addLayout(meta_row)

        url = str(self.item_data.get('url', ''))

        if url:
            url_label = QLabel(url)
            url_label.setObjectName('lbl_url')
            layout.addWidget(url_label)

        main_layout.addWidget(card)

        if self.auto_translate and display_title:
            self.trans_worker = TranserWorker(display_title)
            self.trans_worker.finished.connect(self.set_text)
            self.trans_worker.start()

    def set_text(self, text):
        if not text:
            return

        self.lbl_title.setText(text)
        self.item_data['title_ko'] = text

        if self.data_setter:
            self.data_setter(Qt.ItemDataRole.UserRole, self.item_data)


class MyListWidget(QListWidget):
    nearBottom = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(200)
        self.debounce_timer.timeout.connect(self._trigger_bottom)

        self.verticalScrollBar().valueChanged.connect(self.check_scroll)

    def check_scroll(self, value=None):
        bar = self.verticalScrollBar()
        cur_val = bar.value() if value is None else value

        if bar.maximum() <= 0 or cur_val >= bar.maximum() - 5:
            self.debounce_timer.start()
        else:
            self.debounce_timer.stop()

    def _trigger_bottom(self):
        bar = self.verticalScrollBar()
        if bar.maximum() <= 0 or bar.value() >= bar.maximum() - 5:
            self.nearBottom.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        for index in range(self.count()):
            item = self.item(index)
            widget = self.itemWidget(item)
            if widget:
                item.setSizeHint(widget.sizeHint())

        self.check_scroll()


class MainWindow_Find(QDialog):
    def __init__(self, site, parent=None):
        super().__init__(parent)

        self.site = site
        self.site_config = sl.get_site(site)
        self.search_class = self.site_config['search_class']

        self.setWindowTitle(f'{self.site_config["name"]} 작품 검색기')
        self.resize(1200, 850)
        self.setMinimumSize(1200, 800)

        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint
        )

        self.setStyleSheet(data_iteam.MINIMAL_DARK_THEME)

        self.current_page = 1
        self.search_results = []
        self.active_search_params = None
        self.is_loading = False
        self.has_searched = False
        self.is_searching_new = True
        self.is_end = False

        self.init_ui()
        istaiain.append(self)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(12)

        sidebar = self.build_sidebar()
        content = self.build_content()

        splitter.addWidget(sidebar)
        splitter.addWidget(content)
        splitter.setSizes([390, 810])

        main_layout.addWidget(splitter)

    def build_sidebar(self):
        sidebar = QWidget()
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 8, 0)
        inner_layout.setSpacing(12)

        self.build_keyword_group(inner_layout)
        self.build_basic_filter_group(inner_layout)

        self.check_translate = QCheckBox('제목 / 줄거리 자동 번역')
        self.check_translate.setChecked(True)
        inner_layout.addWidget(self.check_translate)

        self.check_exclude_existing = QCheckBox('내 작품 목록에 있는 작품 제외')
        self.check_exclude_existing.setChecked(True)
        inner_layout.addWidget(self.check_exclude_existing)

        inner_layout.addStretch()

        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        self.btn_search = QPushButton('검색 실행')
        self.btn_search.setObjectName('primaryBtn')
        self.btn_search.clicked.connect(self.start_new_search)
        layout.addWidget(self.btn_search)

        return sidebar

    def build_keyword_group(self, parent_layout):
        group = QGroupBox('키워드 설정')
        group.setObjectName('group_box')

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(QLabel('검색 키워드'))
        header.addStretch()

        include_button = QPushButton('태그 선택')
        include_button.setObjectName('secondaryBtn')
        include_button.clicked.connect(self.open_include_tag_dialog)
        header.addWidget(include_button)

        layout.addLayout(header)

        self.input_query = QLineEdit()
        self.input_query.setPlaceholderText('포함할 검색어 또는 태그')
        layout.addWidget(self.input_query)

        exclude_header = QHBoxLayout()
        exclude_header.addWidget(QLabel('제외 키워드'))
        exclude_header.addStretch()

        exclude_button = QPushButton('태그 선택')
        exclude_button.setObjectName('secondaryBtn')
        exclude_button.clicked.connect(self.open_exclude_tag_dialog)
        exclude_header.addWidget(exclude_button)

        layout.addLayout(exclude_header)

        self.input_exclude = QLineEdit()
        self.input_exclude.setPlaceholderText('제외할 검색어 또는 태그')
        layout.addWidget(self.input_exclude)

        parent_layout.addWidget(group)

    def create_multi_select_section(self, layout, title, options, selected_list):
        title_label = QLabel(title)
        title_label.setObjectName('cat_label')
        layout.addWidget(title_label)

        container = QWidget()
        container.setObjectName('tag_container')

        flow = tag_ui.FlowLayout(container, margin=0, spacing=5)
        button_map = {}

        for display_name, value in options.items():
            btn = QPushButton(display_name)
            btn.setObjectName('btn')
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setChecked(value in selected_list)

            btn.clicked.connect(
                lambda checked, v=value, target=selected_list:
                self.toggle_multi_value(checked, v, target)
            )

            flow.addWidget(btn)
            button_map[value] = btn

        layout.addWidget(container)
        return button_map

    def toggle_multi_value(self, checked, value, selected_list):
        if checked:
            if value not in selected_list:
                selected_list.append(value)
        elif value in selected_list:
            selected_list.remove(value)

    def build_basic_filter_group(self, parent_layout):
        search_cls = self.search_class

        group = QGroupBox('검색 조건')
        group.setObjectName('group_box')

        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(10)

        self.combo_genre = QComboBox()
        self.combo_genre.addItems(list(search_cls.GENRES.keys()))
        self.combo_genre.hide()

        self.combo_serial_status = QComboBox()
        self.combo_serial_status.addItems(
            list(search_cls.SERIAL_STATUSES.keys())
        )

        self.combo_last_published = QComboBox()
        self.combo_last_published.addItems(
            list(search_cls.LAST_PUBLISHED_PERIODS.keys())
        )

        self.spin_min_chars = QSpinBox()
        self.spin_min_chars.setRange(0, 100000000)
        self.spin_min_chars.setSingleStep(10000)
        self.spin_min_chars.setSuffix(' 자')

        self.spin_min_start = QSpinBox()
        self.spin_min_start.setRange(0, 100000000)
        self.spin_min_start.setSingleStep(100)
        self.spin_min_start.setSuffix(
            ' ★' if self.site_config['has_star'] else ' pt'
        )
        self.spin_min_start.hide()

        self.combo_order = QComboBox()
        self.combo_order.addItems(list(search_cls.SORT_ORDERS.keys()))

        if len(search_cls.GENRES.keys()) > 0:
            self.combo_genre.show()
            form.addRow('장르:', self.combo_genre)
        form.addRow('연재 상태:', self.combo_serial_status)
        form.addRow('최근 갱신:', self.combo_last_published)
        form.addRow('최소 글자수:', self.spin_min_chars)
        if not (getattr(search_cls, "NO_POINT", False)):
            self.spin_min_start.show()
            form.addRow('최소 포인트:', self.spin_min_start)
        form.addRow('정렬:', self.combo_order)

        layout.addLayout(form)

        self.site_config['ui_setup'](self, layout)

        parent_layout.addWidget(group)

    def build_params(self):
        return sl.site_build_params(self)

    def build_content(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QFrame()
        header.setObjectName('CardFrame')

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)

        title = QLabel('검색 결과')
        title.setObjectName('title_label')

        self.result_count_label = QLabel('')
        self.result_count_label.setObjectName('new_and_now')

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.result_count_label)

        layout.addWidget(header)

        self.list_widget = MyListWidget()
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.nearBottom.connect(self.load_next_page_if_needed)
        self.list_widget.setSpacing(2)
        self.list_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        layout.addWidget(self.list_widget, stretch=1)

        self.show_panel_message('검색 조건을 설정한 뒤 검색을 실행하세요.')

        return content

    def show_panel_message(self, text):
        self.list_widget.clear()

        item = QListWidgetItem()
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName('new_and_now')
        label.setContentsMargins(0, 50, 0, 50)

        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(0, 180))

        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, label)

    def open_include_tag_dialog(self):
        dialog = tag_ui.TagSelectDialog(
            self.input_query,
            TAG_CATEGORIES,
            '검색 태그 선택',
            self
        )
        dialog.setStyleSheet(data_iteam.MINIMAL_DARK_THEME)
        dialog.show()

    def open_exclude_tag_dialog(self):
        dialog = tag_ui.TagSelectDialog(
            self.input_exclude,
            TAG_CATEGORIES,
            '제외 태그 선택',
            self
        )
        dialog.setStyleSheet(data_iteam.MINIMAL_DARK_THEME)
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

        self.execute_search(True)

    def load_next_page_if_needed(self):
        if not self.has_searched or self.is_end or self.is_loading:
            return

        self.current_page += 1
        self.is_searching_new = False
        self.execute_search(False)

    def execute_search(self, is_new=True):
        if self.is_loading:
            return

        self.is_loading = True
        self.btn_search.setEnabled(False)

        if is_new:
            self.list_widget.clear()
            self.is_end = False
            self.active_search_params = self.build_params()

        params = self.active_search_params.copy()
        params['page'] = self.current_page

        self.search_worker = SearchWorker(params, self.site)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.start()

    def check_fill_screen(self):
        if self.is_loading or self.is_end or not self.has_searched:
            return
        
        self.list_widget.check_scroll()

    def on_search_finished(self, result):
        self.is_loading = False
        self.btn_search.setEnabled(True)

        items = result.get('items', [])
        is_last_page = result.get('is_last_page', False)

        if self.check_exclude_existing.isChecked():
            user_data = load_data()
            saved_list = user_data.get('list', {})
            e_list = {
                sl.normalize_url(info.get('src', ''))
                for info in saved_list.values()
                if isinstance(info, dict) and info.get('src')
            }
            items = [item for item in items if sl.normalize_url(item.get('url', '')) not in e_list]

        if self.is_searching_new:
            self.has_searched = True
            self.is_searching_new = False

            if not items:
                if is_last_page:
                    self.is_end = True
                    self.result_count_label.setText('0개')
                    self.show_panel_message('검색 결과가 없습니다.')
                    return
                else:
                    QTimer.singleShot(200, self.load_next_page_if_needed)
                    return

        elif not items:
            if is_last_page:
                self.is_end = True
                self.add_end_message()
            else:
                QTimer.singleShot(200, self.load_next_page_if_needed)
            return

        self.search_results.extend(items)

        for item_data in items:
            list_item = QListWidgetItem()

            card = WorkCardWidget(
                item_data,
                self.check_translate.isChecked(),
                list_item.setData,
                self.site
            )

            list_item.setSizeHint(card.sizeHint())
            list_item.setData(Qt.ItemDataRole.UserRole, item_data)

            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, card)

        self.result_count_label.setText(
            f'{len(self.search_results)}개 표시'
        )

        if is_last_page:
            self.is_end = True
            self.add_end_message()
        else:
            self.is_end = False
            QTimer.singleShot(200, self.check_fill_screen)

    def add_end_message(self):
        item = QListWidgetItem()
        item.setFlags(Qt.ItemFlag.NoItemFlags)

        label = QLabel('더 이상 검색 결과가 없습니다')
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName('new_and_now')
        label.setContentsMargins(0, 25, 0, 25)

        item.setSizeHint(QSize(0, 70))

        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, label)

    def on_item_clicked(self, list_item):
        item_data = list_item.data(Qt.ItemDataRole.UserRole)

        if not item_data or not isinstance(item_data, dict):
            return

        dialog = detail_ui.DetailDialog(
            item_data,
            self.check_translate.isChecked(),
            self.site,
            self
        )

        dialog.setStyleSheet(data_iteam.MINIMAL_DARK_THEME)
        dialog.show()

    def closeEvent(self, event):
        if self in istaiain:
            istaiain.remove(self)

        super().closeEvent(event)


def rest():
    data_iteam.rest()

    for window in istaiain:
        window.setStyleSheet(data_iteam.MINIMAL_DARK_THEME)