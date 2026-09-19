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

def _make_theme(c, is_light=False, dv=None):
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


def _make_dark_theme(c, dv=None):
    return _make_theme(c, is_light=False, dv=dv)


def _make_light_theme(c, dv=None):
    return _make_theme(c, is_light=True, dv=dv)


# 01. 화이트
COLORS_NEW_WHITE, THEME_WHITE = _make_light_theme({
    "bg": "#F4F5F7",
    "bg2": "#ECEEF2",
    "surface": "#FFFFFF",
    "surface2": "#F1F3F6",
    "surface3": "#E6E9EE",
    "surface4": "#D9DEE6",
    "text": "#20242A",
    "text2": "#59616D",
    "muted": "#7B8490",
    "dim": "#AEB5BE",
    "accent": "#356AE6",
    "accent_light": "#4D7FF0",
    "accent_dark": "#2857C7",
    "selection": "#356AE6",
    "star": "#C88718",
    "delete": "#D84A55",
    "delete_bg": "#FBE9EB",
    "surface_combo_selected": "#356AE6",
    "radius_card": "9px",
    "radius_button": "7px",
    "radius_input": "7px",
    "radius_chip": "7px",
}, dv={
    "dv_primary_btn": "background: #356AE6; color: #FFFFFF; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #4D7FF0; color: #FFFFFF;",
    "dv_button": "background: #F1F3F6; color: #20242A; border: 1px solid rgba(0,0,0,0.14);",
    "dv_button_hover": "background: #E6E9EE; color: #111111;",
})


# 02. 샌드
COLORS_SAND, THEME_SAND = _make_light_theme({
    "bg": "#F6F1E8",
    "bg2": "#EEE6D9",
    "surface": "#FCFAF6",
    "surface2": "#F1E9DC",
    "surface3": "#E5DAC9",
    "surface4": "#D8C9B4",
    "text": "#302A23",
    "text2": "#665B4E",
    "muted": "#877B6B",
    "dim": "#B0A393",
    "accent": "#A96F2D",
    "accent_light": "#C0833A",
    "accent_dark": "#875720",
    "selection": "#A96F2D",
    "star": "#B77A19",
    "delete": "#C94B48",
    "delete_bg": "#F8E9E4",
    "surface_combo_selected": "#A96F2D",
    "radius_card": "10px",
    "radius_button": "8px",
    "radius_input": "8px",
    "radius_chip": "8px",
}, dv={
    "dv_primary_btn": "background: #A96F2D; color: #FFFFFF; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #C0833A; color: #FFFFFF;",
    "dv_button": "background: #F1E9DC; color: #302A23; border: 1px solid rgba(48,42,35,0.13);",
    "dv_button_hover": "background: #E5DAC9; color: #211C17;",
})


# 03. 로즈
COLORS_ROSE, THEME_ROSE = _make_light_theme({
    "bg": "#F8F3F5",
    "bg2": "#F0E6EA",
    "surface": "#FFFDFE",
    "surface2": "#F5EBEF",
    "surface3": "#E9D9E0",
    "surface4": "#DCC5CF",
    "text": "#30252A",
    "text2": "#67535C",
    "muted": "#8B737E",
    "dim": "#B9A1AA",
    "accent": "#C44D78",
    "accent_light": "#D66A91",
    "accent_dark": "#A83C64",
    "selection": "#C44D78",
    "star": "#B98222",
    "delete": "#C94B58",
    "delete_bg": "#FAE9ED",
    "surface_combo_selected": "#C44D78",
    "radius_card": "12px",
    "radius_button": "9px",
    "radius_input": "9px",
    "radius_chip": "10px",
}, dv={
    "dv_primary_btn": "background: #C44D78; color: #FFFFFF; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #D66A91; color: #FFFFFF;",
    "dv_button": "background: #F5EBEF; color: #30252A; border: 1px solid rgba(196,77,120,0.15);",
    "dv_button_hover": "background: #E9D9E0; color: #241B20;",
})


