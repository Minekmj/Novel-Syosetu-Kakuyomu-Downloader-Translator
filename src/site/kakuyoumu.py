import json
import os
import re
import threading
import time
import requests
from bs4 import BeautifulSoup

base_data = None  # 외부 주입용


def create_session():
    session = requests.Session()

    headers = base_data.HEADERS

    session.headers.update(headers)
    return session


def kakuyomu_title(novel_code):
    url = f"https://kakuyomu.jp/works/{novel_code}"

    session = create_session()
    session.headers.update({
        "Referer": url
    })

    try:
        res = session.get(
            url,
            timeout=15
        )

        if res.status_code != 200:
            return novel_code

        soup = BeautifulSoup(
            res.text,
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

        return book_title or novel_code

    except Exception:
        return None

    finally:
        session.close()


def fetch_kakuyomu_episode(
    title_path,
    sem,
    ep,
    current_idx,
    trs_path,
    label_callback,
    total_count,
    progress_state,
    printcall=print,
    max_retries=3
):
    with sem:
        # 1. 백업 폴더(outfolder/list/작품명)에 이미 파일이 있는지 확인
        backup_file = None
        prefix = f"[{current_idx}] "
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

                # 포맷: =*30 \n subtitle \n =*30 \n\n\n\n body
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

                # 진행률 갱신
                with progress_state["lock"]:
                    progress_state["done"] += 1
                    done = progress_state["done"]

                progress_percent = round((100 / total_count) * done, 1)
                label_callback(f"{progress_percent}%")

                return True
            except Exception as e:
                printcall(
                    f"카쿠요무 {current_idx}화 기존 백업 읽기 실패 ({e}). 웹에서 새로 다운로드합니다."
                )

        # 3. 백업이 없거나 오류 시 웹에서 직접 다운로드 수행
        delay = base_data.DELAY

        for attempt in range(max_retries):
            session = create_session()
            session.headers.update({
                "Referer": ep["url"]
            })

            try:
                res = session.get(
                    ep["url"],
                    timeout=30
                )

                if res.status_code != 200:
                    raise Exception(
                        f"HTTP status {res.status_code}"
                    )

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
                    subtitle_tag.get_text(
                        strip=True
                    )
                    if subtitle_tag
                    else ep["subtitle"]
                )

                content_element = ep_soup.select_one(
                    ".widget-episodeBody"
                )

                if not content_element:
                    raise Exception(
                        "본문 태그(.widget-episodeBody) 없음"
                    )

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
                body_paragraphs_raw = []

                for p in content_element.find_all("p"):
                    if base_data.EXPORT_TEXT:
                        for br in p.find_all(
                            ["br", "br/"]
                        ):
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
                        r"**\1**",
                        p_text
                    )

                    p_text = re.sub(
                        r"<[^>]+>",
                        "",
                        p_text
                    )

                    p_text = (
                        p_text
                        .lstrip(" \t")
                        .rstrip()
                    )

                    if (
                        p_text
                        or (
                            base_data.EXPORT_TEXT
                            and not p_text
                        )
                    ):
                        p_text = re.sub(
                            r"《《(.+?)》》",
                            r"\1",
                            p_text
                        )

                        body_paragraphs.append(
                            p_text
                        )
                        
                    if (
                        p_text
                        or (
                            not p_text
                        )
                    ):
                        p_text = re.sub(
                            r"《《(.+?)》》",
                            r"\1",
                            p_text
                        )

                        body_paragraphs_raw.append(
                            p_text
                        )

                body = "\n".join(
                    body_paragraphs
                )
                
                body_raw = "\n".join(
                    body_paragraphs_raw
                )

                safe_title = re.sub(
                    r'[\\/:*?"<>|]',
                    "_",
                    subtitle
                )

                file_path = os.path.join(
                    trs_path,
                    f"{current_idx}번_{safe_title}.txt"
                )

                # trs_path 저장
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

                # outfolder/list/작품명/[current_idx] safe_title.txt 백업 저장
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

                time.sleep(delay)

                return True

            except Exception as e:
                printcall(
                    f"카쿠요무 에피소드 다운로드 오류 "
                    f"({ep.get('id', current_idx)}) "
                    f"[시도 {attempt + 1}/{max_retries}]: {e}"
                )

                if attempt < max_retries - 1:
                    time.sleep(
                        delay * 10
                    )
                else:
                    printcall(
                        f"카쿠요무 에피소드 "
                        f"({ep.get('id', current_idx)}) "
                        f"최대 재시도 횟수 초과"
                    )

                    return None

            finally:
                session.close()


