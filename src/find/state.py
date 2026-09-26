import base64
import ctypes
import json
import os
import random
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

SRC = "session_info.json"
TARGET_URL = "https://syosetu.org"

CLEAN_UI_JS = """
(function() {
    if (document.getElementById('mine-downloader-custom-style')) return;
    const style = document.createElement('style');
    style.id = 'mine-downloader-custom-style';
    style.innerHTML = `
        html, body {
            width: 100% !important;
            min-height: 100vh !important;
            margin: 0 !important;
            padding: 0 !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            background-color: #0f172a !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            overflow: hidden !important;
        }
        h1, h2, h3, p, footer, #footer, .footer, 
        .attribution, #cf-error-details, .cf-subheadline,
        .core-msg, .cft-ray, #cf-bubbles {
            display: none !important;
        }
        #cf-wrapper, #cf-content, .main-wrapper, .main-content {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            background: transparent !important;
            border: none !important;
        }
        #custom-card-wrapper {
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            background: #1e293b !important;
            padding: 24px 32px !important;
            border-radius: 16px !important;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5) !important;
            border: 1px solid #334155 !important;
            text-align: center !important;
        }
        .custom-logo {
            font-size: 18px !important;
            font-weight: 700 !important;
            letter-spacing: -0.5px !important;
            margin-bottom: 6px !important;
            color: #38bdf8 !important;
        }
        .custom-desc {
            font-size: 12px !important;
            color: #94a3b8 !important;
            margin-bottom: 16px !important;
            font-weight: 400 !important;
        }
        #challenge-stage, #challenge-form, [id*="cf-stage"], [id*="turnstile"] {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            margin: 0 !important;
            padding: 0 !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        iframe {
            margin: 0 auto !important;
        }
    `;
    document.head.appendChild(style);

    function setupCustomUI() {
        if (document.getElementById('custom-card-wrapper')) return;
        const stage = document.getElementById('challenge-stage') || 
                      document.querySelector('[id*="cf-stage"]') || 
                      document.querySelector('[id*="turnstile"]') ||
                      document.querySelector('iframe[src*="challenges.cloudflare.com"]');
        if (!stage) return;
        const targetElement = document.getElementById('challenge-stage') || stage.parentElement || stage;
        const wrapper = document.createElement('div');
        wrapper.id = 'custom-card-wrapper';
        wrapper.innerHTML = `
            <div class="custom-logo">Mine Downloader</div>
            <div class="custom-desc">스마트 인증 시도 중...</div>
        `;
        if (targetElement.parentNode) {
            targetElement.parentNode.insertBefore(wrapper, targetElement);
            wrapper.appendChild(targetElement);
        }
    }

    const observer = new MutationObserver((mutations, obs) => {
        const stage = document.getElementById('challenge-stage') || 
                      document.querySelector('[id*="cf-stage"]') || 
                      document.querySelector('iframe[src*="challenges.cloudflare.com"]');
        if (stage) {
            setupCustomUI();
            obs.disconnect();
        }
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    if (document.readyState !== 'loading') {
        setupCustomUI();
    } else {
        document.addEventListener('DOMContentLoaded', setupCustomUI);
    }
})();
"""

def get_browser_path():
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def get_bottom_right_position(width=400, height=300):
    try:
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
    except Exception:
        screen_w, screen_h = 1920, 1080
    pos_x = max(0, screen_w - width - 20)
    pos_y = max(0, screen_h - height - 80)
    return pos_x, pos_y

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def calculate_bezier_curve(p0, p1, p2, p3, num_points=15):
    points = []
    for i in range(num_points + 1):
        t = i / num_points
        u = 1 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t

        x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
        y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
        points.append((int(x), int(y)))
    return points

