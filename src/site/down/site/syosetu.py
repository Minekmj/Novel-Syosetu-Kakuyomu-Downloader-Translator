import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

from ..base import BaseSite, register_site
from ..metrics import IntervalCalculator


@register_site
class SyosetuSite(BaseSite):
    site_name = "syosetu"
    base_data = None  # 외부 주입용

    @classmethod
    def match(cls, site_str: str) -> bool:
        return "syosetu.com" in site_str or bool(re.search(r"n\d{4}[a-z]+", site_str, re.I))

    @classmethod
    def parse_clean_code(cls, site_str: str) -> str:
        code_match = re.search(r"(n\d{4}[a-z]+)", site_str, re.I)
        if code_match:
            return code_match.group(1).lower()
        return site_str.strip("/").split("/")[-1]

    def get_delay(self) -> float:
        return getattr(self.base_data, "DELAY", 1) if self.base_data else 1

    def create_session(self):
        session = super().create_session()
        session.cookies.update({"over18": "yes"})
        return session

    def get_title(self, novel_code: str) -> str:
        url = f"https://ncode.syosetu.com/{novel_code}/"
        session = self.create_session()

        try:
            res = session.get(url, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                t = soup.find("p", class_="p-novel__title") or soup.find("h1")
                if t:
                    return t.get_text(strip=True)
        except Exception:
            pass
        finally:
            session.close()

        return None

    def get_novel_info(self, novel_code: str, session):
        url = f"https://ncode.syosetu.com/{novel_code}/"
        book_title = novel_code

        res = session.get(url, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            t = soup.find("p", class_="p-novel__title") or soup.find("h1")
            if t:
                book_title = t.get_text(strip=True)

        count = self.get_new_number(novel_code, have_make=False) or 9999
        episodes = [
            {"id": str(i), "url": f"{url}{i}/", "subtitle": f"{i}화"}
            for i in range(1, count + 1)
        ]
        return book_title, episodes

    def request_episode(self, ep: dict, session):
        res = session.get(ep["url"], timeout=30)
        if res.status_code != 200:
            base_url = re.sub(r'/\d+/$', '/', ep["url"])
            res = session.get(base_url, timeout=30)
        return res

    def parse_episode_content(self, html: str, ep: dict, current_idx: int):
        soup = BeautifulSoup(html, "html.parser")
        title_tag = (
            soup.find("h1", class_="p-novel__title p-novel__title--rensai")
            or soup.find("h1", class_="p-novel__title")
            or soup.find("h1")
        )
        subtitle = title_tag.get_text(strip=True) if title_tag else ep.get("subtitle", f"{current_idx}화")
        content_element = soup.find("div", class_="js-novel-text p-novel__text")
        return subtitle, content_element, ep["url"]

    def get_new_number(self, novel_code: str, have_make: bool = False):
        url = f"https://ncode.syosetu.com/{novel_code}/"

        with self.create_session() as session:
            try:
                res = session.get(url, timeout=15)
                if res.status_code != 200:
                    return None

                soup = BeautifulSoup(res.text, "html.parser")
                first_soup = soup

                next_page = soup.find("a", class_="c-pager__item c-pager__item--last")
                last_page = 1
                if next_page:
                    href = next_page.get("href", "")
                    match = re.search(r"[?&]p=(\d+)", href)
                    if match:
                        last_page = int(match.group(1))

                if last_page > 1:
                    res = session.get(f"{url}?p={last_page}", timeout=15)
                    if res.status_code != 200:
                        return None
                    soup = BeautifulSoup(res.text, "html.parser")

                last_ep_num = None
                latest_date = None

                body_tag = soup.find("div", class_="p-eplist")
                if body_tag:
                    episodes = body_tag.find_all("a", class_="p-eplist__subtitle")
                    if episodes:
                        match = re.search(r"/(\d+)/", episodes[-1].get("href", ""))
                        if match:
                            last_ep_num = int(match.group(1))

                    sublists = body_tag.find_all("div", class_="p-eplist__sublist")
                    if sublists:
                        update_tag = sublists[-1].find("div", class_="p-eplist__update")
                        if update_tag:
                            span_rev = update_tag.find("span", title=True)
                            if span_rev and "改稿" in span_rev.get("title", ""):
                                latest_date = span_rev["title"]
                            else:
                                latest_date = update_tag.get_text(strip=True)

                if last_ep_num is None:
                    check_2_res = session.get(f"{url}2/", timeout=15)
                    if check_2_res.status_code == 404:
                        last_ep_num = 1
                        m = re.search(r"掲載日[：:]\s*(\d{4}[年/\-]\s*\d{1,2}[月/\-]\s*\d{1,2}(?:日)?(?:\s+\d{1,2}:\d{2})?)", first_soup.get_text())
                        if m:
                            latest_date = m.group(1).strip()
                        else:
                            m_fb = re.search(r"\d{4}[年/\-]\s*\d{1,2}[月/\-]\s*\d{1,2}(?:日)?(?:\s+\d{1,2}:\d{2})?", first_soup.get_text())
                            if m_fb:
                                latest_date = m_fb.group(0).strip()

                if last_ep_num is None:
                    return None

                if not have_make:
                    return last_ep_num

                norm_date = self.base_data.normalize_date(latest_date) if self.base_data else latest_date
                return (last_ep_num, norm_date)

            except Exception as e:
                print(f"오류 발생 ({novel_code}): {e}")
                return None

    def get_number_average(self, novel_code: str):
        code_match = re.search(r"(n\d{4}[a-z]+)", str(novel_code), re.I)
        novel_code = code_match.group(1).lower() if code_match else str(novel_code).strip("/")
        url = f"https://ncode.syosetu.com/{novel_code}/"

        with self.create_session() as session:
            try:
                res = session.get(url, timeout=15)
                if res.status_code != 200:
                    return (None, None, None, None)

                soup = BeautifulSoup(res.text, "html.parser")
                episodes_data = []

                next_page = soup.find("a", class_="c-pager__item c-pager__item--last")
                last_page = 1
                if next_page:
                    match = re.search(r"[?&]p=(\d+)", next_page.get("href", ""))
                    if match:
                        last_page = int(match.group(1))

                delay = self.get_delay()

                for page in range(1, last_page + 1):
                    if page == 1:
                        page_soup = soup
                    else:
                        time.sleep(delay)
                        page_res = session.get(f"{url}?p={page}", timeout=15)
                        if page_res.status_code != 200:
                            continue
                        page_soup = BeautifulSoup(page_res.text, "html.parser")

                    body_tag = page_soup.find("div", class_="p-eplist")
                    if not body_tag:
                        continue

                    sublists = body_tag.find_all("div", class_="p-eplist__sublist")
                    for sublist in sublists:
                        ep_tag = sublist.find("a", class_="p-eplist__subtitle")
                        if not ep_tag:
                            continue

                        ep_match = re.search(r"/(\d+)/", ep_tag.get("href", ""))
                        if not ep_match:
                            continue
                        ep_num = int(ep_match.group(1))

                        update_tag = sublist.find("div", class_="p-eplist__update")
                        if not update_tag:
                            continue

                        date_text = str(update_tag.contents[0] if update_tag.contents else update_tag.get_text()).strip()
                        date_match = re.search(r"(\d{4})[年/\-.]\s*(\d{1,2})[月/\-.]\s*(\d{1,2})(?:日)?(?:\s+(\d{1,2}):(\d{2}))?", date_text)
                        if not date_match:
                            continue

                        y, m, d, h, mn = date_match.groups()
                        try:
                            episodes_data.append((ep_num, datetime(int(y), int(m), int(d), int(h or 0), int(mn or 0))))
                        except ValueError:
                            continue

                if not episodes_data:
                    return (None, None, None, None)

                unique_dates = [dt for _, dt in sorted(set(episodes_data), key=lambda x: x[0], reverse=True)]
                return IntervalCalculator.calculate_averages(unique_dates)

            except Exception:
                return (None, None, None, None)


def syosetu_title(novel_code):
    return SyosetuSite().get_title(novel_code)

def download_syosetu_async(novel_code, start, end, trs_path, label, raw_title):
    return SyosetuSite().download(novel_code, start, end, trs_path, label, raw_title)

def new_syosetu(novel_code, have_make=False):
    return SyosetuSite().get_new_number(novel_code, have_make)

def find_ep_syosetu_average(novel_code):
    return SyosetuSite().get_number_average(novel_code)