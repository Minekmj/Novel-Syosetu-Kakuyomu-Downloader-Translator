import re
from urllib.parse import urlparse
import requests
from ..base import register_search
from ..module.naro_base import SyosetuApiSearchBase, http_session


@register_search
class NaroSearch(SyosetuApiSearchBase):
    site_id = "narow"
    display_name = "나로우"

    API_URL = "https://api.syosetu.com/novelapi/api/"
    BASE_NOVEL_URL = "https://ncode.syosetu.com/"
    NOCGENRE = None

    GENRES = {
        "전체": 0,
        "연애": 1,
        "이세계 연애": 101,
        "현실 연애": 102,
        "판타지": 2,
        "하이 판타지": 201,
        "로우 판타지": 202,
        "문예": 3,
        "순문학": 301,
        "휴먼 드라마": 302,
        "역사": 303,
        "추리": 304,
        "공포": 305,
        "액션": 306,
        "코미디": 307,
        "SF": 4,
        "VR 게임": 401,
        "우주": 402,
        "공산 과학": 403,
        "공황": 404,
        "기타": 99,
        "논픽션": 98,
    }

    FLAG_INCLUSION_AND_EXLUSION = {
        "AI 사용": "ai",
        "R15": "r15",
        "잔인한 묘사": "zankoku",
        "BL": "bl",
        "GL": "gl",
        "이세계 환생": "tensei",
        "이세계 전이": "tenni",
        "장기 연재 중단": "stop",
    }

    @staticmethod
    def fetch_detail_description_real(work_url):
        try:
            match = re.search(r"/(n\d+[a-z]*)/?", urlparse(work_url).path, re.I)
            if not match:
                return ""

            ncode = match.group(1).lower()
            api_url = "https://api.syosetu.com/novelapi/api/"
            res = http_session.get(
                api_url,
                params={"out": "json", "ncode": ncode, "of": "t-s-k"},
                headers=NaroSearch.HEADERS,
                timeout=10,
            )
            res.raise_for_status()
            data = res.json()

            if len(data) < 2:
                return ""

            item = data[1]
            story = item.get("story", "").strip()
            keywords = [k.strip() for k in item.get("keyword", "").split() if k.strip()]

            return story + "\n\n_____1234_____\n" + ", ".join(keywords)

        except Exception as e:
            print(f"나로우 작품 상세 정보 요청 에러: {e}")
            return ""