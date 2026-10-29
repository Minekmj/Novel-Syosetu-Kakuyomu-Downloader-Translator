import json
import re
from datetime import datetime
from bs4 import BeautifulSoup

from ..base import BaseSite, register_site
from ..metrics import IntervalCalculator


@register_site
class KakuyomuSite(BaseSite):
    site_name = "kakuyomu"
    base_data = None  # 외부 주입용

    @classmethod
    def match(cls, site_str: str) -> bool:
        return "kakuyomu.jp" in site_str or site_str.isdigit()

    @classmethod
    def parse_clean_code(cls, site_str: str) -> str:
        return site_str.strip("/").split("/")[-1]

    def get_title(self, novel_code: str) -> str:
        url = f"https://kakuyomu.jp/works/{novel_code}"
        session = self.create_session()
        session.headers.update({"Referer": url})

        try:
            res = session.get(url, timeout=15)
            if res.status_code != 200:
                return novel_code

            soup = BeautifulSoup(res.text, "html.parser")
            full_title = soup.title.string if soup.title else ""
            book_title = re.sub(r'（.+） - カクヨム$', '', full_title).strip()
            return book_title or novel_code
        except Exception:
            return None
        finally:
            session.close()

    def get_novel_info(self, novel_code: str, session):
        url = f"https://kakuyomu.jp/works/{novel_code}"
        session.headers.update({"Referer": url})

        res = session.get(url, timeout=30)
        if res.status_code != 200:
            return novel_code, []

        html_text = res.text
        soup = BeautifulSoup(html_text, "html.parser")
        full_title = soup.title.string if soup.title else ""
        book_title = re.sub(r'（.+） - カクヨム$', '', full_title).strip()

        episodes = []
        next_data_script = soup.find("script", id="__NEXT_DATA__")
        if next_data_script and next_data_script.string:
            try:
                data = json.loads(next_data_script.string)
                apollo_state = data.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
                seen_ids = set()

                for key, value in apollo_state.items():
                    if not isinstance(value, dict):
                        continue
                    if not (key.startswith("Episode:") or value.get("__typename") == "Episode"):
                        continue

                    ep_id = value.get("id")
                    if not ep_id or str(ep_id) in seen_ids:
                        continue

                    seen_ids.add(str(ep_id))
                    episodes.append({
                        "id": str(ep_id),
                        "subtitle": value.get("title", ""),
                        "url": f"https://kakuyomu.jp/works/{novel_code}/episodes/{ep_id}"
                    })
            except Exception:
                pass

        if not episodes:
            matches = re.findall(r'\{"__typename":"Episode","id":"(\d+)","title":"(.+?)"', html_text)
            seen_ids = set()
            for ep_id, ep_title in matches:
                if ep_id in seen_ids:
                    continue
                seen_ids.add(ep_id)
                try:
                    title = json.loads(f'"{ep_title}"')
                except Exception:
                    title = ep_title

                episodes.append({
                    "id": ep_id,
                    "subtitle": title,
                    "url": f"https://kakuyomu.jp/works/{novel_code}/episodes/{ep_id}"
                })

        return (book_title or novel_code), episodes

    def request_episode(self, ep: dict, session):
        session.headers.update({"Referer": ep["url"]})
        return session.get(ep["url"], timeout=30)

    def parse_episode_content(self, html: str, ep: dict, current_idx: int):
        ep_soup = BeautifulSoup(html, "html.parser")
        subtitle_tag = ep_soup.select_one(".widget-episodeTitle") or ep_soup.find("h1")
        subtitle = subtitle_tag.get_text(strip=True) if subtitle_tag else ep.get("subtitle", f"{current_idx}화")
        content_element = ep_soup.select_one(".widget-episodeBody")
        return subtitle, content_element, ep["url"]

    def get_new_number(self, novel_code: str, have_make: bool = False):
        url = f"https://kakuyomu.jp/works/{novel_code}"
        session = self.create_session()
        session.headers.update({"Referer": url})

        try:
            res = session.get(url, timeout=15)
            if res.status_code != 200:
                return None

            html_text = res.text
            soup = BeautifulSoup(html_text, "html.parser")
            count = None
            latest_date = None

            next_data_script = soup.find("script", id="__NEXT_DATA__")
            if next_data_script and next_data_script.string:
                try:
                    data = json.loads(next_data_script.string)
                    apollo_state = data.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
                    episodes = [
                        v for k, v in apollo_state.items()
                        if isinstance(v, dict) and (k.startswith("Episode:") or v.get("__typename") == "Episode")
                    ]
                    if episodes:
                        unique_ids = {str(ep.get("id")) for ep in episodes if ep.get("id") is not None}
                        if unique_ids:
                            count = len(unique_ids)
                        dates = [ep.get("publishedAt") for ep in episodes if ep.get("publishedAt")]
                        if dates:
                            latest_date = max(dates)
                except Exception:
                    pass

            if count is None:
                matches = re.findall(r'\{"__typename":"Episode","id":"(\d+)"', html_text)
                if matches:
                    count = len(set(matches))
                    date_matches = re.findall(r'"publishedAt":"([^"]+)"', html_text)
                    if date_matches:
                        latest_date = max(date_matches)

            if count is None:
                ep_links = soup.select("a.widget-toc-episode-episodeTitle")
                if ep_links:
                    count = len(ep_links)

            if count is None:
                return None

            if not have_make:
                return count

            if not latest_date:
                time_tags = soup.select("time.widget-toc-episode-datePublished, li.widget-toc-episode time, time[datetime]")
                if time_tags:
                    latest_date = time_tags[-1].get("datetime") or time_tags[-1].get_text(strip=True)

            norm_date = self.base_data.normalize_date(latest_date) if self.base_data else latest_date
            return (count, norm_date)

        except Exception as e:
            print(f"카쿠요무 에피소드 수 확인 오류: {e}")
            return None
        finally:
            session.close()

    def get_number_average(self, novel_code: str):
        url = f"https://kakuyomu.jp/works/{novel_code}"
        session = self.create_session()
        session.headers.update({"Referer": url})

        try:
            res = session.get(url, timeout=15)
            if res.status_code != 200:
                return (None, None, None, None)

            soup = BeautifulSoup(res.text, "html.parser")
            html_text = res.text
            episodes_data = []

            next_data_script = soup.find("script", id="__NEXT_DATA__")
            if next_data_script and next_data_script.string:
                try:
                    data = json.loads(next_data_script.string)
                    apollo_state = data.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
                    episodes = [
                        v for k, v in apollo_state.items()
                        if isinstance(v, dict) and (k.startswith("Episode:") or v.get("__typename") == "Episode")
                    ]
                    seen = set()
                    for ep in episodes:
                        ep_id = ep.get("id")
                        pub = ep.get("publishedAt")
                        if ep_id is None or not pub or str(ep_id) in seen:
                            continue
                        seen.add(str(ep_id))
                        try:
                            episodes_data.append((str(ep_id), datetime.fromisoformat(str(pub).replace("Z", "+00:00"))))
                        except (ValueError, TypeError):
                            continue
                except Exception:
                    pass

            if not episodes_data:
                time_tags = soup.select("time.widget-toc-episode-datePublished, li.widget-toc-episode time, time[datetime]")
                for index, tag in enumerate(time_tags):
                    pub = tag.get("datetime") or tag.get_text(strip=True)
                    try:
                        episodes_data.append((str(index), datetime.fromisoformat(str(pub).replace("Z", "+00:00"))))
                    except (ValueError, TypeError):
                        continue

            if len(episodes_data) < 2:
                return (None, None, None, None)

            unique = {ep_id: dt for ep_id, dt in episodes_data}
            return IntervalCalculator.calculate_averages(list(unique.values()))

        except Exception as e:
            print(f"카쿠요무 연재 간격 계산 오류 ({novel_code}): {e}")
            return (None, None, None, None)
        finally:
            session.close()


def kakuyomu_title(novel_code):
    return KakuyomuSite().get_title(novel_code)

def download_kakuyomu_async(novel_code, start, end, trs_path, label, raw_title, act_massage=""):
    return KakuyomuSite().download(novel_code, start, end, trs_path, label, raw_title, act_massage)

def new_kakuyomu(novel_code, have_make=False):
    return KakuyomuSite().get_new_number(novel_code, have_make)

def find_ep_kakuyomu_average(novel_code):
    return KakuyomuSite().get_number_average(novel_code)