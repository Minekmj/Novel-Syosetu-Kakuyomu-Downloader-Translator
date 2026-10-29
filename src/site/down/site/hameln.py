import re
import threading
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

import src.find.site.site_data as sf
from ..base import BaseSite, register_site
from ..metrics import IntervalCalculator

_reset_lock = threading.Lock()
_last_reset_time = 0
_request_sem = threading.Semaphore(1)


@register_site
class HamelnSite(BaseSite):
    site_name = "hameln"
    base_data = None  # 외부 주입용

    def __init__(self):
        self.is_r18 = False

    @classmethod
    def match(cls, site_str: str) -> bool:
        return (
            "syosetu.org" in site_str
            or "h.syosetu.org" in site_str
            or site_str.startswith("h.")
            or site_str.startswith("h_")
        )

    @classmethod
    def parse_clean_code(cls, site_str: str) -> str:
        if "syosetu.org" in site_str or "h.syosetu.org" in site_str:
            is_r18 = "h.syosetu.org" in site_str
            match = re.search(r'/novel/(\d+)', site_str)
            nid = match.group(1) if match else site_str.strip("/").split("/")[-1]
            return f"h.{nid}" if is_r18 else nid
        return site_str

    def get_concurrency_limit(self) -> int:
        return getattr(self.base_data, "CONCURRENCY_LIMIT_H", 1) if self.base_data else 1

    def get_delay(self) -> float:
        return getattr(self.base_data, "DELAY_H", 2.5) if self.base_data else 2.5

    @staticmethod
    def parse_novel_code(novel_code):
        code_str = str(novel_code).strip()
        is_r18 = False

        if code_str.startswith("h.") or code_str.startswith("h_"):
            is_r18 = True
            clean_code = code_str[2:]
        elif "h.syosetu.org" in code_str:
            is_r18 = True
            clean_code = code_str
        else:
            clean_code = code_str

        match = re.search(r'\d+', clean_code)
        nid = match.group(0) if match else clean_code
        return nid, is_r18

    def create_session(self):
        session = requests.Session()
        session.headers.update(sf.BASE_HEADERS)

        if self.is_r18:
            sf.COOKIES["over18"] = "off"
            session.cookies.set("over18", "off", domain=".syosetu.org")

        session.cookies.update(sf.COOKIES)
        return session

    def http_get(self, url, session=None, is_r18=False, headers=None, timeout=30):
        global _last_reset_time

        if session is None:
            session = self.create_session()

        req_headers = dict(sf.BASE_HEADERS)
        if headers:
            req_headers.update(headers)

        with _request_sem:
            res = session.get(url, headers=req_headers, timeout=timeout)

        if res.status_code == 403:
            with _reset_lock:
                if time.time() - _last_reset_time > 3.0:
                    sf.reset(True)
                    _last_reset_time = time.time()
                    time.sleep(1.0)

                if is_r18:
                    sf.COOKIES["over18"] = "off"

                session.cookies.update(sf.COOKIES)
                req_headers = dict(sf.BASE_HEADERS)
                if headers:
                    req_headers.update(headers)

            with _request_sem:
                res = session.get(url, headers=req_headers, timeout=timeout)

        return res

    def http_cookie(self, session=None):
        sf.reset_b()
        if self.is_r18:
            sf.COOKIES["over18"] = "off"
        session.cookies.update(sf.COOKIES)

    def get_title(self, novel_code: str) -> str:
        nid, self.is_r18 = self.parse_novel_code(novel_code)
        base_url = "https://h.syosetu.org" if self.is_r18 else "https://syosetu.org"
        url = f"{base_url}/novel/{nid}/"

        session = self.create_session()
        self.http_cookie(session)

        try:
            res = self.http_get(url, session=session, is_r18=self.is_r18, headers={"Referer": url}, timeout=15)
            if res.status_code != 200:
                return novel_code

            soup = BeautifulSoup(res.text, "html.parser")
            full_title = soup.title.string if soup.title else ""
            book_title = re.sub(r'\s*-\s*ハーメルン.*$', '', full_title).strip()
            return book_title or novel_code
        except Exception:
            return None
        finally:
            session.close()

    def get_novel_info(self, novel_code: str, session):
        nid, self.is_r18 = self.parse_novel_code(novel_code)
        base_url = "https://h.syosetu.org" if self.is_r18 else "https://syosetu.org"
        url = f"{base_url}/novel/{nid}/"

        self.http_cookie(session)
        res = self.http_get(url, session=session, is_r18=self.is_r18, headers={"Referer": url}, timeout=30)
        if res.status_code != 200:
            return novel_code, []

        soup = BeautifulSoup(res.text, "html.parser")
        full_title = soup.title.string if soup.title else ""
        book_title = re.sub(r'\s*-\s*ハーメルン.*$', '', full_title).strip()

        episodes = []
        links = soup.find_all("a", href=True)
        seen_ids = set()
        pattern = re.compile(rf'(?:/novel/{nid}/|\./)(\d+)\.html')

        for a in links:
            match = pattern.search(a.get("href", ""))
            if match:
                ep_id = match.group(1)
                if ep_id not in seen_ids:
                    seen_ids.add(ep_id)
                    episodes.append({
                        "id": ep_id,
                        "subtitle": a.get_text(strip=True),
                        "url": f"{base_url}/novel/{nid}/{ep_id}.html"
                    })

        if not episodes and soup.select_one("#honbun"):
            episodes.append({
                "id": "1",
                "subtitle": book_title or "단편",
                "url": f"{base_url}/novel/{nid}/"
            })

        return (book_title or novel_code), episodes

    def request_episode(self, ep: dict, session):
        return self.http_get(
            ep["url"],
            session=session,
            is_r18=self.is_r18,
            headers={"Referer": ep["url"]},
            timeout=30
        )

    def parse_episode_content(self, html: str, ep: dict, current_idx: int):
        ep_soup = BeautifulSoup(html, "html.parser")
        subtitle_tag = ""
        targets = ep_soup.select("#maind span[style*='font-size:120%']")

        for target in targets:
            if target.find("a") is None:
                if target.find("br"):
                    last_content = target.contents[-1]
                    subtitle_tag = (
                        last_content.strip()
                        if isinstance(last_content, str)
                        else last_content.get_text(strip=True)
                    )
                else:
                    subtitle_tag = target.get_text(strip=True)
                break

        subtitle = subtitle_tag if subtitle_tag else ep.get("subtitle", f"{current_idx}화")
        content_element = ep_soup.select_one("#honbun")
        return subtitle, content_element, ep["url"]

    def get_new_number(self, novel_code: str, have_make: bool = False):
        nid, self.is_r18 = self.parse_novel_code(novel_code)
        session = self.create_session()
        try:
            _, episodes = self.get_novel_info(novel_code, session)
            count = len(episodes) if episodes else None
            if count is None:
                return None

            if not have_make:
                return count

            base_url = "https://h.syosetu.org" if self.is_r18 else "https://syosetu.org"
            url = f"{base_url}/novel/{nid}/"
            res = self.http_get(url, session=session, is_r18=self.is_r18, headers={"Referer": url}, timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")
            latest_date = None

            ep_items = soup.select("li.episode-list__item")
            if ep_items:
                last_item = ep_items[-1]
                revision_tag = last_item.select_one(".episode-list__revision[title]")
                time_tag = last_item.select_one("time.episode-list__date, time")
                if revision_tag and revision_tag.get("title"):
                    latest_date = revision_tag["title"]
                elif time_tag:
                    latest_date = time_tag.get("datetime") or time_tag.get_text(strip=True)

            if not latest_date:
                ep_rows = [
                    tr for tr in soup.find_all("tr")
                    if tr.find("a", href=re.compile(rf"(?:/novel/{nid}/|\./)?\d+\.html"))
                ]
                if ep_rows:
                    last_row = ep_rows[-1]
                    time_tag = last_row.find("time")
                    nobr = last_row.find("nobr")
                    if time_tag:
                        latest_date = time_tag.get("datetime") or time_tag.get_text(strip=True)
                    elif nobr:
                        latest_date = nobr.get_text(strip=True)

            if not latest_date:
                for th in soup.find_all(["th", "td"]):
                    if any(k in th.get_text() for k in ("最新話掲載日", "更新日時", "初回公開日時")):
                        sibling = th.find_next_sibling(["td", "th"])
                        if sibling:
                            latest_date = sibling.get_text(strip=True)
                            break

            norm_date = self.base_data.normalize_date(latest_date) if self.base_data else latest_date
            return (count, norm_date)
        except Exception as e:
            print(f"하멜른 에피소드 수 확인 오류: {e}")
            return None
        finally:
            session.close()

    def get_number_average(self, novel_code: str):
        nid, self.is_r18 = self.parse_novel_code(novel_code)
        base_url = "https://h.syosetu.org" if self.is_r18 else "https://syosetu.org"
        url = f"{base_url}/novel/{nid}/"

        session = self.create_session()
        self.http_cookie(session)

        try:
            res = self.http_get(url, session=session, is_r18=self.is_r18, headers={"Referer": url}, timeout=15)
            if res.status_code != 200:
                return (None, None, None, None)

            def parse_date(value):
                if not value:
                    return None
                try:
                    dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
                    return dt.replace(tzinfo=None)
                except (ValueError, TypeError):
                    pass
                match = re.search(r"(\d{4})[年/\-.]\s*(\d{1,2})[月/\-.]\s*(\d{1,2})(?:日)?(?:\s+(\d{1,2}):(\d{2}))?", str(value))
                if not match:
                    return None
                try:
                    return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4) or 0), int(match.group(5) or 0))
                except ValueError:
                    return None

            date_values = []
            soup = BeautifulSoup(res.text, "html.parser")
            ep_items = soup.select("li.episode-list__item")

            for item in ep_items:
                dt = None
                rev = item.select_one(".episode-list__revision[title]")
                if rev and rev.get("title"):
                    dt = parse_date(rev.get("title"))
                if dt is None:
                    tm = item.select_one("time.episode-list__date, time")
                    if tm:
                        dt = parse_date(tm.get("datetime") or tm.get_text(strip=True))
                if dt:
                    date_values.append(dt)

            if len(date_values) < 2:
                ep_rows = [
                    tr for tr in soup.find_all("tr")
                    if tr.find("a", href=re.compile(rf"(?:/novel/{nid}/|\./)?\d+\.html"))
                ]
                for row in ep_rows:
                    dt = None
                    tm = row.find("time")
                    if tm:
                        dt = parse_date(tm.get("datetime") or tm.get_text(strip=True))
                    if dt is None:
                        nobr = row.find("nobr")
                        if nobr:
                            dt = parse_date(nobr.get_text(strip=True))
                    if dt:
                        date_values.append(dt)

            return IntervalCalculator.calculate_averages(date_values)
        except Exception as e:
            print(f"하멜른 연재 간격 계산 오류 ({novel_code}): {e}")
            return (None, None, None, None)
        finally:
            session.close()


def hameln_title(novel_code):
    return HamelnSite().get_title(novel_code)

def download_hameln_async(novel_code, start, end, trs_path, label, raw_title):
    return HamelnSite().download(novel_code, start, end, trs_path, label, raw_title)

def new_hameln(novel_code, have_make=False):
    return HamelnSite().get_new_number(novel_code, have_make)

def find_ep_hameln_average(novel_code):
    return HamelnSite().get_number_average(novel_code)