# 04. 옐로우 HUD
COLORS_YELLOW_HUD, THEME_YELLOW_HUD = _make_dark_theme({
    "bg": "#10100F",
    "bg2": "#161613",
    "surface": "#1B1B18",
    "surface2": "#24241F",
    "surface3": "#303028",
    "surface4": "#3C3C31",
    "text": "#F3F1E5",
    "text2": "#D0CCB0",
    "muted": "#99947A",
    "dim": "#66634F",
    "accent": "#D7B928",
    "accent_light": "#E8CE4B",
    "accent_dark": "#A99016",
    "selection": "#9C8212",
    "star": "#E8C95A",
    "delete": "#D95765",
    "delete_bg": "#321B1E",
    "surface_combo_selected": "#9C8212",
    "radius_card": "2px",
    "radius_button": "2px",
    "radius_input": "2px",
    "radius_chip": "2px",
    "border_card": "1px solid rgba(215,185,40,0.28); border-left: 3px solid #D7B928;",
    "border_button": "1px solid rgba(215,185,40,0.34)",
    "border_input": "1px solid rgba(215,185,40,0.22)",
}, dv={
    "dv_button": "background: #24241F; color: #E8CE4B; border: 1px solid rgba(215,185,40,0.34);",
    "dv_button_hover": "background: #303028; color: #FFF4A8; border: 1px solid #D7B928;",
    "dv_primary_btn": "background: #D7B928; color: #17160D; font-weight: 800; border: none;",
    "dv_primary_btn_hover": "background: #E8CE4B; color: #17160D;",
    "dv_chip_btn_checked": "background: #D7B928; color: #17160D; font-weight: 750;",
})


# 05. 크림슨
COLORS_CRIMSON, THEME_CRIMSON = _make_dark_theme({
    "bg": "#120C0E",
    "bg2": "#191013",
    "surface": "#21161A",
    "surface2": "#2B1D22",
    "surface3": "#38262C",
    "surface4": "#473139",
    "text": "#F4EAEC",
    "text2": "#D1B9C0",
    "muted": "#997B84",
    "dim": "#68515A",
    "accent": "#D6455D",
    "accent_light": "#EA687A",
    "accent_dark": "#AD3046",
    "selection": "#9E293E",
    "star": "#D5A63B",
    "delete": "#E45D69",
    "delete_bg": "#35181E",
    "surface_combo_selected": "#9E293E",
    "radius_card": "5px",
    "radius_button": "5px",
    "radius_input": "5px",
    "radius_chip": "5px",
    "border_card": "1px solid rgba(214,69,93,0.26); border-left: 3px solid #D6455D;",
    "border_button": "1px solid rgba(214,69,93,0.30)",
}, dv={
    "dv_button": "background: #2B1D22; color: #F4EAEC; border: 1px solid rgba(214,69,93,0.30);",
    "dv_button_hover": "background: #38262C; border: 1px solid #D6455D;",
    "dv_primary_btn": "background: #D6455D; color: #FFFFFF; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #EA687A; color: #FFFFFF;",
})


# 06. 에메랄드
COLORS_EMERALD, THEME_EMERALD = _make_dark_theme({
    "bg": "#0B1210",
    "bg2": "#101A16",
    "surface": "#17231D",
    "surface2": "#203029",
    "surface3": "#2B3D34",
    "surface4": "#385046",
    "text": "#EAF4EE",
    "text2": "#B9D3C3",
    "muted": "#7D9F8A",
    "dim": "#526F5E",
    "accent": "#27A879",
    "accent_light": "#46C996",
    "accent_dark": "#18865F",
    "selection": "#167653",
    "star": "#D5A63B",
    "delete": "#D96770",
    "delete_bg": "#30191D",
    "surface_combo_selected": "#167653",
    "radius_card": "5px",
    "radius_button": "5px",
    "radius_input": "5px",
    "radius_chip": "5px",
    "border_card": "1px solid rgba(39,168,121,0.25); border-left: 3px solid #27A879;",
    "border_button": "1px solid rgba(39,168,121,0.30)",
}, dv={
    "dv_button": "background: #203029; color: #DDF5E7; border: 1px solid rgba(39,168,121,0.30);",
    "dv_button_hover": "background: #2B3D34; color: #FFFFFF; border: 1px solid #46C996;",
    "dv_primary_btn": "background: #27A879; color: #07130E; font-weight: 800; border: none;",
    "dv_primary_btn_hover": "background: #46C996; color: #07130E;",
})


