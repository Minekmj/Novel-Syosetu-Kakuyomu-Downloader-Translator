import re
import sqlite3
import time
import json
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from collections.abc import Callable

import src.find.get as datas
from src.find.get import KakuyomuSearch, NaroSearch, SyosetuSearch
from src.trans.trans_ai_utils import build_thinking_config

from google import genai
from google.genai import types

DB_FILE = "./workdatacache.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS WorkDataCache (
                src_text TEXT PRIMARY KEY,
                dst_text TEXT
            )
        """)
init_db()

def get_cached(text):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT dst_text FROM WorkDataCache WHERE src_text = ?", (text,))
        row = cur.fetchone()
        return row[0] if row else None

def set_cached(src_text, dst_text):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT OR REPLACE INTO WorkDataCache VALUES (?, ?)", (src_text, dst_text))

PRINT_OK = False
def PrintIo(text: str):
    if PRINT_OK: print(text)

def site_delay(site: str):
    if site == 'kakuyomu':
        time.sleep(1)
    elif site == 'hameln':
        time.sleep(2.0)

def site_delay_all(site: str):
    if site == 'kakuyomu':
        time.sleep(1)
    elif site == 'naro':
        time.sleep(1)
    elif site == 'hameln':
        time.sleep(2.0)

def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip('/')
    return f"{parsed.scheme}://{netloc}{path}"

def extract_json_from_response(text: str) -> Any:
    text = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            first_brace = text.find('{')
            last_brace = text.rfind('}')
            if first_brace != -1 and last_brace != -1:
                return json.loads(text[first_brace:last_brace + 1])
            first_bracket = text.find('[')
            last_bracket = text.rfind(']')
            if first_bracket != -1 and last_bracket != -1:
                return json.loads(text[first_bracket:last_bracket + 1])
        except:
            pass
        return {}

class GeminiAIClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.1-flash-lite"):
        self.api_key = api_key
        self.model = model

        if not self.api_key:
            err_msg = "GEMINI_API_KEY 환경변수가 설정되지 않았습니다."
            PrintIo(err_msg)
            raise ValueError(err_msg)

        PrintIo(f"[Gemini] 모델 초기화: {self.model}")
        self.client = genai.Client(api_key=self.api_key)

    def generate(self, prompt: str, system_instruction: str = "", max_retries: int = 5) -> str:
        PrintIo(f"[Gemini 요청] 본문 길이: {len(prompt)}자")

        config = types.GenerateContentConfig(
            system_instruction=system_instruction if system_instruction else None,
            temperature=1.0,
            response_mime_type="application/json",
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            thinking_config=build_thinking_config("HIGH", self.model)
        )

        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config
                )
                return response.text or ""
            except Exception as e:
                err_str = str(e)
                is_transient = any(k in err_str.upper() for k in ["503", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "429", "OVERLOADED"])
                if is_transient and attempt < max_retries:
                    print(f"[Gemini 서버 과부하 감지] 3초 대기 후 재시도... ({attempt}/{max_retries})")
                    time.sleep(3)
                    continue
                print(f"[Gemini API 최종 에러]: {e}\n{traceback.format_exc()}")
                return ""

class SearchExecutor:
    def __init__(self):
        self.http_session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.http_session.mount("http://", adapter)
        self.http_session.mount("https://", adapter)

        for mod in (datas, getattr(datas, 'KakuyomuSearch', None), getattr(datas, 'NaroSearch', None), getattr(datas, 'SyosetuSearch', None)):
            if mod and hasattr(mod, 'http_session'):
                try:
                    mod.http_session.mount("http://", adapter)
                    mod.http_session.mount("https://", adapter)
                except Exception:
                    pass

    def run_search_with_retry(self, site: str, site_cls, params: Dict[str, Any], max_attempts: int = 5) -> Dict[str, Any]:
        for attempt in range(1, max_attempts + 1):
            try:
                PrintIo(f"[{site}] 검색 호출 (시도 {attempt}/{max_attempts}) - p.{params.get('page', 1)}, 파라미터: {params}")

                if site == 'kakuyomu':
                    url_kwargs = {
                        "query": params.get("query", ""),
                        "genre_name": params.get("genre_name", ""),
                        "exclude_words": params.get("exclude_words"),
                        "min_chars": params.get("min_chars"),
                        "last_published": params.get("last_published"),
                        "min_start": params.get("min_start"),
                        "serial_status": params.get("serial_status"),
                        "order": params.get("order", "popular"),
                        "inclusion_flag": params.get("inclusion_flag"),
                        "exclusion_flag": params.get("exclusion_flag"),
                        "page": params.get("page", 1)
                    }
                    search_url = site_cls.build_search_url(**url_kwargs)
                    headers = getattr(site_cls, "HEADERS", {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
                        "Accept-Language": "ja,ko-KR;q=0.9,ko;q=0.8,en-US;q=0.7,en;q=0.6",
                    })
                    resp = self.http_session.get(search_url, headers=headers, timeout=12)

                    if resp.status_code == 503:
                        raise RuntimeError("HTTP 503 Service Unavailable")
                    if resp.status_code != 200:
                        raise RuntimeError(f"HTTP {resp.status_code} 오류")

                    return site_cls.parse_search_results(resp.text)

                elif site in ('naro', 'hameln'):
                    if hasattr(site_cls, 'fetch_search_results'):
                        res = site_cls.fetch_search_results(params)
                    else:
                        inst = site_cls() if callable(site_cls) else site_cls
                        res = inst.fetch_search_results(params)
                    return res

            except Exception as e:
                err_msg = str(e)
                is_transient = any(k in err_msg for k in ["503", "Service Unavailable", "Timeout", "429"])
                if is_transient and attempt < max_attempts:
                    PrintIo(f"[{site}] 일시적 연결 장애 감지 ({err_msg}). 3초 대기 후 재시도... ({attempt}/{max_attempts})")
                    time.sleep(3)
                    continue
                raise

        raise RuntimeError(f"[{site}] 검색 {max_attempts}회 재시도 실패")

    def enrich_description(self, site: str, site_cls, item: Dict[str, Any]) -> str:
        existing_story = item.get("story", "") or ""
        current_keywords = list(item.get("keywords", []))

        if '_____1234_____' in existing_story:
            parts = existing_story.split('_____1234_____')
            existing_story = parts[0].strip()
            if len(parts) > 1 and parts[1].strip():
                extra_tags = [k.strip() for k in parts[1].split(',') if k.strip()]
                for t in extra_tags:
                    if t not in current_keywords:
                        current_keywords.append(t)
                item["keywords"] = current_keywords

        if site == 'naro' and existing_story and item.get("keywords"):
            return existing_story

        if existing_story and len(existing_story) >= 150 and len(current_keywords) >= 3:
            return existing_story

        work_url = item.get("url", "")
        if not work_url:
            return existing_story

        fetch_fn = getattr(site_cls, 'fetch_detail_description', None)
        
        data = get_cached(work_url)
        if callable(fetch_fn):
            for attempt in range(1, 4):
                try:
                    if data:
                        detail = data
                    else:
                        detail = fetch_fn(work_url)
                        set_cached(work_url, detail)
                        
                    if isinstance(detail, str):
                        story_text = detail
                        if '_____1234_____' in detail:
                            d_parts = detail.split('_____1234_____')
                            story_text = d_parts[0].strip()
                            tags_text = d_parts[1].strip()
                            if tags_text:
                                new_tags = [t.strip() for t in tags_text.split(',') if t.strip()]
                                for nt in new_tags:
                                    if nt not in current_keywords:
                                        current_keywords.append(nt)
                                item["keywords"] = current_keywords

                        if story_text and len(story_text) > len(existing_story):
                            return story_text.strip()
                    break
                except Exception as e:
                    if "503" in str(e) and attempt < 3:
                        PrintIo(f"[{site}] 상세 페이지 조회 503 감지. 3초 대기...")
                        time.sleep(3)
                        continue
                    PrintIo(f"[{site}] 상세 페이지 수집 실패 ({work_url}): {e}")
        if not data:  
            site_delay(site)

        return existing_story
    
    def get_description(self, site: str, site_cls, work_url: str) -> str:
        story = ""
        current_keywords = []
        
        fetch_fn = getattr(site_cls, 'fetch_detail_description', None)
        if not fetch_fn:
            fetch_fn = getattr(site_cls, 'fetch_detail_description_real', None)

        data = get_cached(work_url)
        if callable(fetch_fn):
            for attempt in range(1, 4):
                try:
                    if data:
                        detail = data
                    else:
                        detail = fetch_fn(work_url)
                        set_cached(work_url, detail)
                        
                    if isinstance(detail, str):
                        story_text = detail
                        if '_____1234_____' in detail:
                            d_parts = detail.split('_____1234_____')
                            story_text = d_parts[0].strip()
                            tags_text = d_parts[1].strip()
                            if tags_text:
                                new_tags = [t.strip() for t in tags_text.split(',') if t.strip()]
                                for nt in new_tags:
                                    if nt not in current_keywords:
                                        current_keywords.append(nt)
                            story = story_text
                    break
                except Exception as e:
                    if "503" in str(e) and attempt < 3:
                        PrintIo(f"[{site}] 상세 페이지 조회 503 감지. 3초 대기...")
                        time.sleep(3)
                        continue
                    PrintIo(f"[{site}] 상세 페이지 수집 실패 ({work_url}): {e}")
        
        if not data:
            site_delay_all(site)

        return story, current_keywords

class NovelRecommender:
    def __init__(self, gemini_api_key: Optional[str] = None, model: str = "gemini-3.1-flash-lite", user_data: dict = {"list":{"없음":{"src":"None"}}}, log: Callable=None):
        self.ai = GeminiAIClient(api_key=gemini_api_key, model=model)
        self.executor = SearchExecutor()
        self.back_decision = ""
        self.user_data = user_data
        if user_data == {'list': {}}:
            self.user_data = {"list":{"없음":{"src":"None"}}}
        self.log = log

        self.site_meta = {
            'kakuyomu': {'cls': KakuyomuSearch, 'name': '카쿠요무'},
            'naro': {'cls': NaroSearch, 'name': '소설가가 되자'},
            'hameln': {'cls': SyosetuSearch, 'name': '하멜른'}
        }
        self.site_success_counts = {'kakuyomu': 0, 'naro': 0, 'hameln': 0}

    def get_read_history(self) -> Dict[str, Any]:
        self.log("info", "사용자 작품 목록 로드 중...")
        PrintIo("[행동] 사용자 감상 목록 로드")
        user_data = self.user_data

        raw_list = user_data.get("list", {})
        history_items = []
        read_urls = set()

        for title, info in raw_list.items():
            if not isinstance(info, dict):
                continue
            src = info.get("src", "")
            norm_url = normalize_url(src)
            if norm_url:
                read_urls.add(norm_url)

            site_key = "unknown"
            if "kakuyomu.jp" in src:
                site_key = "kakuyomu"
            elif "syosetu.org" in src:
                site_key = "hameln"
            elif "syosetu.com" in src:
                site_key = "naro"
            
            set_data = {
                "title": title,
                "url": src
            }
            a = SearchExecutor()
            try:
                set_data["story"], set_data["keywords"] = a.get_description(site_key, {"kakuyomu":KakuyomuSearch, "naro":NaroSearch, "hameln":SyosetuSearch}[site_key], src)
            except:
                pass
            
            history_items.append(set_data)

        PrintIo(f"[기록] 감상 작품 수: {len(history_items)}개, 등록된 URL: {len(read_urls)}개")
        return {"items": history_items, "read_urls": read_urls}

    def _build_platform_spec_text(self) -> str:
        return """
