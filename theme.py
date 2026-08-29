def gra(*colors, direction="v"):
    if not colors:
        return "#000000"

    colors = tuple(str(c) for c in colors if c)

    if len(colors) == 1:
        return colors[0]

    if direction == "h":
        x1, y1, x2, y2 = 0, 0, 1, 0
    elif direction == "diag":
        x1, y1, x2, y2 = 0, 0, 1, 1
    elif direction == "reverse":
        x1, y1, x2, y2 = 1, 1, 0, 0
    else:
        x1, y1, x2, y2 = 0, 0, 0, 1

    step = 1.0 / (len(colors) - 1)

    stops = ", ".join(
        f"stop: {i * step:g} {color}"
        for i, color in enumerate(colors)
    )

    return (
        f"qlineargradient("
        f"x1: {x1}, y1: {y1}, "
        f"x2: {x2}, y2: {y2}, "
        f"{stops})"
    )

# ============================================================
# THEME BUILDER
# ============================================================

def _make_theme(c):
    return {
       
       
       

        "bg": gra(c["bg"], c["bg2"]),
        "text": c["text"],

       
       
       

        "text_primary": c["text"],
        "text_title": c["text"],
        "text_title_bright": c["accent_light"],
        "text_title_sub": c["text"],
        "text_secondary": c["text2"],
        "text_secondary_light": c["text2"],
        "text_input": c["text"],
        "text_input_list": c["text2"],
        "text_button": c["text2"],
        "text_button_hover": c["text"],
        "text_button_pressed": c["text2"],
        "text_muted": c["muted"],
        "text_meta": c["muted"],
        "text_url": c["accent"],
        "text_category": c["muted"],
        "text_dim": c["dim"],
        "text_disabled": c["dim"],
        "text_disabled_button": c["dim"],
        "text_group": c["muted"],
        "text_group_title": c["text2"],
        "text_star": c["star"],

       
       
       

        "surface_card": gra(c["surface"], c["surface2"]),
        "surface_button": gra(c["surface2"], c["surface3"]),
        "surface_input": gra(c["surface2"], c["surface3"]),
        "surface_textedit": gra(c["surface"], c["surface2"]),
        "surface_chip": gra(c["surface2"], c["surface3"]),
        "surface_tag": gra(c["surface2"], c["surface3"]),
        "surface_hover": gra(c["surface2"], c["surface3"]),
        "surface_button_hover": gra(c["surface3"], c["surface4"]),
        "surface_input_hover": gra(c["surface2"], c["surface3"]),
        "surface_input_focus": gra(c["surface3"], c["surface4"]),
        "surface_textedit_hover": gra(c["surface2"], c["surface3"]),
        "surface_textedit_focus": gra(c["surface3"], c["surface4"]),
        "surface_button_pressed": gra(c["surface"], c["surface2"]),
        "surface_disabled": c["surface"],
        "surface_checkbox_hover": gra(c["surface2"], c["surface3"]),
        "surface_menu": gra(c["surface"], c["surface2"]),
        "surface_menu_selected": gra(c["surface2"], c["surface3"]),
        "surface_combo_selected": gra(c["surface2"], c["surface3"]),
        "surface_delete_hover": c["delete_bg"],
        "surface_chip_hover": gra(c["surface2"], c["surface3"]),

       
       
       

        "primary_bg": gra(
            c["accent_light"],
            c["accent"],
            c["accent_dark"]
        ),

        "primary_text": "#FFFFFF",

        "primary_hover": gra(
            c["accent_light"],
            c["accent"]
        ),

        "primary_hover_text": "#FFFFFF",

        "primary_pressed": gra(
            c["accent"],
            c["accent_dark"]
        ),

       
       
       

        "secondary_bg": gra(
            c["surface2"],
            c["surface3"]
        ),

        "secondary_text": c["text2"],

        "secondary_hover": gra(
            c["surface3"],
            c["surface4"]
        ),

        "secondary_hover_text": c["text"],

       
       
       

        "chip_text": c["muted"],
        "chip_hover_text": c["text2"],

        "chip_checked": gra(
            c["accent_light"],
            c["accent"],
            c["accent_dark"]
        ),

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
        "border_checkbox_hover": c["accent"],
        "border_disabled": c["border"],

       
       
       

        "selection_input": c["selection"],
        "selection_textedit": c["selection"],
        "selection_text": "#FFFFFF",

       
       
       

        "checkbox_text": c["text2"],
        "checkbox_bg": gra(c["surface2"], c["surface3"]),
        "checkbox_hover_bg": gra(c["surface3"], c["surface4"]),

        "checkbox_checked": gra(
            c["accent_light"],
            c["accent"],
            c["accent_dark"]
        ),

        "checkbox_checked_border": c["accent"],
        "checkbox_disabled_bg": c["surface"],

       
       
       

        "textedit_text": c["text2"],
        "textedit_transparent_text": c["text"],

       
       
       

        "scrollbar": gra(
            c["border"],
            c["border2"]
        ),

        "scrollbar_hover": c["accent"],

       
       
       

        "menu_text": c["text2"],
        "menu_selected_text": "#FFFFFF",

       
       
       

        "combo_text": c["text"],
    }

