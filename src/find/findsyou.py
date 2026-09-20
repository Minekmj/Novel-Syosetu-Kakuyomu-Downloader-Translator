import requests
from enum import IntEnum
from PySide6.QtCore import QThread, Signal, Qt, QSize, QRect, QPoint, QTimer, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QComboBox, QCheckBox, QSpinBox, QGroupBox, QDialog,
    QScrollArea, QSizePolicy, QFormLayout, QSplitter,
    QLayout, QFrame, QApplication, QTabWidget, QMenu,
    QMessageBox, QInputDialog
)
from PySide6.QtGui import QCursor, QDesktopServices, QAction
from src.trans.trans import Translator
from src.system.data import TAG_CATEGORIES, NaroSearch, KakuyomuSearch, MidnightSearch, NocturneSearch, SyosetuSearch, SyosetuSearch18
import src.system.data as data_iteam
from src.system.data import load_data, save_data

USER_TAGS_SRC = "./tag_user.json"

click = False
click_plus_url = ''
istaiain = []


def normalize_url(url):
    if not url:
        return ''
    return url.strip().rstrip('/')


class Sites(IntEnum):
    NAROU = 1
    KAKUYOMU = 2
    HAMELLEUN = 3
    MIDNIGHT = 4
    NOCTURNE = 5
    HAMELLEUN18 = 6


SITES = {
    Sites.NAROU: {
        'name': '나로우',
        'search_class': NaroSearch,
        'point_text': lambda value: f'pt {value}',
        'has_star': False,
        'ui_setup': lambda window, layout: na_set_ui(window, layout),
        'build_params': lambda window: na_build_params(window),
    },
    Sites.KAKUYOMU: {
        'name': '카쿠요무',
        'search_class': KakuyomuSearch,
        'point_text': lambda value: f'★ {value}',
        'has_star': True,
        'ui_setup': lambda window, layout: kaku_set_ui(window, layout),
        'build_params': lambda window: kaku_build_params(window),
    },
    Sites.HAMELLEUN: {
        'name': '하멜른',
        'search_class': SyosetuSearch,
        'point_text': lambda value: f'{value}',
        'has_star': False,
        'ui_setup': lambda window, layout: ha_set_ui(window, layout),
        'build_params': lambda window: ha_build_params(window),
    },
    Sites.MIDNIGHT: {
        'name': '미드나이트',
        'search_class': MidnightSearch,
        'point_text': lambda value: f'pt {value}',
        'has_star': False,
        'ui_setup': lambda window, layout: na_set_ui(window, layout),
        'build_params': lambda window: na_build_params(window),
    },
    Sites.NOCTURNE: {
        'name': '녹턴',
        'search_class': NocturneSearch,
        'point_text': lambda value: f'pt {value}',
        'has_star': False,
        'ui_setup': lambda window, layout: na_set_ui(window, layout),
        'build_params': lambda window: na_build_params(window),
    },
    Sites.HAMELLEUN18: {
        'name': '하멜른18',
        'search_class': SyosetuSearch18,
        'point_text': lambda value: f'{value}',
        'has_star': False,
        'ui_setup': lambda window, layout: ha18_set_ui(window, layout),
        'build_params': lambda window: ha_build_params(window),
    }
}

def get_site(site):
    if site not in SITES:
        raise ValueError(f'지원하지 않는 사이트입니다: {site}')
    return SITES[site]


def get_site_name(site):
    return get_site(site)['name']


def get_search_class(site):
    return get_site(site)['search_class']


def site_point_text(site, value):
    return get_site(site)['point_text'](value)


def site_is_kaku(site):
    return site == Sites.KAKUYOMU


def na_set_ui(window, layout):
    window.naro_include_values = []
    window.naro_exclude_values = []
    window.naro_find_area_values = []

    data = {}

    for k, v in NaroSearch.FLAG_INCLUSION_AND_EXLUSION.items():
        if v == 'stop':
            continue
        data[k] = v

    window.naro_include_buttons = window.create_multi_select_section(
        layout, '포함 조건', data, window.naro_include_values
    )

    window.naro_exclude_buttons = window.create_multi_select_section(
        layout, '제외 조건',
        NaroSearch.FLAG_INCLUSION_AND_EXLUSION,
        window.naro_exclude_values
    )

    window.naro_find_area_buttons = window.create_multi_select_section(
        layout, '검색 범위',
        NaroSearch.FIND_AREA,
        window.naro_find_area_values
    )
    