[3대 소설 플랫폼 완벽 파라미터 규격서]

★ 핵심 검색 전략 및 일본 웹소설 엔진 특성:
1. 웹소설 검색창(query)은 기본적으로 AND 조건입니다.  특정 장르를 보고 싶다먄 0개를 사용하소. 1개 또는 최대 2개의 가장 핵심적인 태그만 입력하여 상세 검색하세요. 단만 매우 상세히 검색 하고 싶을 시에는 4개 이상 사용해도 좋습니다.
2. 장르와 쿼리를 중복하지 마세요 (예: 러브코미디 장르를 선택했으면 쿼리에 "ラブコメ"를 또 넣지 말고 "すれ違い"나 "甘々" 같은 구체적 상황 태그를 넣으세요).
3. 컷오프(min_pt, min_chars)를 처음부터 너무 높게 잡으면 작품이 전멸합니다. 적절한 하한선을 설정하세요.
4. 이전 라운드에서 new_added가 (카쿠요무, 나로우는 15개, 하멜른은 6개 이상)개 이상 나온 성공 쿼리는 재량껏 다음 라운드에서 page: 2, page: 3으로 연속 탐색을 할 수 있습니다.

1. kakuyomu (카쿠요무)
- query: 일본어 검색어/태그
- genre_name: "fantasy"(이세계판타지), "action"(현대판타지), "sf"(SF), "love_story"(연애), "romance"(러브코미디), "drama"(현대드라마), "horror"(호러), "mystery"(미스터리), "nonfiction"(에세이/논픽션), "history"(역사/시대), "criticism"(평론/창작론), "others"(시/기타), "fan_fiction"(2차창작), ""(전체)
- order: "popular"(인기순), "weekly_ranking"(주간랭킹순), "published_at"(최신작성순), "last_episode_published_at"(최신갱신순), "total_character_count"(글자수순)
- serial_status: ""(전체), "running"(연재 중), "completed"(완결)
- last_published: ""(전체), "1days"(1일 이내), "7days"(7일 이내), "1months"(1개월 이내), "6months"(6개월 이내), "1years"(1년 이내)
- min_start: 리뷰 별점 하한선 정수 (예: 30, 50, 100, 300)
- min_chars: 총 글자수 하한선 정수 (예: 10000, 30000)
- exclude_words: 제외 단어 리스트 (예: [""])
- inclusion_flag: 필수 포함 플래그 리스트 (허용값: "cruel", "violent", "sexual", "has_publication")
- exclusion_flag: 절대 배제 플래그 리스트 (허용값: "cruel", "violent", "sexual", "has_publication")

