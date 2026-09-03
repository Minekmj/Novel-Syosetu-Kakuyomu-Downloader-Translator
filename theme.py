def gra(*colors, direction="v", mode="linear"):
    if not colors:
        return "#000000"

    colors = tuple(str(c) for c in colors if c)
    if len(colors) == 1:
        return colors[0]

    if mode == "radial":
        step = 1.0 / (len(colors) - 1)
        stops = ", ".join(f"stop: {i * step:g} {color}" for i, color in enumerate(colors))
        return f"qradialgradient(cx: 0.5, cy: 0.5, radius: 0.8, fx: 0.5, fy: 0.5, {stops})"

    dirs = {
        "h": (0, 0, 1, 0),
        "diag": (0, 0, 1, 1),
        "reverse": (1, 1, 0, 0),
        "v": (0, 0, 0, 1)
    }
    x1, y1, x2, y2 = dirs.get(direction, (0, 0, 0, 1))

    step = 1.0 / (len(colors) - 1)
    stops = ", ".join(f"stop: {i * step:g} {color}" for i, color in enumerate(colors))

    return f"qlineargradient(x1: {x1}, y1: {y1}, x2: {x2}, y2: {y2}, {stops})"

def _make_dark_theme(c, dv=None):
    theme = {
        "bg": gra(c["bg"], c["bg2"], direction="v"),
        "text": c["text"],
        "text_primary": c["text"],
        "text_title": c["text"],
        "text_title_bright": c["accent_light"],
        "text_title_sub": c["text2"],
        "text_secondary": c["text2"],
        "text_secondary_light": c["text2"],
        "text_input": c["text"],
        "text_input_list": c["text2"],
        "text_button": c["text"],
        "text_button_hover": "#FFFFFF",
        "text_button_pressed": c["text2"],
        "text_muted": c["muted"],
        "text_meta": c["muted"],
        "text_url": c["accent_light"],
        "text_category": c["muted"],
        "text_dim": c["dim"],
        "text_disabled": c["dim"],
        "text_disabled_button": c["dim"],
        "text_group": c["muted"],
        "text_group_title": c["text2"],
        "text_star": c["star"],

        "text_original": c["muted"],

        "surface_card": gra(c["surface"], c["surface2"], direction="v"),
        "surface_button": gra(c["surface2"], c["surface3"], direction="v"),
        "surface_input": gra(c["surface"], c["surface2"], direction="v"),
        "surface_textedit": gra(c["surface"], c["surface2"], direction="v"),
        "surface_chip": gra(c["surface2"], c["surface3"], direction="h"),
        "surface_tag": c["surface2"],
        "surface_hover": c["surface3"],
        "surface_button_hover": gra(c["surface3"], c["surface4"], direction="v"),
        "surface_input_hover": gra(c["surface2"], c["surface3"], direction="v"),
        "surface_input_focus": c["surface2"],
        "surface_textedit_hover": c["surface2"],
        "surface_textedit_focus": c["surface2"],
        "surface_button_pressed": c["surface"],
        "surface_disabled": c["bg"],
        "surface_checkbox_hover": c["surface3"],
        "surface_menu": c["surface"],
        "surface_menu_selected": c["surface3"],
        "surface_combo_selected": c["surface3"],
        "surface_delete_hover": c["delete_bg"],
        "surface_chip_hover": c["surface4"],

        "surface_rating": "transparent",

        "primary_bg": gra(c["accent_light"], c["accent"], c["accent_dark"], direction="diag"),
        "primary_text": "#FFFFFF",
        "primary_hover": gra(c["accent_light"], c["accent"], direction="diag"),
        "primary_hover_text": "#FFFFFF",
        "primary_pressed": gra(c["accent"], c["accent_dark"], direction="diag"),

        "secondary_bg": gra(c["surface2"], c["surface3"], direction="v"),
        "secondary_text": c["text2"],
        "secondary_hover": c["surface4"],
        "secondary_hover_text": c["text"],

        "chip_text": c["text2"],
        "chip_hover_text": c["text"],
        "chip_checked": gra(c["accent_light"], c["accent"], direction="h"),
        "chip_checked_text": "#FFFFFF",

        "tag_text": c["text2"],

        "delete_text": c["muted"],
        "delete_hover_text": c["delete"],

        "border_subtle": c["border"],
        "border_default": c["border"],
        "border_card_hover": c["border2"],
        "border_input_focus": c["accent"],
        "border_textedit_focus": c["accent"],
        "border_checkbox": c["border2"],
        "border_checkbox_hover": c["accent_light"],
        "border_disabled": c["border"],

        "selection_input": c["selection"],
        "selection_textedit": c["selection"],
        "selection_text": "#FFFFFF",

        "checkbox_text": c["text2"],
        "checkbox_bg": c["surface2"],
        "checkbox_hover_bg": c["surface3"],
        "checkbox_checked": gra(c["accent_light"], c["accent"], direction="diag"),
        "checkbox_checked_border": c["accent"],
        "checkbox_disabled_bg": c["bg"],

        "textedit_text": c["text"],
        "textedit_transparent_text": c["text"],

        "scrollbar": c["border"],
        "scrollbar_hover": c["accent"],

        "menu_text": c["text2"],
        "menu_selected_text": "#FFFFFF",

        "combo_text": c["text"],

        "dv_original_title": "",
        "dv_detail_title": "",
        "dv_detail_original_title": "",
        "dv_detail_section_title": "",
        "dv_detail_rating": "",
        "dv_detail_meta_text": "",
        "dv_detail_url": "",
        "dv_dialog_description": "",
        "dv_dialog_hint": "",
        "dv_detail_tag_btn": "",
        "dv_detail_tag_btn_hover": "",
        "dv_detail_tag_btn_pressed": "",
        "dv_detail_meta": "",
        "dv_detail_tags": "",
        "dv_dialog_separator": "",
        "dv_detail_description": "",
        "dv_is_remainder_point_color": "",
    }

    if dv and isinstance(dv, dict):
        theme.update(dv)
        
    base_color = c["surface2"]

    return base_color, theme