# 07. 노르딕
COLORS_NORDIC, THEME_NORDIC = _make_dark_theme({
    "bg": "#272D36",
    "bg2": "#22272F",
    "surface": "#303744",
    "surface2": "#394250",
    "surface3": "#454F60",
    "surface4": "#566276",
    "text": "#E9EDF3",
    "text2": "#CBD3DE",
    "muted": "#909CAB",
    "dim": "#697482",
    "accent": "#6D91B9",
    "accent_light": "#8EAFCE",
    "accent_dark": "#55799F",
    "selection": "#55799F",
    "star": "#D5B56A",
    "delete": "#BF6A73",
    "delete_bg": "#3A272B",
    "surface_combo_selected": "#55799F",
    "radius_card": "9px",
    "radius_button": "7px",
    "radius_input": "7px",
    "radius_chip": "7px",
    "border_card": "1px solid rgba(142,175,206,0.22); border-top: 2px solid #8EAFCE;",
}, dv={
    "dv_button": "background: #394250; color: #E9EDF3; border: 1px solid rgba(142,175,206,0.28);",
    "dv_button_hover": "background: #454F60; color: #FFFFFF; border: 1px solid #8EAFCE;",
    "dv_primary_btn": "background: #6D91B9; color: #10151B; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #8EAFCE; color: #10151B;",
})


# 08. 브라운
COLORS_BROWN, THEME_BROWN = _make_dark_theme({
    "bg": "#211D1A",
    "bg2": "#191613",
    "surface": "#2A2521",
    "surface2": "#35302A",
    "surface3": "#433B33",
    "surface4": "#53493E",
    "text": "#EFE5D5",
    "text2": "#D0BFA7",
    "muted": "#9D8A72",
    "dim": "#6F604F",
    "accent": "#C18A48",
    "accent_light": "#D8A664",
    "accent_dark": "#9D6B31",
    "selection": "#8B5E28",
    "star": "#D9A83F",
    "delete": "#C96A5D",
    "delete_bg": "#39211E",
    "surface_combo_selected": "#8B5E28",
    "radius_card": "5px",
    "radius_button": "5px",
    "radius_input": "5px",
    "radius_chip": "5px",
}, dv={
    "dv_button": "background: #35302A; color: #EFE5D5; border: 1px solid rgba(193,138,72,0.30);",
    "dv_button_hover": "background: #433B33; color: #FFFFFF;",
    "dv_primary_btn": "background: #C18A48; color: #1D1712; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #D8A664; color: #1D1712;",
})


# 09. 라벤더
COLORS_LAVENDER, THEME_LAVENDER = _make_dark_theme({
    "bg": "#20202C",
    "bg2": "#1A1A24",
    "surface": "#2A2A39",
    "surface2": "#343449",
    "surface3": "#41415A",
    "surface4": "#50506D",
    "text": "#E9E7F2",
    "text2": "#C6C2D8",
    "muted": "#918DA7",
    "dim": "#66627C",
    "accent": "#9586D8",
    "accent_light": "#B0A4E8",
    "accent_dark": "#7567B7",
    "selection": "#6C5FA8",
    "star": "#D6B66A",
    "delete": "#D47886",
    "delete_bg": "#39242B",
    "surface_combo_selected": "#6C5FA8",
    "radius_card": "11px",
    "radius_button": "8px",
    "radius_input": "8px",
    "radius_chip": "9px",
}, dv={
    "dv_button": "background: #343449; color: #E9E7F2; border: 1px solid rgba(176,164,232,0.25);",
    "dv_button_hover": "background: #41415A; color: #FFFFFF;",
    "dv_primary_btn": "background: #9586D8; color: #15131D; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #B0A4E8; color: #15131D;",
})


