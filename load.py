import argparse
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from html.parser import HTMLParser
import urllib.request

URL = "https://minekmj.github.io/Novel-Syosetu-Kakuyomu-Downloader-Translator/"
URL_D = "https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/releases/download/{v}/Novel-Syosetu-Kakuyomu-Downloader-Translator-{v}.exe"

THEME_CONFIG = {
    "bg_color": "#1E1E1E",
    "border_color": "#007ACC",
    "title_color": "#FFFFFF",
    "sub_color": "#AAAAAA",
    "progress_color": "#007ACC",
    "font_family": "맑은 고딕",
    "window_size": (360, 190),
}

V = None

try:
    base_path = sys._MEIPASS
    from v import V
except Exception:
    pass


class VersionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_down_p = False
        self.latest_version = None

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            attrs_dict = dict(attrs)
            if attrs_dict.get("id") == "down":
                self.in_down_p = True

    def handle_endtag(self, tag):
        if tag == "p" and self.in_down_p:
            self.in_down_p = False

    def handle_data(self, data):
        if self.in_down_p and not self.latest_version:
            cleaned_data = data.strip()
            if cleaned_data:
                self.latest_version = cleaned_data


def check_internet(timeout=3):
    try:
        urllib.request.urlopen("https://www.google.com/generate_204", timeout=timeout)
        return True
    except Exception:
        return False

inter = 0

def check_and_update(root, sub_label):
    global inter
    update_status(root, sub_label, "인터넷 연결 확인 중...")
    
    if not check_internet():
        if inter > 3:
            update_status(root, sub_label, "인터넷 연결 없음... 프로그램 종료")
            time.sleep(1.5)
            root.after(0, root.destroy)
            sys.exit(0)
            
        update_status(root, sub_label, "인터넷 연결 없음... 3초후 재시도")
        time.sleep(1)
        update_status(root, sub_label, "인터넷 연결 없음... 2초후 재시도")
        time.sleep(1)
        update_status(root, sub_label, "인터넷 연결 없음... 1초후 재시도")
        time.sleep(1)
        inter = inter + 1
        check_and_update(root, sub_label)
        return
    
    if V is None:
        return

    update_status(root, sub_label, "버전 확인 중...")
    try:
        req = urllib.request.Request(
            URL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            html_content = response.read().decode('utf-8')

        parser = VersionParser()
        parser.feed(html_content)
        latest_version = parser.latest_version

        if latest_version and latest_version != str(V):
            update_status(root, sub_label, f"새로운 버전 발견 ({latest_version}). 다운로드 중...")
            
            download_url = URL_D.format(v=latest_version)
            file_name = f"Novel-Syosetu-Kakuyomu-Downloader-Translator-{latest_version}.exe"
            save_path = os.path.join(os.getcwd(), file_name)

            urllib.request.urlretrieve(download_url, save_path)
            
            update_status(root, sub_label, "다운로드 완료. 프로그램을 종료합니다.")
            time.sleep(1.5)
            
            root.after(0, root.destroy)
            sys.exit(0)
            
    except Exception as e:
        print(f"[업데이트 확인 실패]: {e}")


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def update_status(root, label, text):
    root.after(0, lambda: label.config(text=text))


def start_main_app(root, sub_label, pre_file):
    check_and_update(root, sub_label)

    if pre_file:
        abs_file_path = os.path.abspath(pre_file)

        if os.path.exists(abs_file_path):
            ext = os.path.splitext(abs_file_path)[1].lower()

            if ext in [".bat", ".cmd"]:
                update_status(root, sub_label, "배치 파일 실행 중...")

                file_dir = os.path.dirname(abs_file_path)
                creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

                subprocess.run(
                    f'"{abs_file_path}"',
                    shell=True,
                    cwd=file_dir,
                    creationflags=creationflags,
                )
        else:
            update_status(root, sub_label, "지정된 경로의 파일을 찾을 수 없습니다.")
            time.sleep(1.5)

    update_status(root, sub_label, "메인 프로그램을 실행하는 중...")

    import main

    main.main(
        lambda: root.after(0, root.withdraw),
        lambda: root.after(0, root.destroy),
    )


def create_splash(pre_file=None):
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    width, height = THEME_CONFIG["window_size"]

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)

    root.geometry(f"{width}x{height}+{x}+{y}")
    root.configure(
        bg=THEME_CONFIG["bg_color"],
        highlightthickness=1,
        highlightbackground=THEME_CONFIG["border_color"],
    )

    # ------------------------------------------------------------
    # ICO 이미지 표시
    # ------------------------------------------------------------
    icon_path = resource_path("main.ico")

    if os.path.exists(icon_path):
        try:
            icon_image = Image.open(icon_path)
            icon_image = icon_image.convert("RGBA")
            icon_image.thumbnail((64, 64), Image.Resampling.LANCZOS)

            icon_photo = ImageTk.PhotoImage(icon_image)

            icon_label = tk.Label(
                root,
                image=icon_photo,
                bg=THEME_CONFIG["bg_color"],
            )
            icon_label.image = icon_photo
            icon_label.pack(pady=(18, 5))

        except Exception as e:
            print(f"[ICO] 이미지 로딩 실패: {e}")

    title_label = tk.Label(
        root,
        text="프로그램을 불러오는 중...",
        font=(THEME_CONFIG["font_family"], 13, "bold"),
        fg=THEME_CONFIG["title_color"],
        bg=THEME_CONFIG["bg_color"],
    )
    title_label.pack(pady=(0, 5))

    sub_label = tk.Label(
        root,
        text="잠시만 기다려 주세요.",
        font=(THEME_CONFIG["font_family"], 9),
        fg=THEME_CONFIG["sub_color"],
        bg=THEME_CONFIG["bg_color"],
    )
    sub_label.pack(pady=(0, 8))

    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        "Custom.Horizontal.TProgressbar",
        troughcolor=THEME_CONFIG["bg_color"],
        background=THEME_CONFIG["progress_color"],
        bordercolor=THEME_CONFIG["bg_color"],
        lightcolor=THEME_CONFIG["progress_color"],
        darkcolor=THEME_CONFIG["progress_color"],
    )

    progress = ttk.Progressbar(
        root,
        style="Custom.Horizontal.TProgressbar",
        mode="indeterminate",
        length=260,
    )
    progress.pack(pady=3)
    progress.start(12)

    threading.Thread(
        target=start_main_app,
        args=(root, sub_label, pre_file),
        daemon=True,
    ).start()

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Splash Screen Loader")
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="실행할 절대경로 배치 파일",
        default=None,
    )

    args = parser.parse_args()
    create_splash(pre_file=args.file)


if __name__ == "__main__":
    main()