2. naro (소설가가 되자)
- query: 일본어 검색어/태그
- genre_val: 정수 코드
  0(전체), 1(연애전체), 101(이세계 연애), 102(현실 연애), 2(판타지전체), 201(하이 판타지), 202(로우 판타지), 3(문예), 301(순문학), 302(휴먼 드라마), 303(역사), 304(추리), 305(공포), 306(액션), 307(코미디), 4(SF), 401(VR 게임), 402(우주), 403(공산 과학), 404(공황), 99(기타), 98(논픽션)
- order: "hyoka"(포인트순), "weeklypoint"(주간포인트순), "monthlypoint"(월간포인트순), "quarterpoint"(분기포인트순), "yearlypoint"(연간포인트순), "new"(신작순), "weekly"(최신갱신순), "length"(글자수순)
- serial_status: ""(전체), "r"(연재중), "er"(완결), "t"(단편), "re"(연재-예약포함)
- last_published: 일수 정수 (1, 7, 30, 90, 180, 365, null)
- min_pt: 종합 포인트 하한선 정수 (예: 300, 1000, 3000)
- min_chars: 최소 글자수 정수 (예: 10000, 50000)
- exclude_words: 제외어 리스트 (예: [""])
- inclusion_flags: 필수 포함 태그 리스트 (허용값: "ai", "r15", "zankoku", "bl", "gl", "tensei", "tenni", "stop")
- exlusion_flags: 배제 태그 리스트 (허용값: "ai", "r15", "zankoku", "bl", "gl", "tensei", "tenni", "stop")

