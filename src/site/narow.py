import asyncio
import os
import re
import secrets
import string
from bs4 import BeautifulSoup
import aiohttp

base_data = None #외부 주입용

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
        rand_name = "".join(secrets.choice(chars) for _ in range(16))
        filename = f"{rand_name}{ext}"
        full_path = os.path.join(img_dir, filename)
        if not os.path.exists(full_path):
            return filename, full_path

async def syosetu_title(novel_code):
    url = f"https://ncode.syosetu.com/{novel_code}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # SSL 검증 비활성화 커넥터 생성
    connector = aiohttp.TCPConnector(ssl=False)

    try:
        async with aiohttp.ClientSession(headers=headers, connector=connector, cookies={"over18": "yes"}) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as res:
                if res.status == 200:
                    html = await res.text()
                    soup = BeautifulSoup(html, "html.parser")
                    t = soup.find("p", class_="p-novel__title") or soup.find("h1")
                    if t:
                        return t.get_text(strip=True)
                return None
    except Exception:
        return None


async def fetch_syosetu_episode(
    session,
    sem,
    url,
    ep_num,
    trs_path,
    label_callback,
    total_count,
    progress_state,
    printcall,
    max_retries=3,
):
    async with sem:
        delay = base_data.DELAY

        for attempt in range(max_retries):
            try:
                episode_url = f"{url}{ep_num}/"

                async with session.get(
                    episode_url,
                    timeout=aiohttp.ClientTimeout(total=30),
                    ssl=False,
                ) as res:
                    if res.status != 200:
                        episode_url = f"{url}"
                        async with session.get(
                            episode_url,
                            timeout=aiohttp.ClientTimeout(total=30),
                            ssl=False,
                        ) as res_fallback:
                            if res_fallback.status != 200:
                                raise Exception(
                                    f"HTTP {res_fallback.status} 에러"
                                )
                            html = await res_fallback.text()
                            soup = BeautifulSoup(html, "html.parser")
                            title_tag = soup.find(
                                "h1", class_="p-novel__title"
                            )
                            body_tag = soup.find(
                                "div", class_="js-novel-text p-novel__text"
                            )
                    else:
                        html = await res.text()
                        soup = BeautifulSoup(html, "html.parser")
                        title_tag = soup.find(
                            "h1", class_="p-novel__title p-novel__title--rensai"
                        )
                        body_tag = soup.find(
                            "div", class_="js-novel-text p-novel__text"
                        )

                if not title_tag or not body_tag:
                    raise Exception("파싱 실패 (title_tag 또는 body_tag 없음)")

                title = title_tag.get_text(strip=True)

                # 이미지 다운로드 처리
                img_tags = body_tag.find_all("img")
                has_downloaded_img = False

                if img_tags:
                    img_dir = os.path.join(base_data.OUTFOLDER, "img")
                    os.makedirs(img_dir, exist_ok=True)

                    for img in img_tags:
                        src = img.get("src")
                        if not src:
                            img.decompose()
                            continue

                        full_img_url = urljoin(episode_url, src)
                        ext = os.path.splitext(full_img_url.split("?")[0])[1]
                        if not ext or len(ext) > 5:
                            ext = ".jpg"

                        filename, file_save_path = generate_random_filename(
                            img_dir, ext
                        )

                        try:
                            async with session.get(
                                full_img_url,
                                timeout=aiohttp.ClientTimeout(total=30),
                                ssl=False,
                            ) as img_res:
                                if img_res.status == 200:
                                    img_bytes = await img_res.read()
                                    with open(file_save_path, "wb") as f_img:
                                        f_img.write(img_bytes)
                                    img.replace_with(f"-img-:{filename}")
                                    has_downloaded_img = True
                                else:
                                    img.decompose()
                        except Exception as err:
                            printcall(
                                f"Syosetu {ep_num}화 이미지 다운로드 실패 ({full_img_url}): {err}"
                            )
                            img.decompose()

                # 루비 및 태그 정리
                for tag in body_tag.find_all(["rp", "rt"]):
                    tag.decompose()

                for ruby in body_tag.find_all("ruby"):
                    ruby.replace_with(ruby.get_text(strip=True))

                if base_data.EXPORT_TEXT:
                    for br in body_tag.find_all(["br", "br/"]):
                        br.replace_with("\n")

                body = "\n".join(
                    [
                        p.get_text(" ", strip=True)
                        for p in body_tag.find_all("p")
                        if p.get_text(strip=True)
                        or (
                            base_data.EXPORT_TEXT
                            and not p.get_text(strip=True)
                        )
                    ]
                )

                safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)
                file_path = os.path.join(trs_path, f"{ep_num}번_{safe_title}.txt")

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(title + "\n\n" + body + "\n\n")

                progress_state["done"] += 1
                progress_percent = round(
                    (100 / total_count) * progress_state["done"], 1
                )
                label_callback(f"{progress_percent}%")

                # 대기 시간 계산: 이미지를 다운로드했으면 5배, 아니면 기본 딜레이
                wait_time = delay * 5 if has_downloaded_img else delay
                await asyncio.sleep(wait_time)

                return True

            except Exception as e:
                printcall(
                    f"Syosetu {ep_num}화 다운로드 오류 (시도 {attempt + 1}/{max_retries}): {e}"
                )

                if attempt < max_retries - 1:
                    # 에러 시 원래 딜레이의 10배 대기 후 재시도
                    await asyncio.sleep(delay * 10)
                else:
                    printcall(
                        f"Syosetu {ep_num}화 최대 재시도 횟수 초과로 실패"
                    )
                    return None


