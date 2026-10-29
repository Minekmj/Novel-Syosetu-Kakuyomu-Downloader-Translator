import time
from typing import Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

import src.find.site as datas
from .cache import get_cached, set_cached
from .utils import PrintIo, site_delay, site_delay_all

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
                    res = site_cls.fetch_search_results(params)
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
    
    def get_description(self, site: str, site_cls, work_url: str):
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