3. hameln (하멜른)
- query: 일본어 검색어/태그
- genre_val: "ジャンル：冒険・バトル", "ジャンル：戦記", "ジャンル：恋愛", "ジャンル：スポーツ", "ジャンル：コメディ", "ジャンル：ホラー", "ジャンル：ミステリー", "ジャンル：日常", "ジャンル：文芸", "ジャンル：ノンジャンル", ""(전체)
- origin: "原作：オリジナル"(오리지널 창작), "原作：二次創作"(2차창작), "原作：(`특정 작품` 일본어 제목)"(`특정 작품` 2차창작)
- order: "45"(최종갱신순), "28"(종합평가순), "4"(평균평가순), "42"(가중평균순), "30"(주간종합평가), "31"(월간종합평가), "32"(분기종합평가), "33"(연간종합평가), "10"(즐겨찾기순), "20"(총글자수순), "24"(화수순), "22"(감상순), "6"(1화문자수순), "8"(첫게시일), "0"(신착순)
- serial_status: ""(전체), "rensai_s2"(연재중), "rensai_s4"(완결), "rensai_s1"(단편)
- last_published: 일수 정수 (1, 7, 30, 90, 180, 365, null)
- min_pt: 종합 평가 포인트(soupt2) 하한 정수 (예: 50, 200, 500)
- min_chars: 전체 글자수(mozi2_all) 하한 정수 (예: 20000, 50000)
- exclude_words: 제외어 리스트 (예: [""])
- inclusion_flags: 추가 포함어 리스트
- exclusion_flags: 배제 태그 리스트. 허용 태그코드: "tag15"(AI), "tag2"(R15), "tag7"(잔혹), "tag12"(크로스오버), "tag5"(오리주), "tag6"(신전생), "tag9"(환생), "tag10"(빙의), "tag11"(성전환/TS), "tag3"(BL), "tag4"(GL), "tag8"(안티헤이트), "tag13"(게시판형식), "tag14"(대본형식)
"""

    def build_search_params(self, site: str, strategy: Dict[str, Any], page: int = 1) -> Dict[str, Any]:
        raw_query = strategy.get("query")
        if raw_query is None:
            raw_query = strategy.get("keywords") or strategy.get("tags") or []

        if isinstance(raw_query, list):
            query = " ".join(str(w).strip() for w in raw_query if str(w).strip())
        elif isinstance(raw_query, str):
            query = raw_query.strip()
        else:
            query = ""

        raw_exc = strategy.get("exclude_words", [])
        if isinstance(raw_exc, str):
            exclude = [w.strip() for w in raw_exc.split() if w.strip()]
        elif isinstance(raw_exc, list):
            exclude = [str(w).strip() for w in raw_exc if str(w).strip()]
        else:
            exclude = []

        def to_int(v, default=0):
            try:
                return int(v) if v is not None and str(v).strip() != "" else default
            except (ValueError, TypeError):
                return default

        def to_opt_int(v):
            try:
                return int(v) if v is not None and str(v).strip() != "" else None
            except (ValueError, TypeError):
                return None

        def ensure_list(v):
            if isinstance(v, list):
                return [str(x).strip() for x in v if str(x).strip()]
            if isinstance(v, str) and v.strip():
                return [v.strip()]
            return []

        genre = strategy.get("genre", strategy.get("genre_name", strategy.get("genre_val", "")))
        order = strategy.get("order", "")
        status = strategy.get("serial_status", "")
        last_pub = strategy.get("last_published", None)

        inc_flags = ensure_list(strategy.get("inclusion_flags", strategy.get("inclusion_flag", [])))
        exc_flags = ensure_list(strategy.get("exclusion_flags", strategy.get("exlusion_flags", strategy.get("exclusion_flag", []))))

        min_chars = to_int(strategy.get("min_chars", 0))
        min_pt = to_int(strategy.get("min_pt", strategy.get("min_start", 0)))

        if site == 'kakuyomu':
            genre_name = ""
            if KakuyomuSearch and hasattr(KakuyomuSearch, 'GENRES'):
                if genre in KakuyomuSearch.GENRES.values():
                    genre_name = genre
                elif genre in KakuyomuSearch.GENRES:
                    genre_name = KakuyomuSearch.GENRES[genre]

            order_val = order if (KakuyomuSearch and order in KakuyomuSearch.SORT_ORDERS.values()) else "popular"
            if not order_val and KakuyomuSearch and order in KakuyomuSearch.SORT_ORDERS:
                order_val = KakuyomuSearch.SORT_ORDERS[order]

            status_val = status if (KakuyomuSearch and status in KakuyomuSearch.SERIAL_STATUSES.values()) else ""
            if not status_val and KakuyomuSearch and status in KakuyomuSearch.SERIAL_STATUSES:
                status_val = KakuyomuSearch.SERIAL_STATUSES[status]

            valid_pub = ["1days", "7days", "1months", "6months", "1years"]
            last_pub_str = str(last_pub) if str(last_pub) in valid_pub else ""
            if not last_pub_str and KakuyomuSearch and last_pub in KakuyomuSearch.LAST_PUBLISHED_PERIODS:
                last_pub_str = KakuyomuSearch.LAST_PUBLISHED_PERIODS[last_pub]

            valid_k_flags = {"cruel", "violent", "sexual", "has_publication"}
            k_inc = [f for f in inc_flags if f in valid_k_flags]
            k_exc = [f for f in exc_flags if f in valid_k_flags]

            return {
                'query': query,
                'genre_name': genre_name,
                'exclude_words': exclude,
                'min_chars': min_chars,
                'last_published': last_pub_str,
                'min_start': min_pt,
                'serial_status': status_val,
                'order': order_val or "popular",
                'inclusion_flag': k_inc,
                'exclusion_flag': k_exc,
                'page': page
            }

        elif site == 'naro':
            genre_val = 0
            if isinstance(genre, int):
                genre_val = genre
            elif str(genre).isdigit():
                genre_val = int(genre)
            elif NaroSearch and hasattr(NaroSearch, 'GENRES') and genre in NaroSearch.GENRES:
                genre_val = NaroSearch.GENRES[genre]

            order_val = order if (NaroSearch and order in NaroSearch.SORT_ORDERS.values()) else "hyoka"
            if not order_val and NaroSearch and order in NaroSearch.SORT_ORDERS:
                order_val = NaroSearch.SORT_ORDERS[order]

            status_val = status if (NaroSearch and status in NaroSearch.SERIAL_STATUSES.values()) else ""
            if not status_val and NaroSearch and status in NaroSearch.SERIAL_STATUSES:
                status_val = NaroSearch.SERIAL_STATUSES[status]

            last_pub_val = None
            if last_pub is not None:
                if str(last_pub).isdigit():
                    last_pub_val = int(last_pub)
                elif NaroSearch and hasattr(NaroSearch, 'LAST_PUBLISHED_PERIODS') and last_pub in NaroSearch.LAST_PUBLISHED_PERIODS:
                    last_pub_val = NaroSearch.LAST_PUBLISHED_PERIODS[last_pub]

            valid_n_flags = {"ai", "r15", "zankoku", "bl", "gl", "tensei", "tenni", "stop"}
            flag_map = {
                "AI 사용": "ai", "R15": "r15", "잔인한 묘사": "zankoku", "BL": "bl", "GL": "gl",
                "이세계 환생": "tensei", "이세계 전이": "tenni", "장기 연재 중단": "stop"
            }
            n_inc = [flag_map.get(f, f) for f in inc_flags if flag_map.get(f, f) in valid_n_flags]
            n_exc = [flag_map.get(f, f) for f in exc_flags if flag_map.get(f, f) in valid_n_flags]

            return {
                'query': query,
                'genre_val': genre_val,
                'exclude_words': exclude,
                'min_chars': min_chars,
                'min_pt': min_pt,
                'last_published': last_pub_val,
                'serial_status': status_val,
                'order': order_val or "hyoka",
                'inclusion_flags': n_inc,
                'exlusion_flags': n_exc,
                'page': page
            }

        elif site == 'hameln':
            genre_val = ""
            if SyosetuSearch and hasattr(SyosetuSearch, 'GENRES'):
                if genre in SyosetuSearch.GENRES.values():
                    genre_val = genre
                elif genre in SyosetuSearch.GENRES:
                    genre_val = SyosetuSearch.GENRES[genre]

            order_val = str(order) if (SyosetuSearch and str(order) in SyosetuSearch.SORT_ORDERS.values()) else "45"
            if SyosetuSearch and order in SyosetuSearch.SORT_ORDERS:
                order_val = SyosetuSearch.SORT_ORDERS[order]

            status_val = status if (SyosetuSearch and status in SyosetuSearch.SERIAL_STATUSES.values()) else ""
            if not status_val and SyosetuSearch and status in SyosetuSearch.SERIAL_STATUSES:
                status_val = SyosetuSearch.SERIAL_STATUSES[status]

            origin_val = strategy.get("origin") or strategy.get("flags_main") or strategy.get("gensaku") or "原作：オリジナル"

            last_pub_val = None
            if last_pub is not None:
                if str(last_pub).isdigit():
                    last_pub_val = int(last_pub)
                elif SyosetuSearch and hasattr(SyosetuSearch, 'LAST_PUBLISHED_PERIODS') and last_pub in SyosetuSearch.LAST_PUBLISHED_PERIODS:
                    last_pub_val = SyosetuSearch.LAST_PUBLISHED_PERIODS[last_pub]

            h_exc_map = {
                "AI 사용": "tag15", "ai": "tag15", "tag15": "tag15",
                "R15": "tag2", "r15": "tag2", "tag2": "tag2",
                "잔인한 묘사": "tag7", "zankoku": "tag7", "tag7": "tag7",
                "크로스오버": "tag12", "crossover": "tag12", "tag12": "tag12",
                "오리주": "tag5", "tag5": "tag5",
                "신 전생": "tag6", "하나님 환생": "tag6", "tag6": "tag6",
                "환생": "tag9", "tensei": "tag9", "tag9": "tag9",
                "빙의": "tag10", "tag10": "tag10",
                "성전환": "tag11", "ts": "tag11", "TS": "tag11", "tag11": "tag11",
                "BL": "tag3", "bl": "tag3", "tag3": "tag3",
                "GL": "tag4", "gl": "tag4", "tag4": "tag4",
                "안티 헤이트": "tag8", "tag8": "tag8",
                "게시판 형식": "tag13", "tag13": "tag13",
                "대본 형식": "tag14", "tag14": "tag14",
            }
            h_exc = [h_exc_map[f] for f in exc_flags if f in h_exc_map]

            res = {
                'query': query,
                'genre_val': genre_val,
                'flags_main': origin_val,
                'origin': origin_val,
                'gensaku': origin_val,
                'exclude_words': exclude,
                'serial_status': status_val,
                'order': order_val,
                'last_published': last_pub_val,
                'inclusion_flags': inc_flags,
                'exclusion_flags': h_exc,
                'exlusion_flags': h_exc,
                'page': page
            }

            for field, key in [
                ("min_chars", "min_chars"), ("max_chars", "max_chars"),
                ("min_ep_chars", "min_ep_chars"), ("max_ep_chars", "max_ep_chars"),
                ("min_pt", "min_pt"), ("max_pt", "max_pt"),
                ("min_fav", "min_fav"), ("max_fav", "max_fav"),
                ("min_rate", "min_rate"), ("max_rate", "max_rate"),
                ("min_episodes", "min_episodes"), ("max_episodes", "max_episodes"),
                ("min_rev", "min_rev"), ("min_voters", "min_voters")
            ]:
                val = to_opt_int(strategy.get(field))
                if val is not None:
                    res[key] = val

            return res

        return {}

    def agent_decide_searches(
        self,
        round_num: int,
        history_items: List[Dict[str, Any]],
        user_custom_prompt: Optional[str],
        collected_summary: List[Dict[str, Any]],
        search_history_logs: List[Dict[str, Any]],
        top_k: int = 5
    ) -> Dict[str, Any]:
        spec_text = self._build_platform_spec_text()

        platform_counts = {'kakuyomu': 0, 'naro': 0, 'hameln': 0}
        for c in collected_summary:
            st = c.get('site_type')
            if st in platform_counts:
                platform_counts[st] += 1

        platform_plus = {'kakuyomu': 15, 'naro': 15, 'hameln': 6}
        successful_queries = []
        for log in search_history_logs:
            if log.get("new_added", 0) >= platform_plus[log['site']]:
                successful_queries.append(
                    f"★ 성공 대박 조건: [{log['site']}] p.{log['page']} Q:'{log.get('query')}' -> 유효 신규작 {log.get('new_added')}개 발굴! (다음 페이지 page: {log['page'] + 1} 연속 탐색 추천)"
                )
            elif log.get("returned", 0) == 0 and "FAILED" not in log.get("status", ""):
                successful_queries.append(
                    f"⚠ 결과 0건 실패: [{log['site']}] Q:'{log.get('query')}' (조건이 너무 빡빡하거나 태그가 많음. 태그 수를 1개로 줄이거나 min_pt 완화 필요)"
                )
        success_tips = "\n".join(successful_queries[-8:]) if successful_queries else "아직 성공/실패 패턴 기록 없음"

        user_req_text = f"## ★ [사용자 특별 요청 조건 (최우선 절대 원칙)][매우중요]:\n\"{user_custom_prompt}\"\n[end 사용자 조건]\n" if user_custom_prompt else "★ [사용자 특별 요청 조건]: 없음"
        system_instruction = (
            "당신은 일본 3대 웹소설 플랫폼(카쿠요무, 소설가가되자, 하멜른)을 통달한 최고 실력의 수석 데이터 큐레이터입니다.\n"
            "목표: [사용자 특별 요청 조건]과 독자의 기존 취향을 철저히 분석하여, 방황 없이 가장 정밀한 검색 쿼리와 파라미터를 발주하는 것입니다.\n\n"
            "★ 핵심 지침:\n"
            "1. [검색어(query) 규칙]: 일본어 웹소설 태그를 넣으세요.\n"
            "2. [지뢰 및 금기 배제]: 사용자가 싫어하는 요소는 exclude_words, exclusion_flags를 통해 검색 단계부터 원천 차단하세요.\n"
            "3. [성공 쿼리 심층 페이징]: 이전 라운드에서 유효작이 많이 나온 조건은 반드시 동일 조건에 page만 +1 하여 심층 탐색하세요.\n"
            "4. [플랫폼 집중]: 장르 특성에 맞는 사이트에 집중하세요.\n"
            "5. [종료 판단]: 고품질 후보가 충분히 확보 되었고 요청 조건에 완벽히 부합하면 'FINISH', 부족하면 'CONTINUE'를 선언하세요."
        )
        
        result_list = [
            {
                h.get("title", ""): {
                    "story": h.get("story", ""),
                    "keywords": h.get("keywords", [])
                }
            }
            for h in history_items
        ]
        json_result = json.dumps(result_list, ensure_ascii=False, indent=2)

        prompt = f"""
{spec_text}