def _make_light_theme(c, dv=None):
    _, theme = _make_dark_theme(c, dv)
    theme.update({
        "primary_text": "#FFFFFF",
        "surface_card": gra(c["surface"], c["surface2"], direction="v"),
        "surface_button": gra(c["surface"], c["surface2"], direction="v"),
        "surface_button_hover": gra(c["surface2"], c["surface3"], direction="v"),
        "surface_button_pressed": c["surface3"],
        "border_card_hover": c["accent_light"],
        "scrollbar": c["border2"],
        "scrollbar_hover": c["accent"],
        "dv_is_remainder_point_color": "color: #A3A3A3;",
    })
    
    base_color = "#FFFFFF"
    return base_color ,theme



COLORS_DARK, COLORS_DARK_THEME = _make_dark_theme({
    "bg": "#121316", "bg2": "#1A1B1F",
    "surface": "#1E2024", "surface2": "#25282E", "surface3": "#2E323A", "surface4": "#383D47",
    "text": "#ECEEDF", "text2": "#9EA4B0", "muted": "#6B7280", "dim": "#4B5563",
    "border": "#2D3139", "border2": "#3F4552",
    "accent": "#6366F1", "accent_light": "#818CF8", "accent_dark": "#4F46E5",
    "selection": "#3730A3", "star": "#F59E0B", "delete": "#EF4444", "delete_bg": "#3B1719",
}, dv={
    "dv_app_title": "letter-spacing: 0.5px;",
    "dv_card": "border: 1px solid #2D3139; border-radius: 8px;",
    "dv_button": "letter-spacing: 0.3px;",
})

# 2. Light (라이트)
COLORS_LIGHT, COLORS_LIGHT_THEME = _make_light_theme({
    "bg": "#F8F9FA", "bg2": "#EDF0F2",
    "surface": "#FFFFFF", "surface2": "#F1F3F5", "surface3": "#E9ECEF", "surface4": "#DEE2E6",
    "text": "#212529", "text2": "#495057", "muted": "#868E96", "dim": "#ADB5BD",
    "border": "#E9ECEF", "border2": "#CED4DA",
    "accent": "#4F46E5", "accent_light": "#6366F1", "accent_dark": "#3730A3",
    "selection": "#E0E7FF", "star": "#D97706", "delete": "#DC2626", "delete_bg": "#FEE2E2",
}, dv={
    "dv_card": "border: 1px solid #E9ECEF; border-radius: 8px;",
    "dv_chip": "font-weight: 500;",
})

