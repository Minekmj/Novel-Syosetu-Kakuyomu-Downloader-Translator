import os
import re
import threading
import time
import requests

from .storage import EpisodeStorage
from .media import MediaHandler
from .utils import prepare_title_path


class ContentParser:
    @staticmethod
    def parse(content_element, export_text=False):
        for tag in content_element.find_all(["rt", "rp"]):
            tag.decompose()
        for ruby in content_element.find_all("ruby"):
            ruby.replace_with(ruby.get_text(strip=True))

        p_tags = content_element.find_all("p")
        if not p_tags:
            p_tags = [content_element]

        body_paragraphs = []
        body_paragraphs_raw = []

        for p in p_tags:
            if export_text:
                for br in p.find_all(["br", "br/"]):
                    br.replace_with("\n")

            p_text = p.decode_contents()
            p_text = p_text.replace("<span>", "").replace("</span>", "")
            p_text = re.sub(r'<em class="emphasisDots">(.*?)</em>', r"**\1**", p_text)
            p_text = re.sub(r"<[^>]+>", "", p_text)
            p_text = p_text.lstrip(" \t").rstrip()

            p_clean = re.sub(r"《《(.+?)》》", r"\1", p_text)

            if p_text or (export_text and not p_text):
                body_paragraphs.append(p_clean)

            if p_text or not p_text:
                body_paragraphs_raw.append(p_clean)

        body = "\n".join(body_paragraphs)
        body_raw = "\n".join(body_paragraphs_raw)
        return body, body_raw


class BaseSite:
    site_name = ""
    base_data = None  # 외부 주입용

    @classmethod
    def match(cls, site_str: str) -> bool:
        raise NotImplementedError

    @classmethod
    def parse_clean_code(cls, site_str: str) -> str:
        raise NotImplementedError

    def get_concurrency_limit(self) -> int:
        return getattr(self.base_data, "CONCURRENCY_LIMIT", 2) if self.base_data else 2

    def get_delay(self) -> float:
        return getattr(self.base_data, "DELAY", 0.3) if self.base_data else 0.3

    def create_session(self):
        session = requests.Session()
        headers = self.base_data.HEADERS if self.base_data else {}
        session.headers.update(headers)
        return session

    def get_title(self, novel_code: str) -> str:
        raise NotImplementedError

    def get_novel_info(self, novel_code: str, session):
        raise NotImplementedError

    def request_episode(self, ep: dict, session):
        return session.get(ep["url"], timeout=30)

    def parse_episode_content(self, html: str, ep: dict, current_idx: int):
        raise NotImplementedError

    def fetch_episode_common(
        self,
        title_path,
        sem,
        ep,
        current_idx,
        trs_path,
        label_callback,
        total_count,
        progress_state,
        act_massage="",
        max_retries=3
    ):
        with sem:
            if EpisodeStorage.read_backup(
                title_path, current_idx, trs_path, act_massage, total_count, progress_state, label_callback, print
            ):
                return True

            delay = self.get_delay()

            for attempt in range(max_retries):
                session = self.create_session()
                try:
                    res = self.request_episode(ep, session)
                    if res.status_code != 200:
                        raise Exception(f"HTTP status {res.status_code}")

                    subtitle, content_element, page_url = self.parse_episode_content(res.text, ep, current_idx)
                    if not content_element:
                        raise Exception("본문 태그 없음")

                    outfolder = getattr(self.base_data, "OUTFOLDER", "./out") if self.base_data else "./out"
                    has_downloaded_img = MediaHandler.process_images(
                        content_element,
                        page_url,
                        session,
                        outfolder,
                        is_r18=getattr(self, "is_r18", False),
                        req_func=getattr(self, "http_get", None),
                        printcall=print
                    )

                    export_text = getattr(self.base_data, "EXPORT_TEXT", False) if self.base_data else False
                    body, body_raw = ContentParser.parse(content_element, export_text)

                    EpisodeStorage.save_episode(title_path, trs_path, current_idx, subtitle, body, body_raw, act_massage)
                    EpisodeStorage.update_progress(progress_state, total_count, label_callback)

                    wait_time = delay * 5 if has_downloaded_img else delay
                    time.sleep(wait_time)
                    return True

                except Exception as e:
                    print(
                        f"{self.site_name} 에피소드 다운로드 오류 ({ep.get('id', current_idx)}) [시도 {attempt + 1}/{max_retries}]: {e}"
                    )
                    if str(e) == "HTTP status 503":
                        time.sleep(delay * 5)
                        attempt -= 1
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(delay * 10)
                        else:
                            print(f"{self.site_name} 에피소드 ({ep.get('id', current_idx)}) 최대 재시도 횟수 초과")
                            return None
                finally:
                    session.close()

    def download(
        self,
        novel_code: str,
        start: int,
        end: int,
        trs_path: str,
        label,
        raw_title: str,
        act_massage: str = ""
    ) -> str:
        total_count = end - start + 1
        session = self.create_session()

        try:
            book_title, episodes = self.get_novel_info(novel_code, session)
        except Exception as e:
            print(f"{self.site_name} 목차 가져오기 오류: {e}")
            return novel_code
        finally:
            session.close()

        if not episodes:
            print(f"{self.site_name} 에피소드를 찾지 못했습니다.")
            return book_title or novel_code

        book_title, title_path = prepare_title_path(book_title, raw_title, self.base_data)

        start_idx = max(0, start - 1)
        end_idx = min(len(episodes), end)
        target_episodes = episodes[start_idx:end_idx]

        sem = threading.Semaphore(self.get_concurrency_limit())
        progress_state = {"done": 0, "lock": threading.Lock()}
        label_callback = label.setText

        threads = []
        for idx, ep in enumerate(target_episodes):
            current_idx = idx + start
            thread = threading.Thread(
                target=self.fetch_episode_common,
                args=(
                    title_path,
                    sem,
                    ep,
                    current_idx,
                    trs_path,
                    label_callback,
                    total_count,
                    progress_state,
                    act_massage
                ),
                daemon=True
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        return book_title or novel_code

    def get_new_number(self, novel_code: str, have_make: bool = False):
        raise NotImplementedError

    def get_number_average(self, novel_code: str):
        raise NotImplementedError


class SiteRegistry:
    _sites = []
    base_data = None  # 외부 주입용

    @classmethod
    def register(cls, site_class):
        if site_class not in cls._sites:
            cls._sites.append(site_class)
        if cls.base_data is not None:
            site_class.base_data = cls.base_data
        return site_class

    @classmethod
    def set_base_data(cls, data):
        cls.base_data = data
        for site_class in cls._sites:
            site_class.base_data = data

    @classmethod
    def resolve(cls, site_str: str):
        clean_str = str(site_str).strip()
        for site_class in cls._sites:
            if site_class.match(clean_str):
                clean_code = site_class.parse_clean_code(clean_str)
                return site_class(), clean_code

        for site_class in cls._sites:
            if site_class.site_name == "syosetu":
                clean_code = site_class.parse_clean_code(clean_str)
                return site_class(), clean_code

        clean_code = clean_str.strip("/").split("/")[-1]
        instance = cls._sites[-1]() if cls._sites else BaseSite()
        return instance, clean_code

    @classmethod
    def get_sites(cls):
        return list(cls._sites)


def register_site(cls):
    return SiteRegistry.register(cls)