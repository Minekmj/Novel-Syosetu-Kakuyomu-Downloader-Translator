import os
import re
import shutil

import src.site.kakuyoumu as kaku
import src.site.narow as naru

site_list = [kaku, naru]

from src.trans.trans import Translator

base_data = None #외부 주입용
create_merged_txt = None #외부 주입용

def set_base_data(data, void):
    for i in site_list:
        i.base_data = data
        
    global base_data
    base_data = data
    
    global create_merged_txt
    create_merged_txt = void

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
        title = kaku.kakuyomu_title(site)
    else:
        title = naru.syosetu_title(site)

    title_ko = Translator(title)

    return title_ko

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
        book_title = kaku.download_kakuyomu_async(
            site,
            start,
            end,
            trs_path,
            label
        )
    else:
        book_title = naru.download_syosetu_async(
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
        base_data.OUTFOLDER
    ):
        os.makedirs(
            base_data.OUTFOLDER,
            exist_ok=True
        )

    create_merged_txt(
        trs_path,
        f"{base_data.OUTFOLDER}/{clean_title}.txt",
        book_title
    )

    shutil.rmtree(
        trs_path,
        ignore_errors=True
    )

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
        new = kaku.new_kakuyomu(site)
    else:
        new = naru.new_syosetu(site)

    return new