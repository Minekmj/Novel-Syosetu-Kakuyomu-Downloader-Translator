import html
import os
import re
import time
import zipfile
import shutil
import src.down.downin as downin
from src.down.make_image import create_cover_image

from src.system.config import USE_LOCAL_AI
import src.down.local_ai as lai

def print_progress(current, total, prefix="진행", width=30):
    if total <= 0:
        return

    percent = current / total
    filled = int(width * percent)
    bar = "█" * filled + "░" * (width - filled)

    print(
        f"\r[{prefix}] [{bar}] {percent * 100:6.2f}% ({current}/{total})",
        end="",
        flush=True
    )

def print_ai_progress(current, total):
    print_progress(current, total, "AI 문단 분석")

def extract_number(filename):
    match = re.search(r'(\d+)번', filename)
    return int(match.group(1)) if match else 9999

def get_image_media_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".gif":
        return "image/gif"
    elif ext == ".webp":
        return "image/webp"
    return "image/jpeg"

def create_epub_from_merged_txt(input_txt_path="", base_dir=".", txt_value="", RAW=False):
    global IS_START

    if USE_LOCAL_AI:
        while lai.AI_MODEL_INSTANCE is None:
            time.sleep(1)

    while IS_START:
        time.sleep(1)

    IS_START = True

    try:
        if txt_value != "":
            content = txt_value
        else:
            if not os.path.exists(input_txt_path):
                return False
            try:
                with open(input_txt_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(input_txt_path, "r", encoding="cp949") as f:
                    content = f.read()
            f = content.splitlines()
            if len(f) >= 3 and f[2] == "(raw)":
                RAW = True

        first_line = content.splitlines()[0].strip()
        if first_line and set(first_line) == {"="}:
            if input_txt_path != "":
                filepath = input_txt_path
                
                ff = os.path.basename(os.path.dirname(filepath))

                filename = os.path.splitext(os.path.basename(filepath))[0]

                if filename.startswith("["):
                    s = re.sub(r"^\[.*?[\]\"'\)]\s*", "", filename)
                else:
                    s = filename

                result = f"{ff}\n{s}\n+---+\n"
                
                RAW = True

                content = result + content
        content = content.replace("\r\n", "\n")
        content = content.replace("\r", "\n")

        delimiter = downin.SPLIT_POINT
        out_folder_base = downin.base_data.OUTFOLDER
        src_img_dir = os.path.join(out_folder_base, "img")
        if not os.path.exists(src_img_dir):
            src_img_dir = os.path.join("out", "img")

        # 본문 내 사용된 이미지 추적 (중복 방지)
        used_images = set()

        def process_img_tags_in_line(text):
            """-img-:파일명 패턴을 HTML <img> 태그로 변환하고 used_images에 기록"""
            def replacer(match):
                img_name = match.group(1).strip()
                used_images.add(img_name)
                return f'</p><p class="center"><img src="images/{img_name}" alt="{img_name}"/></p><p>'

            if "-img-:" in text:
                text = re.sub(r'-img-:\s*([^\s<>"\'\r\n]+)', replacer, text)
            return text

        if RAW:
            lines = content.splitlines()

            if not lines:
                return False

            header_title = lines[0].strip() if len(lines) > 0 else "Untitled"
            header_subtitle = lines[1].strip() if len(lines) > 1 else ""

            book_title = (
                f"{header_title} | {header_subtitle}"
                if header_subtitle
                else header_title
            )
            book_title = book_title.replace("<", "〈").replace(">", "〉")

            body_start = 3

            while body_start < len(lines) and not lines[body_start].strip():
                body_start += 1

            if body_start < len(lines) and lines[body_start].strip() == delimiter:
                body_start += 1

            raw_lines = lines[body_start:]

            equal_line_pattern = re.compile(r"^={4,}\s*$")

            chapter_sections = []
            current_body = []
            current_title = None
            i = 0

            while i < len(raw_lines):
                if equal_line_pattern.fullmatch(raw_lines[i].strip()):
                    separator_start = i

                    j = i + 1
                    while j < len(raw_lines) and not raw_lines[j].strip():
                        j += 1

                    if j < len(raw_lines) and not equal_line_pattern.fullmatch(raw_lines[j].strip()):
                        k = j + 1

                        while k < len(raw_lines) and not raw_lines[k].strip():
                            k += 1

                        if k < len(raw_lines) and equal_line_pattern.fullmatch(raw_lines[k].strip()):
                            title_lines = raw_lines[j:k]

                            if len(title_lines) == 1:
                                if current_title is not None:
                                    chapter_sections.append(
                                        (
                                            current_title,
                                            current_body
                                        )
                                    )

                                elif current_body:
                                    pass

                                current_title = title_lines[0].strip()
                                current_body = []

                                i = k + 1
                                continue

                            block_end = k + 1

                            current_body.extend(
                                raw_lines[separator_start:block_end]
                            )

                            i = block_end
                            continue

                    current_body.append(raw_lines[i])
                    i += 1
                    continue

                current_body.append(raw_lines[i])
                i += 1

            if current_title is not None:
                chapter_sections.append(
                    (
                        current_title,
                        current_body
                    )
                )
            elif current_body:
                chapter_sections.append(
                    (
                        header_subtitle if header_subtitle else header_title,
                        current_body
                    )
                )
                
            if not chapter_sections:
                fallback_body = raw_lines[:]
                while fallback_body and not fallback_body[0].strip():
                    fallback_body.pop(0)

                if fallback_body:
                    chapter_sections.append(
                        (
                            header_subtitle if header_subtitle else header_title,
                            fallback_body
                        )
                    )

            build_dir = os.path.join(
                base_dir,
                "temp_epub_build_with_cover"
            )

            if os.path.exists(build_dir):
                shutil.rmtree(build_dir)

            os.makedirs(build_dir, exist_ok=True)
            os.makedirs(os.path.join(build_dir, "META-INF"), exist_ok=True)
            os.makedirs(os.path.join(build_dir, "OEBPS"), exist_ok=True)
            os.makedirs(os.path.join(build_dir, "OEBPS", "css"), exist_ok=True)
            os.makedirs(os.path.join(build_dir, "OEBPS", "images"), exist_ok=True)

            with open(
                os.path.join(build_dir, "mimetype"),
                "w",
                encoding="utf-8"
            ) as f:
                f.write("application/epub+zip")

            container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles>
<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
</rootfiles>
</container>"""

            with open(
                os.path.join(build_dir, "META-INF", "container.xml"),
                "w",
                encoding="utf-8"
            ) as f:
                f.write(container_xml)

            css_content = """@charset "utf-8";

html {
    margin: 0;
    padding: 0;
}

body {
    margin: 0;
    padding: 0;
    font-family: serif;
    line-height: 1.75;
    word-break: keep-all;
    overflow-wrap: break-word;
    -webkit-text-size-adjust: none;
}

p {
    margin: 0;
    padding: 0;
    text-indent: 1em;
    text-align: left;
}

p + p {
    margin-top: 0.3em;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
}

strong, b {
    font-weight: bold;
}

.chapter-title {
    margin: 0 0 2.2em 0;
    padding: 0;
    text-align: center;
    text-indent: 0;
    font-size: 1.35em;
    font-weight: bold;
    line-height: 1.5;
    page-break-after: avoid;
    break-after: avoid-page;
}

.chapter-title + p {
    text-indent: 0;
}

.center {
    margin: 1.2em 0;
    padding: 0;
    text-align: center;
    text-indent: 0;
}

.no-indent {
    text-indent: 0;
}

@page {
    margin: 5%;
}"""

            with open(
                os.path.join(build_dir, "OEBPS", "css", "style.css"),
                "w",
                encoding="utf-8"
            ) as f:
                f.write(css_content)

            create_cover_image(build_dir, book_title)

            manifest_items = [
                '<item id="css" href="css/style.css" media-type="text/css"/>',
                '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
                '<item id="cover-image" href="cover.png" media-type="image/png"/>'
            ]

            spine_items = []
            toc_items = []

            title_html_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>{book_title}</title>
<link rel="stylesheet" type="text/css" href="css/style.css"/>
</head>
<body>
<div style="width:100%; height:100vh; display:flex; align-items:center;">
<div style="text-align:center; margin:0 auto;">
<h2>{html.escape(header_title)}</h2>
<hr/>
<h3>{html.escape(header_subtitle)}</h3>
</div>
</div>
</body>
</html>"""

            with open(
                os.path.join(build_dir, "OEBPS", "title.xhtml"),
                "w",
                encoding="utf-8"
            ) as f:
                f.write(title_html_content)

            manifest_items.append(
                '<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>'
            )
            spine_items.append('<itemref idref="title"/>')
            toc_items.append(
                '<navPoint id="title" playOrder="0">'
                '<navLabel><text>title</text></navLabel>'
                '<content src="title.xhtml"/>'
                '</navPoint>'
            )

            total_chapters = len(chapter_sections)

            for chapter_index, (chapter_title, chapter_body_lines) in enumerate(
                chapter_sections,
                1
            ):
                if "print_progress" in globals():
                    print_progress(
                        chapter_index,
                        total_chapters,
                        "EPUB 변환"
                    )

                chapter_title = (
                    chapter_title
                    .replace("<", "〈")
                    .replace(">", "〉")
                )

                processed_lines = []

                for line in chapter_body_lines:
                    cleaned = line.rstrip("\r\n")

                    if not cleaned.strip():
                        processed_lines.append("<p><br/></p>")
                        continue

                    cleaned = (
                        cleaned
                        .replace("「", "“")
                        .replace("」", "”")
                        .replace("｢", "“")
                        .replace("｣", "”")
                        .replace("<", "〈")
                        .replace(">", "〉")
                    )

                    cleaned = re.sub(
                        r"\*\*(.*?)\*\*",
                        r"<b>\1</b>",
                        cleaned
                    )

                    # -img- 이미지 태그 변환
                    line_html = f"<p>{cleaned}</p>"
                    line_html = process_img_tags_in_line(line_html)
                    line_html = line_html.replace("<p></p>", "")

                    processed_lines.append(line_html)

                paragraphs = "\n".join(processed_lines)

                ch_id = f"chapter_{chapter_index}"
                ch_filename = f"chapter_{chapter_index}.xhtml"

                chapter_html_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>{html.escape(chapter_title)}</title>
<link rel="stylesheet" type="text/css" href="css/style.css"/>
</head>
<body>
<h2 class="chapter-title">{html.escape(chapter_title)}</h2>
{paragraphs}
</body>
</html>"""

                with open(
                    os.path.join(build_dir, "OEBPS", ch_filename),
                    "w",
                    encoding="utf-8"
                ) as f:
                    f.write(chapter_html_content)

                manifest_items.append(
                    f'<item id="{ch_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>'
                )

                spine_items.append(
                    f'<itemref idref="{ch_id}"/>'
                )

                toc_items.append(
                    f'<navPoint id="{ch_id}" playOrder="{chapter_index}">'
                    f'<navLabel><text>{html.escape(chapter_title)}</text></navLabel>'
                    f'<content src="{ch_filename}"/>'
                    f'</navPoint>'
                )

            if "print_progress" in globals():
                print()

        # ============================================================
        # 일반 EPUB (+---+ 기반 처리)
        # ============================================================
        else:
            content = content.replace("\n\n", "\n")
            content = content.replace('SPLIT_POINT = "+---+"', "+---+")

            sections = [
                s.strip()
                for s in content.split(delimiter)
                if s.strip()
            ]

            if not sections:
                return False

            header_lines = [
                line.strip()
                for line in sections[0].splitlines()
                if line.strip()
            ]

            main_title = (
                header_lines[0]
                if len(header_lines) > 0
                else "Untitled"
            )

            sub_title = (
                header_lines[1]
                if len(header_lines) > 1
                else ""
            )

            book_title = (
                f"{main_title} | {sub_title}"
                if sub_title
                else main_title
            )

            book_title = (
                book_title
                .replace("<", "〈")
                .replace(">", "〉")
            )

            build_dir = os.path.join(
                base_dir,
                "temp_epub_build_with_cover"
            )

            if os.path.exists(build_dir):
                shutil.rmtree(build_dir)

            os.makedirs(build_dir, exist_ok=True)
            os.makedirs(os.path.join(build_dir, "META-INF"), exist_ok=True)
            os.makedirs(os.path.join(build_dir, "OEBPS"), exist_ok=True)
            os.makedirs(os.path.join(build_dir, "OEBPS", "css"), exist_ok=True)
            os.makedirs(os.path.join(build_dir, "OEBPS", "images"), exist_ok=True)

            with open(
                os.path.join(build_dir, "mimetype"),
                "w",
                encoding="utf-8"
            ) as f:
                f.write("application/epub+zip")

            container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles>
<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
</rootfiles>
</container>"""

            with open(
                os.path.join(build_dir, "META-INF", "container.xml"),
                "w",
                encoding="utf-8"
            ) as f:
                f.write(container_xml)

            css_content = """@charset "utf-8";

html { margin: 0; padding: 0; }

body {
    margin: 0;
    padding: 0;
    font-family: serif;
    line-height: 1.75;
    word-break: keep-all;
    overflow-wrap: break-word;
    -webkit-text-size-adjust: none;
}

p {
    margin: 0;
    padding: 0;
    text-indent: 1em;
    text-align: left;
}

p + p {
    margin-top: 0.3em;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
}

strong, b { font-weight: bold; }

.chapter-title {
    margin: 0 0 2.2em 0;
    padding: 0;
    text-align: center;
    text-indent: 0;
    font-size: 1.35em;
    font-weight: bold;
    line-height: 1.5;
    page-break-after: avoid;
    break-after: avoid-page;
}

.chapter-title + p { text-indent: 0; }

.center {
    margin: 1.2em 0;
    padding: 0;
    text-align: center;
    text-indent: 0;
}

.no-indent { text-indent: 0; }

@page { margin: 5%; }"""

            with open(
                os.path.join(build_dir, "OEBPS", "css", "style.css"),
                "w",
                encoding="utf-8"
            ) as f:
                f.write(css_content)

            create_cover_image(build_dir, book_title)

            manifest_items = [
                '<item id="css" href="css/style.css" media-type="text/css"/>',
                '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
                '<item id="cover-image" href="cover.png" media-type="image/png"/>'
            ]

            spine_items = []
            toc_items = []

            title_html_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>{html.escape(book_title)}</title>
<link rel="stylesheet" type="text/css" href="css/style.css"/>
</head>
<body>
<div style="width:100%; height:100vh; display:flex; align-items:center;">
<div style="text-align:center; margin:0 auto;">
<h2>{html.escape(main_title)}</h2>
<hr/>
<h3>{html.escape(sub_title)}</h3>
</div>
</div>
</body>
</html>"""

            with open(
                os.path.join(build_dir, "OEBPS", "title.xhtml"),
                "w",
                encoding="utf-8"
            ) as f:
                f.write(title_html_content)

            manifest_items.append(
                '<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>'
            )

            spine_items.append(
                '<itemref idref="title"/>'
            )

            toc_items.append(
                '<navPoint id="title" playOrder="0">'
                '<navLabel><text>title</text></navLabel>'
                '<content src="title.xhtml"/>'
                '</navPoint>'
            )

            chapter_sections = sections[1:]
            idx = 1
            total_chapters = len(chapter_sections)

            for chapter_index, chapter_text in enumerate(
                chapter_sections,
                1
            ):
                if "print_progress" in globals():
                    print_progress(
                        chapter_index,
                        total_chapters,
                        "EPUB 변환"
                    )

                lines = [
                    line.strip()
                    for line in chapter_text.splitlines()
                    if line.strip()
                ]

                if not lines:
                    continue

                subtitle = (
                    lines[0]
                    .replace("**", "")
                    .replace("<", "〈")
                    .replace(">", "〉")
                )

                raw_body_lines = lines[1:]
                first_body_line = (
                    raw_body_lines[0]
                    if raw_body_lines
                    else ""
                )

                if (
                    first_body_line.startswith("<p")
                    or first_body_line.startswith("<div")
                ):
                    paragraphs = "\n".join(raw_body_lines)
                else:
                    merged_body_lines = raw_body_lines

                    ai_breaks = (
                        lai.ai_paragraph_breaks(merged_body_lines)
                        if "ai_paragraph_breaks" in globals()
                        else [False] * len(merged_body_lines)
                    )

                    processed_lines = []
                    back_center = False

                    for line_index, line in enumerate(
                        merged_body_lines
                    ):
                        cleaned = (
                            line
                            .replace("「", "“")
                            .replace("」", "”")
                            .replace("｢", "“")
                            .replace("｣", "”")
                            .replace("<", "〈")
                            .replace(">", "〉")
                            .replace("（", "'")
                            .replace("）", "'")
                            if globals().get(
                                "USE_Quotation_marks",
                                True
                            )
                            else line
                        )

                        cleaned = re.sub(
                            r"\*\*(.*?)\*\*",
                            r"<b>\1</b>",
                            cleaned
                        )

                        stripped_for_check = re.sub(
                            r"\s+",
                            "",
                            cleaned
                        )

                        start = (
                            "<p><br/></p>"
                            if (
                                (
                                    line_index > 0
                                    and ai_breaks[line_index]
                                )
                                or line_index == 0
                                or back_center
                            )
                            else ""
                        )

                        if (
                            globals().get(
                                "USE_Center_marks",
                                True
                            )
                            and re.fullmatch(
                                r'''[^\w.\\"'「」『』“”‘’!?。…]{1,}''',
                                stripped_for_check
                            )
                        ):
                            line_html = (
                                f"<p><br/></p>"
                                f"<p class='center'>{cleaned}</p>"
                            )
                            back_center = True
                        else:
                            line_html = f"{start}<p>{cleaned}</p>"
                            back_center = False

                        # -img- 이미지 태그 변환
                        line_html = process_img_tags_in_line(line_html)
                        line_html = line_html.replace("<p></p>", "")
                        processed_lines.append(line_html)

                    paragraphs = "\n".join(
                        processed_lines
                    )

                chapter_html_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>{html.escape(subtitle)}</title>
<link rel="stylesheet" type="text/css" href="css/style.css"/>
</head>
<body>
<h2 class="chapter-title">{html.escape(subtitle)}</h2>
{paragraphs}
</body>
</html>"""

                ch_id = f"chapter_{idx}"
                ch_filename = f"chapter_{idx}.xhtml"

                with open(
                    os.path.join(build_dir, "OEBPS", ch_filename),
                    "w",
                    encoding="utf-8"
                ) as f:
                    f.write(chapter_html_content)

                manifest_items.append(
                    f'<item id="{ch_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>'
                )

                spine_items.append(
                    f'<itemref idref="{ch_id}"/>'
                )

                toc_items.append(
                    f'<navPoint id="{ch_id}" playOrder="{idx}">'
                    f'<navLabel><text>{html.escape(subtitle)}</text></navLabel>'
                    f'<content src="{ch_filename}"/>'
                    f'</navPoint>'
                )

                idx += 1

            if "print_progress" in globals():
                print()

        # ============================================================
        # 이미지 파일 복사 및 Manifest 등록
        # ============================================================
        epub_img_dir = os.path.join(build_dir, "OEBPS", "images")
        for img_idx, img_name in enumerate(sorted(used_images), 1):
            src_file = os.path.join(src_img_dir, img_name)
            if os.path.exists(src_file):
                dst_file = os.path.join(epub_img_dir, img_name)
                shutil.copy2(src_file, dst_file)
                media_type = get_image_media_type(img_name)
                manifest_items.append(
                    f'<item id="img_{img_idx}" href="images/{img_name}" media-type="{media_type}"/>'
                )

        # ============================================================
        # OPF / NCX / EPUB 생성
        # ============================================================
        manifest_str = "\n".join(manifest_items)
        spine_str = "\n".join(spine_items)
        toc_str = "\n".join(toc_items)

        content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>{html.escape(book_title)}</dc:title>
<dc:language>ko</dc:language>
<dc:identifier id="BookId">urn:uuid:550e8400-e29b-41d4-a716-446655440000</dc:identifier>
<meta name="cover" content="cover-image"/>
</metadata>
<manifest>
{manifest_str}
</manifest>
<spine toc="ncx">
{spine_str}
</spine>
</package>"""

        with open(
            os.path.join(build_dir, "OEBPS", "content.opf"),
            "w",
            encoding="utf-8"
        ) as f:
            f.write(content_opf)

        toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx-1.0.dtd" version="1.0">
<head>
<meta name="dtb:uid" content="urn:uuid:550e8400-e29b-41d4-a716-446655440000"/>
<meta name="dtb:depth" content="1"/>
</head>
<docTitle>
<text>{html.escape(book_title)}</text>
</docTitle>
<navMap>
{toc_str}
</navMap>
</ncx>"""

        with open(
            os.path.join(build_dir, "OEBPS", "toc.ncx"),
            "w",
            encoding="utf-8"
        ) as f:
            f.write(toc_ncx)

        out_folder = downin.base_data.OUTFOLDER

        os.makedirs(out_folder, exist_ok=True)

        out_folder = os.path.join(
            out_folder,
            "epub"
        )

        os.makedirs(out_folder, exist_ok=True)

        output_epub_path = os.path.join(
            out_folder,
            re.sub(
                r'[\\/:*?"<>|]',
                "_",
                book_title
            ) + ".epub"
        )

        with zipfile.ZipFile(
            output_epub_path,
            "w",
            zipfile.ZIP_DEFLATED
        ) as epub_zip:
            epub_zip.write(
                os.path.join(
                    build_dir,
                    "mimetype"
                ),
                "mimetype",
                compress_type=zipfile.ZIP_STORED
            )

            for root, dirs, files in os.walk(build_dir):
                for file in files:
                    if file == "mimetype":
                        continue

                    full_path = os.path.join(
                        root,
                        file
                    )

                    epub_zip.write(
                        full_path,
                        os.path.relpath(
                            full_path,
                            build_dir
                        )
                    )

        shutil.rmtree(build_dir)

        return True

    finally:
        IS_START = False

lai.setup_local_ai_in_thread(wait=False)