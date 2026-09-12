import argparse
import hashlib
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
    from src.system.v import V
except Exception:
    pass


def format_file_size(size):
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.2f} GB"


def update_status(root, label, text):
    try:
        if root.winfo_exists():
            root.after(0, lambda: label.config(text=text))
    except Exception:
        pass


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
        try:
            dialog.destroy()
        except Exception:
            pass

    def download():
        result["download"] = True
        try:
            dialog.destroy()
        except Exception:
            pass

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


# 네트워크 연결 검사 (스레드 처리로 UI 프리징 방지)
def check_internet_async(root, callback):
    def worker():
        connected = False
        try:
            req = urllib.request.Request("https://www.google.com/generate_204", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                connected = (resp.status in (200, 204))
        except Exception:
            connected = False
        root.after(0, lambda: callback(connected))

    threading.Thread(target=worker, daemon=True).start()


# GitHub 릴리스 최신 정보 조회 (스레드 처리로 안전하게 데이터 수신)
def get_latest_release_async(root, callback):
    def worker():
        try:
            req = urllib.request.Request(
                GITHUB_RELEASE_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "Novel-Syosetu-Kakuyomu-Downloader-Translator"
                }
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                data = json.loads(response.read().decode("utf-8"))
            root.after(0, lambda: callback(data, None))
        except Exception as e:
            root.after(0, lambda: callback(None, e))

    threading.Thread(target=worker, daemon=True).start()


def download_update(root, sub_label, asset, callback):
    download_url = asset.get("browser_download_url")
    file_name = asset.get("name")
    expected_digest = asset.get("digest", "")

    if not download_url or not file_name:
        update_status(root, sub_label, "업데이트 파일 정보가 올바르지 않습니다.")
        root.after(1500, lambda: callback(False))
        return

    if expected_digest.startswith("sha256:"):
        expected_digest = expected_digest[7:]

    expected_digest = expected_digest.strip().lower()

    if not expected_digest:
        print("[업데이트 검증 실패] GitHub Release에 SHA-256 digest가 없습니다.")
        update_status(root, sub_label, "업데이트 파일의 SHA-256 정보를 찾을 수 없습니다.")
        root.after(1500, lambda: callback(False))
        return

    save_path = os.path.join(os.getcwd(), file_name)
    temp_path = save_path + ".download"

    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception:
        pass

    update_status(root, sub_label, "새로운 버전 다운로드 준비 중...")

    def worker():
        try:
            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            sha256 = hashlib.sha256()

            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0

                with open(temp_path, "wb") as file:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break

                        file.write(chunk)
                        sha256.update(chunk)
                        downloaded += len(chunk)

                        if total_size:
                            percent = int(downloaded / total_size * 100)
                            update_status(root, sub_label, f"다운로드 중... {percent}%")
                        else:
                            update_status(root, sub_label, f"다운로드 중... {format_file_size(downloaded)}")

            actual_digest = sha256.hexdigest().lower()

            print(f"[업데이트 SHA-256] 예상: {expected_digest}")
            print(f"[업데이트 SHA-256] 실제: {actual_digest}")

            if actual_digest != expected_digest:
                print("[업데이트 검증 실패] SHA-256 불일치")
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception:
                    pass
                update_status(root, sub_label, "업데이트 파일 검증에 실패했습니다.")
                root.after(1500, lambda: callback(False))
                return

            print("[업데이트 검증 성공] SHA-256 일치")
            update_status(root, sub_label, "업데이트 파일 검증 완료!")

            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except Exception as e:
                    print(f"[기존 파일 교체 실패] {e}")
                    try:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except Exception:
                        pass
                    update_status(root, sub_label, "기존 업데이트 파일을 교체할 수 없습니다.")
                    root.after(1500, lambda: callback(False))
                    return

            os.replace(temp_path, save_path)
            update_status(root, sub_label, "다운로드 및 검증 완료! 프로그램을 재시작합니다.")

            def restart():
                try:
                    if save_path.lower().endswith(".exe"):
                        subprocess.Popen([save_path], close_fds=True)
                finally:
                    root.destroy()

            root.after(1200, restart)

        except Exception as e:
            print(f"[업데이트 다운로드 실패]: {e}")
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            update_status(root, sub_label, "업데이트 다운로드 실패")
            root.after(1500, lambda: callback(False))

    threading.Thread(target=worker, daemon=True).start()


def check_and_update(root, sub_label, callback, retry=0):
    update_status(root, sub_label, "인터넷 연결 확인 중...")

    def internet_done(connected):
        if connected:
            if V is None:
                callback(True)
                return

            update_status(root, sub_label, "최신 버전 확인 중...")

            def release_done(release, error):
                if error is not None or release is None:
                    print(f"[업데이트 확인 실패 또는 릴리스 없음] {error}")
                    # 조회 실패 시 프로그램이 멈추지 않고 그대로 메인 실행으로 진행
                    callback(True)
                    return

                latest_version = release.get("tag_name", "")

                if not latest_version or latest_version == str(V):
                    callback(True)
                    return

                update_status(root, sub_label, f"새로운 버전 발견 ({latest_version})")

                download, asset = show_update_dialog(root, release)

                if not download or not asset:
                    update_status(root, sub_label, "업데이트를 건너뛰었습니다.")
                    root.after(700, lambda: callback(True))
                    return

                download_update(root, sub_label, asset, callback)

            get_latest_release_async(root, release_done)
            return

        if retry >= 3:
            update_status(root, sub_label, "인터넷 연결이 없습니다. 프로그램을 종료합니다.")
            root.after(1500, lambda: root.destroy())
            return

        update_status(root, sub_label, f"인터넷 연결 실패. {3 - retry}초 후 재시도...")
        root.after(1000, lambda: check_and_update(root, sub_label, callback, retry + 1))

    check_internet_async(root, internet_done)


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def start_main_app(root, sub_label, pre_file):
    def launch():
        update_status(root, sub_label, "메인 프로그램을 불러오는 중...")

        if pre_file:
            abs_file_path = os.path.abspath(pre_file)

            if os.path.exists(abs_file_path):
                ext = os.path.splitext(abs_file_path)[1].lower()

                if ext in [".bat", ".cmd"]:
                    update_status(root, sub_label, "사전 작업 실행 중...")

                    file_dir = os.path.dirname(abs_file_path)
                    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

                    try:
                        subprocess.run(f'"{abs_file_path}"', shell=True, cwd=file_dir, creationflags=creationflags)
                    except Exception as e:
                        print(f"[사전 작업 실패] {e}")
            else:
                update_status(root, sub_label, "지정된 경로의 파일을 찾을 수 없습니다.")
                root.after(1500, lambda: root.destroy())
                return

        update_status(root, sub_label, "메인 프로그램을 불러오는 중...")

        import src.main.main as main

        def start():
            root.withdraw()

        main.main(start)

        print("exit_root?")
        try:
            root.destroy()
        except Exception:
            pass
        print("exit_root")

    check_and_update(root, sub_label, lambda success: launch() if success else None)


def close_app(root):
    try:
        root.destroy()
    except Exception:
        pass


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

    progress = ttk.Progressbar(progress_frame, style="Custom.Horizontal.TProgressbar", mode="indeterminate")
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

    drag_widgets = [canvas, main_frame, top_bar, title_label, sub_label, progress_frame, progress, version_label, icon_label]
    enable_window_drag(root, drag_widgets)

    root.protocol("WM_DELETE_WINDOW", lambda: close_app(root))

    root.after(100, lambda: start_main_app(root, sub_label, pre_file))
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Splash Screen Loader")
    parser.add_argument("-f", "--file", type=str, help="실행할 절대경로 배치 파일", default=None)
    args = parser.parse_args()
    create_splash(pre_file=args.file)


if __name__ == "__main__":
    main()