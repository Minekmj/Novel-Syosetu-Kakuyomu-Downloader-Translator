import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from src.down.make_img_config import *

def load_font(size, bold=False):
    candidates = []
    if bold:
        candidates.extend(FONT_BOLD_CANDIDATES)
    candidates.extend(FONT_CANDIDATES)

    for name in candidates:
        for search_dir in FONT_SEARCH_DIRS:
            path = os.path.join(search_dir, name) if search_dir else name
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass

    return ImageFont.load_default()


def create_cover_image(build_dir, book_title):
    width, height = CANVAS_WIDTH, CANVAS_HEIGHT
    center_x = width // 2

    image = Image.new("RGB", (width, height))
    bg_pixels = image.load()

    for y in range(height):
        t = y / (height - 1)
        r = int(BG_TOP_COLOR[0] * (1 - t) + BG_BOTTOM_COLOR[0] * t)
        g = int(BG_TOP_COLOR[1] * (1 - t) + BG_BOTTOM_COLOR[1] * t)
        b = int(BG_TOP_COLOR[2] * (1 - t) + BG_BOTTOM_COLOR[2] * t)

        for x in range(width):
            bg_pixels[x, y] = (r, g, b)

    draw = ImageDraw.Draw(image)

    if NOISE_ENABLED:
        random.seed(NOISE_SEED)
        for _ in range(NOISE_COUNT):
            x = random.randrange(width)
            y = random.randrange(height)
            base = image.getpixel((x, y))
            variation = random.choice(NOISE_VARIATION_RANGE)
            color = tuple(max(0, min(255, c + variation)) for c in base)
            draw.point((x, y), fill=color)

    draw.rounded_rectangle(
        (
            OUTER_BORDER_MARGIN,
            OUTER_BORDER_MARGIN,
            width - OUTER_BORDER_MARGIN,
            height - OUTER_BORDER_MARGIN,
        ),
        radius=OUTER_BORDER_RADIUS,
        outline=OUTER_BORDER_COLOR,
        width=OUTER_BORDER_WIDTH,
    )
    draw.rounded_rectangle(
        (
            INNER_BORDER_MARGIN,
            INNER_BORDER_MARGIN,
            width - INNER_BORDER_MARGIN,
            height - INNER_BORDER_MARGIN,
        ),
        radius=INNER_BORDER_RADIUS,
        outline=INNER_BORDER_COLOR,
        width=INNER_BORDER_WIDTH,
    )

    if TOP_ORNAMENT_ENABLED:
        draw.line(
            (
                center_x - TOP_ORNAMENT_LINE_WIDTH_SPAN,
                TOP_ORNAMENT_Y,
                center_x - TOP_ORNAMENT_GAP,
                TOP_ORNAMENT_Y,
            ),
            fill=TOP_ORNAMENT_LINE_COLOR,
            width=TOP_ORNAMENT_LINE_THICKNESS,
        )
        draw.line(
            (
                center_x + TOP_ORNAMENT_GAP,
                TOP_ORNAMENT_Y,
                center_x + TOP_ORNAMENT_LINE_WIDTH_SPAN,
                TOP_ORNAMENT_Y,
            ),
            fill=TOP_ORNAMENT_LINE_COLOR,
            width=TOP_ORNAMENT_LINE_THICKNESS,
        )
        d_sz = TOP_ORNAMENT_DIAMOND_SIZE
        diamond = [
            (center_x, TOP_ORNAMENT_Y - d_sz),
            (center_x + d_sz, TOP_ORNAMENT_Y),
            (center_x, TOP_ORNAMENT_Y + d_sz),
            (center_x - d_sz, TOP_ORNAMENT_Y),
        ]
        draw.polygon(diamond, fill=TOP_ORNAMENT_DIAMOND_COLOR)

    parts = [p.strip() for p in book_title.split(TITLE_DELIMITER, 1)]
    main_title = parts[0] if parts else book_title
    sub_title = parts[1] if len(parts) > 1 else ""

    title_size = TITLE_FONT_SIZE_MAX
    while title_size >= TITLE_FONT_SIZE_MIN:
        title_font = load_font(title_size, bold=True)
        bbox = title_font.getbbox(main_title)
        if (bbox[2] - bbox[0]) <= TITLE_MAX_WIDTH:
            break
        title_size -= TITLE_FONT_SIZE_STEP

    lines = []
    current = ""
    for char in main_title:
        test = current + char
        bbox = title_font.getbbox(test)
        if (bbox[2] - bbox[0]) <= TITLE_MAX_WIDTH:
            current = test
        else:
            if current:
                lines.append(current)
            current = char.strip()
    if current:
        lines.append(current)

    title_heights = [title_font.getbbox(line)[3] - title_font.getbbox(line)[1] for line in lines]
    total_title_height = sum(title_heights) + TITLE_LINE_SPACING * max(0, len(lines) - 1)
    title_y = TITLE_CENTER_Y - total_title_height // 2

    for line in lines:
        bbox = title_font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = center_x - text_width // 2

        draw.text((x, title_y), line, font=title_font, fill=TITLE_COLOR)
        title_y += text_height + TITLE_LINE_SPACING

    if sub_title:
        sub_font_size = SUBTITLE_FONT_SIZE_MAX
        while sub_font_size >= SUBTITLE_FONT_SIZE_MIN:
            sub_font = load_font(sub_font_size)
            bbox = sub_font.getbbox(sub_title)
            if (bbox[2] - bbox[0]) <= SUBTITLE_MAX_WIDTH:
                break
            sub_font_size -= SUBTITLE_FONT_SIZE_STEP

        divider_y = title_y + SUB_DIVIDER_OFFSET_Y
        draw.line(
            (
                center_x - SUB_DIVIDER_HALF_WIDTH,
                divider_y,
                center_x + SUB_DIVIDER_HALF_WIDTH,
                divider_y,
            ),
            fill=SUB_DIVIDER_COLOR,
            width=SUB_DIVIDER_WIDTH,
        )

        sub_y = divider_y + SUBTITLE_TEXT_OFFSET_Y
        bbox = sub_font.getbbox(sub_title)
        sub_width = bbox[2] - bbox[0]
        sub_x = center_x - sub_width // 2

        draw.text((sub_x, sub_y), sub_title, font=sub_font, fill=SUBTITLE_COLOR)

    if BOTTOM_ORNAMENT_ENABLED:
        draw.line(
            (
                center_x - BOTTOM_LINE_HALF_WIDTH,
                BOTTOM_Y,
                center_x + BOTTOM_LINE_HALF_WIDTH,
                BOTTOM_Y,
            ),
            fill=BOTTOM_LINE_COLOR,
            width=BOTTOM_LINE_WIDTH,
        )
        dot_r = BOTTOM_DOT_RADIUS
        draw.ellipse(
            (
                center_x - dot_r,
                BOTTOM_Y - dot_r,
                center_x + dot_r,
                BOTTOM_Y + dot_r,
            ),
            fill=BOTTOM_DOT_COLOR,
        )

        if FOOTER_TEXT:
            small_font = load_font(FOOTER_FONT_SIZE)
            bbox = small_font.getbbox(FOOTER_TEXT)
            footer_width = bbox[2] - bbox[0]
            draw.text(
                (center_x - footer_width // 2, BOTTOM_Y + FOOTER_OFFSET_Y),
                FOOTER_TEXT,
                font=small_font,
                fill=FOOTER_TEXT_COLOR,
            )

    if OVERLAY_ENABLED:
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        overlay_draw.rounded_rectangle(
            (
                OVERLAY_MARGIN,
                OVERLAY_MARGIN,
                width - OVERLAY_MARGIN,
                height - OVERLAY_MARGIN,
            ),
            radius=OVERLAY_RADIUS,
            outline=OVERLAY_OUTLINE_COLOR,
            width=OVERLAY_OUTLINE_WIDTH,
        )
        overlay = overlay.filter(ImageFilter.GaussianBlur(OVERLAY_BLUR_RADIUS))
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

    # 10. 파일 저장
    cover_dir = os.path.join(build_dir, OUTPUT_SUBDIR)
    os.makedirs(cover_dir, exist_ok=True)
    cover_image_path = os.path.join(cover_dir, OUTPUT_FILENAME)
    image.save(cover_image_path, "PNG")

    return cover_image_path