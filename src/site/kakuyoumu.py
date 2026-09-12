import asyncio
import json
import os
import re
import aiohttp
from bs4 import BeautifulSoup

base_data = None #외부 주입용

async def kakuyomu_title(novel_code):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ja,ko-KR;q=0.9,ko;q=0.8,en-US;q=0.7,en;q=0.6"
    }

    url = f"https://kakuyomu.jp/works/{novel_code}"
    headers["Referer"] = url

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as res:
                if res.status != 200:
                    return novel_code

                html = await res.text()
                soup = BeautifulSoup(html, "html.parser")
                full_title = soup.title.string if soup.title else ""
                book_title = re.sub(r'（.+） - カクヨム$', '', full_title).strip()
                return book_title

    except Exception:
        return None


async def fetch_kakuyomu_episode(
    session,
    sem,
    ep,
    current_idx,
    trs_path,
    label_callback,
    total_count,
    progress_state,
    max_retries=3,
):
    async with sem:
        delay = getattr(base_data, "DELAY", 1.0)  # 기본 딜레이 (기본값 1초)

        for attempt in range(max_retries):
            try:
                async with session.get(
                    ep["url"], timeout=aiohttp.ClientTimeout(total=30)
                ) as res:
                    if res.status != 200:
                        raise Exception(f"HTTP status {res.status}")
                    html = await res.text()

                ep_soup = BeautifulSoup(html, "html.parser")

                subtitle_tag = ep_soup.select_one(
                    ".widget-episodeTitle"
                ) or ep_soup.find("h1")
                subtitle = (
                    subtitle_tag.get_text(strip=True)
                    if subtitle_tag
                    else ep["subtitle"]
                )

                content_element = ep_soup.select_one(".widget-episodeBody")
                if not content_element:
                    raise Exception("본문 태그(.widget-episodeBody) 없음")

                for tag in content_element.find_all(["rt", "rp"]):
                    tag.decompose()

                for ruby in content_element.find_all("ruby"):
                    ruby.replace_with(ruby.get_text(strip=True))

                body_paragraphs = []

                for p in content_element.find_all("p"):
                    if base_data.EXPORT_TEXT:
                        for br in p.find_all(["br", "br/"]):
                            br.replace_with("\n")

                    p_text = p.decode_contents()
                    p_text = p_text.replace("<span>", "").replace(
                        "</span>", ""
                    )
                    p_text = re.sub(
                        r'<em class="emphasisDots">(.*?)</em>',
                        r"**\1**",
                        p_text,
                    )
                    p_text = re.sub(r"<[^>]+>", "", p_text)
                    p_text = p_text.lstrip(" \t").rstrip()

                    if p_text or (base_data.EXPORT_TEXT and not p_text):
                        p_text = re.sub(r"《《(.+?)》》", r"\1", p_text)
                        body_paragraphs.append(p_text)

                body = "\n".join(body_paragraphs)

                safe_title = re.sub(r'[\\/:*?"<>|]', "_", subtitle)
                file_path = os.path.join(
                    trs_path, f"{current_idx}번_{safe_title}.txt"
                )

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(subtitle + "\n\n" + body + "\n\n")

                progress_state["done"] += 1
                progress_percent = round(
                    (100 / total_count) * progress_state["done"], 1
                )
                label_callback(f"{progress_percent}%")

                # 성공 시 기본 딜레이 대기
                await asyncio.sleep(delay)
                return True

            except Exception as e:
                print(
                    f"카쿠요무 에피소드 다운로드 오류 ({ep['id']}) [시도 {attempt + 1}/{max_retries}]: {e}"
                )

                if attempt < max_retries - 1:
                    # 에러 시 10배 딜레이 대기 후 재시도
                    await asyncio.sleep(delay * 10)
                else:
                    print(
                        f"카쿠요무 에피소드 ({ep['id']}) 최대 재시도 횟수 초과"
                    )
                    return None


async def download_kakuyomu_async(novel_code, start, end, trs_path, label):
    total_count = end - start + 1
    url = f"https://kakuyomu.jp/works/{novel_code}"

    req_headers = {
        **base_data.HEADERS,
        "Referer": url
    }

    sem = asyncio.Semaphore(base_data.CONCURRENCY_LIMIT)
    progress_state = {"done": 0}
    label_callback = label.setText

    async with aiohttp.ClientSession(headers=req_headers) as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as res:
                if res.status != 200:
                    return novel_code
                html_text = await res.text()

            soup = BeautifulSoup(html_text, "html.parser")
            full_title = soup.title.string if soup.title else ""
            book_title = re.sub(r'（.+） - カクヨム$', '', full_title).strip()

            episodes = []

            next_data_script = soup.find("script", id="__NEXT_DATA__")
            if next_data_script and next_data_script.string:
                try:
                    data = json.loads(next_data_script.string)
                    apollo_state = data.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
                    
                    for k, v in apollo_state.items():
                        if k.startswith("Episode:") or v.get("__typename") == "Episode":
                            ep_id = v.get("id")
                            subtitle = v.get("title", "")
                            if ep_id:
                                episodes.append({
                                    "id": str(ep_id),
                                    "subtitle": subtitle,
                                    "url": f"https://kakuyomu.jp/works/{novel_code}/episodes/{ep_id}"
                                })
                except Exception:
                    pass

            if not episodes:
                pattern = r'\{"__typename":"Episode","id":"(\d+)","title":"(.+?)"'
                matches = re.findall(pattern, html_text)
                seen_ids = set()

                for ep_id, ep_title in matches:
                    if ep_id in seen_ids:
                        continue
                    try:
                        decoded_title = json.loads(f'"{ep_title}"')
                    except Exception:
                        decoded_title = ep_title

                    episodes.append({
                        "id": ep_id,
                        "subtitle": decoded_title,
                        "url": f"https://kakuyomu.jp/works/{novel_code}/episodes/{ep_id}"
                    })
                    seen_ids.add(ep_id)

        except Exception as e:
            print(f"카쿠요무 목차 가져오기 오류: {e}")
            return novel_code

        start_idx = max(0, start - 1)
        end_idx = min(len(episodes), end)
        target_episodes = episodes[start_idx:end_idx]

        tasks = [
            fetch_kakuyomu_episode(
                session,
                sem,
                ep,
                idx + start,
                trs_path,
                label_callback,
                total_count,
                progress_state
            )
            for idx, ep in enumerate(target_episodes)
        ]

        await asyncio.gather(*tasks)

    return book_title


async def new_kakuyomu(novel_code):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,ko-KR;q=0.9,ko;q=0.8,en-US;q=0.7,en;q=0.6"
    }

    url = f"https://kakuyomu.jp/works/{novel_code}"
    headers["Referer"] = url

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as res:
                if res.status != 200:
                    return None
                html_text = await res.text()

            soup = BeautifulSoup(html_text, "html.parser")

            next_data_script = soup.find("script", id="__NEXT_DATA__")
            if next_data_script and next_data_script.string:
                data = json.loads(next_data_script.string)
                apollo_state = data.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
                episodes = [
                    v for k, v in apollo_state.items()
                    if k.startswith("Episode:") or v.get("__typename") == "Episode"
                ]
                if episodes:
                    return len(episodes)

            pattern = r'\{"__typename":"Episode","id":"(\d+)"'
            matches = re.findall(pattern, html_text)
            if matches:
                return len(matches)

            ep_links = soup.select("a.widget-toc-episode-episodeTitle")
            return len(ep_links) if ep_links else None

    except Exception as e:
        print(f"카쿠요무 에피소드 수 확인 오류: {e}")
        return None