import os
import re
import secrets
import string
from .utils import urljoin

class MediaHandler:
    @staticmethod
    def generate_random_filename(img_dir, ext=".jpg"):
        chars = string.ascii_letters + string.digits
        while True:
            rand_name = "".join(secrets.choice(chars) for _ in range(16))
            filename = f"{rand_name}{ext}"
            full_path = os.path.join(img_dir, filename)
            if not os.path.exists(full_path):
                return filename, full_path

    @staticmethod
    def process_images(content_element, page_url, session, outfolder, is_r18=False, req_func=None, printcall=print):
        img_targets = []
        for tag in content_element.find_all(["img", "a"]):
            if tag.name == "img" and tag.get("src"):
                img_targets.append((tag, tag.get("src")))
            elif tag.name == "a" and tag.get("href"):
                href = tag.get("href")
                if (
                    tag.get("name") == "img"
                    or tag.get("alt") == "挿絵"
                    or "挿絵" in tag.get_text()
                    or "/img/" in href
                    or re.search(r'\.(png|jpg|jpeg|gif|webp)', href, re.I)
                ):
                    img_targets.append((tag, href))

        if not img_targets:
            return False

        img_dir = os.path.join(outfolder, "img")
        os.makedirs(img_dir, exist_ok=True)
        has_downloaded_img = False

        for tag, img_url in img_targets:
            full_img_url = urljoin(page_url, img_url)
            ext = os.path.splitext(full_img_url.split("?")[0])[1]
            if not ext or len(ext) > 5:
                ext = ".jpg"

            filename, file_save_path = MediaHandler.generate_random_filename(img_dir, ext)

            try:
                if req_func:
                    img_res = req_func(full_img_url, session=session, is_r18=is_r18, headers={"Referer": page_url}, timeout=30)
                else:
                    img_res = session.get(full_img_url, timeout=30)

                if img_res.status_code == 200:
                    with open(file_save_path, "wb") as f_img:
                        f_img.write(img_res.content)
                    tag.replace_with(f"-img-:{filename}")
                    has_downloaded_img = True
                else:
                    tag.decompose()
            except Exception as err:
                printcall(f"이미지 다운로드 실패 ({full_img_url}): {err}")
                tag.decompose()

        return has_downloaded_img