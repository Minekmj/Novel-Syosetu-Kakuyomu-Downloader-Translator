import os
import re
import requests
import json
from bs4 import BeautifulSoup
import shutil
from trans import Translator
import threading

EXPORT_TEXT = False

SPLIT_POINT = "+---+"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja,ko-KR;q=0.9,ko;q=0.8,en-US;q=0.7,en;q=0.6"
}

CONCURRENCY_LIMIT = 5

def extract_number(filename):
    match = re.search(r'(\d+)번', filename)
    return int(match.group(1)) if match else 9999

def process_text_line(line):
    cleaned = line.strip()
    cleaned = cleaned.replace('「', '“').replace('」', '”')
    return cleaned

def create_merged_txt(folder_path, output_txt_path, book_title, extract_number_fn=extract_number):
    if not os.path.exists(folder_path):
        return False

    all_files = os.listdir(folder_path)

    txt_files = [
        f for f in all_files
        if f.endswith('.txt') and not os.path.isdir(os.path.join(folder_path, f))
    ]

    sort_key = extract_number_fn if extract_number_fn else extract_number
    txt_files.sort(key=sort_key)

    if not txt_files:
        return False

    parts = book_title.split("|")

    main_title = parts[0].strip() if len(parts) > 0 else book_title
    sub_title = parts[1].strip() if len(parts) > 1 else ""

    delimiter = SPLIT_POINT

    if EXPORT_TEXT:
        with open(output_txt_path, "w", encoding="utf-8") as out_f:
            out_f.write(f"{main_title}\n")
            out_f.write(f"{sub_title}\n")
            out_f.write("(raw)\n")
            out_f.write(f"+---+\n{main_title} | {sub_title}\n\n")

            for file_name in txt_files:
                file_path = os.path.join(folder_path, file_name)

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except UnicodeDecodeError:
                    with open(file_path, "r", encoding="cp949") as f:
                        lines = f.readlines()

                if not lines:
                    continue

                out_f.write(f"\n{'=' * 30}\n")
                subtitle = lines[0].strip()
                out_f.write(f"{subtitle}\n")
                out_f.write(f"{'=' * 30}\n\n")

                for line in lines[1:]:
                    if line:
                        processed_text = process_text_line(line)
                        if processed_text != '':
                            out_f.write(f"{processed_text}\n")
                        else:
                            out_f.write("\n")
                
                out_f.write("\n")
        return True

    with open(output_txt_path, "w", encoding="utf-8") as out_f:
        
        out_f.write(f"{main_title}\n")

        if sub_title:
            out_f.write(f"{sub_title}\n")

        
        for file_name in txt_files:
            file_path = os.path.join(folder_path, file_name)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="cp949") as f:
                    lines = f.readlines()

            if not lines:
                continue

            out_f.write(f"{delimiter}\n")

            
            subtitle = lines[0].strip()
            subtitle = subtitle.replace('「', '“').replace('」', '”')
            out_f.write(f"{subtitle}\n")

            
            for line in lines[1:]:
                stripped_line = line.strip()

                if not stripped_line:
                    continue

                clean_text = re.sub(r'<[^>]+>', '', stripped_line)

                if clean_text:
                    processed_text = process_text_line(clean_text)
                    out_f.write(f"{processed_text}\n")

    return True

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

def CheckTitle(site):
    site_type = ""

    if "syosetu.com" in site:
        site = site.split("/")[-2]
        site_type = "syosetu"

    elif "kakuyomu.jp" in site:
        site = site.split("/")[-1]
        site_type = "kakuyomu"

    is_kakuyomu = (site_type == "kakuyomu") or site.isdigit()

    if is_kakuyomu:
        title = kakuyomu_title(site)
    else:
        title = syosetu_title(site)

    title_ko = Translator(title)

    return title_ko

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
                
            if EXPORT_TEXT:
                for br in body_tag.find_all(["br", "br/"]):
                    br.replace_with("\n")

            body = "\n".join(
                [
                    p.get_text(" ", strip=True)
                    for p in body_tag.find_all("p")
                    if p.get_text(strip=True) or (EXPORT_TEXT and not p.get_text(strip=True))
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
        CONCURRENCY_LIMIT
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
        HEADERS
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
                
                if EXPORT_TEXT:
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

                if p_text or (EXPORT_TEXT and not p_text):
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
        **HEADERS,
        "Referer": url
    }

    sem = threading.Semaphore(
        CONCURRENCY_LIMIT
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

def Download(
    site,
    start,
    end,
    label,
    title
):
    site_type = ""

    start = int(start)
    end = int(end)

    if "syosetu.com" in site:
        site = site.split("/")[-2]
        site_type = "syosetu"

    elif "kakuyomu.jp" in site:
        site = site.split("/")[-1]
        site_type = "kakuyomu"

    trs_path = (
        "./temp_trs_"
        + site_type
        + "_"
        + site
    )

    os.makedirs(
        trs_path,
        exist_ok=True
    )

    is_kakuyomu = (
        site_type == "kakuyomu"
    ) or site.isdigit()

    if is_kakuyomu:
        book_title = download_kakuyomu_async(
            site,
            start,
            end,
            trs_path,
            label
        )
    else:
        book_title = download_syosetu_async(
            site,
            start,
            end,
            trs_path,
            label
        )

    data = f"{start} ~ {end}"

    if start == end:
        data = start

    
    book_title = f"{title} | {data}"

    clean_title = re.sub(
        r'[\\/:*?"<>|]',
        '_',
        book_title
    )

    if not os.path.exists(
        OUTFOLDER
    ):
        os.makedirs(
            OUTFOLDER,
            exist_ok=True
        )

    create_merged_txt(
        trs_path,
        f"{OUTFOLDER}/{clean_title}.txt",
        book_title
    )

    shutil.rmtree(
        trs_path,
        ignore_errors=True
    )

OUTFOLDER = "./out"

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

def new_number(site):
    site_type = ""

    if "syosetu.com" in site:
        site = site.split("/")[-2]
        site_type = "syosetu"

    elif "kakuyomu.jp" in site:
        site = site.split("/")[-1]
        site_type = "kakuyomu"

    is_kakuyomu = (
        site_type == "kakuyomu"
    ) or site.isdigit()

    if is_kakuyomu:
        new = new_kakuyomu(site)
    else:
        new = new_syosetu(site)

    return new