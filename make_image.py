import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_cover_image(build_dir, book_title):
    width, height = 1000, 1500

    image = Image.new("RGB", (width, height), "#F5F1EA")
    draw = ImageDraw.Draw(image)

    font_candidates = [
        "NanumMyeongjo.ttf",
        "NanumMyeongjoBold.ttf",
        "batang.ttc",
        "batang.ttf",
        "KoPubWorldBatangMedium.ttf",
        "malgun.ttf",
    ]

    font_path = None

    for font_name in font_candidates:
        paths = [
            os.path.join("C:\\Windows\\Fonts", font_name),
            font_name,
        ]

        for path in paths:
            if os.path.exists(path):
                font_path = path
                break

        if font_path:
            break

    def load_font(size, bold=False):
        candidates = []

        if bold:
            candidates.extend([
                "NanumMyeongjoBold.ttf",
                "malgunbd.ttf",
                "batang.ttc",
            ])

        candidates.extend(font_candidates)

        for name in candidates:
            paths = [
                os.path.join("C:\\Windows\\Fonts", name),
                name,
            ]

            for path in paths:
                if os.path.exists(path):
                    try:
                        return ImageFont.truetype(path, size)
                    except Exception:
                        pass

        return ImageFont.load_default()

    parts = [p.strip() for p in book_title.split("|", 1)]

    main_title = parts[0] if parts else book_title
    sub_title = parts[1] if len(parts) > 1 else ""

    bg = Image.new("RGB", (width, height))
    bg_pixels = bg.load()

    top_color = (248, 245, 239)
    bottom_color = (232, 226, 216)

    for y in range(height):
        t = y / (height - 1)

        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)

        for x in range(width):
            bg_pixels[x, y] = (r, g, b)

    image = bg
    draw = ImageDraw.Draw(image)
    
    random.seed(17)

    for _ in range(12000):
        x = random.randrange(width)
        y = random.randrange(height)

        base = image.getpixel((x, y))
        variation = random.choice([-2, -1, 1, 2])

        color = tuple(
            max(0, min(255, c + variation))
            for c in base
        )

        draw.point((x, y), fill=color)

    margin = 55

    draw.rounded_rectangle(
        (
            margin,
            margin,
            width - margin,
            height - margin
        ),
        radius=18,
        outline="#81796D",
        width=2
    )

   
    inner_margin = 72

    draw.rounded_rectangle(
        (
            inner_margin,
            inner_margin,
            width - inner_margin,
            height - inner_margin
        ),
        radius=12,
        outline="#C8C0B4",
        width=1
    )

    center_x = width // 2

    ornament_y = 185
    ornament_width = 110

    draw.line(
        (
            center_x - ornament_width,
            ornament_y,
            center_x - 22,
            ornament_y
        ),
        fill="#9B9286",
        width=2
    )

    draw.line(
        (
            center_x + 22,
            ornament_y,
            center_x + ornament_width,
            ornament_y
        ),
        fill="#9B9286",
        width=2
    )

   
    diamond = [
        (center_x, ornament_y - 8),
        (center_x + 8, ornament_y),
        (center_x, ornament_y + 8),
        (center_x - 8, ornament_y)
    ]

    draw.polygon(
        diamond,
        fill="#70675B"
    )

    max_title_width = 700
    title_size = 100

    while title_size >= 42:
        title_font = load_font(title_size, bold=True)

        bbox = title_font.getbbox(main_title)
        title_width = bbox[2] - bbox[0]

        if title_width <= max_title_width:
            break

        title_size -= 4

    lines = []
    current = ""

    for char in main_title:
        test = current + char
        bbox = title_font.getbbox(test)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_title_width:
            current = test
        else:
            if current:
                lines.append(current)

            current = char.strip()

    if current:
        lines.append(current)

    line_spacing = 25
    title_heights = []

    for line in lines:
        bbox = title_font.getbbox(line)
        title_heights.append(bbox[3] - bbox[1])

    total_title_height = (
        sum(title_heights) +
        line_spacing * max(0, len(lines) - 1)
    )

    title_center_y = 665
    title_y = title_center_y - total_title_height // 2

    for index, line in enumerate(lines):
        bbox = title_font.getbbox(line)

        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = center_x - text_width // 2

        draw.text(
            (x, title_y),
            line,
            font=title_font,
            fill="#25221E"
        )

        title_y += text_height + line_spacing

    if sub_title:
        sub_font_size = 34

        while sub_font_size >= 22:
            sub_font = load_font(sub_font_size)

            bbox = sub_font.getbbox(sub_title)
            sub_width = bbox[2] - bbox[0]

            if sub_width <= 650:
                break

            sub_font_size -= 2

       
        divider_y = title_y + 45

        draw.line(
            (
                center_x - 28,
                divider_y,
                center_x + 28,
                divider_y
            ),
            fill="#8F877C",
            width=2
        )

        sub_y = divider_y + 30

        bbox = sub_font.getbbox(sub_title)
        sub_width = bbox[2] - bbox[0]

        sub_x = center_x - sub_width // 2

        draw.text(
            (sub_x, sub_y),
            sub_title,
            font=sub_font,
            fill="#686158"
        )

    bottom_y = 1245

    draw.line(
        (
            center_x - 100,
            bottom_y,
            center_x + 100,
            bottom_y
        ),
        fill="#AAA196",
        width=1
    )

    draw.ellipse(
        (
            center_x - 4,
            bottom_y - 4,
            center_x + 4,
            bottom_y + 4
        ),
        fill="#81786C"
    )

    small_font = load_font(22)

    footer_text = "NOVEL"

    bbox = small_font.getbbox(footer_text)
    footer_width = bbox[2] - bbox[0]

    draw.text(
        (
            center_x - footer_width // 2,
            bottom_y + 35
        ),
        footer_text,
        font=small_font,
        fill="#8B8378"
    )

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

   
    overlay_draw.rounded_rectangle(
        (
            42,
            42,
            width - 42,
            height - 42
        ),
        radius=25,
        outline=(60, 50, 40, 25),
        width=12
    )

    overlay = overlay.filter(ImageFilter.GaussianBlur(5))

    image = Image.alpha_composite(
        image.convert("RGBA"),
        overlay
    ).convert("RGB")

    cover_dir = os.path.join(build_dir, "OEBPS")
    os.makedirs(cover_dir, exist_ok=True)

    cover_image_path = os.path.join(
        cover_dir,
        "cover.png"
    )

    image.save(
        cover_image_path,
        "PNG"
    )

    return cover_image_path