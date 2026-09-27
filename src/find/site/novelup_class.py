from datetime import datetime, timedelta
from urllib.parse import urljoin
import html
import re

import requests
from bs4 import BeautifulSoup

http_session = requests.Session()

class NovelupSearch:
    BASE_URL = "https://novelup.plus"
    SEARCH_URL = "https://novelup.plus/search"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
    }

    GENRES = {
        "전체": "",
        "판타지": 1,
        "연애": 2,
        "SF": 3,
        "현대": 4,
        "역사": 5,
        "미스터리": 6,
        "호러": 7,
        "에세이/논평/칼럼": 8,
        "기타": 9
    }

    SORT_ORDERS = {
        "추천순": "1",
        "新着順": "2",
        "更新順": "3",
        "ポイント順": "4",
        "評価順": "5"
    }

    SERIAL_STATUSES = {
        "전체": ("short", "not-short"),
        "단편": ("short",),
        "장편": ("not-short",),
        "완결": ("finish",),
        "연재중": ("not-finish",)
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
        "단편": "short",
        "장편": "not-short",
        "줄거리": "plot",
        "유저 이벤트": "user_event",
        "완결": "finish",
        "연재중": "not-finish",
        "수상작": "award",
        "공개작": "published",
        "일시중단": "pause"
    }

    AI_OPTIONS = {
        "전체": "",
        "AI 사용 여부 불문": "1",
        "AI 사용 작품": "2",
        "AI 사용 안 함": "3"
    }

    FIND_AREA = {
        "작품 제목": "story",
        "소개": "introduction",
        "태그": "tag",
        "작가": "member",
        "라이선스": "license"
    }

    RATING_FLAGS = {
        "1점": "1",
        "2점": "2",
        "3점": "3"
    }

    @staticmethod
    def _clean_text(value):
        if not value:
            return ""
        value = html.unescape(value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    @staticmethod
    def _parse_number(value):
        if not value:
            return 0
        value = value.strip().replace(",", "").replace(" ", "")
        try:
            if value.endswith("K"):
                return int(float(value[:-1]) * 1000)
            if value.endswith("M"):
                return int(float(value[:-1]) * 1000000)
            if value.endswith("B"):
                return int(float(value[:-1]) * 1000000000)
            return int(float(value))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _parse_date(value):
        if not value:
            return ""
        match = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", value)
        if match:
            return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
        return value.strip()[:10]

    @staticmethod
    def _add_checkbox_params(payload, name, values):
        if not values:
            return
        for value in values:
            payload[f"{name}[{value}]"] = 1

    @staticmethod
    def _parse_story_card(card):
        title_tag = card.select_one(".story_name a")
        if not title_tag:
            return None

        title = NovelupSearch._clean_text(title_tag.get_text(" ", strip=True))
        url = urljoin(NovelupSearch.BASE_URL, title_tag.get("href", ""))

        comment_tag = card.select_one(".story_comment")
        author_tag = card.select_one(".story_author_name a")
        introduction_tag = card.select_one(".story_introduction")
        genre_tag = card.select_one(".story_genre")
        short_tag = card.select_one(".story_short")
        episode_tag = card.select_one(".story_episode_count")
        length_tag = card.select_one(".story_length")
        update_tag = card.select_one(".story_update")

        point_tag = card.select_one(".story_point")
        good_tag = card.select_one(".count_good")
        point_pay_tag = card.select_one(".story_point_pay")

        tags = []
        for tag in card.select(".story_tag a"):
            text = NovelupSearch._clean_text(tag.get_text(" ", strip=True))
            if text:
                tags.append(text)

        point = NovelupSearch._parse_number(
            point_tag.get_text(" ", strip=True) if point_tag else ""
        )

        good = NovelupSearch._parse_number(
            good_tag.get_text(" ", strip=True) if good_tag else ""
        )

        point_pay = NovelupSearch._parse_number(
            point_pay_tag.get_text(" ", strip=True) if point_pay_tag else ""
        )

        episode_text = NovelupSearch._clean_text(
            episode_tag.get_text(" ", strip=True) if episode_tag else ""
        )

        length_text = NovelupSearch._clean_text(
            length_tag.get_text(" ", strip=True) if length_tag else ""
        )

        short_text = NovelupSearch._clean_text(
            short_tag.get_text(" ", strip=True) if short_tag else ""
        )

        genre_text = NovelupSearch._clean_text(
            genre_tag.get_text(" ", strip=True) if genre_tag else ""
        )

        introduction = NovelupSearch._clean_text(
            introduction_tag.get_text("\n", strip=True)
            if introduction_tag else ""
        )

        author = NovelupSearch._clean_text(
            author_tag.get_text(" ", strip=True)
            if author_tag else ""
        )

        update_text = NovelupSearch._clean_text(
            update_tag.get_text(" ", strip=True)
            if update_tag else ""
        )

        status = short_text or "장편"

        return {
            "title": title,
            "url": url,
            "stars": point,
            "status_episodes": f"{episode_text} ({status})" if episode_text else status,
            "updated_at": NovelupSearch._parse_date(update_text),
            "ncode": url.rstrip("/").split("/")[-1],
            "story": introduction + "____1234____" + ", ".join(tags),
            "keywords": tags,
            "author": author,
            "comment": NovelupSearch._clean_text(
                comment_tag.get_text(" ", strip=True)
                if comment_tag else ""
            ),
            "genre": genre_text,
            "length": length_text,
            "good": good,
            "point": point,
            "point_pay": point_pay,
            "introduction": introduction
        }

    @staticmethod
    def fetch_search_results(params):
        page = max(1, int(params.get("page", 1)))

        payload = {
            "q": params.get("query", "").strip(),
            "sort": params.get("order", "1")
        }

        genre_val = params.get("genre_val")
        if genre_val:
            payload["genre[1]"] = int(genre_val)

        find_areas = params.get("find_areas", [])
        if find_areas:
            for value in find_areas:
                payload[f"search[{value}]"] = 1
        else:
            for value in NovelupSearch.FIND_AREA.values():
                payload[f"search[{value}]"] = 1

        serial_status = params.get("serial_status")
        if serial_status:
            for value in serial_status:
                payload[value] = 1
        else:
            payload["short"] = 1
            payload["not-short"] = 1
            payload["finish"] = 1
            payload["not-finish"] = 1

        min_chars = params.get("min_chars", 0)
        if min_chars and int(min_chars) > 0:
            payload["length[min]"] = int(min_chars)

        max_chars = params.get("max_chars", 0)
        if max_chars and int(max_chars) > 0:
            payload["length[max]"] = int(max_chars)

        min_pt = params.get("min_pt", 0)
        if min_pt and int(min_pt) > 0:
            payload["point[min]"] = int(min_pt)

        max_pt = params.get("max_pt", 0)
        if max_pt and int(max_pt) > 0:
            payload["point[max]"] = int(max_pt)

        min_point_pay = params.get("min_point_pay", 0)
        if min_point_pay and int(min_point_pay) > 0:
            payload["point_pay[min]"] = int(min_point_pay)

        max_point_pay = params.get("max_point_pay", 0)
        if max_point_pay and int(max_point_pay) > 0:
            payload["point_pay[max]"] = int(max_point_pay)

        period_key = params.get("last_published")
        days = NovelupSearch.LAST_PUBLISHED_PERIODS.get(
            period_key,
            period_key if isinstance(period_key, int) else None
        )

        if days:
            today = datetime.now()
            start_date = today - timedelta(days=days)
            payload["update[from]"] = start_date.strftime("%Y-%m-%d")
            payload["update[to]"] = today.strftime("%Y-%m-%d")

        update_from = params.get("update_from")
        update_to = params.get("update_to")

        if update_from:
            payload["update[from]"] = update_from
        if update_to:
            payload["update[to]"] = update_to

        open_from = params.get("open_from")
        open_to = params.get("open_to")

        if open_from:
            payload["open[from]"] = open_from
        if open_to:
            payload["open[to]"] = open_to

        inclusion_flags = params.get("inclusion_flags", [])
        for flag in inclusion_flags:
            payload[flag] = 1

        exclusion_flags = params.get("exclusion_flags", [])
        for flag in exclusion_flags:
            if flag in payload:
                del payload[flag]

        ai = params.get("ai")
        if ai:
            payload["ai"] = ai

        rating_flags = params.get("rating_flags", [])
        for value in rating_flags:
            payload[f"rating[{value}]"] = 1

        exclude_words = params.get("exclude_words", [])
        if exclude_words:
            payload["e"] = " ".join(
                str(word).strip()
                for word in exclude_words
                if str(word).strip()
            )

        if page > 1:
            payload["page"] = page

        try:
            res = http_session.get(
                NovelupSearch.SEARCH_URL,
                params=payload,
                headers=NovelupSearch.HEADERS,
                timeout=15
            )

            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.select("li.one_set .story_card")

            items = []

            for card in cards:
                item = NovelupSearch._parse_story_card(card)
                if item:
                    items.append(item)

            if not items:
                return {
                    "is_last_page": True,
                    "items": []
                }

            next_link = soup.select_one(
                'a[rel="next"], .pagination a.next, .pager a.next'
            )

            if next_link:
                is_last_page = False
            else:
                current_page = soup.select_one(
                    ".pagination .current, .pager .current"
                )
                is_last_page = True if not current_page else page >= int(
                    current_page.get_text(strip=True) or page
                )

            return {
                "is_last_page": is_last_page,
                "items": items
            }

        except Exception as e:
            print(f"노벨업 플러스 검색 요청 에러: {e}")
            return {
                "is_last_page": True,
                "items": []
            }

    @staticmethod
    def fetch_detail_description(work_url):
        try:
            res = http_session.get(
                work_url,
                headers=NovelupSearch.HEADERS,
                timeout=15
            )

            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")
            synopsis = soup.select_one(".novel_synopsis")

            if synopsis:
                return synopsis.get_text("\n", strip=True)

            introduction = soup.select_one(".story_introduction")
            if introduction:
                return introduction.get_text("\n", strip=True)

            return ""

        except Exception as e:
            print(f"노벨업 플러스 상세 요청 에러: {e}")
            return ""