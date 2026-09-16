import ctypes
import json
import os
import time
from DrissionPage import ChromiumOptions, ChromiumPage

SRC = "session_info.json"
TARGET_URL = "https://syosetu.org"

CLEAN_UI_JS = """
(function() {
    if (document.getElementById('cf-clean-style')) return;
    const style = document.createElement('style');
    style.id = 'cf-clean-style';
    style.innerHTML = `
        html, body {
            width: 100% !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            overflow: hidden !important;
            background-color: #f8fafc !important;
        }
        h1, h2, h3, p, footer, #footer, .footer, 
        .attribution, #cf-error-details, .cf-subheadline,
        #cf-content, #cf-wrapper > div:not(#challenge-stage) {
            display: none !important;
        }
        #challenge-stage, #challenge-form, [id*="cf-stage"], [id*="turnstile"] {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            margin: 0 !important;
            padding: 0 !important;
        }
    `;
    document.head.appendChild(style);
})();
"""


def get_center_position(width=380, height=180):
    try:
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
    except Exception:
        screen_w, screen_h = 1920, 1080

    pos_x = max(0, (screen_w - width) // 2)
    pos_y = max(0, (screen_h - height) // 2)
    return pos_x, pos_y


def find_cf():
    if os.path.exists(SRC):
        try:
            os.remove(SRC)
            print(f"[*] 이전 '{SRC}' 파일을 삭제했습니다.")
        except Exception:
            pass

    win_w, win_h = 380, 180
    pos_x, pos_y = get_center_position(win_w, win_h)

    co = ChromiumOptions()
    co.set_argument(f"--app={TARGET_URL}")
    co.set_argument(f"--window-size={win_w},{win_h}")
    co.set_argument(f"--window-position={pos_x},{pos_y}")

    page = ChromiumPage(co)

    try:
        page.set.cookies.clear()
    except Exception:
        pass

    try:
        page.run_cdp("Network.clearBrowserCookies")
        page.run_cdp("Network.clearBrowserCache")
    except Exception:
        pass

    print("[*] 기존 브라우저 쿠키를 모두 삭제했습니다.")

    page.get(TARGET_URL)
    print(f"[*] 화면 정중앙({pos_x}, {pos_y})에 확인 창이 열렸습니다. 버튼을 클릭해주세요...")

    cf_cookie = None

    while True:
        try:
            page.run_js(CLEAN_UI_JS)

            raw_cookies = page.cookies()

            if isinstance(raw_cookies, dict):
                if "cf_clearance" in raw_cookies:
                    cf_cookie = {
                        "name": "cf_clearance",
                        "value": raw_cookies["cf_clearance"],
                        "domain": ".syosetu.org",
                        "path": "/",
                    }
            elif isinstance(raw_cookies, list):
                for c in raw_cookies:
                    if isinstance(c, dict) and c.get("name") == "cf_clearance":
                        cf_cookie = c
                        break
                    elif hasattr(c, "name") and c.name == "cf_clearance":
                        cf_cookie = {
                            "name": c.name,
                            "value": c.value,
                            "domain": getattr(c, "domain", ".syosetu.org"),
                            "path": getattr(c, "path", "/"),
                        }
                        break

            if cf_cookie:
                print(f"[+] 새 cf_clearance 획득: {cf_cookie['value'][:15]}...")
                break

        except Exception:
            pass

        time.sleep(0.5)

    try:
        user_agent = page.user_agent
    except Exception:
        user_agent = page.run_js("return navigator.userAgent;")

    page.quit()

    session_data = {
        "browser": "drission_page",
        "url": TARGET_URL,
        "headers": {
            "User-Agent": user_agent,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://syosetu.org/",
        },
        "cf_clearance": cf_cookie,
    }

    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=4)

    print(f"[+] '{SRC}' 저장 완료! 세션이 준비되었습니다.")