from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QSizePolicy
)
from src.system.data import load_data, save_data

def normalize_url(url):
    if not url:
        return ''
    return url.strip().rstrip('/')

def ha_set_ui_main(window, layout, l, cache_key=None):
    if cache_key is None:
        from src.find.site import SyosetuSearch
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