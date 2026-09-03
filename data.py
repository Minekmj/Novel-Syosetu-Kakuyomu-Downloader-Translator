import json
import os
import sys

from config import DATA_FILE
from get import *

import re

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

THEME_NAME = "CYAN"

MINIMAL_DARK_THEME = ""

def build_qss(template_qss: str, theme_dict: dict) -> str:
    def replace_var(match):
        key = match.group(1).strip()
        val = theme_dict.get(key, "")
        
        if val is None:
            return ""
        
        if key.startswith("dv_") and val and not val.strip().endswith(";"):
            return f"{val.strip()};"
        
        return str(val)

    pattern = re.compile(r"\|([a-zA-Z0-9_]+)\|\|")
    rendered_qss = pattern.sub(replace_var, template_qss)
    
    lines = [line for line in rendered_qss.splitlines() if line.strip() != ""]
    return "\n".join(lines)

def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def rest():
    global THEME_NAME, MINIMAL_DARK_THEME  

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                THEME_NAME = json.load(f).get("theme", "CYAN")
        except Exception:
            pass

    
    css_file_path = get_resource_path(f"css/main.css")

    try:
        with open(css_file_path, "r", encoding="UTF-8") as f:
            MINIMAL_DARK_THEME = build_qss(f.read(), theme.THEMES[THEME_NAME])
    except FileNotFoundError:
        print(f"CSS 파일을 찾을 수 없습니다: {css_file_path}")
        
def return_theme():
    th = "#000000"
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                th = getattr(theme, f"COLORS_{json.load(f).get('theme', 'CYAN')}", "#000000")
        except Exception:
            pass
    return th

import platform
import subprocess
def open_folder(path):
    
    if path == "./out/":
        path = os.path.join(os.getcwd(), "out")
    
    if not path or not os.path.exists(path):
        return
    
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    except Exception as e:
        print(f"폴더 열기 실패: {e}")
        
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"src": "", "list": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"데이터 저장 실패: {e}")