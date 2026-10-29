from src.find.site import SyosetuSearch, SyosetuSearch18
from .base import BaseSite, Sites, register_site
from .helpers import ha_set_ui_main

class HamelnBaseSite(BaseSite):
    cache_key = ''

    def setup_ui(self, window, layout):
        ha_set_ui_main(window, layout, self.search_class, self.cache_key)

    def build_params(self, window):
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

@register_site
class HamelnSite(HamelnBaseSite):
    site = Sites.HAMELLEUN
    name = '하멜른'
    search_class = SyosetuSearch
    cache_key = 'hameln_flags_main'

@register_site
class Hameln18Site(HamelnBaseSite):
    site = Sites.HAMELLEUN18
    name = '하멜른18'
    search_class = SyosetuSearch18
    cache_key = 'hameln18_flags_main'