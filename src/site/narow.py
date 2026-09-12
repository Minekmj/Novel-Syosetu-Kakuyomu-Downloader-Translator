import os
import re
import secrets
import string
import threading
import time
import requests
from bs4 import BeautifulSoup

base_data = None  # 외부 주입용


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


def create_session():
    session = requests.Session()

    headers = base_data.HEADERS

    session.headers.update(headers)
    session.cookies.update({"over18": "yes"})

    return session


def syosetu_title(novel_code):
    url = f"https://ncode.syosetu.com/{novel_code}/"

    session = create_session()

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
                return t.get_text(strip=True)

    except Exception:
        pass

    finally:
        session.close()

    return None


def fetch_syosetu_episode(
    title_path,
    sem,
    url,
    ep_num,
    trs_path,
    label_callback,
    total_count,
    progress_state,
    printcall,
    max_retries=3
):
    with sem:
        # 1. 백업 폴더(outfolder/list/작품명)에 이미 파일이 있는지 확인
        backup_file = None
        prefix = f"[{ep_num}] "
        if os.path.exists(title_path):
            for fname in os.listdir(title_path):
                if fname.startswith(prefix) and fname.endswith(".txt"):
                    backup_file = os.path.join(title_path, fname)
                    break

        # 2. 백업 파일이 존재하면 읽어서 trs_path에 복원 후 다운로드 생략
        if backup_file and os.path.exists(backup_file):
            try:
                with open(backup_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 포맷: =*30 \n title \n =*30 \n\n\n\n body
                parts = content.split("=" * 30)
                if len(parts) >= 3:
                    title = parts[1].strip()
                    body = ("=" * 30).join(parts[2:]).lstrip("\r\n")
                else:
                    title = os.path.splitext(os.path.basename(backup_file))[0].replace(prefix, "", 1)
                    body = content.strip()

                safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)
                trs_file_path = os.path.join(trs_path, f"{ep_num}번_{safe_title}.txt")

                with open(trs_file_path, "w", encoding="utf-8") as f:
                    f.write(title + "\n\n" + body + "\n\n")

                # 진행률 갱신
                with progress_state["lock"]:
                    progress_state["done"] += 1
                    done = progress_state["done"]

                progress_percent = round((100 / total_count) * done, 1)
                label_callback(f"{progress_percent}%")

                return True
            except Exception as e:
                printcall(
                    f"Syosetu {ep_num}화 기존 백업 읽기 실패 ({e}). 웹에서 새로 다운로드합니다."
                )

        # 3. 백업이 없거나 오류 시 웹에서 직접 다운로드 수행
        delay = getattr(
            base_data,
            "DELAY",
            1
        )

        for attempt in range(max_retries):
            session = create_session()

            try:
                episode_url = f"{url}{ep_num}/"

                res = session.get(
                    episode_url,
                    timeout=30
                )

                if res.status_code != 200:
                    episode_url = url

                    res = session.get(
                        episode_url,
                        timeout=30
                    )

                    if res.status_code != 200:
                        raise Exception(
                            f"HTTP {res.status_code} 에러"
                        )

                    html = res.text
                    soup = BeautifulSoup(
                        html,
                        "html.parser"
                    )

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

                    soup = BeautifulSoup(
                        html,
                        "html.parser"
                    )

                    title_tag = soup.find(
                        "h1",
                        class_="p-novel__title p-novel__title--rensai"
                    )

                    body_tag = soup.find(
                        "div",
                        class_="js-novel-text p-novel__text"
                    )

                if not title_tag or not body_tag:
                    raise Exception(
                        "파싱 실패 (title_tag 또는 body_tag 없음)"
                    )

                title = title_tag.get_text(
                    strip=True
                )

                # 이미지 다운로드
                img_tags = body_tag.find_all("img")
                has_downloaded_img = False

                if img_tags:
                    img_dir = os.path.join(
                        base_data.OUTFOLDER,
                        "img"
                    )

                    os.makedirs(
                        img_dir,
                        exist_ok=True
                    )

                    for img in img_tags:
                        src = img.get("src")

                        if not src:
                            img.decompose()
                            continue

                        full_img_url = urljoin(
                            episode_url,
                            src
                        )

                        ext = os.path.splitext(
                            full_img_url.split("?")[0]
                        )[1]

                        if not ext or len(ext) > 5:
                            ext = ".jpg"

                        filename, file_save_path = generate_random_filename(
                            img_dir,
                            ext
                        )

                        try:
                            img_res = session.get(
                                full_img_url,
                                timeout=30
                            )

                            if img_res.status_code == 200:
                                with open(
                                    file_save_path,
                                    "wb"
                                ) as f_img:
                                    f_img.write(
                                        img_res.content
                                    )

                                img.replace_with(
                                    f"-img-:{filename}"
                                )

                                has_downloaded_img = True

                            else:
                                img.decompose()

                        except Exception as err:
                            printcall(
                                f"Syosetu {ep_num}화 이미지 다운로드 실패 "
                                f"({full_img_url}): {err}"
                            )

                            img.decompose()

                # 루비 제거
                for tag in body_tag.find_all(
                    ["rp", "rt"]
                ):
                    tag.decompose()

                for ruby in body_tag.find_all("ruby"):
                    ruby.replace_with(
                        ruby.get_text(strip=True)
                    )

                # <br> 처리
                if base_data.EXPORT_TEXT:
                    for br in body_tag.find_all(
                        ["br", "br/"]
                    ):
                        br.replace_with("\n")

                body = "\n".join(
                    [
                        p.get_text(
                            " ",
                            strip=True
                        )
                        for p in body_tag.find_all("p")
                        if p.get_text(strip=True)
                        or (
                            base_data.EXPORT_TEXT
                            and not p.get_text(strip=True)
                        )
                    ]
                )

                for br in body_tag.find_all(
                    ["br", "br/"]
                ):
                    br.replace_with("\n")
                body_save = "\n".join(
                    [
                        p.get_text(
                            " ",
                            strip=True
                        )
                        for p in body_tag.find_all("p")
                        if p.get_text(strip=True)
                        or (
                            not p.get_text(strip=True)
                        )
                    ]
                )

                safe_title = re.sub(
                    r'[\\/:*?"<>|]',
                    "_",
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

                # outfolder/list/작품명/[ep_num] safe_title.txt 저장
                with open(
                    os.path.join(title_path, f"[{ep_num}] {safe_title}.txt"),
                    "w",
                    encoding="utf-8"
                ) as f:
                    f.write(
                        '=' * 30 +
                        "\n" +
                        title +
                        "\n" +
                        '=' * 30 +
                        "\n\n\n\n" +
                        body_save
                    )

                # 진행률
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

                # 이미지가 있으면 서버 부담을 고려해 더 대기
                wait_time = (
                    delay * 5
                    if has_downloaded_img
                    else delay
                )

                time.sleep(wait_time)

                return True

            except Exception as e:
                printcall(
                    f"Syosetu {ep_num}화 다운로드 오류 "
                    f"(시도 {attempt + 1}/{max_retries}): {e}"
                )

                if attempt < max_retries - 1:
                    time.sleep(
                        delay * 10
                    )
                else:
                    printcall(
                        f"Syosetu {ep_num}화 최대 재시도 횟수 "
                        f"초과로 실패"
                    )

                    return None

            finally:
                session.close()


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

    label_callback = label.setText

    # 작품 제목 확인
    session = create_session()

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

    finally:
        session.close()

    threads = []

    r_book_title = re.sub(r"^【.*?】", "", book_title)

    r_book_title = re.sub(r"【.*?】$", "", r_book_title)

    r_book_title = r_book_title.strip()

    # outfolder/list/작품명 경로로 변경
    title_path = os.path.join(base_data.OUTFOLDER, "list", r_book_title)

    os.makedirs(title_path, exist_ok=True)

    for i in range(start, end + 1):
        thread = threading.Thread(
            target=fetch_syosetu_episode,
            args=(
                title_path,
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

    # 모든 다운로드 스레드 종료 대기
    for thread in threads:
        thread.join()

    return book_title


def new_syosetu(novel_code):
    url = (
        f"https://ncode.syosetu.com/"
        f"{novel_code}/"
    )

    session = create_session()

    try:
        res = session.get(
            url,
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
            t = next_page.get("href", "")

            match = re.search(
                r"[?&]p=(\d+)",
                t
            )

            if match:
                u = int(match.group(1))

        else:
            urlp = f"{url}?p=1"

            res = session.get(
                urlp,
                timeout=15
            )

            if res.status_code != 200:
                return 1

        res = session.get(
            f"{url}?p={u}",
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

        episodes = body_tag.find_all(
            "a",
            class_="p-eplist__subtitle"
        )

        if not episodes:
            return None

        t = episodes[-1].get(
            "href",
            ""
        )

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

    finally:
        session.close()