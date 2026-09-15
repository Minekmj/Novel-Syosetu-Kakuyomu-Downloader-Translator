import json
import os
import re
import subprocess
import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
import undetected_chromedriver as uc

SRC = "session_info.json"

_orig_quit = uc.Chrome.quit


def _safe_quit(self):
    try:
        _orig_quit(self)
    except Exception:
        pass


uc.Chrome.quit = _safe_quit
uc.Chrome.__del__ = lambda self: None


def get_chrome_version():
    cmds = [
        r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version',
        r'reg query "HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Google\Update\Clients\{8A69D345-D564-463c-AFF1-A69D9E530F96}" /v pv',
    ]
    for cmd in cmds:
        try:
            output = subprocess.check_output(cmd, shell=True).decode(
                "utf-8", errors="ignore"
            )
            match = re.search(r"(?:version|pv)\s+REG_SZ\s+(\d+)\.", output)
            if match:
                return int(match.group(1))
        except Exception:
            pass
    return None


def wait_for_challenge_completion(driver, timeout=60):
    print(f"[*] 봇 통과 감지 중... (최대 {timeout}초 대기)")
    print(
        "[!] (자동 통과되지 않고 체크박스가 멈춰 있다면 직접 마우스로 눌러주세요)"
    )

    start_time = time.time()
    cf_keywords = ["Just a moment", "보안 확인", "セキュリティ", "Cloudflare"]

    while time.time() - start_time < timeout:
        try:
            cookies = driver.get_cookies()
            cf_cookie = next(
                (c for c in cookies if c.get("name") == "cf_clearance"), None
            )
            title = driver.title.strip()
            is_cf_page = any(kw in title for kw in cf_keywords) or not title

            if cf_cookie and not is_cf_page:
                print(f"[+] 봇 통과 확인! (현재 페이지 제목: {title})")
                time.sleep(1.5)
                return cf_cookie
        except Exception:
            pass

        time.sleep(1)

    print("[-] 대기 시간 초과: 봇 체크를 통과하지 못했습니다.")
    return None


def init_driver(browser_type="auto"):
    browser_type = browser_type.lower()

    if browser_type in ["auto", "chrome"]:
        print("[*] Chrome 드라이버 초기화 시도 중...")
        chrome_version = get_chrome_version()
        if chrome_version:
            print(f"[*] 감지된 Chrome 메이저 버전: {chrome_version}")

        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.page_load_strategy = "eager"
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        try:
            if chrome_version:
                driver = uc.Chrome(options=options, version_main=chrome_version)
            else:
                driver = uc.Chrome(options=options)
            return driver, "chrome"
        except Exception as e:
            if browser_type == "auto":
                print(f"[-] Chrome 실행 실패 ({e}). Edge로 자동 전환합니다.")
            else:
                raise e

    if browser_type in ["auto", "edge"]:
        print("[*] Edge 드라이버 초기화 중...")
        options = EdgeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.set_capability("ms:loggingPrefs", {"performance": "ALL"})

        driver = webdriver.Edge(options=options)
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
            },
        )
        return driver, "edge"

    raise ValueError(f"지원하지 않는 브라우저입니다: {browser_type}")


def get_cookies_and_headers(browser="auto"):
    url = "https://syosetu.org"
    driver = None

    try:
        driver, used_browser = init_driver(browser_type=browser)
        print(f"[+] {url} 접속 중... (사용 브라우저: {used_browser})")
        driver.get(url)

        cf_cookie = wait_for_challenge_completion(driver, timeout=60)
        print("[*] 데이터 추출 중...")

        captured_headers = {}

        try:
            logs = driver.get_log("performance")
            for entry in logs:
                message = json.loads(entry["message"])["message"]
                if message["method"] == "Network.requestWillBeSent":
                    req = message["params"]["request"]
                    if (
                        "syosetu.org" in req["url"]
                        and message["params"].get("type") == "Document"
                    ):
                        captured_headers.clear()
                        captured_headers.update(req["headers"])
        except Exception:
            pass

        if not captured_headers:
            captured_headers = {
                "User-Agent": driver.execute_script(
                    "return navigator.userAgent;"
                ),
                "Accept-Language": driver.execute_script(
                    "return navigator.language;"
                ),
                "Referer": "https://syosetu.org/",
            }

        cookies_to_save = [cf_cookie] if cf_cookie else []

        if cf_cookie:
            print(
                f"[+] cf_clearance 쿠키 수집 성공! ({cf_cookie['value'][:15]}...)"
            )
        else:
            print("[-] cf_clearance 쿠키 수집 실패")

        session_data = {
            "browser": used_browser,
            "url": driver.current_url,
            "headers": captured_headers,
            "cookies": cookies_to_save,
        }

        output_file = SRC
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=4)

        print(f"[+] '{output_file}'에 저장 완료! 브라우저를 종료합니다.")
        return True

    except Exception as e:
        print(f"[-] 오류 발생: {e}")
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def find_cf(browser="auto"):
    return get_cookies_and_headers(browser=browser)