# ============================================================
# DARK
# ============================================================

COLORS_DARK_THEME = _make_theme({
    "bg": "#111214",
    "bg2": "#18191C",

    "surface": "#18191B",
    "surface2": "#202124",
    "surface3": "#292A2D",
    "surface4": "#34363A",

    "text": "#E8E9EB",
    "text2": "#B9BABE",
    "muted": "#85868B",
    "dim": "#626368",

    "border": "#303135",
    "border2": "#414247",

    "accent": "#A8AAAF",
    "accent_light": "#D2D4D8",
    "accent_dark": "#7F8186",

    "selection": "#414348",

    "star": "#D5A36C",
    "delete": "#FF7078",
    "delete_bg": "#32191C",
})

# ============================================================
# LIGHT
# ============================================================

COLORS_LIGHT_THEME = _make_theme({
    "bg": "#F3F3F1",
    "bg2": "#EAEAE7",

    "surface": "#FFFFFF",
    "surface2": "#F2F2EF",
    "surface3": "#E8E8E4",
    "surface4": "#DDDDD8",

    "text": "#202124",
    "text2": "#56575A",
    "muted": "#77787B",
    "dim": "#9B9C9F",

    "border": "#D5D5D0",
    "border2": "#C3C3BE",

    "accent": "#617487",
    "accent_light": "#8194A6",
    "accent_dark": "#465A6D",

    "selection": "#C5D2DD",

    "star": "#C48D45",
    "delete": "#D95760",
    "delete_bg": "#F7E5E6",
})

# ============================================================
# BLUE
# ============================================================

COLORS_BLUE_THEME = _make_theme({
    "bg": "#0D1724",
    "bg2": "#142235",

    "surface": "#142235",
    "surface2": "#1A2C43",
    "surface3": "#243A54",
    "surface4": "#304B68",

    "text": "#E3EEF9",
    "text2": "#B4C9DD",
    "muted": "#8199B1",
    "dim": "#61768C",

    "border": "#29415D",
    "border2": "#365675",

    "accent": "#4F9BE8",
    "accent_light": "#78B7F2",
    "accent_dark": "#3978C4",

    "selection": "#315D8A",

    "star": "#D7A85F",
    "delete": "#FF7078",
    "delete_bg": "#352026",
})

# ============================================================
# PURPLE
# ============================================================

COLORS_PURPLE_THEME = _make_theme({
    "bg": "#160F21",
    "bg2": "#1D132A",

    "surface": "#21172F",
    "surface2": "#2A1E3D",
    "surface3": "#35264C",
    "surface4": "#42305B",

    "text": "#F0E8F7",
    "text2": "#C8B8D7",
    "muted": "#9582A7",
    "dim": "#705E80",

    "border": "#493661",
    "border2": "#60497D",

    "accent": "#A97AE8",
    "accent_light": "#C19BEF",
    "accent_dark": "#8959C9",

    "selection": "#68458D",

    "star": "#D7A85F",
    "delete": "#FF7188",
    "delete_bg": "#38202C",
})

# ============================================================
# CYAN
# ============================================================

COLORS_CYAN_THEME = _make_theme({
    "bg": "#09191C",
    "bg2": "#0E2226",

    "surface": "#10262A",
    "surface2": "#163237",
    "surface3": "#1D3E44",
    "surface4": "#285057",

    "text": "#E2F2F4",
    "text2": "#B2D2D6",
    "muted": "#789DA2",
    "dim": "#57777B",

    "border": "#285159",
    "border2": "#35666E",

    "accent": "#42C7D6",
    "accent_light": "#70DCE7",
    "accent_dark": "#2DAAB9",

    "selection": "#286A73",

    "star": "#D7A85F",
    "delete": "#FF7078",
    "delete_bg": "#352026",
})

# ============================================================
# GREEN
# ============================================================

