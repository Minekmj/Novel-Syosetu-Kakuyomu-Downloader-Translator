import json
import os

from src.system.config import DATA_FILE
from src.find.get import *

import re

import src.system.theme as theme
import src.system.theme_back as theme_back

THEME_DATA = {**theme_back.THEME_DATA, **theme.THEME_DATA}

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

from src.system.src import get_resource_path

def rest():
    global THEME_NAME, MINIMAL_DARK_THEME  

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                THEME_NAME = json.load(f).get("theme", "CYAN")
        except Exception:
            pass

    
    css_file_path = get_resource_path(f"css/main.css")
    css_file_path_back = get_resource_path(f"css/main_back.css")

    try:
        with open(css_file_path, "r", encoding="UTF-8") as f:
            try:
                if THEME_NAME in theme.THEMES:
                    MINIMAL_DARK_THEME = build_qss(f.read(), theme.THEMES[THEME_NAME])
            except:
                THEME_NAME = "CYAN"
                if THEME_NAME in theme.THEMES:
                    MINIMAL_DARK_THEME = build_qss(f.read(), theme.THEMES[THEME_NAME])
        with open(css_file_path_back, "r", encoding="UTF-8") as f:
            try:
                if THEME_NAME in theme_back.THEMES:
                    MINIMAL_DARK_THEME = build_qss(f.read(), theme_back.THEMES[THEME_NAME])
            except:
                THEME_NAME = "NEW CYAN"
                if THEME_NAME in theme_back.THEMES:
                    MINIMAL_DARK_THEME = build_qss(f.read(), theme_back.THEMES[THEME_NAME])
    except FileNotFoundError:
        print(f"CSS 파일을 찾을 수 없습니다: {css_file_path}")
        
def return_theme():
    th = "#000000"
    th = getattr(theme, f"COLORS_{THEME_NAME}", "#000000")
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