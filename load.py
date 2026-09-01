import argparse
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import urllib.request
import json

GITHUB_RELEASE_URL = "https://api.github.com/repos/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/releases/latest"

THEME_CONFIG = {
    "bg_color": "#1E1E1E",
    "border_color": "#007ACC",
    "title_color": "#FFFFFF",
    "sub_color": "#AAAAAA",
    "progress_color": "#007ACC",
    "font_family": "맑은 고딕",
    "window_size": (360, 210),
}

V = None

try:
    base_path = sys._MEIPASS
    from v import V
except Exception:
    pass

def check_internet(timeout=3):
    try:
        urllib.request.urlopen(
            "https://www.google.com/generate_204",
            timeout=timeout
        )
        return True
    except Exception:
        return False


def format_file_size(size):
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.2f} GB"


def get_latest_release():
    req = urllib.request.Request(
        GITHUB_RELEASE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Novel-Syosetu-Kakuyomu-Downloader-Translator"
        }
    )

    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def update_status(root, label, text):
    if root.winfo_exists():
        root.after(0, lambda: label.config(text=text))


inter = 0


def show_update_dialog(root, release):
    result = {"download": False}

    latest_version = release.get("tag_name", "")
    assets = release.get("assets", [])

    exe_asset = None

    for asset in assets:
        if asset.get("name", "").lower().endswith(".exe"):
            exe_asset = asset
            break

    if exe_asset is None:
        return False, None

    file_name = exe_asset.get("name", "")
    file_size = format_file_size(exe_asset.get("size", 0))

    dialog = tk.Toplevel(root)
    dialog.overrideredirect(True)
    dialog.attributes("-topmost", True)
    dialog.configure(
        bg=THEME_CONFIG["bg_color"],
        highlightthickness=1,
        highlightbackground=THEME_CONFIG["border_color"]
    )

    width = 400
    height = 245

    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()

    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)

    dialog.geometry(f"{width}x{height}+{x}+{y}")

    top_bar = tk.Frame(
        dialog,
        bg=THEME_CONFIG["bg_color"]
    )
    top_bar.pack(fill="x")

    close_btn = tk.Label(
        top_bar,
        text="✕",
        font=(THEME_CONFIG["font_family"], 10, "bold"),
        fg=THEME_CONFIG["sub_color"],
        bg=THEME_CONFIG["bg_color"],
        width=3,
        cursor="hand2"
    )
    close_btn.pack(side="right", padx=2, pady=2)

    def cancel():
        result["download"] = False
        dialog.destroy()

    def download():
        result["download"] = True
        dialog.destroy()

    close_btn.bind(
        "<Enter>",
        lambda e: close_btn.config(
            bg="#E81123",
            fg="#FFFFFF"
        )
    )

    close_btn.bind(
        "<Leave>",
        lambda e: close_btn.config(
            bg=THEME_CONFIG["bg_color"],
            fg=THEME_CONFIG["sub_color"]
        )
    )

    close_btn.bind("<Button-1>", lambda e: cancel())

    title_label = tk.Label(
        dialog,
        text="새로운 버전이 있습니다.",
        font=(THEME_CONFIG["font_family"], 13, "bold"),
        fg=THEME_CONFIG["title_color"],
        bg=THEME_CONFIG["bg_color"]
    )
    title_label.pack(pady=(15, 8))

    version_label = tk.Label(
        dialog,
        text=f"현재 버전: {V}\n최신 버전: {latest_version}",
        font=(THEME_CONFIG["font_family"], 9),
        fg=THEME_CONFIG["sub_color"],
        bg=THEME_CONFIG["bg_color"],
        justify="center"
    )
    version_label.pack(pady=(0, 8))

    file_label = tk.Label(
        dialog,
        text=f"{file_name}\n파일 크기: {file_size}",
        font=(THEME_CONFIG["font_family"], 9),
        fg=THEME_CONFIG["sub_color"],
        bg=THEME_CONFIG["bg_color"],
        justify="center"
    )
    file_label.pack(pady=(0, 12))

    button_frame = tk.Frame(
        dialog,
        bg=THEME_CONFIG["bg_color"]
    )
    button_frame.pack()

    download_btn = tk.Button(
        button_frame,
        text="다운로드",
        command=download,
        font=(THEME_CONFIG["font_family"], 9, "bold"),
        fg="#FFFFFF",
        bg=THEME_CONFIG["border_color"],
        activebackground="#005A9E",
        activeforeground="#FFFFFF",
        relief="flat",
        width=12,
        cursor="hand2"
    )
    download_btn.pack(side="left", padx=5)

    cancel_btn = tk.Button(
        button_frame,
        text="나중에",
        command=cancel,
        font=(THEME_CONFIG["font_family"], 9),
        fg=THEME_CONFIG["sub_color"],
        bg="#2A2A2A",
        activebackground="#333333",
        activeforeground="#FFFFFF",
        relief="flat",
        width=12,
        cursor="hand2"
    )
    cancel_btn.pack(side="left", padx=5)

    dialog.protocol("WM_DELETE_WINDOW", cancel)

    dialog.grab_set()
    root.wait_window(dialog)

    return result["download"], exe_asset


