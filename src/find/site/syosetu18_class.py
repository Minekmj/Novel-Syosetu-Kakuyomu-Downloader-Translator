from .base import register_search
from .module.hameln_base import HamelnSearchBase


@register_search
class SyosetuSearch18(HamelnSearchBase):
    site_id = "syosetu18"
    display_name = "하멜른 R18"

    BASE_URL = "https://h.syosetu.org"
    SEARCH_URL = "https://h.syosetu.org/search/"
    IS_R18 = True