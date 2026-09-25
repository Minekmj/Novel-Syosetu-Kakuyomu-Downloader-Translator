import json
import os
import re
import secrets
import string
import threading
import time
import requests
from bs4 import BeautifulSoup

import src.find.site.site_data as sf

base_data = None

_reset_lock = threading.Lock()
_last_reset_time = 0
_request_sem = threading.Semaphore(3)


def urljoin(base_url: str, relative_url: str) -> str:
    relative_url = relative_url.strip()

    if relative_url.startswith("http://") or relative_url.startswith("https://"):
        return relative_url

    scheme = ""
    if base_url.startswith("https://"):
        scheme = "https:"
        base_without_scheme = base_url[8:]
    elif base_url.startswith("http://"):
        scheme = "http:"
        base_without_scheme = base_url[7:]
    else:
        scheme = "https:"
        base_without_scheme = base_url

    if relative_url.startswith("//"):
        return f"{scheme}{relative_url}"

    if "/" in base_without_scheme:
        domain, base_path = base_without_scheme.split("/", 1)
        base_path = "/" + base_path
    else:
        domain = base_without_scheme
        base_path = "/"

    if relative_url.startswith("/"):
        return f"{scheme}//{domain}{relative_url}"

    if not base_path.endswith("/"):
        base_path = base_path.rsplit("/", 1)[0] + "/"

    full_path = base_path + relative_url
    segments = full_path.split("/")
    resolved_segments = []

    for seg in segments:
        if seg in ("", "."):
            continue
        elif seg == "..":
            if resolved_segments:
                resolved_segments.pop()
        else:
            resolved_segments.append(seg)

    normalized_path = "/" + "/".join(resolved_segments)

    if relative_url.endswith("/") and not normalized_path.endswith("/"):
        normalized_path += "/"

    return f"{scheme}//{domain}{normalized_path}"


def generate_random_filename(img_dir, ext=".jpg"):
    chars = string.ascii_letters + string.digits

    while True:
        rand_name = "".join(
            secrets.choice(chars)
            for _ in range(16)
        )

        filename = f"{rand_name}{ext}"
        full_path = os.path.join(img_dir, filename)

        if not os.path.exists(full_path):
            return filename, full_path


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


def create_session(is_r18=False):
    session = requests.Session()
    session.headers.update(sf.BASE_HEADERS)

    if is_r18:
        sf.COOKIES["over18"] = "off"
        session.cookies.set("over18", "off", domain=".syosetu.org")

    session.cookies.update(sf.COOKIES)
    return session


def http_get(url, session=None, is_r18=False, headers=None, timeout=30):
    global _last_reset_time

    if session is None:
        session = create_session(is_r18=is_r18)

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


def http_cookie(session=None, is_r18=False):
    sf.reset_b()
    if is_r18:
        sf.COOKIES["over18"] = "off"
    session.cookies.update(sf.COOKIES)


def hameln_title(novel_code):
    nid, is_r18 = parse_novel_code(novel_code)
    base_url = "https://h.syosetu.org" if is_r18 else "https://syosetu.org"
    url = f"{base_url}/novel/{nid}/"

    session = create_session(is_r18=is_r18)
    http_cookie(session, is_r18=is_r18)

    try:
        res = http_get(url, session=session, is_r18=is_r18, headers={"Referer": url}, timeout=15)

        if res.status_code != 200:
            return novel_code

        soup = BeautifulSoup(res.text, "html.parser")
        full_title = soup.title.string if soup.title else ""

        book_title = re.sub(
            r'\s*-\s*ハーメルン.*$',
            '',
            full_title
        ).strip()

        return book_title or novel_code

    except Exception:
        return None

    finally:
        session.close()