def ha_set_ui(window, layout):
    ha_set_ui_main(window, layout, SyosetuSearch)
    
def ha18_set_ui(window, layout):
    ha_set_ui_main(window, layout, SyosetuSearch18)

def ha_set_ui_main(window, layout, l):
    cache_key = 'hameln_flags_main' if l == SyosetuSearch else 'hameln18_flags_main'
    l.set_flag()
    saved_data = load_data()
    cached_flags = saved_data.get(cache_key)
    if cached_flags and isinstance(cached_flags, dict):
        l.FLAGS_MAIN = cached_flags
    elif not getattr(l, 'FLAGS_MAIN', None):
        try:
            l.set_flag()
        except Exception:
            pass

    window.naro_exclude_values = []
    window.naro_find_area_values = []
    window.ha_selected_origin = ''

    origin_header = QHBoxLayout()
    origin_label = QLabel('주요 원작')
    origin_label.setObjectName('cat_label')
    origin_header.addWidget(origin_label)
    origin_header.addStretch()

    btn_load_origin = QPushButton('최신 주요 원작 불러오기')
    btn_load_origin.setObjectName('secondaryBtn')
    origin_header.addWidget(btn_load_origin)
    layout.addLayout(origin_header)

    window.combo_ha_origin = QComboBox()
    window.combo_ha_origin.setSizeAdjustPolicy(
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    window.combo_ha_origin.setMinimumContentsLength(10)
    window.combo_ha_origin.setSizePolicy(
        QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
    )
    if window.combo_ha_origin.view():
        window.combo_ha_origin.view().setTextElideMode(Qt.TextElideMode.ElideRight)

    layout.addWidget(window.combo_ha_origin)

    window.input_ha_origin = QLineEdit()
    window.input_ha_origin.setPlaceholderText('원작 직접 입력')
    layout.addWidget(window.input_ha_origin)

    def populate_origin_combo(flags_dict):
        window.combo_ha_origin.blockSignals(True)
        window.combo_ha_origin.clear()
        window.combo_ha_origin.addItem('전체', '')
        if flags_dict:
            for ko_name, jp_name in flags_dict.items():
                window.combo_ha_origin.addItem(ko_name, jp_name)
        window.combo_ha_origin.blockSignals(False)

    populate_origin_combo(l.FLAGS_MAIN if getattr(l, 'FLAGS_MAIN', None) else {})

    def on_origin_combo_changed(index):
        chosen = window.combo_ha_origin.currentData() or ''
        window.ha_selected_origin = chosen
        window.input_ha_origin.setText(chosen)

    window.combo_ha_origin.currentIndexChanged.connect(on_origin_combo_changed)

    def reload_flags_main():
        btn_load_origin.setEnabled(False)
        btn_load_origin.setText('불러오는 중...')
        try:
            new_flags = l.load_flags_main()
            if new_flags and isinstance(new_flags, dict):
                l.FLAGS_MAIN = new_flags
                cur_data = load_data()
                cur_data[cache_key] = new_flags
                save_data(cur_data)
                populate_origin_combo(new_flags)
                btn_load_origin.setText('불러오기 완료')
            else:
                btn_load_origin.setText('불러오기 실패')
        except Exception as e:
            print(f'주요 원작 불러오기 오류: {e}')
            btn_load_origin.setText('불러오기 실패')
        finally:
            QTimer.singleShot(1500, lambda: (
                btn_load_origin.setEnabled(True),
                btn_load_origin.setText('최신 주요 원작 불러오기')
            ))

    btn_load_origin.clicked.connect(reload_flags_main)

    data = {}
    for k, v in l.FLAG_EXCLUSION.items():
        if v == 'stop':
            continue
        data[k] = v
        
    window.naro_exclude_buttons = window.create_multi_select_section(
        layout, '제외 조건',
        l.FLAG_EXCLUSION,
        window.naro_exclude_values
    )


def kaku_set_ui(window, layout):
    window.kaku_include_values = []
    window.kaku_exclude_values = []

    window.kaku_include_buttons = window.create_multi_select_section(
        layout,
        '포함 조건',
        KakuyomuSearch.FLAG_INCLUSION_AND_EXLUSION,
        window.kaku_include_values
    )

    window.kaku_exclude_buttons = window.create_multi_select_section(
        layout,
        '제외 조건',
        KakuyomuSearch.FLAG_INCLUSION_AND_EXLUSION,
        window.kaku_exclude_values
    )
    

def na_build_params(window):
    return {
        'query': window.input_query.text().strip(),
        'genre_val': NaroSearch.GENRES.get(
            window.combo_genre.currentText(), 0
        ),
        'exclude_words': window.input_exclude.text().strip().split(),
        'min_chars': window.spin_min_chars.value(),
        'min_pt': window.spin_min_start.value(),
        'last_published': NaroSearch.LAST_PUBLISHED_PERIODS.get(
            window.combo_last_published.currentText()
        ),
        'serial_status': NaroSearch.SERIAL_STATUSES.get(
            window.combo_serial_status.currentText(), ''
        ),
        'order': NaroSearch.SORT_ORDERS.get(
            window.combo_order.currentText(), 'hyoka'
        ),
        'inclusion_flags': window.naro_include_values.copy(),
        'exlusion_flags': window.naro_exclude_values.copy(),
        'find_areas': window.naro_find_area_values.copy()
    }
    

def ha_build_params(window):
    selected_origin = getattr(window, 'ha_selected_origin', '')
    if hasattr(window, 'input_ha_origin'):
        custom = window.input_ha_origin.text().strip()
        if custom:
            selected_origin = custom

    return {
        'query': window.input_query.text().strip(),
        'genre_val': SyosetuSearch.GENRES.get(
            window.combo_genre.currentText(), 0
        ),
        'flags_main': selected_origin,
        'origin': selected_origin,
        'exclude_words': window.input_exclude.text().strip().split(),
        'min_chars': window.spin_min_chars.value(),
        'min_pt': window.spin_min_start.value(),
        'last_published': SyosetuSearch.LAST_PUBLISHED_PERIODS.get(
            window.combo_last_published.currentText()
        ),
        'serial_status': SyosetuSearch.SERIAL_STATUSES.get(
            window.combo_serial_status.currentText(), ''
        ),
        'order': SyosetuSearch.SORT_ORDERS.get(
            window.combo_order.currentText(), 'hyoka'
        ),
        'exlusion_flags': window.naro_exclude_values.copy(),
        'find_areas': window.naro_find_area_values.copy()
    }
    

def kaku_build_params(window):
    return {
        'query': window.input_query.text().strip(),
        'genre_name': KakuyomuSearch.GENRES.get(
            window.combo_genre.currentText(), ''
        ),
        'exclude_words': window.input_exclude.text().strip().split(),
        'min_chars': window.spin_min_chars.value(),
        'last_published': KakuyomuSearch.LAST_PUBLISHED_PERIODS.get(
            window.combo_last_published.currentText(), ''
        ),
        'min_start': window.spin_min_start.value(),
        'serial_status': KakuyomuSearch.SERIAL_STATUSES.get(
            window.combo_serial_status.currentText(), ''
        ),
        'order': KakuyomuSearch.SORT_ORDERS.get(
            window.combo_order.currentText(), 'popular'
        ),
        'inclusion_flag': window.kaku_include_values.copy(),
        'exclusion_flag': window.kaku_exclude_values.copy()
    }

def site_build_params(window):
    return get_site(window.site)['build_params'](window)


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


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=4):
        super().__init__(parent)
        self.itemList = []
        self.m_hSpace = spacing
        self.m_vSpace = spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        while self.takeAt(0):
            pass

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        return self.itemList[index] if 0 <= index < len(self.itemList) else None

    def takeAt(self, index):
        return self.itemList.pop(index) if 0 <= index < len(self.itemList) else None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
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
            hint = item.sizeHint()
            nextX = x + hint.width() + spaceX

            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y += lineHeight + spaceY
                nextX = x + hint.width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), hint))

            x = nextX
            lineHeight = max(lineHeight, hint.height())

        return y + lineHeight - rect.y()


