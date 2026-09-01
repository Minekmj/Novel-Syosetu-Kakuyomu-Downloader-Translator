import argparse
import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
import urllib.request
from PIL import Image, ImageTk

GITHUB_RELEASE_URL = "https://api.github.com/repos/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/releases/latest"

THEME_CONFIG = {
    "bg_color": "#263238",
    "surface_color": "#37474F",
    "surface_hover": "#455A64",
    "border_color": "#455A64",
    "border_focus": "#64B5F6",
    "accent_color": "#4DB6AC",
    "accent_hover": "#80CBC4",
    "text_primary": "#ECEFF1",
    "text_secondary": "#B0BEC5",
    "text_muted": "#78909C",
    "font_family": "맑은 고딕",
    "window_size": (400, 250),
    "corner_radius": 12,
}

V = None

try:
    base_path = sys._MEIPASS
    from v import V
except Exception:
    pass


def check_internet(timeout=3):
    try:
        urllib.request.urlopen("https://www.google.com/generate_204", timeout=timeout)
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


def enable_window_drag(window, widgets=None):
    drag_data = {"x": 0, "y": 0}

    def start_drag(event):
        drag_data["x"] = event.x_root - window.winfo_x()
        drag_data["y"] = event.y_root - window.winfo_y()

    def drag(event):
        x = event.x_root - drag_data["x"]
        y = event.y_root - drag_data["y"]
        window.geometry(f"+{x}+{y}")

    window.bind("<ButtonPress-1>", start_drag)
    window.bind("<B1-Motion>", drag)

    if widgets:
        for widget in widgets:
            if widget:
                widget.bind("<ButtonPress-1>", start_drag)
                widget.bind("<B1-Motion>", drag)