{user_req_text}

[독자의 기존 감상 작품 이력]
{json_result}

[현재 탐색 상태]
- 라운드: {round_num}차 루프
- 누적 확보 고유 후보: 총 {len(collected_summary)}개 (카쿠요무 {platform_counts['kakuyomu']}개, 나로우 {platform_counts['naro']}개, 하멜른 {platform_counts['hameln']}개)
- 최근 확보된 후보 표본: {[c['title'] for c in collected_summary[-5:]]}

[최근 검색 시도 분석 및 피드백]
{success_tips}

[최근 5회 원본 검색 로그]
{json.dumps(search_history_logs[-5:], ensure_ascii=False, indent=2) if search_history_logs else "첫 번째 탐색 라운드입니다."}

위 정보를 바탕으로 아래 JSON 규격으로만 응답하세요:
{{
  "ai_thought": "현재 후보군 상태, 사용자 요청 조건 및 금기 사항 분석, 이번 라운드에 발주할 검색 전략",
  "decision": "CONTINUE",  // 후보가 충분히 검증되었으면 "FINISH", 더 필요하면 "CONTINUE"
  "actions": [
    {{
      "site": "kakuyomu",  // "kakuyomu", "naro", "hameln"
      "reason": "구체적인 전략적 선정 사유", //다만 조건들을 나열하는 것이 아니라 자연스럽게 설명하는 것이며 일본어 태그를 말할 시 한국어로 말 해준다. "decision"의 상태를 직접적으로 말하는 것이아니라 '속행', '끝' 이런식으로 일반 사용자가 들을 수 있도록 한다.
      "page": 1,
      "query": [],  // 핵심 일본어 태그 0~2개. 매우 상세히 알고 싶으면 3개 이상(이 때는 대중적인 태그를 사용하여야 함.)
      "genre": "romance",
      "order": "popular",
      "serial_status": "running",
      "last_published": "1months",
      "min_pt": 50,
      "min_chars": 10000,
      "exclude_words": [],
      "inclusion_flags": [],
      "exclusion_flags": [],
      "origin": "原作：オリジナル",  // 하멜른 전용
    }}
  ]
}}
* CONTINUE일 때는 반드시 1~3개의 action을 지시하세요.
* action은 보통 사이트를 골고루 넣지만 같은 사이트를 여러번하여도 좋습니다.
* 70개 이상 많은 작품이 있을 시 더이상 검색을 하지 말고 "FINISH"를 무조건 사용해야 합니다. [매우중요]
* 무조건 70개 이상일 때만 멈추는 것이 아니라 70개 보다 작은 수의 작품이라도 이정도면 충분하다고 판단되면 "FINISH" 해도 좋습니다.
"""
        raw_res = self.ai.generate(prompt, system_instruction)
        return extract_json_from_response(raw_res)

    def triage_candidates_with_ai(
        self,
        items_to_triage: List[Dict[str, Any]],
        user_custom_prompt: Optional[str],
        history_items: List[Dict[str, Any]]
    ) -> Dict[int, Dict[str, str]]:
        if not items_to_triage:
            return {}

        simplified_list = []
        for idx, it in enumerate(items_to_triage):
            simplified_list.append({
                "id": idx,
                "title": it.get("title", ""),
                "keywords": it.get("keywords", []),
                "story_preview": (it.get("story", "") or "")[:250]
            })

        user_req_text = f"★ [사용자 특별 요청 조건 (최우선 절대 원칙)]:\n\"{user_custom_prompt}\"\n" if user_custom_prompt else "★ [사용자 특별 요청 조건]: 없음"

        system_instruction = (
            "당신은 일본 웹소설 1차 사전 스크리닝 심사관입니다.\n"
            "목표1: 제목, 키워드(태그), 간이 줄거리를 보고 사용자의 특별 요청 조건과 독자 취향에 맞는지 냉철하게 판정하는 것입니다.\n"
            "목표2: 작품 후보를 줄이는 역할을 하며 25개 이상의 매우 많은 작품일 경우 최대 20개의 작품만 '줄거리'로 판정 할 수 있고, 5개만 '의심' 판정 할 수 있습니다. 그리고 남은 작품은 전부 '버려'로 지정합니다. 이 때 최선의 선택을 하여야 합니다.\n\n"
            "★ 판정 상태 (정확히 다음 3가지 중 하나로 판정):\n"
            "1. '버려': 사용자의 금기 조건이 확인되거나, 질적으로 부적합한 경우. 또는 사용자가 싫어할 것으로 예상이 되거나 절대 선택될 일이 없는 작품 -> 상세 조회 없이 즉시 폐기.\n"
            "2. '줄거리': 요청 조건과 취향에 부합하는 명백한 핵심 키워드가 확인되어 정밀 검토할 가치가 매우 높은 경우.\n"
            "3. '의심': 제목이나 미리보기만으로는 적합성을 단정하기 어려워 상세 줄거리를 확인할 필요가 있는 경우.\n"
        )
        
        result_list = [
            {
                h.get("title", ""): {
                    "story": h.get("story", ""),
                    "keywords": h.get("keywords", [])
                }
            }
            for h in history_items
        ]
        json_result = json.dumps(result_list, ensure_ascii=False, indent=2)

        prompt = f"""
{user_req_text}

