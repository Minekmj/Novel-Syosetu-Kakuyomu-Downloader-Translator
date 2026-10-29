from typing import Dict, Any
from src.find.site import KakuyomuSearch, NaroSearch, SyosetuSearch

PLATFORM_SPEC_TEXT = """
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

def build_search_params(site: str, strategy: Dict[str, Any], page: int = 1) -> Dict[str, Any]:
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
        if KakuyomuSearch and genre in KakuyomuSearch.GENRES.values():
            genre_name = genre
        elif KakuyomuSearch and genre in KakuyomuSearch.GENRES:
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
        elif NaroSearch and genre in NaroSearch.GENRES:
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
            elif NaroSearch and last_pub in NaroSearch.LAST_PUBLISHED_PERIODS:
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
        if SyosetuSearch and genre in SyosetuSearch.GENRES.values():
            genre_val = genre
        elif SyosetuSearch and genre in SyosetuSearch.GENRES:
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
            elif SyosetuSearch and last_pub in SyosetuSearch.LAST_PUBLISHED_PERIODS:
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