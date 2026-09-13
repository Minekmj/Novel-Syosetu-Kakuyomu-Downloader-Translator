import os
import socket
import string
import secrets
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image
import qrcode

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel


def _get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def _create_handler(target_file_path: str, valid_token: str):
    class FileDownloadHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == f"/{valid_token}":
                if not os.path.isfile(target_file_path):
                    self.send_error(404, "File not found")
                    return

                file_size = os.path.getsize(target_file_path)
                file_name = os.path.basename(target_file_path)
                encoded_filename = urllib.parse.quote(file_name)

                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{encoded_filename}")
                self.send_header("Content-Length", str(file_size))
                self.end_headers()

                with open(target_file_path, "rb") as f:
                    while chunk := f.read(1024 * 64):
                        self.wfile.write(chunk)
            else:
                self.send_error(404, "Not Found")

        def log_message(self, format, *args):
            pass

    return FileDownloadHandler


def Make_Qrcode(path: str, timer: QLabel, out_time: int = 30) -> Image.Image:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

    local_ip = _get_local_ip()
    handler = _create_handler(path, token)
    server = HTTPServer(("0.0.0.0", 0), handler)
    assigned_port = server.server_address[1]

    download_url = f"http://{local_ip}:{assigned_port}/{token}"

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    remaining = out_time
    timer.setText(f"({remaining}초)")

    qtimer = QTimer(timer)

    def on_tick():
        nonlocal remaining
        remaining -= 1
        if remaining > 0:
            timer.setText(f"({remaining}초)")
        else:
            timer.setText("(만료됨)")
            qtimer.stop()
            threading.Thread(target=server.shutdown, daemon=True).start()

    qtimer.timeout.connect(on_tick)
    qtimer.start(1000)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(download_url)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    return qr_img