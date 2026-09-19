import os
import re
import shutil
from src.system.data import load_data

def Fs(f):
    return f

import src.site.kakuyoumu as kaku
import src.site.narow as naru
import src.site.hameln as hame

site_list = [kaku, naru, hame]

from src.trans.trans import Translator

base_data = None  # 외부 주입용
create_merged_txt = None  # 외부 주입용


def set_base_data(data, void):
    for i in site_list:
        i.base_data = data
        
    global base_data
    base_data = data
    
    global create_merged_txt
    create_merged_txt = void


def parse_site_info(site):
    site_str = str(site).strip()

    if "syosetu.org" in site_str or "h.syosetu.org" in site_str:
        is_r18 = "h.syosetu.org" in site_str
        match = re.search(r'/novel/(\d+)', site_str)
        nid = match.group(1) if match else site_str.strip("/").split("/")[-1]
        clean_site = f"h.{nid}" if is_r18 else nid
        return clean_site, "hameln"

    elif site_str.startswith("h.") or site_str.startswith("h_"):
        return site_str, "hameln"

    elif "kakuyomu.jp" in site_str:
        clean_site = site_str.strip("/").split("/")[-1]
        return clean_site, "kakuyomu"

    elif "syosetu.com" in site_str:
        clean_site = site_str.strip("/").split("/")[-1]
        return clean_site, "syosetu"

    elif site_str.isdigit():
        return site_str, "kakuyomu"

    return site_str, "syosetu"


def CheckTitle(site):
    clean_site, site_type = parse_site_info(site)

    if site_type == "hameln":
        title = Fs(hame.hameln_title(clean_site))
    elif site_type == "kakuyomu":
        title = Fs(kaku.kakuyomu_title(clean_site))
    else:
        title = Fs(naru.syosetu_title(clean_site))

    title_ko = Translator(title, True)
    return title_ko


def Download(
    site,
    start,
    end,
    label,
    title
):
    start = int(start)
    end = int(end)

    clean_site, site_type = parse_site_info(site)

    safe_folder_name = re.sub(r'[\\/:*?"<>|.]', '_', clean_site)
    trs_path = f"./temp_trs_{site_type}_{safe_folder_name}"

    os.makedirs(trs_path, exist_ok=True)

    if site_type == "hameln":
        book_title = Fs(hame.download_hameln_async(
            clean_site,
            start,
            end,
            trs_path,
            label
        ))
    elif site_type == "kakuyomu":
        book_title = Fs(kaku.download_kakuyomu_async(
            clean_site,
            start,
            end,
            trs_path,
            label
        ))
    else:
        book_title = Fs(naru.download_syosetu_async(
            clean_site,
            start,
            end,
            trs_path,
            label
        ))

    data = f"{start} ~ {end}"
    if start == end:
        data = start

    if load_data().get("origin_name", False):
        book_title = f"{book_title} | {data}"
    else:
        book_title = f"{title} | {data}"

    clean_title = re.sub(
        r'[\\/:*?"<>|]',
        '_',
        book_title
    )

    if not os.path.exists(base_data.OUTFOLDER):
        os.makedirs(base_data.OUTFOLDER, exist_ok=True)

    create_merged_txt(
        trs_path,
        f"{base_data.OUTFOLDER}/{clean_title}.txt",
        book_title
    )

    shutil.rmtree(
        trs_path,
        ignore_errors=True
    )


def new_number(site, have=False):
    clean_site, site_type = parse_site_info(site)

    if site_type == "hameln":
        new = Fs(hame.new_hameln(clean_site, have))
    elif site_type == "kakuyomu":
        new = Fs(kaku.new_kakuyomu(clean_site, have))
    else:
        new = Fs(naru.new_syosetu(clean_site, have))

    return new