# 3. Blue (딥 블루)
COLORS_BLUE, COLORS_BLUE_THEME = _make_dark_theme({
    "bg": "#0B132B", "bg2": "#1C2541",
    "surface": "#1C2541", "surface2": "#273459", "surface3": "#3A4A78", "surface4": "#47598F",
    "text": "#E0E6ED", "text2": "#95A5A6", "muted": "#5C6B73", "dim": "#3D4A52",
    "border": "#253342", "border2": "#37495B",
    "accent": "#3A86FF", "accent_light": "#60A5FA", "accent_dark": "#2563EB",
    "selection": "#1D4ED8", "star": "#F59E0B", "delete": "#F87171", "delete_bg": "#371A22",
}, dv={
    "dv_app_title": "letter-spacing: 1px;",
    "dv_card": "border: 1px solid #253342; border-radius: 8px;",
})

# 4. Purple (퍼플 네온)
COLORS_PURPLE, COLORS_PURPLE_THEME = _make_dark_theme({
    "bg": "#130E1B", "bg2": "#1A1425",
    "surface": "#211A2E", "surface2": "#2C233D", "surface3": "#392E4E", "surface4": "#473A61",
    "text": "#F3EFF8", "text2": "#B3A7C3", "muted": "#7B6F8E", "dim": "#564B67",
    "border": "#352A4A", "border2": "#4B3C68",
    "accent": "#9D4EDD", "accent_light": "#C77DFF", "accent_dark": "#7B2CBF",
    "selection": "#5A189A", "star": "#FFB703", "delete": "#F72585", "delete_bg": "#391225",
}, dv={
    "dv_card": "border: 1px solid #352A4A; border-radius: 8px;",
    "dv_app_title": "letter-spacing: 1.2px;",
})

# 5. Cyan (시안 사이버)
COLORS_CYAN, COLORS_CYAN_THEME = _make_dark_theme({
    "bg": "#081417", "bg2": "#0E1E22",
    "surface": "#13272C", "surface2": "#1C363D", "surface3": "#264750", "surface4": "#315964",
    "text": "#E1FAF9", "text2": "#94C2C7", "muted": "#5C8B90", "dim": "#3D6367",
    "border": "#1F424A", "border2": "#2F5D68",
    "accent": "#00B4D8", "accent_light": "#90E0EF", "accent_dark": "#0077B6",
    "selection": "#023E8A", "star": "#FFB703", "delete": "#FF5A5F", "delete_bg": "#38171E",
}, dv={
    "dv_card": "border: 1px solid #1F424A; border-radius: 8px;",
})

# 6. Green (에메랄드 그린)
COLORS_GREEN, COLORS_GREEN_THEME = _make_dark_theme({
    "bg": "#0C140E", "bg2": "#131F17",
    "surface": "#18271D", "surface2": "#223528", "surface3": "#2D4736", "surface4": "#395944",
    "text": "#E8F5E9", "text2": "#A3C9A8", "muted": "#699470", "dim": "#47694E",
    "border": "#273E2E", "border2": "#385942",
    "accent": "#2EC4B6", "accent_light": "#80ED99", "accent_dark": "#107A72",
    "selection": "#155D57", "star": "#FFB703", "delete": "#E63946", "delete_bg": "#351518",
}, dv={
    "dv_card": "border: 1px solid #273E2E; border-radius: 8px;",
    "dv_chip": "letter-spacing: 0.2px;",
})

# 7. Red (크림슨 레드)
COLORS_RED, COLORS_RED_THEME = _make_dark_theme({
    "bg": "#190B0E", "bg2": "#241216",
    "surface": "#2D171C", "surface2": "#3B1E25", "surface3": "#4C2830", "surface4": "#5E333E",
    "text": "#FDF0F2", "text2": "#D4A5AD", "muted": "#966B73", "dim": "#69454C",
    "border": "#47232B", "border2": "#63323D",
    "accent": "#E63946", "accent_light": "#F87171", "accent_dark": "#9B1C1C",
    "selection": "#7F1D1D", "star": "#F59E0B", "delete": "#FF4D4D", "delete_bg": "#421217",
}, dv={
    "dv_card": "border: 1px solid #47232B; border-radius: 8px;",
})

