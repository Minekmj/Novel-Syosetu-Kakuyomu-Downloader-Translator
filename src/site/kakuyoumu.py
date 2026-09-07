import json
import os
import re
import requests
from bs4 import BeautifulSoup
import threading

base_data = None #외부 주입용

def kakuyomu_title(novel_code):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ja,ko-KR;q=0.9,ko;q=0.8,en-US;q=0.7,en;q=0.6"
    }

    url = f"https://kakuyomu.jp/works/{novel_code}"
    headers["Referer"] = url

    try:
        res = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        res.encoding = "utf-8"

        if res.status_code != 200:
            return novel_code

        soup = BeautifulSoup(res.text, "html.parser")

        full_title = soup.title.string if soup.title else ""

        book_title = re.sub(
            r'（.+） - カクヨム$',
            '',
            full_title
        ).strip()

        return book_title

    except Exception:
        return None

def fetch_kakuyomu_episode(
    session,
    sem,
    ep,
    current_idx,
    trs_path,
    label_callback,
    total_count,
    progress_state
):
    with sem:
        try:
            res = session.get(
                ep["url"],
                timeout=30
            )

            if res.status_code != 200:
                return

            html = res.text

            ep_soup = BeautifulSoup(
                html,
                "html.parser"
            )

            subtitle_tag = (
                ep_soup.select_one(
                    ".widget-episodeTitle"
                )
                or ep_soup.find("h1")
            )

            subtitle = (
                subtitle_tag.get_text(strip=True)
                if subtitle_tag
                else ep["subtitle"]
            )

            content_element = ep_soup.select_one(
                ".widget-episodeBody"
            )

            if not content_element:
                return

            for tag in content_element.find_all(
                ["rt", "rp"]
            ):
                tag.decompose()

            for ruby in content_element.find_all(
                "ruby"
            ):
                ruby.replace_with(
                    ruby.get_text(strip=True)
                )

            body_paragraphs = []

            for p in content_element.find_all("p"):
                
                if base_data.EXPORT_TEXT:
                    for br in p.find_all(["br", "br/"]):
                        br.replace_with("\n")
                    
                p_text = p.decode_contents()

                p_text = p_text.replace(
                    "<span>",
                    ""
                ).replace(
                    "</span>",
                    ""
                )

                p_text = re.sub(
                    r'<em class="emphasisDots">(.*?)</em>',
                    r'**\1**',
                    p_text
                )

                p_text = re.sub(
                    r'<[^>]+>',
                    '',
                    p_text
                )

                p_text = p_text.lstrip(
                    " \t"
                ).rstrip()

                if p_text or (base_data.EXPORT_TEXT and not p_text):
                    p_text = re.sub(
                        r'《《(.+?)》》',
                        r'\1',
                        p_text
                    )

                    body_paragraphs.append(
                        p_text
                    )
            
            body = "\n".join(
                body_paragraphs
            )

            safe_title = re.sub(
                r'[\\/:*?"<>|]',
                '_',
                subtitle
            )

            file_path = os.path.join(
                trs_path,
                f"{current_idx}번_{safe_title}.txt"
            )

            with open(
                file_path,
                "w",
                encoding="utf-8"
            ) as f:
                f.write(
                    subtitle +
                    "\n\n" +
                    body +
                    "\n\n"
                )

            with progress_state["lock"]:
                progress_state["done"] += 1
                done = progress_state["done"]

            progress_percent = round(
                (100 / total_count) * done,
                1
            )

            
            label_callback(
                f"{progress_percent}%"
            )

        except Exception as e:
            print(
                f"카쿠요무 에피소드 다운로드 오류 "
                f"({ep['id']}): {e}"
            )
            
def download_kakuyomu_async(
    novel_code,
    start,
    end,
    trs_path,
    label
):
    total_count = end - start + 1

    url = (
        f"https://kakuyomu.jp/"
        f"works/{novel_code}"
    )

    req_headers = {
        **base_data.HEADERS,
        "Referer": url
    }

    sem = threading.Semaphore(
        base_data.CONCURRENCY_LIMIT
    )

    progress_state = {
        "done": 0,
        "lock": threading.Lock()
    }

    session = requests.Session()

    session.headers.update(
        req_headers
    )

    label_callback = label.setText

    
    try:
        res = session.get(
            url,
            timeout=30
        )

        if res.status_code != 200:
            session.close()
            return novel_code

        html_text = res.text

        soup = BeautifulSoup(
            html_text,
            "html.parser"
        )

        full_title = (
            soup.title.string
            if soup.title
            else ""
        )

        book_title = re.sub(
            r'（.+） - カクヨム$',
            '',
            full_title
        ).strip()

        pattern = (
            r'\{"__typename":"Episode",'
            r'"id":"(\d+)",'
            r'"title":"(.+?)"'
        )

        matches = re.findall(
            pattern,
            html_text
        )

        episodes = []
        seen_ids = set()

        for ep_id, ep_title in matches:
            if ep_id in seen_ids:
                continue

            try:
                decoded_title = json.loads(
                    f'"{ep_title}"'
                )
            except Exception:
                decoded_title = ep_title

            episodes.append({
                "id": ep_id,
                "subtitle": decoded_title,
                "url": (
                    f"https://kakuyomu.jp/"
                    f"works/{novel_code}/"
                    f"episodes/{ep_id}"
                )
            })

            seen_ids.add(ep_id)

    except Exception as e:
        print(
            f"카쿠요무 목차 가져오기 오류: {e}"
        )

        session.close()
        return novel_code

    start_idx = max(
        0,
        start - 1
    )

    end_idx = min(
        len(episodes),
        end
    )

    target_episodes = episodes[
        start_idx:end_idx
    ]

    threads = []

    for idx, ep in enumerate(
        target_episodes
    ):
        thread = threading.Thread(
            target=fetch_kakuyomu_episode,
            args=(
                session,
                sem,
                ep,
                idx + 1,
                trs_path,
                label_callback,
                total_count,
                progress_state
            ),
            daemon=True
        )

        threads.append(thread)
        thread.start()

    
    for thread in threads:
        thread.join()

    session.close()

    return book_title

def new_kakuyomu(novel_code):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ja,ko-KR;q=0.9,ko;q=0.8,en-US;q=0.7,en;q=0.6"
    }

    url = (
        f"https://kakuyomu.jp/"
        f"works/{novel_code}"
    )

    headers["Referer"] = url

    try:
        res = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        res.encoding = "utf-8"

        if res.status_code != 200:
            return novel_code

        html_text = res.text

        pattern = (
            r'\{"__typename":"Episode",'
            r'"id":"(\d+)",'
            r'"title":"(.+?)"'
        )

        matches = re.findall(
            pattern,
            html_text
        )

        
        return len(matches)

    except Exception:
        return None