# 10. 틸
COLORS_NEW_TEAL, THEME_TEAL = _make_dark_theme({
    "bg": "#0B1719",
    "bg2": "#091215",
    "surface": "#122225",
    "surface2": "#193036",
    "surface3": "#234149",
    "surface4": "#2E535C",
    "text": "#E5F1F1",
    "text2": "#B5D0D1",
    "muted": "#77999B",
    "dim": "#506F72",
    "accent": "#2B9B99",
    "accent_light": "#48BBB7",
    "accent_dark": "#217876",
    "selection": "#1E6F70",
    "star": "#D2A83D",
    "delete": "#D7656D",
    "delete_bg": "#321B20",
    "surface_combo_selected": "#1E6F70",
    "radius_card": "7px",
    "radius_button": "6px",
    "radius_input": "6px",
    "radius_chip": "6px",
}, dv={
    "dv_button": "background: #193036; color: #E5F1F1; border: 1px solid rgba(72,187,183,0.27);",
    "dv_button_hover": "background: #234149; color: #FFFFFF;",
    "dv_primary_btn": "background: #2B9B99; color: #071313; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #48BBB7; color: #071313;",
})


# 11. 인디고
COLORS_NEW_INDIGO, THEME_INDIGO = _make_dark_theme({
    "bg": "#11131A",
    "bg2": "#0D0F15",
    "surface": "#191C26",
    "surface2": "#222735",
    "surface3": "#2D3344",
    "surface4": "#3A4256",
    "text": "#EEF0F6",
    "text2": "#B6BDCE",
    "muted": "#7D879B",
    "dim": "#555F73",
    "accent": "#6674D9",
    "accent_light": "#8490EA",
    "accent_dark": "#4E5BB9",
    "selection": "#4652A4",
    "star": "#D8AE45",
    "delete": "#D95B6A",
    "delete_bg": "#32191F",
    "surface_combo_selected": "#4652A4",
    "radius_card": "8px",
    "radius_button": "7px",
    "radius_input": "7px",
    "radius_chip": "7px",
}, dv={
    "dv_button": "background: #222735; color: #EEF0F6; border: 1px solid rgba(132,144,234,0.25);",
    "dv_button_hover": "background: #2D3344; color: #FFFFFF;",
    "dv_primary_btn": "background: #6674D9; color: #FFFFFF; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #8490EA; color: #FFFFFF;",
})


# 12. 바이올렛
COLORS_VIOLET, THEME_VIOLET = _make_dark_theme({
    "bg": "#17141D",
    "bg2": "#121017",
    "surface": "#211C2A",
    "surface2": "#2C2638",
    "surface3": "#393148",
    "surface4": "#483E5A",
    "text": "#F0ECF4",
    "text2": "#C5BBD0",
    "muted": "#8D809B",
    "dim": "#62586D",
    "accent": "#A477C5",
    "accent_light": "#BE98DA",
    "accent_dark": "#865DA9",
    "selection": "#714D91",
    "star": "#D8AD54",
    "delete": "#D76D7B",
    "delete_bg": "#371E25",
    "surface_combo_selected": "#714D91",
    "radius_card": "10px",
    "radius_button": "7px",
    "radius_input": "7px",
    "radius_chip": "8px",
}, dv={
    "dv_button": "background: #2C2638; color: #F0ECF4; border: 1px solid rgba(190,152,218,0.25);",
    "dv_button_hover": "background: #393148; color: #FFFFFF;",
    "dv_primary_btn": "background: #A477C5; color: #17111C; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #BE98DA; color: #17111C;",
})


