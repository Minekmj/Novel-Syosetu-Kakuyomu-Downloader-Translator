import os
import re
import shutil
from src.system.data import load_data
from src.trans.trans import Translator
from .base import SiteRegistry
from .utils import clean_raw_title

base_data = None  # 외부 주입용
create_merged_txt = None  # 외부 주입용

def Fs(f):
    return f

def set_base_data(data, void):
    global base_data
    base_data = data
    global create_merged_txt
    create_merged_txt = void
    SiteRegistry.set_base_data(data)

def parse_site_info(site):
    handler, clean_site = SiteRegistry.resolve(site)
    return clean_site, handler.site_name

def CheckTitle(site):
    handler, clean_site = SiteRegistry.resolve(site)
    title = Fs(handler.get_title(clean_site))
    title_ko = Translator(title, True)
    return title_ko

def CheckTitle_Raw(site):
    handler, clean_site = SiteRegistry.resolve(site)
    title = Fs(handler.get_title(clean_site))
    return clean_raw_title(title)

def Download(
    site,
    start,
    end,
    label,
    title,
    raw_title,
    act_massage=""
):
    start = int(start)
    end = int(end)

    handler, clean_site = SiteRegistry.resolve(site)

    safe_folder_name = re.sub(r'[\\/:*?"<>|.]', '_', clean_site)
    trs_path = f"./temp_trs_{handler.site_name}_{safe_folder_name}"
    os.makedirs(trs_path, exist_ok=True)

    book_title = Fs(handler.download(
        clean_site,
        start,
        end,
        trs_path,
        label,
        raw_title,
        act_massage
    ))

    data = f"{start} ~ {end}"
    if start == end:
        data = start

    if load_data().get("origin_name", False):
        book_title = f"{book_title} | {data}"
    else:
        book_title = f"{title} | {data}"

    clean_title = re.sub(r'[\\/:*?"<>|]', '_', book_title)

    outfolder = os.environ.get("minedown_setting_src", "./out/")
    if not os.path.exists(outfolder):
        os.makedirs(outfolder, exist_ok=True)

    create_merged_txt(
        trs_path,
        f"{outfolder}/{clean_title}.txt",
        book_title
    )

    shutil.rmtree(trs_path, ignore_errors=True)

def new_number(site, have=False):
    handler, clean_site = SiteRegistry.resolve(site)
    return Fs(handler.get_new_number(clean_site, have))

def number_average(site):
    handler, clean_site = SiteRegistry.resolve(site)
    new = Fs(handler.get_number_average(clean_site))
    if new is not None:
        return new
    else:
        return (None, None, None, None)