[독자의 기존 감상 작품 이력]
{json_result}

[1차 심사 대상 작품 목록 ({len(simplified_list)}개)]
{json.dumps(simplified_list, ensure_ascii=False, indent=2)}

각 id에 대해 아래 JSON 규격으로 응답하세요:
{{
  "triage_results": [
    {{
      "id": 0,
      "status": "줄거리",  // "줄거리", "의심", "버려" 중 하나
    }}
  ]
}}
* 모든 id가 포함되어야 합니다.
"""
        try:
            parsed = {}
            for _ in range(3):
                raw_res = self.ai.generate(prompt, system_instruction)
                parsed = extract_json_from_response(raw_res)
                if parsed != {}:
                    break
            results = parsed.get("triage_results", [])

            status_map = {}
            for r in results:
                if isinstance(r, dict) and "id" in r:
                    status_map[r["id"]] = {
                        "status": r.get("status", "의심")
                    }

            for idx in range(len(items_to_triage)):
                if idx not in status_map:
                    status_map[idx] = {"status": "의심"}
                    PrintIo(f"[경고] 결과에 {idx}가 없어 '의심'으로 지정")

            return status_map

        except Exception as e:
            PrintIo(f"[1차 스크리닝 AI 오류]: {e} -> 전원 '의심'으로 처리합니다.")
            return {idx: {"status": "의심"} for idx in range(len(items_to_triage))}

    def run_agentic_search(
        self,
        history_items: List[Dict[str, Any]],
        read_urls: Set[str],
        user_custom_prompt: Optional[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        
        PrintIo("=== AI 자율 에이전트 다회차 탐색 가동 ===")

        all_candidates: Dict[str, Dict[str, Any]] = {}
        discarded_urls: Set[str] = set()
        search_history_logs: List[Dict[str, Any]] = []

        max_agent_rounds = 7
        
        round_idx = 0
        round_all = 0

        while round_idx < max_agent_rounds:
            
            round_idx += 1
            round_all += 1
            
            if self.back_decision == "FINISH":
                if len(all_candidates) < top_k:
                    PrintIo(f"[안내] 목표({top_k}작품) 대비 후보군({len(all_candidates)}개)이 부족하여 추가 탐색합니다.")
                else:
                    PrintIo(f"[AI 자율 판단] 후보군({len(all_candidates)}개) 확보 완료로 탐색을 자율 종료합니다.")
                    break
                
            total_searches = sum(self.site_success_counts.values())
            if total_searches >= 20:
                PrintIo("[안내] 총 검색 실행 횟수 상한에 도달하여 탐색을 마칩니다.")
                break

            PrintIo(f"\n[라운드 {round_idx}/{max_agent_rounds}] 전략 수립 및 파라미터 계획 수립")

            plan = self.agent_decide_searches(
                round_num=round_all,
                history_items=history_items,
                user_custom_prompt=user_custom_prompt,
                collected_summary=list(all_candidates.values()),
                search_history_logs=search_history_logs,
                top_k=top_k
            )

            ai_thought = plan.get("ai_thought", "")
            decision = str(plan.get("decision", "CONTINUE")).upper()
            actions = plan.get("actions", [])
            if not isinstance(actions, list):
                actions = []

            PrintIo(f"[AI 사고 과정]: {ai_thought}")
            self.log("ai", ai_thought)
            PrintIo(f"[AI 결정]: {decision} (실행할 액션: {len(actions)}건)")
            
            self.back_decision = decision
            if len(actions) == 0:
                if self.back_decision == "FINISH":
                    if len(all_candidates) < top_k:
                        PrintIo(f"[안내] 목표({top_k}작품) 대비 후보군({len(all_candidates)}개)이 부족하여 추가 탐색합니다.")
                    else:
                        PrintIo(f"[AI 자율 판단] 후보군({len(all_candidates)}개) 확보 완료로 탐색을 자율 종료합니다.")
                        break

            round_pending_items: List[Dict[str, Any]] = []
            action_results_meta: List[Dict[str, Any]] = []

            for act in actions:
                if not isinstance(act, dict):
                    continue
                site = act.get("site", "kakuyomu")
                if site not in self.site_meta:
                    continue

                try:
                    page = int(act.get("page", 1) or 1)
                except (ValueError, TypeError):
                    page = 1

                site_cls = self.site_meta[site]['cls']
                params = self.build_search_params(site, act, page=page)

                pt_disp = params.get('min_pt') if 'min_pt' in params else params.get('min_start', 0)
                exc_disp = params.get('exclude_words', []) + params.get('exclusion_flag', []) + params.get('exlusion_flags', [])

                PrintIo(
                    f"▶ [{site}] 실행 (누적 {self.site_success_counts[site]}회) - p.{page}, Q:'{params.get('query')}', 장르:'{params.get('genre_name') or params.get('genre_val')}', 정렬:'{params.get('order')}', PT:{pt_disp}, 제외:{exc_disp}"
                )
                self.log("info", f"{site} 검색 실행")

                try:
                    result = self.executor.run_search_with_retry(site, site_cls, params)
                    site_delay_all(site)
                    raw_items = result.get("items", []) if isinstance(result, dict) else []
                    self.site_success_counts[site] += 1

                    valid_action_items = []
                    for it in raw_items:
                        if not isinstance(it, dict):
                            continue
                        u = normalize_url(it.get("url", ""))
                        if u and u not in read_urls and u not in all_candidates and u not in discarded_urls:
                            if any(normalize_url(x.get("url", "")) == u for x in round_pending_items):
                                continue
                            it["site_type"] = site
                            it["_site_cls"] = site_cls
                            it["_action_idx"] = len(action_results_meta)
                            round_pending_items.append(it)
                            valid_action_items.append(it)

                    action_results_meta.append({
                        "site": site,
                        "page": page,
                        "query": params.get("query"),
                        "raw_count": len(raw_items),
                        "pending_count": len(valid_action_items),
                        "new_added": 0,
                        "status": "SUCCESS"
                    })

                except Exception as e:
                    PrintIo(f"   => [검색 실패]: {e}")
                    search_history_logs.append({
                        "site": site,
                        "page": page,
                        "query": params.get("query"),
                        "returned": 0,
                        "new_added": 0,
                        "status": f"FAILED: {e}"
                    })

            if not round_pending_items:
                PrintIo("   => 이번 라운드 신규 발견 작품이 없습니다.")
                for meta in action_results_meta:
                    search_history_logs.append({
                        "site": meta["site"],
                        "page": meta["page"],
                        "query": meta["query"],
                        "returned": meta["raw_count"],
                        "new_added": 0,
                        "status": meta["status"]
                    })
                round_idx -= 1
                continue

            PrintIo(f"[1차 스크리닝] 신규 발굴 {len(round_pending_items)}작품 대상 적합성 사전 심사")
            self.log("info", f"총 {len(round_pending_items)}개의 찾은 작품 정리 중...")
            triage_map = self.triage_candidates_with_ai(
                round_pending_items,
                user_custom_prompt=user_custom_prompt,
                history_items=history_items
            )

            triage_stats = {"통과": 0, "의심": 0, "버려": 0}

            for idx, it in enumerate(round_pending_items):
                u = normalize_url(it.get("url", ""))
                site = it.get("site_type", "kakuyomu")
                site_cls = it.get("_site_cls")
                act_idx = it.get("_action_idx", 0)
                title = it.get("title", "")

                decision_info = triage_map.get(idx, {"status": "의심"})
                raw_status = str(decision_info.get("status", "의심")).strip()

                if "버려" in raw_status or "삭제" in raw_status or "제외" in raw_status or "탈락" in raw_status:
                    norm_status = "버려"
                elif "줄거리" in raw_status or "적합" in raw_status:
                    norm_status = "통과"
                else:
                    norm_status = "의심"

                triage_stats[norm_status] += 1

                if norm_status == "버려":
                    PrintIo(f"   ✖ [1차 탈락] {title} ({site})")
                    discarded_urls.add(u)
                    continue

                PrintIo(f"   ✔ [1차 통과/{norm_status}] {title} ({site}) - OK")
                try:
                    it["story"] = self.executor.enrich_description(site, site_cls, it)
                except Exception as e:
                    PrintIo(f"상세 정보 수집 중 에러 ({u}): {e}")

                all_candidates[u] = it

                if 0 <= act_idx < len(action_results_meta):
                    action_results_meta[act_idx]["new_added"] += 1

            PrintIo(
                f"[1차 스크리닝 결산] 신규 {len(round_pending_items)}개 중 [통과: {triage_stats['통과'] + triage_stats['의심']}개], [버려: {triage_stats['버려']}개 제외] (누적 고유 후보: {len(all_candidates)}개)"
            )
            self.log("info", f"{len(round_pending_items)}개의 결과 중 {triage_stats['통과'] + triage_stats['의심']}개 통과")

            for meta in action_results_meta:
                search_history_logs.append({
                    "site": meta["site"],
                    "page": meta["page"],
                    "query": meta["query"],
                    "returned": meta["raw_count"],
                    "new_added": meta["new_added"],
                    "status": meta["status"]
                })

        return list(all_candidates.values())

    def rerank_and_synthesize(
        self,
        history_items: List[Dict[str, Any]],
        user_custom_prompt: Optional[str],
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> Dict[str, Any]:
        PrintIo(f"[행동] Gemini 2차: 수집된 {len(candidates)}개 후보 중 최적의 {top_k}작품 심층 리랭킹 및 평가")

        if not candidates:
            return {"curator_note": "조건에 부합하는 신작 소설을 발굴하지 못했습니다.", "recommended_works": []}

        simplified_candidates = []
        for idx, c in enumerate(candidates):
            simplified_candidates.append({
                "candidate_id": idx,
                "title": c.get("title", ""),
                "site": c.get("site_type", ""),
                "url": c.get("url", ""),
                "stars": c.get("stars", 0),
                "episodes": c.get("status_episodes", ""),
                "updated_at": c.get("updated_at", ""),
                "story": (c.get("story", "") or "")[:900],
                "keywords": c.get("keywords", [])
            })

        user_cond_note = f"""
