from datetime import datetime, timedelta
import os
import re
import secrets
import string
import threading
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

base_data = None  # 외부 주입용


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


def create_session():
    session = requests.Session()
    headers = base_data.HEADERS
    session.headers.update(headers)
    return session


def parse_novelup_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()

    m = re.search(r'(\d{2,4})[/-](\d{1,2})[/-](\d{1,2})(?:\s+(\d{1,2}):(\d{1,2}))?', date_str)
    if m:
        y, mth, d, h, mn = m.groups()
        if len(y) == 2:
            y = f"20{y}"
        h = int(h) if h else 0
        mn = int(mn) if mn else 0
        try:
            return datetime(int(y), int(mth), int(d), h, mn)
        except ValueError:
            pass

    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日(?:\s*(\d{1,2}):(\d{1,2}))?', date_str)
    if m:
        y, mth, d, h, mn = m.groups()
        h = int(h) if h else 0
        mn = int(mn) if mn else 0
        try:
            return datetime(int(y), int(mth), int(d), h, mn)
        except ValueError:
            pass

    return None


def get_novelup_total_info(soup):
    total_count = None
    last_page = 1

    total_elem = soup.select_one(".total_episode_num, .story_episode_count, .episode_count")
    if total_elem:
        m = re.search(r'総エピソード数[：:]\s*([0-9,]+)\s*話', total_elem.get_text())
        if not m:
            m = re.search(r'([0-9,]+)\s*話', total_elem.get_text())
        if m:
            total_count = int(m.group(1).replace(",", ""))
            last_page = (total_count - 1) // 100 + 1

    last_btn = soup.select_one("a[aria-label='最後のページへ'], a[data-label='最後のページへ']")
    if last_btn:
        href = last_btn.get("href", "")
        m = re.search(r'[?&]p=(\d+)', href)
        if m:
            last_page = max(last_page, int(m.group(1)))
    else:
        links = soup.select(".pagination a, div.pager a, a[href*='?p=']")
        for a in links:
            href = a.get("href", "")
            m = re.search(r'[?&]p=(\d+)', href)
            if m:
                p_val = int(m.group(1))
                if p_val > last_page:
                    last_page = p_val

    return total_count, last_page


def parse_episodes_from_soup(soup):
    """단일 목차 페이지에서 100개 단위의 에피소드 목록 파싱"""
    episodes = []
    items = soup.select(".episodeList .episodeListItem, .episodeListItem")

    for item in items:
        title_tag = item.select_one("a.episodeTitle, a[href*='/story/']")
        if not title_tag:
            continue

        href = title_tag.get("href", "")
        match = re.search(r'/story/\d+/(\d+)', href)
        if not match:
            continue

        ep_id = match.group(1)
        subtitle = title_tag.get_text(strip=True)
        subtitle = " ".join(subtitle.split())

        data_num = title_tag.get("data-number", "")
        ep_no = int(data_num) if data_num.isdigit() else None

        date_elem = item.select_one(".publishDate, .episodeDate")
        date_text = date_elem.get_text(strip=True) if date_elem else ""
        dt = parse_novelup_date(date_text)

        full_url = urljoin("https://novelup.plus", href)

        episodes.append({
            "id": ep_id,
            "no": ep_no,
            "subtitle": subtitle,
            "url": full_url,
            "published_at": dt.isoformat() if dt else None,
            "datetime": dt
        })

    return episodes


def novelup_title(novel_code):
    url = f"https://novelup.plus/story/{novel_code}"

    session = create_session()
    session.headers.update({"Referer": url})

    try:
        res = session.get(url, timeout=15)
        if res.status_code != 200:
            return novel_code

        soup = BeautifulSoup(res.text, "html.parser")

        name_tag = soup.select_one(".story_title, .story_name, h1")
        if name_tag:
            t = name_tag.get_text(strip=True)
            if t:
                return t

        full_title = soup.title.string if soup.title else ""
        book_title = re.sub(r'（.+?）\s*\|\s*小説投稿サイト.*$', '', full_title).strip()
        book_title = re.sub(r'\s*\|\s*小説投稿サイト.*$', '', book_title).strip()

        return book_title or novel_code

    except Exception:
        return None

    finally:
        session.close()


