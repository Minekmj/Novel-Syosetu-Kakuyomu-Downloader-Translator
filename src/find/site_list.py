from enum import IntEnum
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSizePolicy
)
from src.system.data import NaroSearch, KakuyomuSearch, MidnightSearch, NocturneSearch, SyosetuSearch, SyosetuSearch18
from src.system.data import load_data, save_data

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