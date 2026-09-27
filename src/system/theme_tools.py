import colorsys

def hex_to_rgb(hex_str: str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

def rgb_to_hex(rgb) -> str:
    r, g, b = [max(0, min(255, round(c * 255))) for c in rgb]
    return f"#{r:02X}{g:02X}{b:02X}"

def rgba(hex_str: str, alpha: float) -> str:
    r, g, b = [round(c * 255) for c in hex_to_rgb(hex_str)]
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"

def color_blend(base: str, overlay: str, strength: float = 1.0) -> str:
    strength = max(0.0, min(1.0, strength))
    br, bg, bb = hex_to_rgb(base)
    tr, tg, tb = hex_to_rgb(overlay)
    r = ((br ** 2.2) * (1.0 - strength) + (tr ** 2.2) * strength) ** (1.0 / 2.2)
    g = ((bg ** 2.2) * (1.0 - strength) + (tg ** 2.2) * strength) ** (1.0 / 2.2)
    b = ((bb ** 2.2) * (1.0 - strength) + (tb ** 2.2) * strength) ** (1.0 / 2.2)
    return rgb_to_hex((r, g, b))

def adjust_luma(hex_str: str, delta: float) -> str:
    r, g, b = hex_to_rgb(hex_str)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    v = max(0.0, min(1.0, v + delta))
    return rgb_to_hex(colorsys.hsv_to_rgb(h, s, v))

def desaturate(hex_str: str, amount: float = 0.2) -> str:
    r, g, b = hex_to_rgb(hex_str)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = max(0.0, min(1.0, s * (1.0 - amount)))
    return rgb_to_hex(colorsys.hsv_to_rgb(h, s, v))

def gra(*colors, direction="v", mode="linear") -> str:
    valid = [str(c) for c in colors if c]
    if not valid:
        return "#000000"
    if len(valid) == 1:
        return valid[0]
    step = 1.0 / (len(valid) - 1)
    stops = ", ".join(f"stop: {i * step:.2f} {color}" for i, color in enumerate(valid))
    dirs = {
        "v": (0, 0, 0, 1),
        "h": (0, 0, 1, 0),
        "diag": (0, 0, 1, 1),
        "reverse": (0, 1, 0, 0)
    }
    x1, y1, x2, y2 = dirs.get(direction, (0, 0, 0, 1))
    return f"qlineargradient(x1: {x1}, y1: {y1}, x2: {x2}, y2: {y2}, {stops})"

def gra_sheen(base: str, top_lift: float = 0.018, bot_dip: float = 0.012) -> str:
    top = adjust_luma(base, top_lift)
    bottom = adjust_luma(base, -bot_dip)
    return f"qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0.0 {top}, stop: 1.0 {bottom})"

def make_theme(c, is_light=False, dv=None):
    white = "#FFFFFF"
    black = "#000000"

    if is_light:
        border_base = black
        subtle_alpha = 0.085
        default_alpha = 0.145
    else:
        border_base = white
        subtle_alpha = 0.105
        default_alpha = 0.17

    radius_card = c.get("radius_card", "9px")
    radius_button = c.get("radius_button", "7px")
    radius_input = c.get("radius_input", "7px")
    radius_chip = c.get("radius_chip", "7px")

    border_subtle = c.get("border_subtle", rgba(border_base, subtle_alpha))
    border_default = c.get("border_default", rgba(border_base, default_alpha))
    border_card_hover = c.get("border_card_hover", rgba(c["accent_light"], 0.55))

    border_card = c.get("border_card", f"1px solid {border_subtle}")
    border_button = c.get("border_button", f"1px solid {border_default}")
    border_input = c.get("border_input", f"1px solid {border_subtle}")
    border_chip = c.get("border_chip", f"1px solid {border_subtle}")

    card_top = c.get("card_top", 0.012 if is_light else 0.018)
    card_bot = c.get("card_bot", 0.010 if is_light else 0.014)

    button_top = c.get("button_top", 0.018)
    button_bot = c.get("button_bot", 0.014)

    combo_selected = c.get("surface_combo_selected", c["accent"])
    combo_text = c.get("combo_selected_text", "#FFFFFF")

    secondary_hover_text = c.get(
        "secondary_hover_text",
        "#111111" if is_light else "#FFFFFF"
    )

    theme = {
        "bg": gra(c["bg"], c["bg2"], direction="v"),
        "bg_solid": c["bg"],

        "text": c["text"],
        "text_primary": c.get("text_primary", c["text"]),
        "text_title": c.get("text_title", c["text"]),
        "text_title_bright": c.get("text_title_bright", c["accent_light"]),
        "text_title_sub": c["text2"],
        "text_secondary": c["text2"],
        "text_secondary_light": c.get("text_secondary_light", c["text2"]),
        "text_input": c.get("text_input", c["text"]),
        "text_input_list": c.get("text_input_list", c["text2"]),
        "text_button": c.get("text_button", c["text"]),
        "text_button_hover": c.get(
            "text_button_hover",
            "#111111" if is_light else "#FFFFFF"
        ),
        "text_button_pressed": c.get("text_button_pressed", c["text2"]),
        "text_muted": c["muted"],
        "text_meta": c["muted"],
        "text_url": c.get("text_url", c["accent_light"]),
        "text_category": c["muted"],
        "text_dim": c["dim"],
        "text_disabled": c["dim"],
        "text_disabled_button": c["dim"],
        "text_group": c["muted"],
        "text_group_title": c["text2"],
        "text_star": c.get("star", "#D99A24"),
        "text_original": c["muted"],

        "surface_card": gra_sheen(c["surface"], card_top, card_bot),
        "surface_button": gra_sheen(c["surface2"], button_top, button_bot),
        "surface_input": c["surface"],
        "surface_textedit": c["surface"],
        "surface_chip": gra(c["surface2"], c["surface3"], direction="v"),
        "surface_tag": c["surface2"],
        "surface_hover": gra_sheen(c["surface2"], 0.018, 0.010),
        "surface_button_hover": gra_sheen(c["surface3"], 0.022, 0.012),
        "surface_input_hover": c["surface2"],
        "surface_input_focus": c.get("surface_input_focus", c["surface"]),
        "surface_textedit_hover": c["surface2"],
        "surface_textedit_focus": c["surface"],
        "surface_button_pressed": c.get("surface_button_pressed", c["surface3"]),
        "surface_disabled": c["bg2"],
        "surface_checkbox_hover": c["surface3"],
        "surface_menu": c["surface"],
        "surface_menu_selected": c["surface3"],
        "surface_combo_selected": combo_selected,
        "combo_selected_text": combo_text,
        "surface_delete_hover": c["delete_bg"],
        "surface_delete": gra(c["delete_bg"], color_blend(c["delete"], c["delete_bg"], 0.30), direction="v"),
        "surface_chip_hover": c["surface3"],
        "surface_rating": "transparent",

        "primary_bg": c.get(
            "primary_bg",
            gra(c["accent_light"], c["accent"], direction="v")
        ),
        "primary_text": c.get("primary_text", "#FFFFFF"),
        "primary_hover": c.get(
            "primary_hover",
            gra(adjust_luma(c["accent_light"], 0.035), c["accent"], direction="v")
        ),
        "primary_hover_text": c.get("primary_hover_text", "#FFFFFF"),
        "primary_pressed": c.get(
            "primary_pressed",
            gra(c["accent"], c["accent_dark"], direction="v")
        ),

        "secondary_bg": c.get("secondary_bg", gra_sheen(c["surface2"])),
        "secondary_text": c.get("secondary_text", c["text"]),
        "secondary_hover": c.get("secondary_hover", gra_sheen(c["surface3"])),
        "secondary_hover_text": secondary_hover_text,

        "chip_text": c["text2"],
        "chip_hover_text": c.get(
            "chip_hover_text",
            "#111111" if is_light else "#FFFFFF"
        ),
        "chip_checked": c.get(
            "chip_checked",
            gra(c["accent_light"], c["accent"], direction="h")
        ),
        "chip_checked_text": c.get("chip_checked_text", "#FFFFFF"),
        "tag_text": c["text2"],

        "delete_text": c["muted"],
        "delete_hover_text": c["delete"],

        "radius_card": radius_card,
        "radius_button": radius_button,
        "radius_input": radius_input,
        "radius_chip": radius_chip,

        "border_card": border_card,
        "border_button": border_button,
        "border_input": border_input,
        "border_chip": border_chip,
        "border_subtle": border_subtle,
        "border_default": border_default,
        "border_card_hover": border_card_hover,
        "border_input_focus": c["accent"],
        "border_textedit_focus": c["accent"],
        "border_checkbox": border_default,
        "border_checkbox_hover": c["accent_light"],
        "border_disabled": border_subtle,

        "selection_input": c["selection"],
        "selection_textedit": c["selection"],
        "selection_text": "#FFFFFF",
        "checkbox_text": c["text2"],
        "checkbox_bg": c["surface2"],
        "checkbox_hover_bg": c["surface3"],
        "checkbox_checked": gra(c["accent_light"], c["accent"], direction="v"),
        "checkbox_checked_border": c["accent"],
        "checkbox_disabled_bg": c["bg2"],

        "textedit_text": c["text"],
        "textedit_transparent_text": c["text"],
        "scrollbar": border_default,
        "scrollbar_hover": c["accent_light"],
        "menu_text": c["text2"],
        "menu_selected_text": c["text"],
        "combo_text": c["text"],

        "dv_window": f"selection-background-color: {c['selection']};",
        "dv_label": "",
        "dv_app_title": "",
        "dv_title": "",
        "dv_title_label": "",
        "dv_lbl_title": "",
        "dv_original_title": "",
        "dv_label_meta": "",
        "dv_url": "",
        "dv_progress": "",
        "dv_cat_label": "",
        "dv_tilde": "",
        "dv_stars": "",
        "dv_detail_title": "",
        "dv_detail_original_title": "",
        "dv_detail_section_title": "",
        "dv_detail_rating": "",
        "dv_detail_meta_text": "",
        "dv_detail_url": "",
        "dv_dialog_description": "",
        "dv_dialog_hint": "",
        "dv_tag": "",
        "dv_input": "",
        "dv_input_hover": "",
        "dv_input_focus": "",
        "dv_input_disabled": "",
        "dv_combo": "",
        "dv_combo_dropdown": "",
        "dv_combo_arrow": "",
        "dv_combo_view": "",
        "dv_combo_item": "",
        "dv_button": "",
        "dv_button_hover": "",
        "dv_button_pressed": "",
        "dv_button_disabled": "",
        "dv_primary_btn": "",
        "dv_primary_btn_hover": "",
        "dv_primary_btn_pressed": "",
        "dv_secondary_btn": "",
        "dv_secondary_btn_hover": "",
        "dv_del_btn": "",
        "dv_del_btn_hover": "",
        "dv_chip_btn": "",
        "dv_chip_btn_hover": "",
        "dv_chip_btn_checked": "",
        "dv_detail_tag_btn": "",
        "dv_detail_tag_btn_hover": "",
        "dv_detail_tag_btn_pressed": "",
        "dv_groupbox": "",
        "dv_groupbox_title": "",
        "dv_card": "",
        "dv_card_hover": "",
        "dv_list": "",
        "dv_list_item": "",
        "dv_list_item_selected": "",
        "dv_detail_meta": "",
        "dv_detail_tags": "",
        "dv_dialog_separator": "",
        "dv_textedit": "",
        "dv_detail_description": "",
        "dv_textedit_transparent": "",
        "dv_checkbox": "",
        "dv_checkbox_hover": "",
        "dv_checkbox_indicator": "",
        "dv_checkbox_indicator_hover": "",
        "dv_checkbox_indicator_checked": "",
        "dv_checkbox_indicator_disabled": "",
        "dv_scrollarea": "",
        "dv_scrollbar_v": "",
        "dv_scrollbar_handle_v": "",
        "dv_scrollbar_handle_v_hover": "",
        "dv_menu": "",
        "dv_menu_item": "",
        "dv_menu_item_selected": "",
        "dv_menu_separator": "",
        "dv_tag_container": "",
        "dv_group_box_title_transparent": "",
        "dv_is_remainder_point_color": f"color: {c['accent_light']}; font-weight: 700;",
        "dv_dictionary_dialog": f"selection-background-color: {c['selection']};",
        "dv_dictionary_title": "",
        "dv_dictionary_container": "",
        "dv_dictionary_item": "",
        "dv_dictionary_item_hover": "",
        "dv_dictionary_input": "",
        "dv_dictionary_input_hover": "",
        "dv_dictionary_input_focus": "",
        "dv_dictionary_arrow": "",
        "dv_dictionary_remove": "",
        "dv_dictionary_remove_hover": "",
        "dv_dictionary_add": "",
        "dv_dictionary_add_hover": "",
        "dv_dictionary_add_pressed": "",
    }

    if dv and isinstance(dv, dict):
        theme.update(dv)

    return c["surface2"], theme


def make_dark_theme(c, dv=None):
    return make_theme(c, is_light=False, dv=dv)


def make_light_theme(c, dv=None):
    return make_theme(c, is_light=True, dv=dv)