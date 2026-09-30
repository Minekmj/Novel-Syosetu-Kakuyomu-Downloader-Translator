import os
import json
import src.find.state as sf

COOKIES = {}
BASE_HEADERS = {}

COOKIES_H = {}
BASE_HEADERS_H = {}


def load_headers(data):
    if isinstance(data, dict) and "headers" in data and isinstance(data["headers"], dict):
        return {str(k): str(v) for k, v in data["headers"].items() if isinstance(v, (str, bytes, int, float))}
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items() if isinstance(v, (str, bytes, int, float))}
    return {}


def load_cookies(data):
    if isinstance(data, dict) and "cookies" in data and isinstance(data["cookies"], dict):
        return {str(k): str(v) for k, v in data["cookies"].items() if isinstance(v, (str, bytes, int, float))}
    return {}


def reset(b):
    if b:
        sf.find_cf()
    global COOKIES, BASE_HEADERS
    if os.path.exists(sf.SRC):
        try:
            with open(sf.SRC, "r", encoding="UTF-8") as f:
                g = json.load(f)
                BASE_HEADERS = load_headers(g)
                if "cf_clearance" in g and isinstance(g["cf_clearance"], dict):
                    COOKIES = {"cf_clearance": g["cf_clearance"].get("value", "")}
                elif "cookies" in g and isinstance(g["cookies"], dict):
                    COOKIES = load_cookies(g)
                else:
                    COOKIES = {}
        except Exception as e:
            print(f"[!] reset 로드 실패: {e}")


def reset_b():
    reset(False)


def reset_H(b):
    if b:
        sf.find_cf_header()
    global BASE_HEADERS_H, COOKIES_H
    if os.path.exists(sf.SRC_H):
        try:
            with open(sf.SRC_H, "r", encoding="UTF-8") as f:
                g = json.load(f)
                BASE_HEADERS_H = load_headers(g)
                COOKIES_H = load_cookies(g)
        except Exception as e:
            print(f"[!] reset_H 로드 실패: {e}")


def reset_b_H():
    reset_H(False)


# 초기 로드 실행
reset(False)
reset_H(False)