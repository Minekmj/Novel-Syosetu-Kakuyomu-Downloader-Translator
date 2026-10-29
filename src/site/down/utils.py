import os
import re

def urljoin(base_url: str, relative_url: str) -> str:
    relative_url = relative_url.strip()

    if relative_url.startswith("http://") or relative_url.startswith("https://"):
        return relative_url

    scheme = ""
    if base_url.startswith("https://"):
        scheme = "https:"
        base_without_scheme = base_url[8:]
    elif base_url.startswith("http://"):
        scheme = "http:"
        base_without_scheme = base_url[7:]
    else:
        scheme = "https:"
        base_without_scheme = base_url

    if relative_url.startswith("//"):
        return f"{scheme}{relative_url}"

    if "/" in base_without_scheme:
        domain, base_path = base_without_scheme.split("/", 1)
        base_path = "/" + base_path
    else:
        domain = base_without_scheme
        base_path = "/"

    if relative_url.startswith("/"):
        return f"{scheme}//{domain}{relative_url}"

    if not base_path.endswith("/"):
        base_path = base_path.rsplit("/", 1)[0] + "/"

    full_path = base_path + relative_url
    segments = full_path.split("/")
    resolved_segments = []

    for seg in segments:
        if seg in ("", "."):
            continue
        elif seg == "..":
            if resolved_segments:
                resolved_segments.pop()
        else:
            resolved_segments.append(seg)

    normalized_path = "/" + "/".join(resolved_segments)

    if relative_url.endswith("/") and not normalized_path.endswith("/"):
        normalized_path += "/"

    return f"{scheme}//{domain}{normalized_path}"

def clean_raw_title(title: str) -> str:
    r_title = re.sub(r"^【.*?】", "", title)
    r_title = re.sub(r"【.*?】$", "", r_title)
    return r_title

def prepare_title_path(book_title: str, raw_title: str, base_data):
    if raw_title != "":
        book_title = raw_title
    r_book_title = clean_raw_title(book_title)
    r_book_title = re.sub(r'[\\/:*?"<>|]', "_", r_book_title).strip()
    if base_data and hasattr(base_data, "sanitize_file_name"):
        r_book_title = base_data.sanitize_file_name(r_book_title)

    outfolder = os.environ.get("minedown_setting_src", "./out/")
    title_path = os.path.join(outfolder, "list", r_book_title)
    os.makedirs(title_path, exist_ok=True)
    return book_title, title_path