def human_like_background_click(hwnd, win_w, win_h, target_x, target_y):
    try:
        user32 = ctypes.windll.user32
        
        corners = [
            (random.randint(10, 30), random.randint(10, 30)),
            (win_w - random.randint(10, 30), random.randint(10, 30)),
            (random.randint(10, 30), win_h - random.randint(10, 30)),
            (win_w - random.randint(10, 30), win_h - random.randint(10, 30))
        ]
        start_x, start_y = random.choice(corners)
        
        control1 = (start_x + random.randint(-40, 40), start_y + random.randint(-40, 40))
        control2 = (target_x + random.randint(-25, 25), target_y + random.randint(-25, 25))
        
        path = calculate_bezier_curve((start_x, start_y), control1, control2, (target_x, target_y), num_points=15)
        
        WM_MOUSEMOVE = 0x0200
        WM_LBUTTONDOWN = 0x0201
        WM_LBUTTONUP = 0x0202
        MK_LBUTTON = 0x0001
        
        for px, py in path:
            l_param = (py << 16) | (px & 0xFFFF)
            user32.PostMessageW(hwnd, WM_MOUSEMOVE, MK_LBUTTON, l_param)
            time.sleep(random.uniform(0.01, 0.02))
            
        final_x = target_x + random.randint(-5, 5)
        final_y = target_y + random.randint(-5, 5)
        final_l_param = (final_y << 16) | (final_x & 0xFFFF)
        
        time.sleep(random.uniform(0.05, 0.15))
        user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, final_l_param)
        time.sleep(random.uniform(0.05, 0.1))
        user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, final_l_param)
        
        print("[*] 백그라운드 가상 마우스 클릭 실행")
    except Exception as e:
        print(f"[!] 클릭 실패: {e}")

class SimpleWebSocketClient:
    def __init__(self, ws_url):
        parsed = urllib.parse.urlsplit(ws_url)
        self.host = parsed.hostname
        self.port = parsed.port or 80
        self.path = parsed.path
        if parsed.query:
            self.path += f"?{parsed.query}"
        self.sock = socket.create_connection((self.host, self.port), timeout=10)
        self._handshake()
        self.msg_id = 0
    def _handshake(self):
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode("ascii"))
        res_data = bytearray()
        while b"\r\n\r\n" not in res_data:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("웹소켓 핸드셰이크 중 연결이 종료되었습니다.")
            res_data.extend(chunk)
        if b"101 " not in res_data:
            raise ConnectionError(f"핸드셰이크 실패: {res_data.decode('latin1', errors='ignore')}")
    def _recv_exact(self, length):
        buf = bytearray()
        while len(buf) < length:
            chunk = self.sock.recv(length - len(buf))
            if not chunk:
                raise ConnectionError("소켓 연결이 닫혔습니다.")
            buf.extend(chunk)
        return bytes(buf)
    def send_frame(self, message: str):
        data = message.encode("utf-8")
        length = len(data)
        frame = bytearray([0x81])
        mask = os.urandom(4)
        if length <= 125:
            frame.append(0x80 | length)
        elif length <= 65535:
            frame.append(0x80 | 126)
            frame.extend(length.to_bytes(2, "big"))
        else:
            frame.append(0x80 | 127)
            frame.extend(length.to_bytes(8, "big"))
        frame.extend(mask)
        frame.extend(bytes(b ^ mask[i % 4] for i, b in enumerate(data)))
        self.sock.sendall(frame)
    def recv_frame(self):
        while True:
            head = self._recv_exact(2)
            opcode = head[0] & 0x0F
            masked = (head[1] & 0x80) != 0
            payload_len = head[1] & 0x7F
            if payload_len == 126:
                payload_len = int.from_bytes(self._recv_exact(2), "big")
            elif payload_len == 127:
                payload_len = int.from_bytes(self._recv_exact(8), "big")
            mask_key = self._recv_exact(4) if masked else None
            payload = self._recv_exact(payload_len)
            if masked:
                payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
            if opcode == 0x9:
                pong = bytearray([0x8A, 0x80]) + os.urandom(4)
                self.sock.sendall(pong)
                continue
            if opcode == 0x1:
                return payload.decode("utf-8", errors="ignore")
            if opcode == 0x8:
                return None
    def call_cdp(self, method, params=None):
        self.msg_id += 1
        req_id = self.msg_id
        payload = {"id": req_id, "method": method}
        if params:
            payload["params"] = params
        self.send_frame(json.dumps(payload))
        while True:
            raw = self.recv_frame()
            if not raw:
                return {}
            try:
                res = json.loads(raw)
                if res.get("id") == req_id:
                    return res.get("result", {})
            except Exception:
                continue
    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass

