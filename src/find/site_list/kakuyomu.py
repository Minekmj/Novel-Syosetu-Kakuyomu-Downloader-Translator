from src.find.site import KakuyomuSearch
from .base import BaseSite, Sites, register_site

@register_site
class KakuyomuSite(BaseSite):
    site = Sites.KAKUYOMU
    name = '카쿠요무'
    search_class = KakuyomuSearch
    has_star = True

    def point_text(self, value):
        return f'★ {value}'

    def setup_ui(self, window, layout):
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

    def build_params(self, window):
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