★ [사용자 특별 요청 조건 (최우선 절대 원칙)]:
"{user_custom_prompt}\n[end 사용자 조건]"
""" if user_custom_prompt else ""

        system_instruction = (
            "당신은 일본 웹소설 업계 최고의 냉혹하고 객관적인 수석 평론가입니다.\n"
            "목표: 방대한 후보작 중에서 사용자의 특별 요청 조건과 과거 감상작 취향을 가장 완벽하게 만족하는 최상위 작품을 엄선하여 리포트를 작성하는 것입니다.\n\n"
            "★ 점수 인플레이션 절대 엄벌 (매우 객관적이고 냉정한 점수 산정 기준):\n"
            "- 평균적인 보통 소설의 점수는 60점대입니다.\n"
            "- 90~100점: 사용자의 특별 요청 조건 100% 충족 + 과거 최고 감상작과 핵심 재미 포인트 완벽 일치 + 문체와 전개의 완성도가 검증된 극소수 명작. 하지만 매우 극소수만 가능하기에 왠만해선 이 점수를 주지 마(1위라도 90점대는 힘듦).\n"
            "- 80~89점: 요청 조건의 핵심을 만족하나 1~2가지 아쉬운 클리셰나 약간의 호불호 요소가 포함된 수작.\n"
            "- 70~79점: 기본 조건은 맞추었으나 과거 취향과 미묘하게 어긋나거나 평이한 양산형 전개가 섞인 경우.  (대다수가 이 점수로)\n"
            "- 60~69점: 조건 중 일부만 일치하거나 매력이 부족한 평작.\n"
            "- 60점 미만: 조건 위배 또는 지뢰 요소 포함.\n"
            "※ 절대 억지로 점수를 80~90점대로 부풀리지 마세요. 아쉬운 점과 지뢰/불호 가능성을 cons_and_warnings에 날카롭게 지적하세요."
        )
        
        result_list = [
            {
                h.get("title", ""): {
                    "story": h.get("story", ""),
                    "keywords": h.get("keywords", [])
                }
            }
            for h in history_items
        ]
        json_result = json.dumps(result_list, ensure_ascii=False, indent=2)

        prompt = f"""
{user_cond_note}
[독자가 감상했던 대표 작품 목록]
{json_result}