COLORS_GREEN_THEME = _make_theme({
    "bg": "#0C1811",
    "bg2": "#112219",

    "surface": "#13251A",
    "surface2": "#19301F",
    "surface3": "#203B27",
    "surface4": "#2B4933",

    "text": "#E3F2E8",
    "text2": "#B5D5BE",
    "muted": "#7FA48A",
    "dim": "#5B7964",

    "border": "#2C5135",
    "border2": "#396745",

    "accent": "#4DCB7A",
    "accent_light": "#79DD9B",
    "accent_dark": "#3BAE69",

    "selection": "#2E7548",

    "star": "#D7A85F",
    "delete": "#FF7078",
    "delete_bg": "#342026",
})

# ============================================================
# RED
# ============================================================

COLORS_RED_THEME = _make_theme({
    "bg": "#1C0C10",
    "bg2": "#251116",

    "surface": "#2A1318",
    "surface2": "#35191F",
    "surface3": "#421F26",
    "surface4": "#512832",

    "text": "#F7E6E8",
    "text2": "#D8B5B9",
    "muted": "#A27A80",
    "dim": "#7C585D",

    "border": "#5A2B34",
    "border2": "#713843",

    "accent": "#E85D68",
    "accent_light": "#F0838B",
    "accent_dark": "#C94858",

    "selection": "#73333D",

    "star": "#E0A65D",
    "delete": "#FF7A83",
    "delete_bg": "#4A2025",
})

# ============================================================
# ORANGE
# ============================================================

COLORS_ORANGE_THEME = _make_theme({
    "bg": "#1C1108",
    "bg2": "#24160B",

    "surface": "#2A180C",
    "surface2": "#351F10",
    "surface3": "#422712",
    "surface4": "#523219",

    "text": "#F8E9DA",
    "text2": "#D9BEA5",
    "muted": "#A7866D",
    "dim": "#7D654F",

    "border": "#5A361A",
    "border2": "#71451F",

    "accent": "#F39A45",
    "accent_light": "#FFB66D",
    "accent_dark": "#DD7732",

    "selection": "#80501F",

    "star": "#D9A34D",
    "delete": "#FF7078",
    "delete_bg": "#432126",
})

# ============================================================
# PINK
# ============================================================

COLORS_PINK_THEME = _make_theme({
    "bg": "#1C0C15",
    "bg2": "#25101C",

    "surface": "#2A1320",
    "surface2": "#35192A",
    "surface3": "#421F34",
    "surface4": "#51283F",

    "text": "#F8E5EE",
    "text2": "#D9B5C6",
    "muted": "#A47B91",
    "dim": "#7B5A6C",

    "border": "#592B46",
    "border2": "#703858",

    "accent": "#E96C9E",
    "accent_light": "#F18DB5",
    "accent_dark": "#D4558B",

    "selection": "#743654",

    "star": "#D8A05E",
    "delete": "#FF7188",
    "delete_bg": "#43202E",
})

# ============================================================
# YELLOW
# ============================================================

COLORS_YELLOW_THEME = _make_theme({
    "bg": "#191708",
    "bg2": "#211D0B",

    "surface": "#27230D",
    "surface2": "#332E12",
    "surface3": "#403A17",
    "surface4": "#4F471C",

    "text": "#F5F0D9",
    "text2": "#D5CFA8",
    "muted": "#9E966D",
    "dim": "#766F4F",

    "border": "#584F1F",
    "border2": "#70652A",

    "accent": "#DCC447",
    "accent_light": "#EBD66C",
    "accent_dark": "#C4A934",

    "selection": "#756A20",

    "star": "#E0A44D",
    "delete": "#FF7078",
    "delete_bg": "#443025",
})

# ============================================================
# AMBER
# ============================================================

COLORS_AMBER_THEME = _make_theme({
    "bg": "#1B1207",
    "bg2": "#23180A",

    "surface": "#291A0A",
    "surface2": "#35230D",
    "surface3": "#422C11",
    "surface4": "#513719",

    "text": "#F7EBDD",
    "text2": "#D7BE9C",
    "muted": "#A48865",
    "dim": "#7C654A",

    "border": "#5A3C18",
    "border2": "#714B1E",

    "accent": "#E6A33D",
    "accent_light": "#F3BD62",
    "accent_dark": "#C98729",

    "selection": "#754A19",

    "star": "#E0A04B",
    "delete": "#FF7078",
    "delete_bg": "#442126",
})

# ============================================================
# TEAL
# ============================================================