class TagFlowWidget(QWidget):
    def __init__(self, target_line_edit, categories_data, parent=None):
        super().__init__(parent)
        self.target_line_edit = target_line_edit
        self.categories_data = categories_data or {}
        self.buttons = {}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 6, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setObjectName('tag_container')
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(10)
        container_layout.setContentsMargins(4, 4, 4, 4)

        for category_name, tag_map in self.categories_data.items():
            if not isinstance(tag_map, dict):
                continue
            cat_label = QLabel(category_name)
            cat_label.setObjectName('cat_label')
            container_layout.addWidget(cat_label)

            tag_container = QWidget()
            tag_container.setObjectName('tag_container')
            flow_layout = FlowLayout(tag_container, margin=0, spacing=4)

            for ko_name, jp_word in tag_map.items():
                btn = QPushButton(f'+ {ko_name}')
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setObjectName('btn')
                btn.clicked.connect(
                    lambda checked, j=jp_word, b=btn, k=ko_name:
                    self.toggle_tag(j, b, k)
                )
                flow_layout.addWidget(btn)
                self.buttons[jp_word] = (btn, ko_name)

            container_layout.addWidget(tag_container)

        container_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.target_line_edit.textChanged.connect(self.sync_buttons_from_text)
        self.sync_buttons_from_text(self.target_line_edit.text())

    def toggle_tag(self, jp_word, button, ko_name):
        current_text = self.target_line_edit.text().strip()
        words = current_text.split() if current_text else []

        if jp_word in words:
            words.remove(jp_word)
            button.setChecked(False)
            button.setText(f'+ {ko_name}')
        else:
            words.append(jp_word)
            button.setChecked(True)
            button.setText(f'✓ {ko_name}')

        self.target_line_edit.setText(' '.join(words))

    def sync_buttons_from_text(self, text):
        words = text.strip().split()

        for jp_word, (btn, ko_name) in self.buttons.items():
            if jp_word in words:
                btn.setChecked(True)
                btn.setText(f'✓ {ko_name}')
            else:
                btn.setChecked(False)
                btn.setText(f'+ {ko_name}')


