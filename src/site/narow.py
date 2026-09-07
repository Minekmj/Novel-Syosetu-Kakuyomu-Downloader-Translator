import os
import re
import requests
from bs4 import BeautifulSoup
import threading

base_data = None #외부 주입용

def syosetu_title(novel_code):
    url = f"https://ncode.syosetu.com/{novel_code}/"

    try:
        res = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )

        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            t = soup.find("p", class_="p-novel__title") or soup.find("h1")

            if t:
                return t.get_text(strip=True)

            return None

    except Exception:
        return None
    
def download_syosetu_async(
    novel_code,
    start,
    end,
    trs_path,
    label
):
    total_count = end - start + 1

    url = f"https://ncode.syosetu.com/{novel_code}/"

    book_title = novel_code

    sem = threading.Semaphore(
        base_data.CONCURRENCY_LIMIT
    )

    progress_state = {
        "done": 0,
        "lock": threading.Lock()
    }

    
    def ANDROID_LABEL(text):
        label.text = text

    label_callback = label.setText

    session = requests.Session()

    session.headers.update(
        base_data.HEADERS
    )

    
    try:
        res = session.get(
            url,
            timeout=15
        )

        if res.status_code == 200:
            soup = BeautifulSoup(
                res.text,
                "html.parser"
            )

            t = (
                soup.find(
                    "p",
                    class_="p-novel__title"
                )
                or soup.find("h1")
            )

            if t:
                book_title = t.get_text(
                    strip=True
                )

    except Exception:
        pass

    threads = []

    for i in range(start, end + 1):
        thread = threading.Thread(
            target=fetch_syosetu_episode,
            args=(
                session,
                sem,
                url,
                i,
                trs_path,
                label_callback,
                total_count,
                progress_state,
                print
            ),
            daemon=True
        )

        threads.append(thread)
        thread.start()

    
    for thread in threads:
        thread.join()

    session.close()

    return book_title

def fetch_syosetu_episode(
    session,
    sem,
    url,
    ep_num,
    trs_path,
    label_callback,
    total_count,
    progress_state,
    printcall
):
    with sem:
        try:
            episode_url = f"{url}{ep_num}/"

            res = session.get(
                episode_url,
                timeout=30
            )

            if res.status_code != 200:
                episode_url = f"{url}"
                    
                res = session.get(
                    episode_url,
                    timeout=30
                )
    
                if res.status_code != 200:
                    return None
    
                html = res.text
    
                soup = BeautifulSoup(html, "html.parser")
    
                title_tag = soup.find(
                    "h1",
                    class_="p-novel__title"
                )
    
                body_tag = soup.find(
                    "div",
                    class_="js-novel-text p-novel__text"
                )
            else:
                html = res.text

                soup = BeautifulSoup(html, "html.parser")

                title_tag = soup.find(
                    "h1",
                    class_="p-novel__title p-novel__title--rensai"
                )

                body_tag = soup.find(
                    "div",
                    class_="js-novel-text p-novel__text"
                )

            if not title_tag or not body_tag:
                return None

            title = title_tag.get_text(strip=True)

            for tag in body_tag.find_all(["rp", "rt"]):
                tag.decompose()

            for ruby in body_tag.find_all("ruby"):
                ruby.replace_with(
                    ruby.get_text(strip=True)
                )
                
            if base_data.EXPORT_TEXT:
                for br in body_tag.find_all(["br", "br/"]):
                    br.replace_with("\n")

            body = "\n".join(
                [
                    p.get_text(" ", strip=True)
                    for p in body_tag.find_all("p")
                    if p.get_text(strip=True) or (base_data.EXPORT_TEXT and not p.get_text(strip=True))
                ]
            )

            safe_title = re.sub(
                r'[\\/:*?"<>|]',
                '_',
                title
            )

            file_path = os.path.join(
                trs_path,
                f"{ep_num}번_{safe_title}.txt"
            )

            with open(
                file_path,
                "w",
                encoding="utf-8"
            ) as f:
                f.write(
                    title +
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

            return True

        except Exception as e:
            printcall(
                f"Syosetu {ep_num}화 다운로드 오류: {e}"
            )

            return None
        
def new_syosetu(novel_code):
    url = (
        f"https://ncode.syosetu.com/"
        f"{novel_code}/"
    )

    try:
        res = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=15
        )

        if res.status_code != 200:
            return None

        soup = BeautifulSoup(
            res.text,
            "html.parser"
        )

        next_page = soup.find(
            "a",
            class_="c-pager__item c-pager__item--last"
        )

        u = 1

        if next_page:
            t = next_page["href"]

            u = int(
                t[t.find("=") + 1:]
            )

        else:
            urlp = url + "1"

            res = requests.get(
                urlp,
                headers={
                    "User-Agent": "Mozilla/5.0"
                },
                timeout=15
            )

            if res.status_code != 200:
                return 1

        res = requests.get(
            f"{url}/?p={u}",
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=15
        )

        if res.status_code != 200:
            return None

        soup = BeautifulSoup(
            res.text,
            "html.parser"
        )

        body_tag = soup.find(
            "div",
            class_="p-eplist"
        )

        if not body_tag:
            return None

        t = body_tag.find_all(
            "a",
            class_="p-eplist__subtitle"
        )[-1]["href"]

        match = re.search(
            r"/(\d+)/",
            t
        )

        return (
            int(match.group(1))
            if match
            else None
        )

    except Exception as e:
        print(
            f"오류: {e}"
        )

    return None