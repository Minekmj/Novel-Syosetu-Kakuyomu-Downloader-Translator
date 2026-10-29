from ..base import register_search
from ..module.naro_base import SyosetuApiSearchBase


@register_search
class MidnightSearch(SyosetuApiSearchBase):
    site_id = "midnight"
    display_name = "미드나이트"

    API_URL = "https://api.syosetu.com/novel18api/api/"
    BASE_NOVEL_URL = "https://novel18.syosetu.com/"
    NOCGENRE = 4