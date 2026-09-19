from collections import OrderedDict
from datetime import datetime, timedelta
import re
from urllib.parse import urljoin, urlencode, unquote_plus

from bs4 import BeautifulSoup
import requests

import src.find.site.site_data as sf
from src.trans.trans import Translator

http_session = requests.Session()
sf.COOKIES["over18"] = "off"
http_session.cookies.update(sf.COOKIES)


class SyosetuSearch18:
    BASE_URL = "https://h.syosetu.org"
    SEARCH_URL = "https://h.syosetu.org/search/"

    GENRES = {}
 
    NO_POINT = True

    FLAGS_MAIN = OrderedDict()

    SORT_ORDERS = {
        "기본": "0", "신착순": "0", "시착순": "0",
        "최종 갱신순": "45",
        "종합 평가순": "28",
        "평균평가 높은 순": "4", "평균 평가순": "4",
        "가중 평가 높은 순": "42", "가중평균순": "42",
        "이야기당 문자 순": "6", "1화 문자수순": "6",
        "첫 개시일": "8", "첫 게시일": "8",
        "총 평가 수(많은 순)": "18",
        "연간 종합평가": "33", "분기 종합평가": "32",
        "월간 종합평가": "31", "주간 종합평가": "30",
        "일간 종합평가": "29",
        "무작위": "37", "랜덤": "37",
        "이야기 많은 순": "24", "화수순": "24",
        "감상 많은 순": "22", "감상순": "22",
        "즐겨찾기순": "10",
        "총 글자수순": "20",
    }

    SERIAL_STATUSES = {
        "전체": "",
        "단편": "rensai_s1",
        "연재": "rensai_s2",
        "연재중": "rensai_s2",
        "완결": "rensai_s4",
    }

    LAST_PUBLISHED_PERIODS = {
        "전체": None,
        "1일 이내": 1,
        "1주일 이내": 7,
        "1개월 이내": 30,
        "3개월 이내": 90,
        "반년 이내": 180,
        "1년 이내": 365,
    }

    FLAG_EXCLUSION = {
        "AI 사용": "tag15",
        "R15": "tag2",
        "잔인한 묘사": "tag7",
        "크로스오버": "tag12",
        "오리주": "tag5",
        "신 전생": "tag6",
        "하나님 환생": "tag6",
        "환생": "tag9",
        "빙의": "tag10",
        "성전환": "tag11",
        "BL": "tag3",
        "GL": "tag4",
        "안티 헤이트": "tag8",
        "게시판 형식": "tag13",
        "대본 형식": "tag14",
    }

    @classmethod
    def _get(cls, url, headers=None, timeout=12):
        req_headers = dict(sf.BASE_HEADERS)
        if headers:
            req_headers.update(headers)

        res = http_session.get(url, headers=req_headers, timeout=timeout)

        if res.status_code == 403:
            print(f"[하멜른 R18 403 차단 감지] reset(True) 호출 및 재시도: {url}")
            sf.reset(True)
            sf.COOKIES["over18"] = "off"
            http_session.cookies.update(sf.COOKIES)
            
            # reset 후 변경되었을 수 있는 BASE_HEADERS를 다시 적용
            req_headers = dict(sf.BASE_HEADERS)
            if headers:
                req_headers.update(headers)

            res = http_session.get(url, headers=req_headers, timeout=timeout)

        return res

    @staticmethod
    def _number(text):
        if not text:
            return 0
        match = re.search(r"[\d,]+", str(text))
        return int(match.group(0).replace(",", "")) if match else 0

    @staticmethod
    def _date(text):
        if not text:
            return ""
        match = re.search(r"(20\d{2})[./年-](\d{1,2})[./月-](\d{1,2})", str(text))
        if not match:
            return ""
        return f"{match.group(1)}/{int(match.group(2)):02d}/{int(match.group(3)):02d}"

    @classmethod
    def load_flags_main(cls):
        jp_origins = []
        seen = set()

        for page in (1, 2):
            try:
                url = f"{cls.SEARCH_URL}?mode=search_gensaku_list&word=&filter=1&page={page}&r18=1"
                res = cls._get(url, headers={"referer": cls.SEARCH_URL}, timeout=12)
                if res.status_code != 200:
                    continue

                soup = BeautifulSoup(res.text, "html.parser")
                table = soup.select_one("table.table1") or soup

                for a in table.find_all("a"):
                    href = a.get("href", "")
                    decoded_href = unquote_plus(href)

                    if "原作：" in decoded_href or "原作:" in decoded_href:
                        jp_name = a.get_text(strip=True)

                        if not jp_name:
                            match = re.search(r"原作[：:]([^&]+)", decoded_href)
                            jp_name = match.group(1).strip() if match else ""

                        if jp_name and jp_name not in seen:
                            seen.add(jp_name)
                            jp_origins.append(jp_name)

            except Exception as e:
                print(f"[하멜른 R18 FLAGS_MAIN 수집 에러 (page {page})] {e}")

        if not jp_origins:
            return OrderedDict()

        ko_origins = []
        chunk_size = 25

        for i in range(0, len(jp_origins), chunk_size):
            chunk = jp_origins[i:i + chunk_size]
            try:
                combined_text = "\n".join(chunk)
                translated_combined = Translator(combined_text, True)
                lines = [line.strip() for line in translated_combined.split("\n") if line.strip()]

                if len(lines) == len(chunk):
                    ko_origins.extend(lines)
                else:
                    for item in chunk:
                        try:
                            ko_origins.append(str(Translator(item, True)).strip() or item)
                        except Exception:
                            ko_origins.append(item)
            except Exception as e:
                print(f"[하멜른 R18 FLAGS_MAIN 번역 에러 (청크 {i})] {e}")
                for item in chunk:
                    ko_origins.append(item)

        flags_main = OrderedDict()
        used_keys = set()

        for jp, ko in zip(jp_origins, ko_origins):
            display_name = ko if ko else jp
            if display_name in used_keys:
                display_name = f"{display_name} ({jp})"
            used_keys.add(display_name)
            flags_main[display_name] = jp

        return flags_main

    @classmethod
    def set_flag(cls):
        sf.reset_b()
        sf.COOKIES["over18"] = "off"
        http_session.cookies.update(sf.COOKIES)

    @classmethod
    def fetch_search_results(cls, params):
        try:
            page = max(1, int(params.get("page", 1)))

            word = str(params.get("query", "")).strip()
            search_words = []

            if word:
                search_words.append(word)

            for flag in params.get("inclusion_flags", []):
                flag = str(flag).strip()
                if flag:
                    search_words.append(flag)

            for exc in params.get("exclude_words", []):
                exc = str(exc).strip()
                if exc:
                    search_words.append(f"-{exc}")

            full_word = " ".join(search_words)

            order_key = params.get("order", "최종 갱신순")
            sort_type = cls.SORT_ORDERS.get(
                order_key,
                str(order_key) if str(order_key).isdigit() else "45"
            )

            search_type = "0"

            gensaku_val = ""
            origin_input = params.get("flags_main") or params.get("origin") or params.get("gensaku")
            if origin_input:
                origin = str(origin_input).strip()
                if origin in cls.FLAGS_MAIN:
                    origin = cls.FLAGS_MAIN[origin]

                if origin.startswith("原作：") or origin in ("その他原作", "オリジナル", "二次創作"):
                    gensaku_val = origin
                elif origin.startswith("原作:"):
                    gensaku_val = f"原作：{origin[3:].strip()}"
                else:
                    gensaku_val = f"原作：{origin}"

            d2_val = ""
            d1_val = ""
            period = params.get("last_published")
            days = cls.LAST_PUBLISHED_PERIODS.get(
                period,
                period if isinstance(period, int) else None
            )

            if days:
                today = datetime.now()
                start_date = today - timedelta(days=days)
                d2_val = start_date.strftime("%Y/%m/%d")
                d1_val = today.strftime("%Y/%m/%d")

            query_params = OrderedDict([
                ("search_type", search_type),
                ("word", full_word),
                ("gensaku", gensaku_val),
                ("type", sort_type),
                ("mozi2", str(params.get("min_ep_chars", ""))),
                ("mozi1", str(params.get("max_ep_chars", ""))),
                ("mozi2_all", str(params.get("min_chars", ""))),
                ("mozi1_all", str(params.get("max_chars", ""))),
                ("rate2", str(params.get("min_rate", ""))),
                ("rate1", str(params.get("max_rate", ""))),
                ("soupt2", str(params.get("min_pt", ""))),
                ("soupt1", str(params.get("max_pt", ""))),
                ("f2", str(params.get("min_fav", ""))),
                ("f1", str(params.get("max_fav", ""))),
                ("re2", str(params.get("min_rev", ""))),
                ("re1", str(params.get("max_rev", ""))),
                ("v2", str(params.get("min_episodes", ""))),
                ("v1", str(params.get("max_episodes", ""))),
                ("r2", str(params.get("min_voters", ""))),
                ("r1", str(params.get("max_voters", ""))),
                ("t2", str(params.get("min_conversation", ""))),
                ("t1", str(params.get("max_conversation", ""))),
                ("d2", d2_val),
                ("d1", d1_val),
            ])

            direct_fields = (
                "search_type", "word", "gensaku", "type",
                "mozi2", "mozi1", "mozi2_all", "mozi1_all",
                "rate2", "rate1", "soupt2", "soupt1",
                "f2", "f1", "re2", "re1", "v2", "v1",
                "r2", "r1", "t2", "t1", "d2", "d1"
            )

            for key in direct_fields:
                if key in params:
                    value = params[key]
                    if value is not None:
                        query_params[key] = str(value)

            # 연재 형태
            serial_status = params.get("serial_status")
            if serial_status:
                status_field = cls.SERIAL_STATUSES.get(
                    serial_status,
                    str(serial_status)
                )
                if status_field:
                    query_params[status_field] = "1"

            # 제외 태그
            exclusion_flags = params.get(
                "exclusion_flags",
                params.get("exlusion_flags", [])
            )

            for flag in exclusion_flags:
                tag_field = cls.FLAG_EXCLUSION.get(flag, flag)
                if tag_field:
                    query_params[tag_field] = "1"

            query_params["mode"] = "search_r18"
            query_params["page"] = str(page)

            url = cls.SEARCH_URL + "?" + urlencode(query_params)

            res = cls._get(url, headers={"referer": cls.SEARCH_URL}, timeout=12)
            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")
            items = []

            cards = soup.select(".search-result")

            for card in cards:
                title_a = card.select_one(".blo_title_link")
                if not title_a:
                    continue

                title = title_a.get_text(" ", strip=True)
                href = title_a.get("href", "").strip()

                card_id = card.get("id", "")
                id_match = re.search(r"nid_(\d+)", card_id)

                if id_match:
                    novel_id = id_match.group(1)
                else:
                    url_match = re.search(r"/novel/(\d+)/?", href)
                    novel_id = url_match.group(1) if url_match else ""

                url = urljoin(cls.BASE_URL, href)

                sak_div = card.select_one(".blo_title_sak")
                author = ""
                origin_name = ""

                if sak_div:
                    author_a = sak_div.select_one("a[href*='/user/']")
                    if author_a:
                        author = author_a.get_text(" ", strip=True)

                    for a_tag in sak_div.select("a"):
                        if "/user/" not in a_tag.get("href", ""):
                            origin_name = a_tag.get_text(" ", strip=True)
                            break

                wasuu_div = card.select_one(".blo_wasuu_base")
                episode = 0
                total_chars = 0
                status = ""

                if wasuu_div:
                    status_span = wasuu_div.select_one("span")

                    if status_span:
                        status_title = status_span.get("title", "")
                        status_text = status_span.get_text(strip=True)
                        full_status = f"{status_title} {status_text}"

                        if "完結" in full_status or "완결" in full_status:
                            status = "완결"
                        elif "連載" in full_status or "연재" in full_status:
                            status = "연재중"
                        elif "短編" in full_status or "단편" in full_status:
                            status = "단편"

                    strong_tag = wasuu_div.select_one("strong")

                    if strong_tag:
                        episode = cls._number(strong_tag.get_text())
                    elif status == "단편":
                        episode = 1

                    chars_div = wasuu_div.select_one(
                        "div[title*='字'], div[title*='문자']"
                    )

                    if chars_div:
                        total_chars = cls._number(chars_div.get_text())

                stars = 0
                mix_div = card.select_one(".result-stats")

                if mix_div:
                    star_match = re.search(
                        r"：([\d,]+)",
                        mix_div.get_text()
                    )

                    if star_match:
                        try:
                            raw_val = star_match.group(1)
                            stars = int(raw_val.replace(",", ""))
                        except ValueError:
                            stars = 0

                date_div = card.select_one(".blo_date")
                updated_at = cls._date(
                    date_div.get_text(strip=True)
                ) if date_div else ""

                arasuji_div = card.select_one(".blo_inword")
                story = (
                    arasuji_div.get_text(" ", strip=True)
                    if arasuji_div else ""
                )

                tags_div = card.select_one(".result-tags")
                keywords = []

                if tags_div:
                    keywords = [
                        t.get_text(" ", strip=True)
                        for t in tags_div.select("a")
                        if t.get_text(strip=True)
                    ]

                items.append({
                    "title": title,
                    "url": url,
                    "ncode": novel_id,
                    "author": author,
                    "origin": origin_name,
                    "stars": stars,
                    "total_chars": total_chars,
                    "status_episodes": (
                        f"총 {episode}화 ({status})"
                        if episode else status
                    ),
                    "updated_at": updated_at,
                    "story": story,
                    "keywords": keywords,
                })

            has_next = bool(soup.select_one(".paging a[rel='next']"))

            return {
                "is_last_page": not has_next,
                "items": items
            }

        except Exception as e:
            print(f"[하멜른 R18 검색 에러] {e}")
            return {
                "is_last_page": True,
                "items": []
            }

    @classmethod
    def fetch_detail_description(cls, work_url):
        try:
            res = cls._get(work_url, headers={"referer": cls.SEARCH_URL}, timeout=12)
            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")
            maind_element = soup.find(id="maind")

            if not maind_element:
                return ""

            ss_divs = maind_element.find_all("div", class_="ss")
            if not ss_divs:
                return ""

            for br in maind_element.find_all("br"):
                br.replace_with("\n")

            tag_text = ""
            tag_text_list = []

            for span in (ss_divs[0].find_all("span", itemprop="keywords") + ss_divs[0].find_all("a", class_="alert_color")):
                tag_text_list.append(span.getText())

            target_div = ss_divs[1]
            story_text = target_div.get_text("\n")
            story_text = re.sub(r"\n{3,}", "\n\n", story_text).strip()

            if len(story_text.splitlines()) > 120:
                story_text = '\n'.join(story_text.splitlines()[1:120]) + "\n......."

            if len(ss_divs) > 1:
                tag_text = ','.join(tag_text_list)
                return f"{story_text}\n\n_____1234_____\n{tag_text}"

            return story_text

        except Exception as e:
            print(f"[하멜른 R18 상세 줄거리 조회 에러: {work_url}] {e}")
            return ""