# 8. Orange (스파이시 오렌지)
COLORS_ORANGE, COLORS_ORANGE_THEME = _make_dark_theme({
    "bg": "#191009", "bg2": "#24180E",
    "surface": "#2E1F13", "surface2": "#3C2A1B", "surface3": "#4D3624", "surface4": "#5F442E",
    "text": "#FCF3EC", "text2": "#D8B79D", "muted": "#9B7A60", "dim": "#6A503B",
    "border": "#473121", "border2": "#63452F",
    "accent": "#F97316", "accent_light": "#FB923C", "accent_dark": "#C2410C",
    "selection": "#9A3412", "star": "#F59E0B", "delete": "#EF4444", "delete_bg": "#3D1414",
}, dv={
    "dv_card": "border: 1px solid #473121; border-radius: 8px;",
})

# 9. Pink (핫 핑크)
COLORS_PINK, COLORS_PINK_THEME = _make_dark_theme({
    "bg": "#180C13", "bg2": "#23131D",
    "surface": "#2C1A25", "surface2": "#3B2432", "surface3": "#4B2E40", "surface4": "#5D3A50",
    "text": "#FDF2F7", "text2": "#D4A7C1", "muted": "#966D85", "dim": "#69485C",
    "border": "#46283C", "border2": "#613953",
    "accent": "#EC4899", "accent_light": "#F472B6", "accent_dark": "#BE185D",
    "selection": "#831843", "star": "#F59E0B", "delete": "#F43F5E", "delete_bg": "#3D121F",
}, dv={
    "dv_card": "border: 1px solid #46283C; border-radius: 8px;",
})

# 10. Yellow (선셋 옐로우)
COLORS_YELLOW, COLORS_YELLOW_THEME = _make_dark_theme({
    "bg": "#16140A", "bg2": "#211D0F",
    "surface": "#2B2615", "surface2": "#38321C", "surface3": "#474025", "surface4": "#584F30",
    "text": "#FAF7EC", "text2": "#CEC7A7", "muted": "#918A6A", "dim": "#635D43",
    "border": "#443D23", "border2": "#5E5533",
    "accent": "#EAB308", "accent_light": "#FACC15", "accent_dark": "#A16207",
    "selection": "#713F12", "star": "#F59E0B", "delete": "#EF4444", "delete_bg": "#3C1513",
}, dv={
    "dv_card": "border: 1px solid #443D23; border-radius: 8px;",
})

# 11. Amber (클래식 앰버)
COLORS_AMBER, COLORS_AMBER_THEME = _make_dark_theme({
    "bg": "#171109", "bg2": "#22190E",
    "surface": "#2C2113", "surface2": "#3A2C1B", "surface3": "#4A3924", "surface4": "#5C472E",
    "text": "#FAF4ED", "text2": "#D6C3AA", "muted": "#98846A", "dim": "#675743",
    "border": "#463521", "border2": "#604A30",
    "accent": "#D97706", "accent_light": "#F59E0B", "accent_dark": "#92400E",
    "selection": "#78350F", "star": "#F59E0B", "delete": "#EF4444", "delete_bg": "#3B1413",
}, dv={
    "dv_card": "border: 1px solid #463521; border-radius: 8px;",
})

# 12. Teal (딥 틸)
COLORS_TEAL, COLORS_TEAL_THEME = _make_dark_theme({
    "bg": "#091414", "bg2": "#0F1F1F",
    "surface": "#142828", "surface2": "#1C3737", "surface3": "#264747", "surface4": "#315858",
    "text": "#E6FAFA", "text2": "#97C5C5", "muted": "#5E8E8E", "dim": "#3E6363",
    "border": "#1F4242", "border2": "#2F5D5D",
    "accent": "#14B8A6", "accent_light": "#2DD4BF", "accent_dark": "#0F766E",
    "selection": "#115E59", "star": "#F59E0B", "delete": "#F87171", "delete_bg": "#371818",
}, dv={
    "dv_card": "border: 1px solid #1F4242; border-radius: 8px;",
})