def fetch_hameln_episode(
    title_path,
    sem,
    ep,
    current_idx,
    trs_path,
    label_callback,
    total_count,
    progress_state,
    is_r18=False,
    printcall=print,
    max_retries=3
):
    with sem:
        backup_file = None
        prefix = f"[{current_idx}] "
        if os.path.exists(title_path):
            for fname in os.listdir(title_path):
                if fname.startswith(prefix) and fname.endswith(".txt"):
                    backup_file = os.path.join(title_path, fname)
                    break

        if backup_file and os.path.exists(backup_file):
            try:
                with open(backup_file, "r", encoding="utf-8") as f:
                    content = f.read()

                parts = content.split("=" * 30)
                if len(parts) >= 3:
                    subtitle = parts[1].strip()
                    body = ("=" * 30).join(parts[2:]).lstrip("\r\n")
                else:
                    subtitle = os.path.splitext(os.path.basename(backup_file))[0].replace(prefix, "", 1)
                    body = content.strip()

                safe_title = re.sub(r'[\\/:*?"<>|]', "_", subtitle)
                trs_file_path = os.path.join(trs_path, f"{current_idx}번_{safe_title}.txt")

                with open(trs_file_path, "w", encoding="utf-8") as f:
                    f.write(subtitle + "\n\n" + body + "\n\n")

                with progress_state["lock"]:
                    progress_state["done"] += 1
                    done = progress_state["done"]

                progress_percent = round((100 / total_count) * done, 1)
                label_callback(f"{progress_percent}%")

                return True
            except Exception as e:
                printcall(
                    f"하멜른 {current_idx}화 기존 백업 읽기 실패 ({e}). 웹에서 새로 다운로드합니다."
                )

        delay = base_data.DELAY_H

        for attempt in range(max_retries):
            session = create_session(is_r18=is_r18)

            try:
                res = http_get(
                    ep["url"],
                    session=session,
                    is_r18=is_r18,
                    headers={"Referer": ep["url"]},
                    timeout=30
                )

                if res.status_code != 200:
                    raise Exception(f"HTTP status {res.status_code}")

                html = res.text
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

                subtitle = (
                    subtitle_tag
                    if subtitle_tag
                    else ep.get("subtitle", f"{current_idx}화")
                )

                content_element = ep_soup.select_one("#honbun")
                if not content_element:
                    raise Exception("본문 태그(#honbun) 없음")

                has_downloaded_img = False
                img_targets = []

                for tag in content_element.find_all(["img", "a"]):
                    if tag.name == "img" and tag.get("src"):
                        img_targets.append((tag, tag.get("src")))
                    elif tag.name == "a" and tag.get("href"):
                        href = tag.get("href")
                        if (
                            tag.get("name") == "img"
                            or tag.get("alt") == "挿絵"
                            or "挿絵" in tag.get_text()
                            or "/img/" in href
                            or re.search(r'\.(png|jpg|jpeg|gif|webp)', href, re.I)
                        ):
                            img_targets.append((tag, href))

                if img_targets:
                    img_dir = os.path.join(base_data.OUTFOLDER, "img")
                    os.makedirs(img_dir, exist_ok=True)

                    for tag, img_url in img_targets:
                        full_img_url = urljoin(ep["url"], img_url)
                        ext = os.path.splitext(full_img_url.split("?")[0])[1]
                        if not ext or len(ext) > 5:
                            ext = ".jpg"

                        filename, file_save_path = generate_random_filename(img_dir, ext)

                        try:
                            img_res = http_get(
                                full_img_url,
                                session=session,
                                is_r18=is_r18,
                                headers={"Referer": ep["url"]},
                                timeout=30
                            )

                            if img_res.status_code == 200:
                                with open(file_save_path, "wb") as f_img:
                                    f_img.write(img_res.content)

                                tag.replace_with(f"-img-:{filename}")
                                has_downloaded_img = True
                            else:
                                tag.decompose()

                        except Exception as err:
                            printcall(
                                f"하멜른 {current_idx}화 이미지 다운로드 실패 ({full_img_url}): {err}"
                            )
                            tag.decompose()

                for tag in content_element.find_all(["rt", "rp"]):
                    tag.decompose()

                for ruby in content_element.find_all("ruby"):
                    ruby.replace_with(ruby.get_text(strip=True))

                body_paragraphs = []
                body_paragraphs_raw = []

                p_tags = content_element.find_all("p")
                if not p_tags:
                    p_tags = [content_element]

                export_text = getattr(base_data, "EXPORT_TEXT", False)

                for p in p_tags:
                    if export_text:
                        for br in p.find_all(["br", "br/"]):
                            br.replace_with("\n")

                    p_text = p.decode_contents()
                    p_text = p_text.replace("<span>", "").replace("</span>", "")
                    p_text = re.sub(r'<em class="emphasisDots">(.*?)</em>', r"**\1**", p_text)
                    p_text = re.sub(r"<[^>]+>", "", p_text)
                    p_text = p_text.lstrip(" \t").rstrip()

                    if p_text or (export_text and not p_text):
                        p_text_clean = re.sub(r"《《(.+?)》》", r"\1", p_text)
                        body_paragraphs.append(p_text_clean)

                    if p_text or not p_text:
                        p_text_clean = re.sub(r"《《(.+?)》》", r"\1", p_text)
                        body_paragraphs_raw.append(p_text_clean)

                body = "\n".join(body_paragraphs)
                body_raw = "\n".join(body_paragraphs_raw)

                safe_title = re.sub(r'[\\/:*?"<>|]', "_", subtitle)
                file_path = os.path.join(trs_path, f"{current_idx}번_{safe_title}.txt")

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(subtitle + "\n\n" + body + "\n\n")

                with open(
                    os.path.join(title_path, f"[{current_idx}] {safe_title}.txt"),
                    "w",
                    encoding="utf-8"
                ) as f:
                    f.write('=' * 30 + "\n" + subtitle + "\n" + '=' * 30 + "\n\n\n\n" + body_raw)

                with progress_state["lock"]:
                    progress_state["done"] += 1
                    done = progress_state["done"]

                progress_percent = round((100 / total_count) * done, 1)
                label_callback(f"{progress_percent}%")

                wait_time = delay * 5 if has_downloaded_img else delay
                time.sleep(wait_time)
                return True

            except Exception as e:
                printcall(
                    f"하멜른 에피소드 다운로드 오류 ({ep.get('id', current_idx)}) [시도 {attempt + 1}/{max_retries}]: {e}"
                )
                if e == "HTTP status 503":
                    time.sleep(delay * 5)
                    attempt -= 1
                else:
                    if attempt < max_retries - 1:
                        time.sleep(delay * 10)
                    else:
                        printcall(f"하멜른 에피소드 ({ep.get('id', current_idx)}) 최대 재시도 횟수 초과")
                        return None

            finally:
                session.close()