[발굴된 신작 후보군 ({len(simplified_candidates)}개)]
{json.dumps(simplified_candidates, ensure_ascii=False, indent=2)}

위 후보작 중에서 독자의 취향 및 특별 요청 조건에 가장 알맞은 최상위 {top_k}작품을 선별하여 아래 JSON 규격으로 반환하세요:
{{
  "curator_note": "독자에게 전하는 종합 코멘트 (특별 요청 사항 반영 내역 및 엄격한 선별 기준 설명 3문장)", //다만 조건들을 나열하는 것이 아니라 자연스럽게 설명하는 것이며 일본어 태그를 말할 시 한국어로 말 해준다.
  "recommended_works": [
    {{
      "candidate_id": 0,
      "match_score": 78,
      "score_rationale": "냉정한 점수 산출 근거 (요청 조건 만족도 및 감점 사유 명시)",
      "connection_with_past_reads": "과거 읽은 특정 작품의 감상 포인트와 이어지는 이유",
      "cons_and_warnings": ["독자에 따라 거슬릴 수 있는 호불호 요소, 드리프트 가능성, 문체적 주의점"],
      "curator_one_liner": "큐레이터의 날카로운 한 줄 평"
    }}
  ]
}}
반드시 위와 같은 JSON 규격으로 출력하세요.
"""
        final_output = None
        for _ in range(3):
            raw_res = self.ai.generate(prompt, system_instruction)
            try:
                final_output = extract_json_from_response(raw_res)
                if final_output == {}:
                    continue
                break
            except Exception:
                print("error")
                continue

        if not isinstance(final_output, dict):
            final_output = {"curator_note": "추천 결과를 생성했습니다.", "recommended_works": []}

        recs = final_output.get("recommended_works", [])
        if isinstance(recs, list):
            for rec in recs:
                if not isinstance(rec, dict):
                    continue
                cid = rec.get("candidate_id")
                if cid is not None and isinstance(cid, int) and 0 <= cid < len(candidates):
                    orig = candidates[cid]
                    rec["stars"] = orig.get("stars", 0)
                    rec["status_episodes"] = orig.get("status_episodes", "")
                    rec["updated_at"] = orig.get("updated_at", "")
                    rec["story"] = orig.get("story", "")
                    rec["keywords"] = orig.get("keywords", [])
                    rec["url"] = orig.get("url", "")
                    rec["site"] = orig.get("site_type", "")
                    rec["title_ja"] = orig.get("title", "")

        return final_output

    def run_recommendation(
        self,
        top_k: int = 5,
        user_custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = datetime.now()
        PrintIo("=== 추천 파이프라인 가동 ===")
        if user_custom_prompt:
            PrintIo(f"[사용자 특별 요청 반영]: \"{user_custom_prompt}\"")

        try:
            history = self.get_read_history()
            history_items = history["items"]
            read_urls = history["read_urls"]

            if not history_items:
                msg = "읽은 작품 기록이 없습니다."
                PrintIo(msg)
                return {"error": msg, "recommended_works": []}
            
            self.log("info", "Ai를 시작하는 중...")

            candidates = self.run_agentic_search(
                history_items=history_items,
                read_urls=read_urls,
                user_custom_prompt=user_custom_prompt,
                top_k=top_k
            )

            PrintIo(f"\n[최종 탐색 결산] 중복 제외 총 {len(candidates)}개의 고유 신작 후보 확보")
            PrintIo(f"[플랫폼별 검색 성공 횟수]: {self.site_success_counts}")
            
            self.log("info", f"검색 종료. {len(candidates)}개의 작품 중 {top_k}개 선별")

            final_result = self.rerank_and_synthesize(
                history_items=history_items,
                user_custom_prompt=user_custom_prompt,
                candidates=candidates,
                top_k=top_k
            )
            final_result["user_custom_prompt"] = user_custom_prompt

            duration = (datetime.now() - start_time).total_seconds()
            PrintIo(f"=== 추천 파이프라인 완료 (소요시간: {duration:.2f}초) ===")
            PrintIo(f"=== {final_result['curator_note']} ===")
            return final_result

        except Exception as e:
            PrintIo(f"[치명적 오류 발생]: {e}\n{traceback.format_exc()}")
            return {"error": str(e), "recommended_works": []}