def get_kakuyomu_episodes(
    novel_code,
    session,
    html_text
):
    episodes = []

    soup = BeautifulSoup(
        html_text,
        "html.parser"
    )

    next_data_script = soup.find(
        "script",
        id="__NEXT_DATA__"
    )

    if (
        next_data_script
        and next_data_script.string
    ):
        try:
            data = json.loads(
                next_data_script.string
            )

            apollo_state = (
                data
                .get("props", {})
                .get("pageProps", {})
                .get("__APOLLO_STATE__", {})
            )

            seen_ids = set()

            for key, value in apollo_state.items():
                if not isinstance(value, dict):
                    continue

                if not (
                    key.startswith("Episode:")
                    or value.get("__typename") == "Episode"
                ):
                    continue

                ep_id = value.get("id")
                subtitle = value.get(
                    "title",
                    ""
                )

                if not ep_id:
                    continue

                ep_id = str(ep_id)

                if ep_id in seen_ids:
                    continue

                seen_ids.add(ep_id)

                episodes.append({
                    "id": ep_id,
                    "subtitle": subtitle,
                    "url": (
                        f"https://kakuyomu.jp/works/"
                        f"{novel_code}/episodes/{ep_id}"
                    )
                })

        except Exception:
            pass

    if not episodes:
        pattern = (
            r'\{"__typename":"Episode",'
            r'"id":"(\d+)","title":"(.+?)"'
        )

        matches = re.findall(
            pattern,
            html_text
        )

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
                    f"https://kakuyomu.jp/works/"
                    f"{novel_code}/episodes/{ep_id}"
                )
            })

            seen_ids.add(ep_id)

    return episodes


def download_kakuyomu_async(
    novel_code,
    start,
    end,
    trs_path,
    label
):
    total_count = end - start + 1

    url = (
        f"https://kakuyomu.jp/works/"
        f"{novel_code}"
    )

    book_title = novel_code

    progress_state = {
        "done": 0,
        "lock": threading.Lock()
    }

    label_callback = label.setText

    session = create_session()
    session.headers.update({
        "Referer": url
    })

    try:
        res = session.get(
            url,
            timeout=30
        )

        if res.status_code != 200:
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

        episodes = get_kakuyomu_episodes(
            novel_code,
            session,
            html_text
        )

    except Exception as e:
        print(
            f"카쿠요무 목차 가져오기 오류: {e}"
        )

        return novel_code

    finally:
        session.close()

    if not episodes:
        print(
            "카쿠요무 에피소드를 찾지 못했습니다."
        )

        return book_title or novel_code

    # 백업 폴더 경로 생성 (outfolder/list/작품명)
    r_book_title = re.sub(r"^【.*?】", "", book_title)
    r_book_title = re.sub(r"【.*?】$", "", r_book_title)
    r_book_title = re.sub(r'[\\/:*?"<>|]', "_", r_book_title).strip()

    title_path = os.path.join(base_data.OUTFOLDER, "list", r_book_title)
    os.makedirs(title_path, exist_ok=True)

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

    sem = threading.Semaphore(
        base_data.CONCURRENCY_LIMIT
    )

    threads = []

    for idx, ep in enumerate(
        target_episodes
    ):
        current_idx = idx + start

        thread = threading.Thread(
            target=fetch_kakuyomu_episode,
            args=(
                title_path,
                sem,
                ep,
                current_idx,
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

    return book_title or novel_code


def new_kakuyomu(novel_code):
    url = (
        f"https://kakuyomu.jp/works/"
        f"{novel_code}"
    )

    session = create_session()
    session.headers.update({
        "Referer": url
    })

    try:
        res = session.get(
            url,
            timeout=15
        )

        if res.status_code != 200:
            return None

        html_text = res.text

        soup = BeautifulSoup(
            html_text,
            "html.parser"
        )

        next_data_script = soup.find(
            "script",
            id="__NEXT_DATA__"
        )

        if (
            next_data_script
            and next_data_script.string
        ):
            try:
                data = json.loads(
                    next_data_script.string
                )

                apollo_state = (
                    data
                    .get("props", {})
                    .get("pageProps", {})
                    .get("__APOLLO_STATE__", {})
                )

                episodes = [
                    value
                    for key, value in apollo_state.items()
                    if isinstance(value, dict)
                    and (
                        key.startswith("Episode:")
                        or value.get("__typename") == "Episode"
                    )
                ]

                if episodes:
                    unique_ids = {
                        str(ep.get("id"))
                        for ep in episodes
                        if ep.get("id") is not None
                    }

                    if unique_ids:
                        return len(unique_ids)

            except Exception:
                pass

        pattern = (
            r'\{"__typename":"Episode",'
            r'"id":"(\d+)"'
        )

        matches = re.findall(
            pattern,
            html_text
        )

        if matches:
            return len(set(matches))

        ep_links = soup.select(
            "a.widget-toc-episode-episodeTitle"
        )

        return (
            len(ep_links)
            if ep_links
            else None
        )

    except Exception as e:
        print(
            f"카쿠요무 에피소드 수 확인 오류: {e}"
        )

        return None

    finally:
        session.close()