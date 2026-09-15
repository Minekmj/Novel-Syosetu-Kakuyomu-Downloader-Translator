from datetime import datetime, timedelta

import requests
http_session = requests.Session()

class NocturneSearch:
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    GENRES = {}

    SORT_ORDERS = {
        "포인트순": "hyoka",
        "주간 포인트순": "weeklypoint",
        "월간 포인트순": "monthlypoint",
        "분기 포인트순": "quarterpoint",
        "연간 포인트순": "yearlypoint",
        "신작순": "new",
        "최신 갱신순": "weekly",
        "글자수순": "length",
    }

    SERIAL_STATUSES = {
        "전체": "",
        "단편": "t",
        "연재": "re",
        "연재중": "r",
        "완결": "er",
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

    FLAG_INCLUSION_AND_EXLUSION = {
        "잔인한 묘사": "zankoku",
        "BL": "bl",
        "GL": "gl",
        "이세계 환생": "tensei",
        "이세계 전이": "tenni",
        "장기 연재 중단": "stop",
    }

    FIND_AREA = {
        "작품 제목": "title",
        "줄거리": "ex",
        "키워드": "keyword",
        "저자 이름": "wname",
    }

    @staticmethod
    def fetch_search_results(params):
        api_url = "https://api.syosetu.com/novel18api/api/"
        page = max(1, int(params.get("page", 1)))

        payload = {
            "out": "json",
            "lim": 20,
            "st": (page - 1) * 20 + 1,
            "word": params.get("query", ""),
            "order": params.get("order", "hyoka"),
            "nocgenre": 1,  # 1: 녹턴 노벨즈(남성향 R18) 고정
        }

        # 제외 단어
        exclude_words = params.get("exclude_words", [])
        if exclude_words:
            payload["notword"] = " ".join(
                str(word).strip() for word in exclude_words if str(word).strip()
            )

        # 장르 (파라미터가 들어올 경우 대비)
        genre_val = params.get("genre_val")
        if genre_val and int(genre_val) != 0:
            payload["genre"] = int(genre_val)

        # 최소 글자수
        min_chars = params.get("min_chars", 0)
        if min_chars and int(min_chars) > 0:
            payload["minlen"] = int(min_chars)

        # 최소 종합 포인트
        min_pt = params.get("min_pt", 0)
        if min_pt and int(min_pt) > 0:
            payload["min_globalpoint"] = int(min_pt)

        # 연재 상태 (단편/연재/완결 등)
        serial_status = params.get("serial_status")
        if serial_status:
            payload["type"] = serial_status

        # 최종 갱신일 필터링
        period_key = params.get("last_published")
        days = NocturneSearch.LAST_PUBLISHED_PERIODS.get(
            period_key, period_key if isinstance(period_key, int) else None
        )
        if days:
            today = datetime.now()
            start_date = today - timedelta(days=days)
            payload["minlastup"] = start_date.strftime("%Y/%m/%d")
            payload["maxlastup"] = today.strftime("%Y/%m/%d")

        # 태그/플래그 포함 설정
        inclusion_flags = params.get("inclusion_flags", [])
        if inclusion_flags:
            for i in inclusion_flags:
                payload["is" + i] = 1

        # 태그/플래그 제외 설정
        exlusion_flags = params.get("exlusion_flags", [])
        if exlusion_flags:
            for i in exlusion_flags:
                payload["not" + i if i != "stop" else "stop"] = 1

        # 검색 대상 영역 설정 (제목/줄거리/키워드/저자명)
        find_areas = params.get("find_areas", [])
        if find_areas:
            for i in find_areas:
                payload[i] = 1

        try:
            res = http_session.get(
                api_url,
                params=payload,
                headers=NocturneSearch.HEADERS,
                timeout=10,
            )
            res.raise_for_status()
            data = res.json()

            if not data:
                return {"is_last_page": True, "items": []}

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

                items.append(
                    {
                        "title": item.get("title", ""),
                        "url": f"https://novel18.syosetu.com/{ncode}/",
                        "stars": item.get("global_point", 0),
                        "status_episodes": (
                            f"총 {item.get('general_all_no', 0)}화 "
                            f"({status})"
                        ),
                        "updated_at": item.get("general_lastup", "")[:10],
                        "ncode": ncode,
                        "story": item.get("story", "")
                        + "_____tags_____"
                        + ", ".join(keywords_list),
                        "keywords": keywords_list,
                    }
                )

            is_last_page = page * 20 >= all_count
            return {"is_last_page": is_last_page, "items": items}

        except Exception as e:
            print(f"녹턴 API 요청 에러: {e}")
            return {"is_last_page": True, "items": []}

    @staticmethod
    def fetch_detail_description(work_url):
        return work_url
    
    