# 13. 오렌지
COLORS_NEW_ORANGE, THEME_ORANGE = _make_dark_theme({
    "bg": "#14110F",
    "bg2": "#0F0D0B",
    "surface": "#201A16",
    "surface2": "#2B231D",
    "surface3": "#382D24",
    "surface4": "#473A2E",
    "text": "#F3ECE5",
    "text2": "#CDBBAA",
    "muted": "#927D69",
    "dim": "#665546",
    "accent": "#D56A32",
    "accent_light": "#E5894E",
    "accent_dark": "#AE4E20",
    "selection": "#914019",
    "star": "#D5A43C",
    "delete": "#D65D5D",
    "delete_bg": "#351C1A",
    "surface_combo_selected": "#914019",
    "radius_card": "6px",
    "radius_button": "6px",
    "radius_input": "6px",
    "radius_chip": "6px",
}, dv={
    "dv_button": "background: #2B231D; color: #F3ECE5; border: 1px solid rgba(229,137,78,0.27);",
    "dv_button_hover": "background: #382D24; color: #FFFFFF; border: 1px solid #D56A32;",
    "dv_primary_btn": "background: #D56A32; color: #190E08; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #E5894E; color: #190E08;",
})


# 14. 딥 블루
COLORS_DEEP_BLUE, THEME_DEEP_BLUE = _make_dark_theme({
    "bg": "#0B111A",
    "bg2": "#080D14",
    "surface": "#121B27",
    "surface2": "#192636",
    "surface3": "#223448",
    "surface4": "#2C425A",
    "text": "#E8F0F7",
    "text2": "#B4C7D9",
    "muted": "#758CA1",
    "dim": "#506477",
    "accent": "#3F82B8",
    "accent_light": "#61A0D2",
    "accent_dark": "#2D6595",
    "selection": "#28577F",
    "star": "#D3A743",
    "delete": "#D35E68",
    "delete_bg": "#301A1E",
    "surface_combo_selected": "#28577F",
    "radius_card": "8px",
    "radius_button": "7px",
    "radius_input": "7px",
    "radius_chip": "7px",
}, dv={
    "dv_button": "background: #192636; color: #E8F0F7; border: 1px solid rgba(97,160,210,0.26);",
    "dv_button_hover": "background: #223448; color: #FFFFFF;",
    "dv_primary_btn": "background: #3F82B8; color: #07121A; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #61A0D2; color: #07121A;",
})


# 15. 모노
COLORS_NEW_MONO, THEME_MONO = _make_dark_theme({
    "bg": "#111214",
    "bg2": "#0C0D0F",
    "surface": "#191A1D",
    "surface2": "#24262A",
    "surface3": "#303238",
    "surface4": "#3D4047",
    "text": "#EEEEF0",
    "text2": "#B2B4BA",
    "muted": "#777A82",
    "dim": "#50535A",
    "accent": "#9FA3AA",
    "accent_light": "#C2C5CA",
    "accent_dark": "#777B82",
    "selection": "#555960",
    "star": "#C9A85B",
    "delete": "#D46068",
    "delete_bg": "#321A1D",
    "surface_combo_selected": "#555960",
    "radius_card": "5px",
    "radius_button": "5px",
    "radius_input": "5px",
    "radius_chip": "5px",
    "border_card": "1px solid rgba(255,255,255,0.12)",
    "border_button": "1px solid rgba(255,255,255,0.18)",
}, dv={
    "dv_button": "background: #24262A; color: #EEEEF0; border: 1px solid rgba(255,255,255,0.18); font-weight: 650;",
    "dv_button_hover": "background: #303238; color: #FFFFFF; border: 1px solid #C2C5CA;",
    "dv_primary_btn": "background: #9FA3AA; color: #101114; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #C2C5CA; color: #101114;",
})


