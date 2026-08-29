import json
import os
import sys

from config import DATA_FILE
from get import *

import theme

THEME_DATA = {
    "다크": "DARK",
    "라이트": "LIGHT",
    "블루": "BLUE",
    "퍼플": "PURPLE",
    "시안": "CYAN",
    "그린": "GREEN",
    "레드": "RED",
    "오렌지": "ORANGE",
    "핑크": "PINK",
    "옐로우": "YELLOW",
    "앰버": "AMBER",
    "틸": "TEAL",
    "인디고": "INDIGO",
    "슬레이트": "SLATE",
    "모노": "MONO",
    "OLED": "OLED",
}

THEME_NAME = "DARK"

MINIMAL_DARK_THEME = ""

def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def rest():
    global THEME_NAME, MINIMAL_DARK_THEME  

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                THEME_NAME = json.load(f).get("theme", "DARK")
        except Exception:
            pass

    
    css_file_path = get_resource_path(f"css/main.css")

    try:
        with open(css_file_path, "r", encoding="UTF-8") as f:
            MINIMAL_DARK_THEME = f.read().replace("{", "([(").replace("}", ")])").replace("||","}").replace("|", "{").format(**theme.THEMES[THEME_NAME]).replace("([(", "{").replace(")])", "}")
    except FileNotFoundError:
        print(f"CSS 파일을 찾을 수 없습니다: {css_file_path}")

rest()