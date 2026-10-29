from .base import register_search
from .module.naro_base import SyosetuApiSearchBase


@register_search
class NocturneSearch(SyosetuApiSearchBase):
    site_id = "nocturne"
    display_name = "녹턴"

    API_URL = "https://api.syosetu.com/novel18api/api/"
    BASE_NOVEL_URL = "https://novel18.syosetu.com/"
    NOCGENRE = 1