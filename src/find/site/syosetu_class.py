from .base import register_search
from .module.hameln_base import HamelnSearchBase


@register_search
class SyosetuSearch(HamelnSearchBase):
    site_id = "syosetu"
    display_name = "하멜른"

    BASE_URL = "https://syosetu.org"
    SEARCH_URL = "https://syosetu.org/search/"
    IS_R18 = False