import argparse
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

THEME_CONFIG = {
    "bg_color": "#1E1E1E",
    "border_color": "#007ACC",
    "title_color": "#FFFFFF",
    "sub_color": "#AAAAAA",
    "progress_color": "#007ACC",
    "font_family": "맑은 고딕",
    "window_size": (360, 190),
}

def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
       
        return os.path.join(sys._MEIPASS, relative_path)
    
   
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, relative_path)

def update_status(root, label, text):
    root.after(0, lambda: label.config(text=text))

def start_main_app(root, sub_label, pre_file):
   
    if pre_file:
        abs_file_path = os.path.abspath(pre_file)
        
        if os.path.exists(abs_file_path):
            ext = os.path.splitext(abs_file_path)[1].lower()
            if ext in [".bat", ".cmd"]:
                update_status(root, sub_label, "배치 파일 실행 중...")

                file_dir = os.path.dirname(abs_file_path)
                creationflags = (
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )

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
    main.main(lambda: root.after(0, root.withdraw), lambda: root.after(0, root.destroy))

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

    title_label = tk.Label(
        root,
        text="프로그램을 불러오는 중...",
        font=(THEME_CONFIG["font_family"], 13, "bold"),
        fg=THEME_CONFIG["title_color"],
        bg=THEME_CONFIG["bg_color"],
    )
    title_label.pack(pady=(35, 8))

    sub_label = tk.Label(
        root,
        text="잠시만 기다려 주세요.",
        font=(THEME_CONFIG["font_family"], 9),
        fg=THEME_CONFIG["sub_color"],
        bg=THEME_CONFIG["bg_color"],
    )
    sub_label.pack(pady=(0, 20))

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
    progress.pack(pady=5)
    progress.start(12)
    
    threading.Thread(
        target=start_main_app,
        args=(root, sub_label, pre_file),
        daemon=True,
    ).start()

    root.mainloop()

def main():
    parser = argparse.ArgumentParser(description="Splash Screen Loader")
    parser.add_argument("-f", "--file", type=str, help="실행할 절대경로 배치 파일", default=None)
    args = parser.parse_args()

    create_splash(pre_file=args.file)

if __name__ == "__main__":
    main()