def fetch_novelup_episode(
    title_path,
    sem,
    ep,
    current_idx,
    trs_path,
    label_callback,
    total_count,
    progress_state,
    act_massage,
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

                if act_massage != "":
                    a = body.find(act_massage)
                    if a > 0:
                        body = body[0:a]

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
                    f"노벨업 {current_idx}화 기존 백업 읽기 실패 ({e}). 웹에서 새로 다운로드합니다."
                )

        delay = getattr(base_data, "DELAY", 1)

        for attempt in range(max_retries):
            session = create_session()
            session.headers.update({"Referer": ep["url"]})

            try:
                res = session.get(ep["url"], timeout=30)
                if res.status_code != 200:
                    raise Exception(f"HTTP status {res.status_code}")

                html = res.text
                ep_soup = BeautifulSoup(html, "html.parser")

                subtitle_tag = (
                    ep_soup.select_one(".episode_title h1")
                    or ep_soup.select_one(".episode_title")
                    or ep_soup.find("h1")
                )

                subtitle = (
                    subtitle_tag.get_text(strip=True)
                    if subtitle_tag
                    else ep["subtitle"]
                )

                content_element = (
                    ep_soup.select_one("#episode_content")
                    or ep_soup.select_one("div.content")
                    or ep_soup.select_one("#section_episode .content_inner")
                )

                if not content_element:
                    raise Exception("본문 태그(#episode_content) 없음")

                img_tags = content_element.find_all("img")
                has_downloaded_img = False

                if img_tags:
                    img_dir = os.path.join(base_data.OUTFOLDER, "img")
                    os.makedirs(img_dir, exist_ok=True)

                    for img in img_tags:
                        src = img.get("src")
                        if not src:
                            img.decompose()
                            continue

                        full_img_url = urljoin(ep["url"], src)
                        ext = os.path.splitext(full_img_url.split("?")[0])[1]
                        if not ext or len(ext) > 5:
                            ext = ".jpg"

                        filename, file_save_path = generate_random_filename(img_dir, ext)

                        try:
                            img_res = session.get(full_img_url, timeout=30)
                            if img_res.status_code == 200:
                                with open(file_save_path, "wb") as f_img:
                                    f_img.write(img_res.content)
                                img.replace_with(f"-img-:{filename}")
                                has_downloaded_img = True
                            else:
                                img.decompose()
                        except Exception as err:
                            printcall(f"노벨업 {current_idx}화 이미지 다운로드 실패 ({full_img_url}): {err}")
                            img.decompose()

                for tag in content_element.find_all(["rt", "rp"]):
                    tag.decompose()

                for ruby in content_element.find_all("ruby"):
                    ruby.replace_with(ruby.get_text(strip=True))

                for br in content_element.find_all(["br", "br/"]):
                    br.replace_with("\n")

                raw_html = content_element.decode_contents()
                raw_html = raw_html.replace("<span>", "").replace("</span>", "")
                raw_html = re.sub(r'<em class="emphasisDots">(.*?)</em>', r"**\1**", raw_html)
                raw_html = re.sub(r"<[^>]+>", "", raw_html)

                lines = raw_html.splitlines()

                body_paragraphs = []
                body_paragraphs_raw = []

                for line in lines:
                    line_text = line.lstrip(" \t").rstrip()
                    line_text = re.sub(r"《《(.+?)》》", r"\1", line_text)

                    if line_text or (base_data.EXPORT_TEXT and not line_text):
                        body_paragraphs.append(line_text)

                    if line_text or (not line_text):
                        body_paragraphs_raw.append(line_text)

                body = "\n".join(body_paragraphs)
                body_raw = "\n".join(body_paragraphs_raw)

                safe_title = re.sub(r'[\\/:*?"<>|]', "_", subtitle)
                file_path = os.path.join(trs_path, f"{current_idx}번_{safe_title}.txt")

                if act_massage != "":
                    a = body.find(act_massage)
                    if a > 0:
                        body = body[0:a]

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(subtitle + "\n\n" + body + "\n\n")

                with open(
                    os.path.join(title_path, f"[{current_idx}] {safe_title}.txt"),
                    "w",
                    encoding="utf-8"
                ) as f:
                    f.write(
                        '=' * 30 +
                        "\n" +
                        subtitle +
                        "\n" +
                        '=' * 30 +
                        "\n\n\n\n" +
                        body_raw
                    )

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
                    f"노벨업 에피소드 다운로드 오류 "
                    f"({ep.get('id', current_idx)}) "
                    f"[시도 {attempt + 1}/{max_retries}]: {e}"
                )

                if attempt < max_retries - 1:
                    time.sleep(delay * 10)
                else:
                    printcall(
                        f"노벨업 에피소드 "
                        f"({ep.get('id', current_idx)}) "
                        f"최대 재시도 횟수 초과"
                    )
                    return None

            finally:
                session.close()


