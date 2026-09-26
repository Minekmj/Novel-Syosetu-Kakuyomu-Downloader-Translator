import json
import os

from src.system.config import DATA_FILE
from src.find.get import *

import re

import src.system.theme as theme
import src.system.theme_back as theme_back
from src.system.load_save import load_data, save_data

from PySide6.QtGui import QColor

THEME_DATA = {**theme_back.THEME_DATA, **theme.THEME_DATA}

THEME_NAME = "LAVENDER"

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
                THEME_NAME = json.load(f).get("theme", "LAVENDER")
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
                THEME_NAME = "LAVENDER"
                if THEME_NAME in theme.THEMES:
                    MINIMAL_DARK_THEME = build_qss(f.read(), theme.THEMES[THEME_NAME])
        with open(css_file_path_back, "r", encoding="UTF-8") as f:
            try:
                if THEME_NAME in theme_back.THEMES:
                    MINIMAL_DARK_THEME = build_qss(f.read(), theme_back.THEMES[THEME_NAME])
            except:
                THEME_NAME = "CYAN"
                if THEME_NAME in theme_back.THEMES:
                    MINIMAL_DARK_THEME = build_qss(f.read(), theme_back.THEMES[THEME_NAME])
                    
        raw_color = get_item_background_color("CardFrame_ui", MINIMAL_DARK_THEME)
                
        def replace_color_to_rgba(match):
            hex_code = match.group(0)
            color = QColor(hex_code)
            r, g, b = color.red(), color.green(), color.blue()
            return f"rgba({r}, {g}, {b}, 0.4)"

        transparent_gradient = re.sub(r'#[0-9a-fA-F]{6}', replace_color_to_rgba, raw_color)
        
        MINIMAL_DARK_THEME = change_item_background_color("CardFrame_ui", MINIMAL_DARK_THEME, transparent_gradient)

    except FileNotFoundError:
        print(f"CSS 파일을 찾을 수 없습니다: {css_file_path}")
        
def return_theme():
    th = "#000000"
    if THEME_NAME in theme.THEMES:
        th = getattr(theme, f"COLORS_{THEME_NAME.replace(' ', '_')}", "#000000")
    else:
        th = getattr(theme_back, f"COLORS_{THEME_NAME}", "#000000")
    return th

def get_item_background_color(item, MINIMAL_DARK_THEME):
    th = str(MINIMAL_DARK_THEME)
    data = th[th.find(item):]
    return re.search(r'background-color\s*:\s*([^;]+);', data).group(1).strip()

def change_item_background_color(item, MINIMAL_DARK_THEME, new_color):
    th = str(MINIMAL_DARK_THEME)
    
    item_index = th.find(item)
    if item_index == -1:
        return th
    
    prefix = th[:item_index]
    target_data = th[item_index:]
    
    updated_data = re.sub(
        r'(background-color\s*:\s*)[^;]+(;)',
        rf'\g<1>{new_color}\2',
        target_data,
        count=1
    )
    
    return prefix + updated_data

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