def find_cf():
    if os.path.exists(SRC):
        try:
            os.remove(SRC)
            print(f"[*] 이전 '{SRC}' 파일을 삭제했습니다.")
        except Exception:
            pass

    browser_path = get_browser_path()
    if not browser_path:
        print("[!] 지원되는 브라우저(Chrome/Edge)를 찾을 수 없습니다.")
        return

    win_w, win_h = 400, 300
    pos_x, pos_y = get_bottom_right_position(win_w, win_h)
    
    debug_port = get_free_port()
    temp_dir = tempfile.mkdtemp(prefix="cf_bypass_")

    default_dir = os.path.join(temp_dir, "Default")
    os.makedirs(default_dir, exist_ok=True)
    preferences = {
        "translate": {"enabled": False},
        "translate_site_blacklist": {},
        "translate_whitelists": {},
        "intl": {"accept_languages": "ko-KR,ko,en-US,en"},
        "browser": {"enable_translate": False}
    }
    try:
        with open(os.path.join(default_dir, "Preferences"), "w", encoding="utf-8") as f:
            json.dump(preferences, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[!] 브라우저 Preferences 설정 실패: {e}")

    cmd = [
        browser_path,
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={temp_dir}",
        f"--app={TARGET_URL}",
        f"--window-size={win_w},{win_h}",
        f"--window-position={pos_x},{pos_y}",
        "--disable-sync",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-search-engine-choice-screen",
        "--disable-translate",
        "--disable-features=Translate,TranslateUI,msEdgeTranslate,EdgeFre,msEdgeFreDialogSupport",
        "--disable-notifications",
        "--disable-infobars",
        "--disable-popup-blocking",
        "--disable-component-update",
        "--disable-session-crashed-bubble",
        "--lang=ko-KR",
        "--silent",
        "--log-level=3",
        "--disable-logging",
    ]

    print("[*] 화면 우측 하단에 작은 크기로 인증 브라우저를 실행합니다...")
    proc = subprocess.Popen(cmd)
    ws_client = None

    try:
        ws_url = None
        for _ in range(50):
            try:
                req_url = f"http://127.0.0.1:{debug_port}/json"
                with urllib.request.urlopen(req_url, timeout=1) as resp:
                    targets = json.loads(resp.read().decode("utf-8"))
                    for t in targets:
                        if t.get("type") == "page":
                            ws_url = t.get("webSocketDebuggerUrl")
                            break
                    if ws_url:
                        break
            except Exception:
                time.sleep(0.1)

        if not ws_url:
            raise RuntimeError("CDP 엔드포인트에 접속할 수 없습니다.")

        ws_client = SimpleWebSocketClient(ws_url)
        ws_client.call_cdp("Network.enable")
        ws_client.call_cdp("Network.clearBrowserCookies")
        ws_client.call_cdp("Network.clearBrowserCache")

        cf_cookie = None
        start_time = time.time()
        target_hwnd = None
        
        last_click_time = 0.0
        retry_interval = 1.0

        while True:
            try:
                ws_client.call_cdp(
                    "Runtime.evaluate",
                    {
                        "expression": CLEAN_UI_JS,
                        "returnByValue": True
                    }
                )
            except Exception:
                pass

            if not target_hwnd:
                def enum_windows_proc(hwnd, lParam):
                    nonlocal target_hwnd
                    pid = ctypes.c_ulong()
                    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value == proc.pid:
                        if ctypes.windll.user32.IsWindowVisible(hwnd):
                            target_hwnd = hwnd
                            return False
                    return True
                
                EnumWindowsProcType = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                ctypes.windll.user32.EnumWindows(EnumWindowsProcType(enum_windows_proc), 0)

            now = time.time()
            
            if target_hwnd and (now - start_time > 0.5) and (now - last_click_time > retry_interval):
                print(f"[*] 인증 우회 시도 중...")
                target_x = 200
                target_y = 150
                human_like_background_click(target_hwnd, win_w, win_h, target_x, target_y)
                last_click_time = now

            try:
                cookie_res = ws_client.call_cdp(
                    "Network.getCookies",
                    {"urls": [TARGET_URL]}
                )
                cookies = cookie_res.get("cookies", [])
                for c in cookies:
                    if c.get("name") == "cf_clearance":
                        cf_cookie = {
                            "name": "cf_clearance",
                            "value": c.get("value"),
                            "domain": c.get("domain", ".syosetu.org"),
                            "path": c.get("path", "/"),
                        }
                        break
            except Exception:
                pass

            if cf_cookie:
                print(f"[+] 인증 완료: {cf_cookie['value'][:15]}...")
                break

            if now - start_time > 60:
                print("[!] 시간 초과.")
                break

            time.sleep(0.1)

        ua_res = ws_client.call_cdp(
            "Runtime.evaluate",
            {
                "expression": "navigator.userAgent",
                "returnByValue": True
            }
        )
        user_agent = ua_res.get("result", {}).get("value", "")

        session_data = {
            "browser": "native_cdp",
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
        print(f"[+] '{SRC}' 저장 완료!")

    finally:
        if ws_client:
            ws_client.close()
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
        time.sleep(0.2)
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    find_cf()