def rounded_window(window, width, height):
    transparent_color = "#010101"

    window.overrideredirect(True)
    window.attributes("-topmost", True)

    try:
        window.attributes("-transparentcolor", transparent_color)
    except Exception:
        pass

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)

    window.geometry(f"{width}x{height}+{x}+{y}")
    window.configure(bg=transparent_color)

    canvas = tk.Canvas(
        window,
        width=width,
        height=height,
        bg=transparent_color,
        highlightthickness=0,
        bd=0
    )
    canvas.pack(fill="both", expand=True)

    r = THEME_CONFIG["corner_radius"]

    def create_rounded_rect(x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    create_rounded_rect(2, 2, width - 2, height - 2, r, fill=THEME_CONFIG["border_color"])
    create_rounded_rect(3, 3, width - 3, height - 3, r, fill=THEME_CONFIG["bg_color"])

    return canvas


def show_update_dialog(root, release):
    result = {"download": False}

    latest_version = release.get("tag_name", "")
    assets = release.get("assets", [])

    exe_asset = next((a for a in assets if a.get("name", "").lower().endswith(".exe")), None)

    if exe_asset is None:
        return False, None

    file_name = exe_asset.get("name", "")
    file_size = format_file_size(exe_asset.get("size", 0))

    dialog = tk.Toplevel(root)
    width, height = 420, 270

    canvas = rounded_window(dialog, width, height)

    content = tk.Frame(canvas, bg=THEME_CONFIG["bg_color"])
    canvas.create_window(width // 2, height // 2, window=content, width=width - 16, height=height - 16)

    # 상단 닫기 바
    top_bar = tk.Frame(content, bg=THEME_CONFIG["bg_color"], height=28)
    top_bar.pack(fill="x", side="top")

    close_btn = tk.Label(
        top_bar,
        text="✕",
        font=(THEME_CONFIG["font_family"], 11, "bold"),
        fg=THEME_CONFIG["text_secondary"],
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

    close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#EF4444", fg="#FFFFFF"))
    close_btn.bind("<Leave>", lambda e: close_btn.config(bg=THEME_CONFIG["bg_color"], fg=THEME_CONFIG["text_secondary"]))
    close_btn.bind("<Button-1>", lambda e: cancel())

    title_label = tk.Label(
        content,
        text="새로운 업데이트가 있습니다",
        font=(THEME_CONFIG["font_family"], 13, "bold"),
        fg=THEME_CONFIG["text_primary"],
        bg=THEME_CONFIG["bg_color"]
    )
    title_label.pack(anchor="w", padx=20, pady=(0, 4))

    version_label = tk.Label(
        content,
        text=f"현재 버전 {V}  ➔  최신 버전 {latest_version}",
        font=(THEME_CONFIG["font_family"], 9),
        fg=THEME_CONFIG["accent_color"],
        bg=THEME_CONFIG["bg_color"]
    )
    version_label.pack(anchor="w", padx=20, pady=(0, 14))

    info_frame = tk.Frame(
        content,
        bg=THEME_CONFIG["surface_color"],
        highlightthickness=1,
        highlightbackground=THEME_CONFIG["border_color"]
    )
    info_frame.pack(fill="x", padx=20, pady=(0, 18))

    file_label = tk.Label(
        info_frame,
        text=file_name,
        font=(THEME_CONFIG["font_family"], 9, "bold"),
        fg=THEME_CONFIG["text_primary"],
        bg=THEME_CONFIG["surface_color"],
        anchor="w",
        justify="left"
    )
    file_label.pack(fill="x", padx=12, pady=(10, 2))

    size_label = tk.Label(
        info_frame,
        text=f"다운로드 크기: {file_size}",
        font=(THEME_CONFIG["font_family"], 8),
        fg=THEME_CONFIG["text_muted"],
        bg=THEME_CONFIG["surface_color"],
        anchor="w"
    )
    size_label.pack(fill="x", padx=12, pady=(0, 10))

    button_frame = tk.Frame(content, bg=THEME_CONFIG["bg_color"])
    button_frame.pack(fill="x", padx=20)

    download_btn = tk.Button(
        button_frame,
        text="지금 업데이트",
        command=download,
        font=(THEME_CONFIG["font_family"], 9, "bold"),
        fg="#0F172A",
        bg=THEME_CONFIG["accent_color"],
        activebackground=THEME_CONFIG["accent_hover"],
        activeforeground="#FFFFFF",
        relief="flat",
        bd=0,
        height=2,
        cursor="hand2"
    )
    download_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))

    cancel_btn = tk.Button(
        button_frame,
        text="나중에",
        command=cancel,
        font=(THEME_CONFIG["font_family"], 9),
        fg=THEME_CONFIG["text_secondary"],
        bg=THEME_CONFIG["surface_color"],
        activebackground=THEME_CONFIG["surface_hover"],
        activeforeground="#FFFFFF",
        relief="flat",
        bd=0,
        height=2,
        cursor="hand2"
    )
    cancel_btn.pack(side="right", fill="x", expand=True, padx=(0, 4))

    dialog.protocol("WM_DELETE_WINDOW", cancel)

    enable_window_drag(
        dialog,
        [canvas, content, top_bar, title_label, version_label, info_frame, file_label, size_label]
    )

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

        update_status(root, sub_label, "새로운 버전 다운로드 준비 중...")

        req = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})

        with urllib.request.urlopen(req, timeout=30) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0

            with open(temp_path, "wb") as file:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    file.write(chunk)
                    downloaded += len(chunk)

                    if total_size:
                        percent = int(downloaded / total_size * 100)
                        update_status(root, sub_label, f"다운로드 중... {percent}%")

        if os.path.exists(save_path):
            os.remove(save_path)

        os.replace(temp_path, save_path)
        update_status(root, sub_label, "다운로드 완료! 프로그램을 재시작합니다.")
        time.sleep(1.5)
        
        if save_path.lower().endswith(".exe"):
            subprocess.Popen([save_path])

        root.after(0, root.destroy)
        return True

    except Exception as e:
        print(f"[업데이트 다운로드 실패]: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        update_status(root, sub_label, "업데이트 다운로드 실패")
        time.sleep(1.5)
        return False


def check_and_update(root, sub_label):
    global inter

    update_status(root, sub_label, "인터넷 연결 확인 중...")

    if not check_internet():
        if inter >= 3:
            update_status(root, sub_label, "인터넷 연결이 없습니다. 프로그램을 종료합니다.")
            time.sleep(1.5)
            root.after(0, root.destroy)
            return False

        for i in range(3, 0, -1):
            update_status(root, sub_label, f"인터넷 연결 실패. {i}초 후 재시도...")
            time.sleep(1)

        inter += 1
        return check_and_update(root, sub_label)

    if V is None:
        return True

    update_status(root, sub_label, "최신 버전 확인 중...")

    try:
        release = get_latest_release()
        latest_version = release.get("tag_name", "")

        if not latest_version or latest_version == str(V):
            return True

        update_status(root, sub_label, f"새로운 버전 발견 ({latest_version})")

        result = {"download": False, "asset": None, "done": False}

        def open_update_dialog():
            try:
                result["download"], result["asset"] = show_update_dialog(root, release)
            except Exception as e:
                print(f"[업데이트 창 오류]: {e}")
            finally:
                result["done"] = True

        root.after(0, open_update_dialog)

        while not result["done"]:
            time.sleep(0.1)

        if result["download"] and result["asset"]:
            if download_update(root, sub_label, result["asset"]):
                return False

        update_status(root, sub_label, "업데이트를 건너뛰었습니다.")
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
    return os.path.join(base_path, relative_path)


def start_main_app(root, sub_label, pre_file):
    if not check_and_update(root, sub_label):
        return

    if pre_file:
        abs_file_path = os.path.abspath(pre_file)
        if os.path.exists(abs_file_path):
            ext = os.path.splitext(abs_file_path)[1].lower()
            if ext in [".bat", ".cmd"]:
                update_status(root, sub_label, "사전 작업 실행 중...")
                file_dir = os.path.dirname(abs_file_path)
                creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                subprocess.run(f'"{abs_file_path}"', shell=True, cwd=file_dir, creationflags=creationflags)
        else:
            update_status(root, sub_label, "지정된 경로의 파일을 찾을 수 없습니다.")
            time.sleep(1.5)

    update_status(root, sub_label, "메인 프로그램을 불러오는 중...")

    import main
    main.main(
        lambda: root.after(0, root.withdraw),
        lambda: root.after(0, root.destroy),
    )


def close_app(root):
    root.destroy()
    sys.exit(0)


def create_splash(pre_file=None):
    root = tk.Tk()
    width, height = THEME_CONFIG["window_size"]

    canvas = rounded_window(root, width, height)

    main_frame = tk.Frame(canvas, bg=THEME_CONFIG["bg_color"])
    canvas.create_window(width // 2, height // 2, window=main_frame, width=width - 16, height=height - 16)

    top_bar = tk.Frame(main_frame, bg=THEME_CONFIG["bg_color"], height=24)
    top_bar.pack(fill="x", side="top")

    close_btn = tk.Label(
        top_bar,
        text="✕",
        font=(THEME_CONFIG["font_family"], 10, "bold"),
        fg=THEME_CONFIG["text_secondary"],
        bg=THEME_CONFIG["bg_color"],
        width=3,
        cursor="hand2"
    )
    close_btn.pack(side="right", padx=2)

    close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#EF4444", fg="#FFFFFF"))
    close_btn.bind("<Leave>", lambda e: close_btn.config(bg=THEME_CONFIG["bg_color"], fg=THEME_CONFIG["text_secondary"]))
    close_btn.bind("<Button-1>", lambda e: close_app(root))

    icon_path = resource_path("main.ico")
    icon_label = None

    if os.path.exists(icon_path):
        try:
            icon_image = Image.open(icon_path).convert("RGBA")
            icon_image.thumbnail((52, 52), Image.Resampling.LANCZOS)
            icon_photo = ImageTk.PhotoImage(icon_image)

            icon_label = tk.Label(main_frame, image=icon_photo, bg=THEME_CONFIG["bg_color"])
            icon_label.image = icon_photo
            icon_label.pack(pady=(4, 8))
        except Exception as e:
            print(f"[ICO] 로딩 실패: {e}")

    title_label = tk.Label(
        main_frame,
        text="프로그램 시작 중",
        font=(THEME_CONFIG["font_family"], 13, "bold"),
        fg=THEME_CONFIG["text_primary"],
        bg=THEME_CONFIG["bg_color"]
    )
    title_label.pack(pady=(0, 2))

    sub_label = tk.Label(
        main_frame,
        text="잠시만 기다려 주세요...",
        font=(THEME_CONFIG["font_family"], 9),
        fg=THEME_CONFIG["text_secondary"],
        bg=THEME_CONFIG["bg_color"]
    )
    sub_label.pack(pady=(0, 16))

    progress_frame = tk.Frame(main_frame, bg=THEME_CONFIG["bg_color"])
    progress_frame.pack(fill="x", padx=40)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Custom.Horizontal.TProgressbar",
        troughcolor=THEME_CONFIG["surface_color"],
        background=THEME_CONFIG["accent_color"],
        bordercolor=THEME_CONFIG["surface_color"],
        lightcolor=THEME_CONFIG["accent_color"],
        darkcolor=THEME_CONFIG["accent_color"],
        thickness=3
    )

    progress = ttk.Progressbar(
        progress_frame,
        style="Custom.Horizontal.TProgressbar",
        mode="indeterminate"
    )
    progress.pack(fill="x")
    progress.start(10)

    version_text = f"{V}" if V is not None else ""
    version_label = tk.Label(
        main_frame,
        text=version_text,
        font=(THEME_CONFIG["font_family"], 8),
        fg=THEME_CONFIG["text_muted"],
        bg=THEME_CONFIG["bg_color"]
    )
    version_label.pack(pady=(12, 0))

    drag_widgets = [
        canvas, main_frame, top_bar, title_label, sub_label, progress_frame, progress, version_label, icon_label
    ]
    enable_window_drag(root, drag_widgets)

    threading.Thread(
        target=start_main_app,
        args=(root, sub_label, pre_file),
        daemon=True
    ).start()

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Splash Screen Loader")
    parser.add_argument("-f", "--file", type=str, help="실행할 절대경로 배치 파일", default=None)
    args = parser.parse_args()

    create_splash(pre_file=args.file)


if __name__ == "__main__":
    main()