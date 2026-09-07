import urllib.parse
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timedelta
import requests

from src.system.src import get_resource_path

http_session = requests.Session()

TAG_CATEGORIES = json.load(open(get_resource_path("find/tag.json"), encoding="UTF-8"))


class KakuyomuSearch:
    BASE_URL = "https://kakuyomu.jp/search"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja,ko-KR;q=0.9,ko;q=0.8,en-US;q=0.7,en;q=0.6",
    }

    GENRES = {
        "전체": "",
        "이세계 판타지": "fantasy",
        "현대 판타지": "action",
        "SF": "sf",
        "연애": "love_story",
        "러브코미디": "romance",
        "현대 드라마": "drama",
        "호러": "horror",
        "미스터리": "mystery",
        "에세이/논픽션": "nonfiction",
        "역사/시대": "history",
        "평론/창작론": "criticism",
        "시/기타": "others",
        "2차 창작": "fan_fiction",
    }

    SORT_ORDERS = {
        "인기순": "popular",
        "주간 랭킹순": "weekly_ranking",
        "최신 작성순": "published_at",
        "최신 갱신순": "last_episode_published_at",
        "글자수 많은 순": "total_character_count",
    }

    LAST_PUBLISHED_PERIODS = {
        "전체": "",
        "1일 이내": "1days",
        "7일 이내": "7days",
        "1개월 이내": "1months",
        "6개월 이내": "6months",
        "1년 이내": "1years",
    }

    SERIAL_STATUSES = {
        "전체": "",
        "연재 중": "running",
        "완결": "completed",
    }
    
    FLAG_INCLUSION_AND_EXLUSION = {
        "잔혹 묘사": "cruel",
        "폭력 묘사": "violent",
        "성 묘사": "sexual",
        "서적 미디어화": "has_publication"
    }

    @staticmethod
    def build_search_url(
        query: str = "",
        genre_name: str = "",
        exclude_words: list = None,
        min_chars: int = None,
        last_published: str = None,
        min_start: int = None,
        serial_status: str = None,
        order: str = "popular",
        inclusion_flag: list = None,
        exclusion_flag: list = None,
        page: int = 1,
    ) -> str:
        params = []
        if order:
            params.append(("order", order))
        if query:
            params.append(("q", query))
        if exclude_words:
            params.append(("ex_q", " ".join(exclude_words)))
        if genre_name:
            params.append(("genre_name", genre_name))
        if min_chars is not None and min_chars > 0:
            params.append(("total_character_count_range", f"{min_chars}-"))
        if last_published:
            params.append(("last_episode_published_date_range", last_published))
        if min_start:
            params.append(("total_review_point_range", f"{min_start}-"))
        if serial_status:
            params.append(("serial_status", serial_status))
        if inclusion_flag:
            params.append(("inclusion_conditions", ",".join(inclusion_flag)))
        if exclusion_flag:
            for i in exclusion_flag:
                params.append(("exclusion_flag_name", i))

        if page > 1:
            params.append(("page", str(page)))

        query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        return f"{KakuyomuSearch.BASE_URL}?{query_string}"

    @classmethod
    def parse_search_results(cls, html_content: str) -> dict:
        soup = BeautifulSoup(html_content, "html.parser")
        results = []

        empty_msg = soup.find("div", class_=lambda c: c and "EmptyMessage_body" in c)
        if empty_msg:
            return {"is_last_page": True, "items": []}

        card_boxes = soup.find_all(
            "div",
            class_=lambda c: c
            and "NewBox_box__45ont" in c
            and "NewBox_borderSize-bb-m" in c,
        )

        if not card_boxes:
            card_boxes = soup.find_all(
                "div",
                class_=lambda c: c
                and "LayoutItem_layoutItem__cl360" in c
                and "LayoutItem_flex-1__hhrWm" in c,
            )

        processed_work_ids = set()

        for card in card_boxes:
            title_tag = card.find("a", href=lambda h: h and h.startswith("/works/"))
            if not title_tag:
                continue

            href = title_tag.get("href", "")
            parts = [p for p in href.split("/") if p]
            if len(parts) < 2 or parts[0] != "works":
                continue

            work_id = parts[1]
            if work_id in processed_work_ids:
                continue

            title_text = title_tag.get_text(strip=True)
            if not title_text:
                continue

            stars = "0"
            status_episodes = ""
            updated_at = ""

            meta_items = card.find_all(
                "li", class_=lambda c: c and "Meta_metaItemWrapper" in c
            )
            for item in meta_items:
                item_text = item.get_text(strip=True)
                if "★" in item_text:
                    stars = item_text.replace("★", "").strip()
                elif "更新" in item_text or item.find("time"):
                    time_tag = item.find("time")
                    if time_tag:
                        updated_at = time_tag.get_text(strip=True)
                    else:
                        updated_at = item_text.replace("更新", "").strip()
                elif "話" in item_text or "連載" in item_text or "完結" in item_text:
                    status_episodes = item_text

            if status_episodes:
                status_episodes = status_episodes.replace("連載中", "연재중 ").replace("完結済", "완결 ")
                status_episodes = re.sub(r'(\d+)話', r'\1화', status_episodes)

            if updated_at:
                updated_at = updated_at.replace("年", "년 ").replace("月", "월 ").replace("日", "일")

            processed_work_ids.add(work_id)
            results.append(
                {
                    "work_id": work_id,
                    "title": title_text,
                    "url": f"https://kakuyomu.jp/works/{work_id}",
                    "stars": stars,
                    "status_episodes": status_episodes,
                    "updated_at": updated_at
                }
            )

        return {"is_last_page": len(results) == 0, "items": results}

    @classmethod
    def fetch_detail_description(cls, work_url: str) -> str:
        try:
           
            res = http_session.get(work_url, headers=cls.HEADERS, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")

               
                next_data = soup.find("script", id="__NEXT_DATA__")
                if next_data and next_data.string:
                    data = json.loads(next_data.string)

                   
                    def find_key(obj, target_key):
                        if isinstance(obj, dict):
                            if target_key in obj:
                                return obj[target_key]
                            for v in obj.values():
                                res = find_key(v, target_key)
                                if res:
                                    return res
                        elif isinstance(obj, list):
                            for item in obj:
                                res = find_key(item, target_key)
                                if res:
                                    return res
                        return None

                    intro_text = find_key(data, "introduction")
                    lal = ', '.join(find_key(data, "tagLabels"))
                    if intro_text:
                        return str(intro_text).strip() + "\n\n_____tags_____\n" + lal

                return "상세 줄거리를 찾을 수 없습니다."
            return f"페이지 로드 실패 (HTTP {res.status_code})"
        except Exception as e:
            return f"상세 정보 요청 오류: {e}"
        
class NaroSearch:
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

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
        "논픽션": 98
    }

    SORT_ORDERS = {
        "포인트순": "hyoka",
        "주간 포인트순": "weeklypoint",
        "월간 포인트순": "monthlypoint",
        "분기 포인트순": "quarterpoint",
        "연간 포인트순": "yearlypoint",
        "신작순": "new",
        "최신 갱신순": "weekly",
        "글자수순": "length"
    }

    SERIAL_STATUSES = {
        "전체": "",
        "단편": "t",
        "연재": "re",
        "연재중": "r",
        "완결": "er"
    }

    LAST_PUBLISHED_PERIODS = {
        "전체": None,
        "1일 이내": 1,
        "1주일 이내": 7,
        "1개월 이내": 30,
        "3개월 이내": 90,
        "반년 이내": 180,
        "1년 이내": 365
    }
    
    FLAG_INCLUSION_AND_EXLUSION = {
        "AI 사용": "ai",
        "R15": "r15",
        "잔인한 묘사": "zankoku",
        "BL": "bl",
        "GL": "gl",
        "이세계 환생": "tensei",
        "이세계 전이": "tenni",
        "장기 연재 중단": "stop"
    }
    
    FIND_AREA = {
        "작품 제목": "title",
        "줄거리": "ex",
        "키워드": "keyword",
        "저자 이름": "wname"
    }

    @staticmethod
    def fetch_search_results(params):

        api_url = "https://api.syosetu.com/novelapi/api/"

        page = max(1, int(params.get("page", 1)))

        payload = {
            "out": "json",
            "lim": 20,
            "st": (page - 1) * 20 + 1,
            "word": params.get("query", ""),
            "order": params.get("order", "hyoka")
        }

       
       
       

        exclude_words = params.get("exclude_words", [])

        if exclude_words:
            payload["notword"] = " ".join(
                str(word).strip()
                for word in exclude_words
                if str(word).strip()
            )

       
       
       

        genre_val = params.get("genre_val")

        if genre_val and int(genre_val) != 0:
            payload["genre"] = int(genre_val)

       
       
       

        min_chars = params.get("min_chars", 0)

        if min_chars and int(min_chars) > 0:
            payload["minlen"] = int(min_chars)
          
       
       
       
        min_pt = params.get("min_pt", 0)
        
        if min_pt and int(min_pt) > 0:
            payload["min_globalpoint"] = int(min_pt)

       
       
       

        serial_status = params.get("serial_status")

        if serial_status:
            payload["type"] = serial_status

       
       
       

        period_key = params.get("last_published")

        days = NaroSearch.LAST_PUBLISHED_PERIODS.get(
            period_key,
            period_key if isinstance(period_key, int) else None
        )

        if days:
            today = datetime.now()
            start_date = today - timedelta(days=days)

            payload["minlastup"] = start_date.strftime("%Y/%m/%d")
            payload["maxlastup"] = today.strftime("%Y/%m/%d")
        
       
       
       
        
        inclusion_flags = params.get("inclusion_flags", [])
        
        if inclusion_flags:
            for i in inclusion_flags:
                payload["is" + i] = 1
                
        exlusion_flags = params.get("exlusion_flags", [])
                
        if exlusion_flags:
            for i in exlusion_flags:
                payload["not" + i if i != "stop" else "stop"] = 1
                
       
       
       
        
        find_areas = params.get("find_areas", [])
          
        if find_areas:
            for i in exlusion_flags:
                payload[i] = 1

        try:
           
            res = http_session.get(
                api_url,
                params=payload,
                headers=NaroSearch.HEADERS,
                timeout=10
            )

            res.raise_for_status()

            data = res.json()

            if not data:
                return {
                    "is_last_page": True,
                    "items": []
                }

            all_count = data[0].get("allcount", 0)

            items = []

            for item in data[1:]:

                ncode = item.get("ncode", "").lower()

                keywords_str = item.get("keyword", "")

                keywords_list = [
                    keyword.strip()
                    for keyword in keywords_str.split()
                    if keyword.strip()
                ]

                end_value = item.get("end", 1)

                if end_value == 1:
                    status = "연재중"
                else:
                    status = "완결"

                items.append({
                    "title": item.get("title", ""),

                    "url": f"https://ncode.syosetu.com/{ncode}/",

                    "stars": item.get("global_point", 0),

                    "status_episodes":
                        f"총 {item.get('general_all_no', 0)}화 "
                        f"({status})",

                    "updated_at":
                        item.get("general_lastup", "")[:10],

                    "ncode": ncode,
                    
                    "story": item.get("story", "") + '_____tags_____' + ', '.join(keywords_list),

                    "keywords": keywords_list
                })

            is_last_page = page * 20 >= all_count

            return {
                "is_last_page": is_last_page,
                "items": items
            }

        except Exception as e:

            print(f"나로우 API 요청 에러: {e}")

            return {
                "is_last_page": True,
                "items": []
            }
    
    @staticmethod
    def fetch_detail_description(work_url):
        return work_url