from src.find.site import NaroSearch, MidnightSearch, NocturneSearch
from .base import BaseSite, Sites, register_site

class NarouBaseSite(BaseSite):
    def point_text(self, value):
        return f'pt {value}'

    def setup_ui(self, window, layout):
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

    def build_params(self, window):
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

@register_site
class NarouSite(NarouBaseSite):
    site = Sites.NAROU
    name = '나로우'
    search_class = NaroSearch

@register_site
class MidnightSite(NarouBaseSite):
    site = Sites.MIDNIGHT
    name = '미드나이트'
    search_class = MidnightSearch

@register_site
class NocturneSite(NarouBaseSite):
    site = Sites.NOCTURNE
    name = '녹턴'
    search_class = NocturneSearch