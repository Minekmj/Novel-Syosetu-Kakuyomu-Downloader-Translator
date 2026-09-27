import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

http_session = requests.Session()


class NovelupSearch:
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://novelup.plus/search",
    }

    GENRES = {
        "전체": 0,
        "이세계 판타지": 1,
        "현대/기타 판타지": 2,
        "SF": 3,
        "연애/러브코미디": 4,
        "호러": 5,
        "미스터리": 6,
        "에세이/평론/칼럼": 7,
        "역사/시대": 8,
        "문예/순문학": 9,
        "블로그/활동보고": 10,
        "현대/청춘 드라마": 11,
        "시/단가": 12,
        "노베플라 게재작품 소개": 13,
        "코미디/개그": 14,
        "동화/그림책/기타": 15,
        "2차 창작": 16
    }

    SORT_ORDERS = {
        '최신 갱신순': 1,
        '신작순': 2,
        '북마크순': 3,
        '일간 랭킹순': 4,
        '누적 랭킹순': 8,
        '포인트순': 9,
        '노벨라 포인트순': 10
    }

    SERIAL_STATUSES = {
        "전체": "",
        "단편": "short",
        "연재": "not-short",
        "연재중": "not-finish",
        "완결": "finish"
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
        "잔혹 묘사": "rating_1",
        "폭력 묘사": "rating_2",
        "성적 표현": "rating_3",
        "장기 연재 중단 제외": "pause",
        "서적화 작품": "published",
        "수상작": "award",
        "자주 기획": "user_event",
        "설정/플롯": "plot"
    }

    FIND_AREA = {
        "줄거리": "story",
        "작품 소개": "introduction",
        "태그": "tag",
        "작가명": "member",
        "라이선스/제목": "license"
    }

    _sort_initialized = False

    @staticmethod
    def fetch_search_results(params):

        search_url = "https://novelup.plus/search"
        query = params.get("query", "").strip()

        exclude_words = params.get("exclude_words", [])
        if isinstance(exclude_words, list):
            exclude_str = " ".join(str(w).strip() for w in exclude_words if str(w).strip())
        else:
            exclude_str = str(exclude_words).strip()

        min_chars = params.get("min_chars", 0)
        length_min = str(int(min_chars)) if min_chars and int(min_chars) > 0 else ""

        min_pt = params.get("min_pt", 0)
        point_min = str(int(min_pt)) if min_pt and int(min_pt) > 0 else ""

        update_from = ""
        period_key = params.get("last_published")
        days = NovelupSearch.LAST_PUBLISHED_PERIODS.get(
            period_key,
            period_key if isinstance(period_key, int) else None
        )
        if days:
            start_date = datetime.now() - timedelta(days=days)
            update_from = start_date.strftime("%Y-%m-%d")

        order_key = params.get("order", "1")
        sort_val = NovelupSearch.SORT_ORDERS.get(order_key, order_key)

        payload = {
            "q": query,
            "ai": "1",
            "length[min]": length_min,
            "length[max]": "",
            "point[min]": point_min,
            "point[max]": "",
            "point_pay[min]": "",
            "point_pay[max]": "",
            "update[from]": update_from,
            "update[to]": "",
            "open[from]": "",
            "open[to]": "",
            "e": exclude_str,
            "sort": str(sort_val)
        }

        page = max(1, int(params.get("page", 1)))
        if page > 1:
            payload["p"] = page

        genre_val = params.get("genre_val")
        if genre_val and int(genre_val) != 0:
            payload[f"genre[{int(genre_val)}]"] = 1

        serial_status = params.get("serial_status")
        if serial_status == "short":
            payload["short"] = 1
        elif serial_status == "not-short":
            payload["not-short"] = 1
        elif serial_status == "finish":
            payload["finish"] = 1
        elif serial_status == "not-finish":
            payload["not-finish"] = 1

        find_areas = params.get("find_areas", [])
        if find_areas:
            for area in find_areas:
                payload[f"search[{area}]"] = 1

        inclusion_flags = params.get("inclusion_flags", [])
        if inclusion_flags:
            for flag in inclusion_flags:
                if flag.startswith("rating_"):
                    r_id = flag.split("_")[1]
                    payload[f"rating[{r_id}]"] = 1
                else:
                    payload[flag] = 1

        try:
            res = http_session.get(
                search_url,
                params=payload,
                headers=NovelupSearch.HEADERS,
                timeout=25
            )
            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.select("div.story_card")

            if not cards:
                return {
                    "is_last_page": True,
                    "items": []
                }

            items = []
            for card in cards:
                name_elem = card.select_one("p.story_name a")
                title = name_elem.get_text(strip=True) if name_elem else ""
                raw_url = name_elem.get("href", "") if name_elem else ""
                url = urljoin("https://novelup.plus", raw_url)

                ncode_match = re.search(r'/story/(\d+)', url)
                ncode = ncode_match.group(1) if ncode_match else ""

                point_elem = card.select_one("p.story_point span")
                stars = point_elem.get_text(strip=True) if point_elem else "0"

                ep_elem = card.select_one("p.story_episode_count")
                ep_text = ep_elem.get_text(strip=True) if ep_elem else ""
                ep_num_match = re.search(r'\d+', ep_text)
                episodes = int(ep_num_match.group(0)) if ep_num_match else 0

                short_elem = card.select_one("p.story_short")
                short_text = short_elem.get_text(strip=True) if short_elem else ""

                card_full_text = card.get_text()
                if "完結" in card_full_text:
                    status = "완결"
                elif "短編" in short_text:
                    status = "단편"
                else:
                    status = "연재중"

                status_episodes = f"총 {episodes}화 ({status})"

                update_elem = card.select_one("p.story_update")
                update_text = update_elem.get_text(strip=True) if update_elem else ""
                date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', update_text)
                if date_match:
                    y, m, d = date_match.groups()
                    updated_at = f"{y}-{int(m):02d}-{int(d):02d}"
                else:
                    updated_at = update_text[:10]

                tag_elems = card.select("ul.story_tag li a")
                keywords_list = [
                    t.get_text(strip=True)
                    for t in tag_elems
                    if t.get_text(strip=True)
                ]

                items.append({
                    "title": title,
                    "url": url,
                    "stars": stars,
                    "status_episodes": status_episodes,
                    "updated_at": updated_at,
                    "ncode": ncode,
                    "keywords": keywords_list
                })

            is_last_page = len(cards) < 30
            total_match = re.search(r'検索結果[：:]\s*([0-9,]+)\s*件', res.text)
            if total_match:
                total_count = int(total_match.group(1).replace(",", ""))
                is_last_page = page * 30 >= total_count

            return {
                "is_last_page": is_last_page,
                "items": items
            }

        except Exception as e:
            print(f"노벨업 검색 에러: {e}")
            return {
                "is_last_page": True,
                "items": []
            }

    @staticmethod
    def fetch_detail_description(work_url):
        if not work_url:
            return ""
        try:
            work_url, keywords_list = (work_url[:work_url.find("!")], work_url[work_url.find("!")+1:])
            res = http_session.get(
                work_url,
                headers=NovelupSearch.HEADERS,
                timeout=20
            )
            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")
            synopsis_elem = soup.select_one("div.novel_synopsis")
            if synopsis_elem:
                return synopsis_elem.get_text(separator="\n", strip=True)+ "_____1234_____" + keywords_list

            return work_url
        except Exception as e:
            print(f"노벨업 상세 설명 요청 에러: {e}")
            return work_url