COLORS_TEAL_THEME = _make_theme({
    "bg": "#081815",
    "bg2": "#0D211C",

    "surface": "#0F2520",
    "surface2": "#15302A",
    "surface3": "#1C3B34",
    "surface4": "#285047",

    "text": "#E0F1ED",
    "text2": "#B0D2C9",
    "muted": "#789E95",
    "dim": "#56766F",

    "border": "#285047",
    "border2": "#35645A",

    "accent": "#43C5B1",
    "accent_light": "#70D9C7",
    "accent_dark": "#2FA692",

    "selection": "#276E62",

    "star": "#D5A36C",
    "delete": "#FF7078",
    "delete_bg": "#352026",
})

# ============================================================
# INDIGO
# ============================================================

COLORS_INDIGO_THEME = _make_theme({
    "bg": "#0D1020",
    "bg2": "#12162A",

    "surface": "#151932",
    "surface2": "#1B2040",
    "surface3": "#22294E",
    "surface4": "#2E3760",

    "text": "#E7EAF7",
    "text2": "#B8C0DD",
    "muted": "#7F89AE",
    "dim": "#5F6889",

    "border": "#303967",
    "border2": "#3F4B80",

    "accent": "#7187E8",
    "accent_light": "#94A6F0",
    "accent_dark": "#596FD0",

    "selection": "#3D4C92",

    "star": "#D7A85F",
    "delete": "#FF7078",
    "delete_bg": "#352026",
})

# ============================================================
# SLATE
# ============================================================

COLORS_SLATE_THEME = _make_theme({
    "bg": "#11171D",
    "bg2": "#171F27",

    "surface": "#192129",
    "surface2": "#202B35",
    "surface3": "#293640",
    "surface4": "#354550",

    "text": "#E5EBEF",
    "text2": "#BAC7CF",
    "muted": "#82919B",
    "dim": "#63717A",

    "border": "#354550",
    "border2": "#455764",

    "accent": "#8199AD",
    "accent_light": "#A2B5C5",
    "accent_dark": "#667E92",

    "selection": "#40515E",

    "star": "#D5A36C",
    "delete": "#FF7078",
    "delete_bg": "#352026",
})

# ============================================================
# MONO
# ============================================================

COLORS_MONO_THEME = _make_theme({
    "bg": "#111111",
    "bg2": "#181818",

    "surface": "#191919",
    "surface2": "#222222",
    "surface3": "#2B2B2B",
    "surface4": "#373737",

    "text": "#E8E8E8",
    "text2": "#B8B8B8",
    "muted": "#858585",
    "dim": "#626262",

    "border": "#363636",
    "border2": "#454545",

    "accent": "#A8A8A8",
    "accent_light": "#D0D0D0",
    "accent_dark": "#858585",

    "selection": "#444444",

    "star": "#BFA16A",
    "delete": "#FF7078",
    "delete_bg": "#332020",
})

# ============================================================
# OLED
# ============================================================

COLORS_OLED_THEME = _make_theme({
    "bg": "#000000",
    "bg2": "#050505",

    "surface": "#080808",
    "surface2": "#101010",
    "surface3": "#181818",
    "surface4": "#222222",

    "text": "#F5F5F5",
    "text2": "#C2C2C2",
    "muted": "#888888",
    "dim": "#606060",

    "border": "#252525",
    "border2": "#353535",

    "accent": "#4D9EFF",
    "accent_light": "#82C0FF",
    "accent_dark": "#347DD0",

    "selection": "#254F7D",

    "star": "#D5A36C",
    "delete": "#FF7078",
    "delete_bg": "#32191C",
})

# ============================================================
# ALL THEMES
# ============================================================

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

# ============================================================
# THEME NAMES
# ============================================================

THEME_NAMES = {
    "DARK": "다크",
    "LIGHT": "라이트",
    "BLUE": "블루",
    "PURPLE": "퍼플",
    "CYAN": "시안",
    "GREEN": "그린",
    "RED": "레드",
    "ORANGE": "오렌지",
    "PINK": "핑크",
    "YELLOW": "옐로우",
    "AMBER": "앰버",
    "TEAL": "틸",
    "INDIGO": "인디고",
    "SLATE": "슬레이트",
    "MONO": "모노",
    "OLED": "OLED",
}

# ============================================================
# GET THEME
# ============================================================

def get_theme(name="DARK"):
    return THEMES.get(str(name).upper(), COLORS_DARK_THEME)

# ============================================================
# APPLY QSS
# ============================================================

def apply_theme(widget, qss, theme="DARK"):
    colors = get_theme(theme)

    try:
        stylesheet = qss.format(**colors)
    except KeyError as e:
        raise KeyError(f"QSS에서 정의되지 않은 색상 변수: {e}") from e

    widget.setStyleSheet(stylesheet)

    return stylesheet