# 16. 시안
COLORS_NEW_CYAN, THEME_CYAN = _make_dark_theme({
    "bg": "#0A1519",
    "bg2": "#081115",
    "surface": "#122027",
    "surface2": "#192D35",
    "surface3": "#23404A",
    "surface4": "#2E515C",
    "text": "#E7F5F7",
    "text2": "#B2D2D7",
    "muted": "#729AA2",
    "dim": "#4F7077",
    "accent": "#299BB0",
    "accent_light": "#50BDD0",
    "accent_dark": "#1E7487",
    "selection": "#1A6070",
    "star": "#D2A840",
    "delete": "#D45E69",
    "delete_bg": "#311A1F",
    "surface_combo_selected": "#1A6070",
    "radius_card": "7px",
    "radius_button": "6px",
    "radius_input": "6px",
    "radius_chip": "6px",
}, dv={
    "dv_button": "background: #192D35; color: #E7F5F7; border: 1px solid rgba(80,189,208,0.28);",
    "dv_button_hover": "background: #23404A; color: #FFFFFF; border: 1px solid #50BDD0;",
    "dv_primary_btn": "background: #299BB0; color: #061215; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: #50BDD0; color: #061215;",
})


# 17. OLED
COLORS_NEW_OLED, THEME_OLED = _make_dark_theme({
    "bg": "#000000",
    "bg2": "#030303",
    "surface": "#08090A",
    "surface2": "#111315",
    "surface3": "#1A1D20",
    "surface4": "#25292D",
    "text": "#F7F8F9",
    "text2": "#A9ADB2",
    "muted": "#6D7278",
    "dim": "#41454A",
    "accent": "#63C7D4",
    "accent_light": "#86DCE6",
    "accent_dark": "#3894A1",
    "selection": "#205F69",
    "star": "#D5AE43",
    "delete": "#D85F68",
    "delete_bg": "#260D10",
    "surface_combo_selected": "#205F69",
    "radius_card": "6px",
    "radius_button": "6px",
    "radius_input": "6px",
    "radius_chip": "6px",
    "border_card": "1px solid rgba(99,199,212,0.32)",
    "border_button": "1px solid rgba(99,199,212,0.38)",
    "border_input": "1px solid rgba(99,199,212,0.28)",
}, dv={
    "dv_button": "background: #111315; color: #DDF8FA; border: 1px solid rgba(99,199,212,0.38); font-weight: 650;",
    "dv_button_hover": "background: #1A1D20; color: #FFFFFF; border: 1px solid #63C7D4;",
    "dv_primary_btn": "background: #63C7D4; color: #041013; font-weight: 800; border: none;",
    "dv_primary_btn_hover": "background: #86DCE6; color: #041013;",
})

THEMES = {
    "NEW WHITE": THEME_WHITE,
    "SAND": THEME_SAND,
    "ROSE": THEME_ROSE,
    "YELLOW_HUD": THEME_YELLOW_HUD,
    "CRIMSON": THEME_CRIMSON,
    "EMERALD": THEME_EMERALD,
    "NORDIC": THEME_NORDIC,
    "BROWN": THEME_BROWN,
    "LAVENDER": THEME_LAVENDER,
    "NEW TEAL": THEME_TEAL,
    "NEW INDIGO": THEME_INDIGO,
    "VIOLET": THEME_VIOLET,
    "NEW ORANGE": THEME_ORANGE,
    "DEEP_BLUE": THEME_DEEP_BLUE,
    "NEW MONO": THEME_MONO,
    "NEW CYAN": THEME_CYAN,
    "NEW OLED": THEME_OLED,
}

THEME_DATA = {
    "NEW 화이트": "NEW WHITE",
    "NEW 틸": "NEW TEAL",
    "NEW 인디고": "NEW INDIGO",
    "NEW 오렌지": "NEW ORANGE",
    "NEW 모노": "NEW MONO",
    "NEW 시안": "NEW CYAN",
    "NEW OLED": "NEW OLED",
    "샌드": "SAND",
    "로즈": "ROSE",
    "옐로우 HUD": "YELLOW_HUD",
    "크림슨": "CRIMSON",
    "에메랄드": "EMERALD",
    "노르딕": "NORDIC",
    "브라운": "BROWN",
    "라벤더": "LAVENDER",
    "바이올렛": "VIOLET",
    "딥 블루": "DEEP_BLUE"
}