# 13. Indigo (인디고 블루)
COLORS_INDIGO, COLORS_INDIGO_THEME = _make_dark_theme({
    "bg": "#0E101D", "bg2": "#15182B",
    "surface": "#1C2038", "surface2": "#252B4A", "surface3": "#31385E", "surface4": "#3E4775",
    "text": "#EEF2FF", "text2": "#A5B4FC", "muted": "#6366F1", "dim": "#4338CA",
    "border": "#283054", "border2": "#374272",
    "accent": "#6366F1", "accent_light": "#818CF8", "accent_dark": "#4338CA",
    "selection": "#312E81", "star": "#F59E0B", "delete": "#EF4444", "delete_bg": "#361622",
}, dv={
    "dv_card": "border: 1px solid #283054; border-radius: 8px;",
})

# 14. Slate (테크 슬레이트)
COLORS_SLATE, COLORS_SLATE_THEME = _make_dark_theme({
    "bg": "#0F172A", "bg2": "#1E293B",
    "surface": "#1E293B", "surface2": "#334155", "surface3": "#475569", "surface4": "#64748B",
    "text": "#F8FAFC", "text2": "#94A3B8", "muted": "#64748B", "dim": "#475569",
    "border": "#334155", "border2": "#475569",
    "accent": "#38BDF8", "accent_light": "#7DD3FC", "accent_dark": "#0284C7",
    "selection": "#0369A1", "star": "#F59E0B", "delete": "#F87171", "delete_bg": "#381B25",
}, dv={
    "dv_card": "border: 1px solid #334155; border-radius: 8px;",
    "dv_app_title": "letter-spacing: 0.8px;",
})

# 15. Mono (모노크롬)
COLORS_MONO, COLORS_MONO_THEME = _make_dark_theme({
    "bg": "#121212", "bg2": "#181818",
    "surface": "#1E1E1E", "surface2": "#282828", "surface3": "#333333", "surface4": "#3F3F3F",
    "text": "#F5F5F5", "text2": "#A0A0A0", "muted": "#6E6E6E", "dim": "#4A4A4A",
    "border": "#2C2C2C", "border2": "#3D3D3D",
    "accent": "#D4D4D4", "accent_light": "#FFFFFF", "accent_dark": "#A3A3A3",
    "selection": "#404040", "star": "#EAB308", "delete": "#EF4444", "delete_bg": "#331818",
}, dv={
    "dv_card": "border: 1px solid #2C2C2C; border-radius: 8px;",
    "dv_app_title": "letter-spacing: 1.5px;",
})

# 16. OLED (트루 블랙)
COLORS_OLED, COLORS_OLED_THEME = _make_dark_theme({
    "bg": "#000000", "bg2": "#080808",
    "surface": "#0F0F0F", "surface2": "#171717", "surface3": "#242424", "surface4": "#303030",
    "text": "#FFFFFF", "text2": "#A3A3A3", "muted": "#666666", "dim": "#404040",
    "border": "#222222", "border2": "#333333",
    "accent": "#38BDF8", "accent_light": "#7DD3FC", "accent_dark": "#0284C7",
    "selection": "#1D4ED8", "star": "#FACC15", "delete": "#F87171", "delete_bg": "#2B0F14",
}, dv={
    "dv_card": "border: 1px solid #222222; border-radius: 8px;",
})


THEMES = {
    "DARK": COLORS_DARK_THEME,
    "LIGHT": COLORS_LIGHT_THEME,
    "BLUE": COLORS_BLUE_THEME,
    "PURPLE": COLORS_PURPLE_THEME,
    "CYAN": COLORS_CYAN_THEME,
    "GREEN": COLORS_GREEN_THEME,
    "RED": COLORS_RED_THEME,
    "ORANGE": COLORS_ORANGE_THEME,
    "PINK": COLORS_PINK_THEME,
    "YELLOW": COLORS_YELLOW_THEME,
    "AMBER": COLORS_AMBER_THEME,
    "TEAL": COLORS_TEAL_THEME,
    "INDIGO": COLORS_INDIGO_THEME,
    "SLATE": COLORS_SLATE_THEME,
    "MONO": COLORS_MONO_THEME,
    "OLED": COLORS_OLED_THEME,
}