def download_update(root, sub_label, asset):
    try:
        download_url = asset.get("browser_download_url")
        file_name = asset.get("name")

        if not download_url or not file_name:
            return False

        save_path = os.path.join(os.getcwd(), file_name)
        temp_path = save_path + ".download"

        update_status(
            root,
            sub_label,
            "새로운 버전 다운로드 중..."
        )

        req = urllib.request.Request(
            download_url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            total_size = int(
                response.headers.get("Content-Length", 0)
            )

            downloaded = 0

            with open(temp_path, "wb") as file:
                while True:
                    chunk = response.read(1024 * 1024)

                    if not chunk:
                        break

                    file.write(chunk)
                    downloaded += len(chunk)

                    if total_size:
                        percent = int(
                            downloaded / total_size * 100
                        )

                        update_status(
                            root,
                            sub_label,
                            f"다운로드 중... {percent}%"
                        )

        if os.path.exists(save_path):
            os.remove(save_path)

        os.replace(temp_path, save_path)

        update_status(
            root,
            sub_label,
            "다운로드 완료. 프로그램을 종료합니다."
        )

        time.sleep(1.5)

        root.after(0, root.destroy)

        return True

    except Exception as e:
        print(f"[업데이트 다운로드 실패]: {e}")

        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

        update_status(
            root,
            sub_label,
            "업데이트 다운로드 실패"
        )

        time.sleep(1.5)

        return False


def check_and_update(root, sub_label):
    global inter

    update_status(
        root,
        sub_label,
        "인터넷 연결 확인 중..."
    )

    if not check_internet():
        if inter > 3:
            update_status(
                root,
                sub_label,
                "인터넷 연결 없음... 프로그램 종료"
            )

            time.sleep(1.5)

            root.after(0, root.destroy)

            return False

        update_status(
            root,
            sub_label,
            "인터넷 연결 없음... 3초후 재시도"
        )
        time.sleep(1)

        update_status(
            root,
            sub_label,
            "인터넷 연결 없음... 2초후 재시도"
        )
        time.sleep(1)

        update_status(
            root,
            sub_label,
            "인터넷 연결 없음... 1초후 재시도"
        )
        time.sleep(1)

        inter += 1

        return check_and_update(
            root,
            sub_label
        )

    if V is None:
        return True

    update_status(
        root,
        sub_label,
        "최신 버전 확인 중..."
    )

    try:
        release = get_latest_release()

        latest_version = release.get(
            "tag_name",
            ""
        )

        if not latest_version:
            return True

        if latest_version != str(V):
            update_status(
                root,
                sub_label,
                f"새로운 버전 발견 ({latest_version})"
            )

            result = {
                "download": False,
                "asset": None,
                "done": False
            }

            def open_update_dialog():
                try:
                    result["download"], result["asset"] = show_update_dialog(
                        root,
                        release
                    )
                except Exception as e:
                    print(f"[업데이트 창 오류]: {e}")
                finally:
                    result["done"] = True

            root.after(
                0,
                open_update_dialog
            )

            while not result["done"]:
                time.sleep(0.1)

            if result["download"] and result["asset"]:
                if download_update(
                    root,
                    sub_label,
                    result["asset"]
                ):
                    return False

            update_status(
                root,
                sub_label,
                "업데이트를 건너뛰었습니다."
            )

            time.sleep(0.7)

        return True

    except Exception as e:
        print(f"[업데이트 확인 실패]: {e}")

        return True


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(
        base_path,
        relative_path
    )


def start_main_app(root, sub_label, pre_file):
    if not check_and_update(
        root,
        sub_label
    ):
        return

    if pre_file:
        abs_file_path = os.path.abspath(
            pre_file
        )

        if os.path.exists(abs_file_path):
            ext = os.path.splitext(
                abs_file_path
            )[1].lower()

            if ext in [".bat", ".cmd"]:
                update_status(
                    root,
                    sub_label,
                    "배치 파일 실행 중..."
                )

                file_dir = os.path.dirname(
                    abs_file_path
                )

                creationflags = (
                    subprocess.CREATE_NO_WINDOW
                    if sys.platform == "win32"
                    else 0
                )

                subprocess.run(
                    f'"{abs_file_path}"',
                    shell=True,
                    cwd=file_dir,
                    creationflags=creationflags
                )
        else:
            update_status(
                root,
                sub_label,
                "지정된 경로의 파일을 찾을 수 없습니다."
            )

            time.sleep(1.5)

    update_status(
        root,
        sub_label,
        "메인 프로그램을 실행하는 중..."
    )

    import main

    main.main(
        lambda: root.after(
            0,
            root.withdraw
        ),
        lambda: root.after(
            0,
            root.destroy
        ),
    )


def close_app(root):
    root.destroy()
    sys.exit(0)


def create_splash(pre_file=None):
    root = tk.Tk()

    root.overrideredirect(True)
    root.attributes("-topmost", True)

    width, height = THEME_CONFIG["window_size"]

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)

    root.geometry(
        f"{width}x{height}+{x}+{y}"
    )

    root.configure(
        bg=THEME_CONFIG["bg_color"],
        highlightthickness=1,
        highlightbackground=THEME_CONFIG["border_color"],
    )

    top_bar = tk.Frame(
        root,
        bg=THEME_CONFIG["bg_color"]
    )
    top_bar.pack(
        fill="x",
        side="top"
    )

    close_btn = tk.Label(
        top_bar,
        text="✕",
        font=(
            THEME_CONFIG["font_family"],
            10,
            "bold"
        ),
        fg=THEME_CONFIG["sub_color"],
        bg=THEME_CONFIG["bg_color"],
        width=3,
        height=1,
        cursor="hand2"
    )

    close_btn.pack(
        side="right",
        padx=2,
        pady=2
    )

    close_btn.bind(
        "<Enter>",
        lambda e: close_btn.config(
            bg="#E81123",
            fg="#FFFFFF"
        )
    )

    close_btn.bind(
        "<Leave>",
        lambda e: close_btn.config(
            bg=THEME_CONFIG["bg_color"],
            fg=THEME_CONFIG["sub_color"]
        )
    )

    close_btn.bind(
        "<Button-1>",
        lambda e: close_app(root)
    )

    icon_path = resource_path(
        "main.ico"
    )

    if os.path.exists(icon_path):
        try:
            icon_image = Image.open(
                icon_path
            )

            icon_image = icon_image.convert(
                "RGBA"
            )

            icon_image.thumbnail(
                (56, 56),
                Image.Resampling.LANCZOS
            )

            icon_photo = ImageTk.PhotoImage(
                icon_image
            )

            icon_label = tk.Label(
                root,
                image=icon_photo,
                bg=THEME_CONFIG["bg_color"],
            )

            icon_label.image = icon_photo

            icon_label.pack(
                pady=(5, 5)
            )

        except Exception as e:
            print(
                f"[ICO] 이미지 로딩 실패: {e}"
            )

    title_label = tk.Label(
        root,
        text="프로그램을 불러오는 중...",
        font=(
            THEME_CONFIG["font_family"],
            13,
            "bold"
        ),
        fg=THEME_CONFIG["title_color"],
        bg=THEME_CONFIG["bg_color"],
    )

    title_label.pack(
        pady=(0, 5)
    )

    sub_label = tk.Label(
        root,
        text="잠시만 기다려 주세요.",
        font=(
            THEME_CONFIG["font_family"],
            9
        ),
        fg=THEME_CONFIG["sub_color"],
        bg=THEME_CONFIG["bg_color"],
    )

    sub_label.pack(
        pady=(0, 8)
    )

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

    progress.pack(
        pady=3
    )

    progress.start(12)

    threading.Thread(
        target=start_main_app,
        args=(
            root,
            sub_label,
            pre_file
        ),
        daemon=True
    ).start()

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(
        description="Splash Screen Loader"
    )

    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="실행할 절대경로 배치 파일",
        default=None,
    )

    args = parser.parse_args()

    create_splash(
        pre_file=args.file
    )


if __name__ == "__main__":
    main()