async def download_syosetu_async(novel_code, start, end, trs_path, label):
    total_count = end - start + 1
    url = f"https://ncode.syosetu.com/{novel_code}/"
    book_title = novel_code

    sem = asyncio.Semaphore(base_data.CONCURRENCY_LIMIT)
    progress_state = {"done": 0}
    label_callback = label.setText

    # SSL 검증 비활성화 커넥터 적용
    connector = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(headers=base_data.HEADERS, connector=connector, cookies={"over18": "yes"}) as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), ssl=False) as res:
                if res.status == 200:
                    html = await res.text()
                    soup = BeautifulSoup(html, "html.parser")
                    t = soup.find("p", class_="p-novel__title") or soup.find("h1")
                    if t:
                        book_title = t.get_text(strip=True)
        except Exception:
            pass

        tasks = [
            fetch_syosetu_episode(
                session,
                sem,
                url,
                i,
                trs_path,
                label_callback,
                total_count,
                progress_state,
                print
            )
            for i in range(start, end + 1)
        ]

        await asyncio.gather(*tasks)

    return book_title


async def new_syosetu(novel_code):
    url = f"https://ncode.syosetu.com/{novel_code}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # SSL 검증 비활성화 커넥터 적용
    connector = aiohttp.TCPConnector(ssl=False)

    try:
        async with aiohttp.ClientSession(headers=headers, connector=connector, cookies={"over18": "yes"}) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), ssl=False) as res:
                if res.status != 200:
                    return None
                html = await res.text()

            soup = BeautifulSoup(html, "html.parser")
            next_page = soup.find("a", class_="c-pager__item c-pager__item--last")

            u = 1
            if next_page:
                t = next_page["href"]
                u = int(t[t.find("=") + 1:])
            else:
                urlp = f"{url}1"
                async with session.get(urlp, timeout=aiohttp.ClientTimeout(total=15), ssl=False) as res_check:
                    if res_check.status != 200:
                        return 1

            async with session.get(f"{url}/?p={u}", timeout=aiohttp.ClientTimeout(total=15), ssl=False) as res_last:
                if res_last.status != 200:
                    return None
                html_last = await res_last.text()

            soup = BeautifulSoup(html_last, "html.parser")
            body_tag = soup.find("div", class_="p-eplist")

            if not body_tag:
                return None

            t = body_tag.find_all("a", class_="p-eplist__subtitle")[-1]["href"]
            match = re.search(r"/(\d+)/", t)

            return int(match.group(1)) if match else None

    except Exception as e:
        print(f"오류: {e}")

    return None