def get_hameln_episodes(nid, session, html_text, is_r18=False):
    episodes = []
    base_url = "https://h.syosetu.org" if is_r18 else "https://syosetu.org"

    soup = BeautifulSoup(html_text, "html.parser")
    links = soup.find_all("a", href=True)
    seen_ids = set()

    pattern = re.compile(rf'(?:/novel/{nid}/|\./)(\d+)\.html')

    for a in links:
        href = a.get("href", "")
        match = pattern.search(href)
        if match:
            ep_id = match.group(1)
            if ep_id not in seen_ids:
                seen_ids.add(ep_id)
                subtitle = a.get_text(strip=True)
                episodes.append({
                    "id": ep_id,
                    "subtitle": subtitle,
                    "url": f"{base_url}/novel/{nid}/{ep_id}.html"
                })

    if not episodes and soup.select_one("#honbun"):
        full_title = soup.title.string if soup.title else ""
        book_title = re.sub(r'\s*-\s*ハーメルン.*$', '', full_title).strip()
        episodes.append({
            "id": "1",
            "subtitle": book_title or "단편",
            "url": f"{base_url}/novel/{nid}/"
        })

    return episodes


def download_hameln_async(novel_code, start, end, trs_path, label):
    total_count = end - start + 1
    nid, is_r18 = parse_novel_code(novel_code)

    base_url = "https://h.syosetu.org" if is_r18 else "https://syosetu.org"
    url = f"{base_url}/novel/{nid}/"

    book_title = novel_code

    progress_state = {
        "done": 0,
        "lock": threading.Lock()
    }

    label_callback = label.setText
    session = create_session(is_r18=is_r18)
    http_cookie(session, is_r18=is_r18)

    try:
        res = http_get(url, session=session, is_r18=is_r18, headers={"Referer": url}, timeout=30)

        if res.status_code != 200:
            return novel_code

        html_text = res.text
        soup = BeautifulSoup(html_text, "html.parser")

        full_title = soup.title.string if soup.title else ""
        book_title = re.sub(r'\s*-\s*ハーメルン.*$', '', full_title).strip()

        episodes = get_hameln_episodes(nid, session, html_text, is_r18=is_r18)

    except Exception as e:
        print(f"하멜른 목차 가져오기 오류: {e}")
        return novel_code

    finally:
        session.close()

    if not episodes:
        print("하멜른 에피소드를 찾지 못했습니다.")
        return book_title or novel_code

    r_book_title = re.sub(r"^【.*?】", "", book_title)
    r_book_title = re.sub(r"【.*?】$", "", r_book_title)
    r_book_title = re.sub(r'[\\/:*?"<>|]', "_", r_book_title).strip()

    title_path = os.path.join(base_data.OUTFOLDER, "list", r_book_title)
    os.makedirs(title_path, exist_ok=True)

    start_idx = max(0, start - 1)
    end_idx = min(len(episodes), end)
    target_episodes = episodes[start_idx:end_idx]

    sem = threading.Semaphore(base_data.CONCURRENCY_LIMIT_H)
    threads = []

    for idx, ep in enumerate(target_episodes):
        current_idx = idx + start

        thread = threading.Thread(
            target=fetch_hameln_episode,
            args=(
                title_path,
                sem,
                ep,
                current_idx,
                trs_path,
                label_callback,
                total_count,
                progress_state,
                is_r18,
                print
            ),
            daemon=True
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return book_title or novel_code


def new_hameln(novel_code, have_make=False):
    nid, is_r18 = parse_novel_code(novel_code)
    base_url = "https://h.syosetu.org" if is_r18 else "https://syosetu.org"
    url = f"{base_url}/novel/{nid}/"

    session = create_session(is_r18=is_r18)
    http_cookie(session, is_r18=is_r18)

    try:
        res = http_get(url, session=session, is_r18=is_r18, headers={"Referer": url}, timeout=15)

        if res.status_code != 200:
            return None

        html_text = res.text
        episodes = get_hameln_episodes(nid, session, html_text, is_r18=is_r18)

        count = len(episodes) if episodes else None
        if count is None:
            return None

        if not have_make:
            return count

        latest_date = None
        soup = BeautifulSoup(html_text, "html.parser")

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

        return (count, base_data.normalize_date(latest_date))

    except Exception as e:
        print(f"하멜른 에피소드 수 확인 오류: {e}")
        return None

    finally:
        session.close()