class UserTagWidget(QWidget):
    def __init__(self, target_line_edit, parent=None):
        super().__init__(parent)
        self.target_line_edit = target_line_edit
        self.buttons = {}
        self.user_tags = {}
        self.init_ui()
        self.load_user_tags()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 8, 0, 0)
        main_layout.setSpacing(8)

        panel = QFrame()
        panel.setStyleSheet("""
            QLineEdit, QComboBox {
                border-radius: 7px;
                padding: 4px 8px;
                min-height: 22px;
                font-size: 12px;
            }
            QPushButton {
                border-radius: 7px;
                min-height: 22px;
                font-size: 12px;
            }
            QFrame {background: transparent;}
        """)

        p_layout = QVBoxLayout(panel)
        p_layout.setContentsMargins(10, 10, 10, 10)
        p_layout.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        cat_title = QLabel('분류')
        cat_title.setObjectName('cat_label')
        row1.addWidget(cat_title)

        self.combo_category = QComboBox()
        self.combo_category.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row1.addWidget(self.combo_category)

        btn_new_cat = QPushButton('+ 분류 추가')
        btn_new_cat.setObjectName('secondaryBtn')
        btn_new_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_cat.clicked.connect(self.prompt_add_category)
        row1.addWidget(btn_new_cat)

        btn_del_cat = QPushButton('분류 삭제')
        btn_del_cat.setObjectName('secondaryBtn')
        btn_del_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del_cat.clicked.connect(self.delete_current_category)
        row1.addWidget(btn_del_cat)

        p_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)

        self.input_jp = QLineEdit()
        self.input_jp.setPlaceholderText('일본어(입력 용)')
        row2.addWidget(self.input_jp)

        self.input_ko = QLineEdit()
        self.input_ko.setPlaceholderText('한국어(보이는 용)')
        row2.addWidget(self.input_ko)
        p_layout.addLayout(row2)
        
        p_layout.addStretch(1)
        
        row3 = QHBoxLayout()
        row3.setSpacing(6)

        self.btn_add_tag = QPushButton('태그 추가')
        self.btn_add_tag.setObjectName('secondaryBtn')
        self.btn_add_tag.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_tag.clicked.connect(self.add_tag)
        row2.addWidget(self.btn_add_tag)

        p_layout.addLayout(row3)
        main_layout.addWidget(panel)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.container = QWidget()
        self.container.setObjectName('tag_container')
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setSpacing(10)
        self.container_layout.setContentsMargins(4, 4, 4, 4)

        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll, stretch=1)

        self.target_line_edit.textChanged.connect(self.sync_buttons_from_text)

    def load_user_tags(self):
        try:
            loaded = load_data(USER_TAGS_SRC)
            if isinstance(loaded, dict):
                self.user_tags = loaded
            else:
                self.user_tags = {}
        except Exception:
            self.user_tags = {}

        self.refresh_ui()

    def save_user_tags(self):
        try:
            save_data(self.user_tags, USER_TAGS_SRC)
        except Exception as e:
            print(f'사용자 태그 저장 실패: {e}')

    def prompt_add_category(self):
        cat_name, ok = QInputDialog.getText(self, '분류 추가', '새로운 분류(카테고리) 이름을 입력하세요:')
        if ok and cat_name.strip():
            c = cat_name.strip()
            if c not in self.user_tags:
                self.user_tags[c] = {}
                self.save_user_tags()
                self.refresh_ui()
                self.combo_category.setCurrentText(c)
            else:
                self.combo_category.setCurrentText(c)

    def delete_current_category(self):
        cur_cat = self.combo_category.currentText().strip()
        if not cur_cat:
            return

        confirm = QMessageBox.question(
            self, '분류 삭제',
            f"'{cur_cat}' 분류와 그 안의 모든 태그를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            if cur_cat in self.user_tags:
                del self.user_tags[cur_cat]
                self.save_user_tags()
                self.refresh_ui()

    def refresh_ui(self):
        cur_selected = self.combo_category.currentText().strip()
        self.combo_category.blockSignals(True)
        self.combo_category.clear()

        categories = list(self.user_tags.keys())
        if categories:
            self.combo_category.addItems(categories)
            if cur_selected in categories:
                self.combo_category.setCurrentText(cur_selected)
        self.combo_category.blockSignals(False)

        self.buttons.clear()
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.user_tags:
            no_tag = QLabel('등록된 사용자 태그가 없습니다.\n위에서 분류를 추가하고 원하는 태그를 등록해보세요.')
            no_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_tag.setObjectName('new_and_now')
            self.container_layout.addWidget(no_tag)
            self.container_layout.addStretch()
            return

        for category_name, tag_map in self.user_tags.items():
            cat_label = QLabel(category_name)
            cat_label.setObjectName('cat_label')
            self.container_layout.addWidget(cat_label)

            tag_container = QWidget()
            tag_container.setObjectName('tag_container')
            flow_layout = FlowLayout(tag_container, margin=0, spacing=4)

            if isinstance(tag_map, dict) and tag_map:
                for ko_name, jp_word in tag_map.items():
                    btn = QPushButton(f'+ {ko_name}')
                    btn.setCheckable(True)
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setObjectName('btn')
                    btn.setToolTip(f'원문: {jp_word}\n(우클릭 시 태그 삭제)')

                    btn.clicked.connect(
                        lambda checked, j=jp_word, b=btn, k=ko_name:
                        self.toggle_tag(j, b, k)
                    )

                    btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                    btn.customContextMenuRequested.connect(
                        lambda pos, c=category_name, k=ko_name, j=jp_word, b=btn:
                        self.show_tag_context_menu(pos, c, k, j, b)
                    )

                    flow_layout.addWidget(btn)
                    self.buttons[jp_word] = (btn, ko_name)
            else:
                hint = QLabel('(비어있는 분류)')
                hint.setObjectName('new_and_now')
                flow_layout.addWidget(hint)

            self.container_layout.addWidget(tag_container)

        self.container_layout.addStretch()
        self.sync_buttons_from_text(self.target_line_edit.text())

    def add_tag(self):
        category = self.combo_category.currentText().strip()
        jp_word = self.input_jp.text().strip()
        ko_name = self.input_ko.text().strip()

        if not category:
            QMessageBox.warning(self, '경고', '분류를 선택하거나 [+ 분류 추가]를 눌러 분류를 먼저 만들어주세요.')
            return
        if not jp_word or not ko_name:
            QMessageBox.warning(self, '경고', '일본어 원문과 한국어 표기를 모두 입력해주세요.')
            return

        if category not in self.user_tags:
            self.user_tags[category] = {}

        self.user_tags[category][ko_name] = jp_word
        self.save_user_tags()

        self.input_jp.clear()
        self.input_ko.clear()
        self.refresh_ui()

    def show_tag_context_menu(self, pos, category, ko_name, jp_word, button):
        menu = QMenu(self)
        delete_action = QAction(f"'{ko_name}' 삭제", self)
        delete_action.triggered.connect(lambda: self.delete_tag(category, ko_name, jp_word))
        menu.addAction(delete_action)
        menu.exec(button.mapToGlobal(pos))

    def delete_tag(self, category, ko_name, jp_word):
        if category in self.user_tags and ko_name in self.user_tags[category]:
            del self.user_tags[category][ko_name]
            self.save_user_tags()

            current_text = self.target_line_edit.text().strip()
            words = current_text.split() if current_text else []
            if jp_word in words:
                words.remove(jp_word)
                self.target_line_edit.setText(' '.join(words))

            self.refresh_ui()

    def toggle_tag(self, jp_word, button, ko_name):
        current_text = self.target_line_edit.text().strip()
        words = current_text.split() if current_text else []

        if jp_word in words:
            words.remove(jp_word)
            button.setChecked(False)
            button.setText(f'+ {ko_name}')
        else:
            words.append(jp_word)
            button.setChecked(True)
            button.setText(f'✓ {ko_name}')

        self.target_line_edit.setText(' '.join(words))

    def sync_buttons_from_text(self, text):
        words = text.strip().split()

        for jp_word, (btn, ko_name) in self.buttons.items():
            if jp_word in words:
                btn.setChecked(True)
                btn.setText(f'✓ {ko_name}')
            else:
                btn.setChecked(False)
                btn.setText(f'+ {ko_name}')


class TagSelectDialog(QDialog):
    def __init__(self, target_line_edit, categories_data, title='태그 선택', parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(540, 520)
        self.setMinimumSize(480, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName('detail_dialog_title')
        top_row.addWidget(title_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        desc = QLabel('클릭하여 검색어에 반영하고, 사용자 태그는 우클릭하여 삭제할 수 있습니다.')
        desc.setObjectName('dialog_hint')
        layout.addWidget(desc)

        self.tabs = QTabWidget()
        self.tabs.setObjectName('no_back-settingsTab')
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar {
                background: transparent;
            }
            QTabBar::tab {
                background: transparent;
                border: none;
                padding: 6px 14px;
                margin-right: 4px;
                font-weight: 600;
            }
        """)

        self.tag_panel = TagFlowWidget(target_line_edit, categories_data, self)
        self.user_tag_panel = UserTagWidget(target_line_edit, self)

        self.tabs.addTab(self.tag_panel, '기본 태그')
        self.tabs.addTab(self.user_tag_panel, '사용자 태그')
        layout.addWidget(self.tabs, 1)

        bottom_line = QFrame()
        bottom_line.setObjectName('dialog_separator')
        bottom_line.setFixedHeight(1)
        layout.addWidget(bottom_line)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 2, 0, 0)

        selected_label = QLabel('입력란에 태그가 실시간 반영됩니다.')
        selected_label.setObjectName('dialog_hint')
        bottom_layout.addWidget(selected_label, 1)

        btn_close = QPushButton('완료')
        btn_close.setObjectName('primaryBtn')
        btn_close.setMinimumWidth(80)
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)

        layout.addLayout(bottom_layout)


class SearchWorker(QThread):
    finished = Signal(dict)

    def __init__(self, search_params, site):
        super().__init__()
        self.params = search_params
        self.site = site

    def run(self):
        try:
            config = get_site(self.site)
            search_class = config['search_class']

            if self.site == Sites.KAKUYOMU:
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
        self.lbl_stars = QLabel(site_point_text(self.site, stars))
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
        self.tags_layout = FlowLayout(self.tags_widget, margin=0, spacing=6)
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


class MyListWidget(QListWidget):
    nearBottom = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 0.2초(200ms) 디바운스 타이머 설정
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
        self.site_config = get_site(site)
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

        flow = FlowLayout(container, margin=0, spacing=5)
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
        return site_build_params(self)

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
        dialog = TagSelectDialog(
            self.input_query,
            TAG_CATEGORIES,
            '검색 태그 선택',
            self
        )
        dialog.setStyleSheet(data_iteam.MINIMAL_DARK_THEME)
        dialog.show()

    def open_exclude_tag_dialog(self):
        dialog = TagSelectDialog(
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
                normalize_url(info.get('src', ''))
                for info in saved_list.values()
                if isinstance(info, dict) and info.get('src')
            }
            items = [item for item in items if normalize_url(item.get('url', '')) not in e_list]

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

        dialog = DetailDialog(
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