def download_novelup_async(
    novel_code,
    start,
    end,
    trs_path,
    label,
    act_massage
):
    total_count = end - start + 1
    url = f"https://novelup.plus/story/{novel_code}"
    book_title = novel_code

    progress_state = {
        "done": 0,
        "lock": threading.Lock()
    }

    label_callback = label.setText

    session = create_session()
    session.headers.update({"Referer": url})

    try:
        res = session.get(url, timeout=30)
        if res.status_code != 200:
            return novel_code

        first_soup = BeautifulSoup(res.text, "html.parser")

        name_tag = first_soup.select_one(".story_title, .story_name, h1")
        if name_tag:
            book_title = name_tag.get_text(strip=True)
        else:
            full_title = first_soup.title.string if first_soup.title else ""
            book_title = re.sub(r'（.+?）\s*\|\s*小説投稿サイト.*$', '', full_title).strip()

        start_page = max(1, (start - 1) // 100 + 1)
        end_page = max(1, (end - 1) // 100 + 1)

        total_cnt, max_avail_page = get_novelup_total_info(first_soup)
        end_page = min(end_page, max_avail_page)

        collected_episodes = []
        seen_ids = set()

        for p in range(start_page, end_page + 1):
            if p == 1:
                page_soup = first_soup
            else:
                time.sleep(getattr(base_data, "DELAY", 1))
                page_res = session.get(f"{url}?p={p}", timeout=15)
                if page_res.status_code != 200:
                    continue
                page_soup = BeautifulSoup(page_res.text, "html.parser")

            p_eps = parse_episodes_from_soup(page_soup)
            for ep in p_eps:
                if ep["id"] not in seen_ids:
                    seen_ids.add(ep["id"])
                    collected_episodes.append(ep)

        if not collected_episodes:
            content_element = first_soup.select_one("#episode_content, div.content")
            if content_element:
                collected_episodes.append({
                    "id": "1",
                    "subtitle": book_title or novel_code,
                    "url": url,
                    "published_at": None,
                    "datetime": None
                })

    except Exception as e:
        print(f"노벨업 목차 가져오기 오류: {e}")
        return novel_code

    finally:
        session.close()

    if not collected_episodes:
        print("노벨업 에피소드를 찾지 못했습니다.")
        return book_title or novel_code

    r_book_title = re.sub(r"^【.*?】", "", book_title)
    r_book_title = re.sub(r"【.*?】$", "", r_book_title)
    r_book_title = re.sub(r'[\\/:*?"<>|]', "_", r_book_title).strip()

    title_path = os.path.join(base_data.OUTFOLDER, "list", r_book_title)
    os.makedirs(title_path, exist_ok=True)

    offset = (start_page - 1) * 100
    local_start = max(0, start - 1 - offset)
    local_end = local_start + total_count

    target_episodes = collected_episodes[local_start:local_end]

    sem = threading.Semaphore(base_data.CONCURRENCY_LIMIT)
    threads = []

    for idx, ep in enumerate(target_episodes):
        current_idx = idx + start

        thread = threading.Thread(
            target=fetch_novelup_episode,
            args=(
                title_path,
                sem,
                ep,
                current_idx,
                trs_path,
                label_callback,
                total_count,
                progress_state,
                act_massage,
                print
            ),
            daemon=True
        )

        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return book_title or novel_code


def new_novelup(novel_code, have_make=False):
    url = f"https://novelup.plus/story/{novel_code}"

    with create_session() as session:
        try:
            res = session.get(url, timeout=15)
            if res.status_code != 200:
                return None

            first_soup = BeautifulSoup(res.text, "html.parser")
            total_count, last_page = get_novelup_total_info(first_soup)
            latest_date = None

            if total_count is None:
                first_eps = parse_episodes_from_soup(first_soup)
                if not first_eps and first_soup.select_one("#episode_content, div.content"):
                    total_count = 1

            if total_count is None:
                return None

            if not have_make:
                return total_count

            if last_page > 1:
                last_res = session.get(f"{url}?p={last_page}", timeout=15)
                if last_res.status_code == 200:
                    last_soup = BeautifulSoup(last_res.text, "html.parser")
                else:
                    last_soup = first_soup
            else:
                last_soup = first_soup

            last_page_eps = parse_episodes_from_soup(last_soup)
            if last_page_eps:
                latest_date = last_page_eps[-1].get("published_at")

            return (total_count, base_data.normalize_date(latest_date) if latest_date else None)

        except Exception as e:
            print(f"노벨업 에피소드 수 확인 오류 ({novel_code}): {e}")
            return None


def find_ep_novelup_average(novel_code):
    url = f"https://novelup.plus/story/{novel_code}"

    with create_session() as session:
        try:
            res = session.get(url, timeout=15)
            if res.status_code != 200:
                return (None, None, None, None)

            first_soup = BeautifulSoup(res.text, "html.parser")
            _, last_page = get_novelup_total_info(first_soup)

            episodes_data = []

            for page in range(1, last_page + 1):
                if page == 1:
                    page_soup = first_soup
                else:
                    time.sleep(getattr(base_data, "DELAY", 1))
                    page_res = session.get(f"{url}?p={page}", timeout=15)
                    if page_res.status_code != 200:
                        continue
                    page_soup = BeautifulSoup(page_res.text, "html.parser")

                page_eps = parse_episodes_from_soup(page_soup)
                for ep in page_eps:
                    dt = ep.get("datetime")
                    ep_no = ep.get("no")
                    if dt:
                        episodes_data.append((ep_no or len(episodes_data) + 1, dt))

            if not episodes_data or len(episodes_data) < 2:
                return (None, None, None, None)

            episodes_data = sorted(set(episodes_data), key=lambda x: x[0], reverse=True)

            def get_average_from_selected(selected):
                if len(selected) < 2:
                    return None
                selected = sorted(selected, key=lambda x: x[1])
                intervals = []
                for (_, prev_dt), (_, curr_dt) in zip(selected, selected[1:]):
                    diff = (curr_dt - prev_dt).total_seconds() / 86400
                    if diff >= 0:
                        intervals.append(diff)
                return sum(intervals) / len(intervals) if intervals else None

            recent_avg = get_average_from_selected(episodes_data[:2])
            avg_10 = get_average_from_selected(episodes_data[:10])

            target_date = datetime.now()
            selected_30 = [item for item in episodes_data if target_date - timedelta(days=30) <= item[1] <= target_date]
            avg_30 = get_average_from_selected(selected_30)

            avg_all = get_average_from_selected(episodes_data)

            return (recent_avg, avg_10, avg_30, avg_all)

        except Exception as e:
            print(f"노벨업 연재 간격 계산 오류 ({novel_code}): {e}")
            return (None, None, None, None)