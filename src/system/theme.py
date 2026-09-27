from src.system.theme_tools import make_dark_theme, make_light_theme

COLORS_NEW_WHITE, THEME_WHITE = make_light_theme({
    "bg": "#F3F5F8", "bg2": "#E9ECF1", "surface": "#FFFFFF", "surface2": "#F5F7FA",
    "surface3": "#E9EDF3", "surface4": "#DDE2EA", "text": "#1D232C", "text2": "#505A68",
    "muted": "#747F8D", "dim": "#A5ADB8", "accent": "#3867D6", "accent_light": "#5B83E5",
    "accent_dark": "#2B52B5", "selection": "#3867D6", "star": "#C38A20", "delete": "#D34F5B",
    "delete_bg": "#FCEBED", "surface_combo_selected": "#3867D6",
    "radius_card": "10px", "radius_button": "8px", "radius_input": "8px", "radius_chip": "8px",
}, dv={
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #5B83E5, stop:1 #3867D6); color: #FFFFFF; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #6D92EB, stop:1 #4674DE); color: #FFFFFF;",
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #FFFFFF, stop:1 #EEF1F5); color: #1D232C; border: 1px solid rgba(29,35,44,0.12);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #F8FAFC, stop:1 #E7EBF1); color: #11161D; border: 1px solid rgba(56,103,214,0.25);",
})

COLORS_SAND, THEME_SAND = make_light_theme({
    "bg": "#F5F0E7", "bg2": "#EBE3D5", "surface": "#FCFAF5", "surface2": "#F4ECDD",
    "surface3": "#E9DECB", "surface4": "#D9C9B1", "text": "#302820", "text2": "#625548",
    "muted": "#827365", "dim": "#AD9D8A", "accent": "#A96F32", "accent_light": "#C28A4B",
    "accent_dark": "#865521", "selection": "#986329", "star": "#B77A1C", "delete": "#C84F49",
    "delete_bg": "#F9EAE3", "surface_combo_selected": "#986329",
    "radius_card": "11px", "radius_button": "8px", "radius_input": "8px", "radius_chip": "8px",
}, dv={
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #C28A4B, stop:1 #A96F32); color: #FFFFFF; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #D09A5A, stop:1 #B77939); color: #FFFFFF;",
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #F8F1E6, stop:1 #EEE3D3); color: #302820; border: 1px solid rgba(91,70,47,0.15);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #FBF5EC, stop:1 #E7DAC8); color: #241D17; border: 1px solid rgba(169,111,50,0.28);",
})

COLORS_ROSE, THEME_ROSE = make_light_theme({
    "bg": "#F7F2F4", "bg2": "#EEE5E9", "surface": "#FFFDFE", "surface2": "#F7EDF1",
    "surface3": "#EBDD E3".replace(" ", ""), "surface4": "#DCC6CF", "text": "#30242A",
    "text2": "#66525B", "muted": "#88717B", "dim": "#B39CA5", "accent": "#C45179",
    "accent_light": "#D66D92", "accent_dark": "#A83C62", "selection": "#AF4169",
    "star": "#B98322", "delete": "#C94F5B", "delete_bg": "#FAE9ED",
    "surface_combo_selected": "#AF4169", "radius_card": "12px", "radius_button": "9px",
    "radius_input": "9px", "radius_chip": "9px",
}, dv={
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #D66D92, stop:1 #C45179); color: #FFFFFF; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #E17FA2, stop:1 #D05D86); color: #FFFFFF;",
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #FAF3F6, stop:1 #F0E5EA); color: #30242A; border: 1px solid rgba(196,81,121,0.14);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #FFF8FA, stop:1 #E9D9E0); color: #241A20; border: 1px solid rgba(196,81,121,0.27);",
})

COLORS_YELLOW_HUD, THEME_YELLOW_HUD = make_dark_theme({
    "bg": "#10100F", "bg2": "#151512", "surface": "#1B1B18", "surface2": "#25251F",
    "surface3": "#303028", "surface4": "#3E3E31", "text": "#F4F1E3", "text2": "#D1CCAC",
    "muted": "#9A9578", "dim": "#68644F", "accent": "#D7B928", "accent_light": "#E9D24F",
    "accent_dark": "#A78F18", "selection": "#806D12", "star": "#E8C95A", "delete": "#D95765",
    "delete_bg": "#321B1E", "surface_combo_selected": "#806D12",
    "radius_card": "3px", "radius_button": "3px", "radius_input": "3px", "radius_chip": "3px",
    "border_card": "1px solid rgba(215,185,40,0.22); border-left: 3px solid #D7B928;",
    "border_button": "1px solid rgba(215,185,40,0.30)",
    "border_input": "1px solid rgba(215,185,40,0.20)",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #29291F, stop:1 #202019); color: #E8CE4B; border: 1px solid rgba(215,185,40,0.30);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #353528, stop:1 #29291F); color: #FFF4A8; border: 1px solid #D7B928;",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #E5C93B, stop:1 #C9AA1D); color: #17160D; font-weight: 800; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #F0D95A, stop:1 #D7B928); color: #17160D;",
    "dv_chip_btn_checked": "background: #D7B928; color: #17160D; font-weight: 750;",
})

COLORS_CRIMSON, THEME_CRIMSON = make_dark_theme({
    "bg": "#130D10", "bg2": "#1A1114", "surface": "#21171B", "surface2": "#2B1D22",
    "surface3": "#38262C", "surface4": "#49323A", "text": "#F4EAED", "text2": "#D2B9C1",
    "muted": "#9A7B85", "dim": "#68515A", "accent": "#D6455D", "accent_light": "#EA687A",
    "accent_dark": "#AC3047", "selection": "#85253A", "star": "#D5A63B", "delete": "#E45D69",
    "delete_bg": "#35181E", "surface_combo_selected": "#85253A",
    "radius_card": "6px", "radius_button": "5px", "radius_input": "5px", "radius_chip": "5px",
    "border_card": "1px solid rgba(214,69,93,0.24); border-left: 3px solid #D6455D;",
    "border_button": "1px solid rgba(214,69,93,0.28)",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #302027, stop:1 #261A1F); color: #F4EAED; border: 1px solid rgba(214,69,93,0.28);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #3D2930, stop:1 #302027); border: 1px solid #D6455D;",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #EA687A, stop:1 #D6455D); color: #FFFFFF; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #F07C8B, stop:1 #E4546B); color: #FFFFFF;",
})

COLORS_EMERALD, THEME_EMERALD = make_dark_theme({
    "bg": "#0B1210", "bg2": "#0F1915", "surface": "#17231D", "surface2": "#203129",
    "surface3": "#2B3D34", "surface4": "#385046", "text": "#EAF5EE", "text2": "#B9D4C4",
    "muted": "#7FA08B", "dim": "#526F5E", "accent": "#27A879", "accent_light": "#4ACD99",
    "accent_dark": "#18865F", "selection": "#146A4A", "star": "#D5A63B", "delete": "#D96770",
    "delete_bg": "#30191D", "surface_combo_selected": "#146A4A",
    "radius_card": "6px", "radius_button": "6px", "radius_input": "6px", "radius_chip": "6px",
    "border_card": "1px solid rgba(39,168,121,0.22); border-left: 3px solid #27A879;",
    "border_button": "1px solid rgba(39,168,121,0.28)",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #263A31, stop:1 #1C2C24); color: #DDF5E7; border: 1px solid rgba(39,168,121,0.28);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #30483D, stop:1 #263A31); color: #FFFFFF; border: 1px solid #46C996;",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #46C996, stop:1 #27A879); color: #07130E; font-weight: 800; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #5AD6A5, stop:1 #35B987); color: #07130E;",
})

COLORS_NORDIC, THEME_NORDIC = make_dark_theme({
    "bg": "#252B33", "bg2": "#20252C", "surface": "#303744", "surface2": "#394350",
    "surface3": "#454F60", "surface4": "#566276", "text": "#EBEEF3", "text2": "#CBD3DE",
    "muted": "#919DAB", "dim": "#697582", "accent": "#7195BC", "accent_light": "#94B5D2",
    "accent_dark": "#567AA0", "selection": "#4E7197", "star": "#D5B56A", "delete": "#BF6A73",
    "delete_bg": "#3A272B", "surface_combo_selected": "#4E7197",
    "radius_card": "9px", "radius_button": "7px", "radius_input": "7px", "radius_chip": "7px",
    "border_card": "1px solid rgba(148,181,210,0.18); border-top: 2px solid #94B5D2;",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #414B59, stop:1 #343D49); color: #EBEEF3; border: 1px solid rgba(148,181,210,0.25);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #505C6B, stop:1 #414B59); color: #FFFFFF; border: 1px solid #94B5D2;",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #87A9C9, stop:1 #7195BC); color: #10151B; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #A0BED8, stop:1 #87A9C9); color: #10151B;",
})

COLORS_BROWN, THEME_BROWN = make_dark_theme({
    "bg": "#211C18", "bg2": "#191512", "surface": "#2A2520", "surface2": "#353029",
    "surface3": "#433B33", "surface4": "#54493D", "text": "#F0E6D6", "text2": "#D0BFA7",
    "muted": "#9E8A72", "dim": "#70604F", "accent": "#C18A48", "accent_light": "#D8A664",
    "accent_dark": "#9C6B31", "selection": "#805624", "star": "#D9A83F", "delete": "#C96A5D",
    "delete_bg": "#39211E", "surface_combo_selected": "#805624",
    "radius_card": "6px", "radius_button": "6px", "radius_input": "6px", "radius_chip": "6px",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #3D362E, stop:1 #302A24); color: #EFE5D5; border: 1px solid rgba(193,138,72,0.27);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #4A4036, stop:1 #3D362E); color: #FFFFFF; border: 1px solid rgba(216,166,100,0.35);",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #D8A664, stop:1 #C18A48); color: #1D1712; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #E1B278, stop:1 #D09A59); color: #1D1712;",
})

COLORS_LAVENDER, THEME_LAVENDER = make_dark_theme({
    "bg": "#20202C", "bg2": "#191922", "surface": "#2A2A39", "surface2": "#343449",
    "surface3": "#41415A", "surface4": "#50506D", "text": "#EAE8F2", "text2": "#C6C2D8",
    "muted": "#918DA7", "dim": "#66627C", "accent": "#9586D8", "accent_light": "#B0A4E8",
    "accent_dark": "#7567B7", "selection": "#5F5398", "star": "#D6B66A", "delete": "#D47886",
    "delete_bg": "#39242B", "surface_combo_selected": "#5F5398",
    "radius_card": "11px", "radius_button": "8px", "radius_input": "8px", "radius_chip": "9px",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #3A3A50, stop:1 #303043); color: #E9E7F2; border: 1px solid rgba(176,164,232,0.23);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #484861, stop:1 #3A3A50); color: #FFFFFF; border: 1px solid rgba(176,164,232,0.45);",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #B0A4E8, stop:1 #9586D8); color: #15131D; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #C0B5EF, stop:1 #A397E0); color: #15131D;",
})

COLORS_NEW_TEAL, THEME_TEAL = make_dark_theme({
    "bg": "#0B1719", "bg2": "#091215", "surface": "#122225", "surface2": "#193036",
    "surface3": "#234149", "surface4": "#2E535C", "text": "#E7F3F3", "text2": "#B5D0D1",
    "muted": "#77999B", "dim": "#506F72", "accent": "#2B9B99", "accent_light": "#4CBDB9",
    "accent_dark": "#217876", "selection": "#185F61", "star": "#D2A83D", "delete": "#D7656D",
    "delete_bg": "#321B20", "surface_combo_selected": "#185F61",
    "radius_card": "7px", "radius_button": "6px", "radius_input": "6px", "radius_chip": "6px",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #1E383D, stop:1 #172B2F); color: #E5F1F1; border: 1px solid rgba(72,187,183,0.26);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #294A50, stop:1 #1E383D); color: #FFFFFF; border: 1px solid #48BBB7;",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #48BBB7, stop:1 #2B9B99); color: #071313; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #63CCC7, stop:1 #3DAFAD); color: #071313;",
})

COLORS_NEW_INDIGO, THEME_INDIGO = make_dark_theme({
    "bg": "#11131A", "bg2": "#0D0F15", "surface": "#191C26", "surface2": "#222735",
    "surface3": "#2D3344", "surface4": "#3A4256", "text": "#EEF0F6", "text2": "#B6BDCE",
    "muted": "#7D879B", "dim": "#555F73", "accent": "#6674D9", "accent_light": "#8490EA",
    "accent_dark": "#4E5BB9", "selection": "#414B99", "star": "#D8AE45", "delete": "#D95B6A",
    "delete_bg": "#32191F", "surface_combo_selected": "#414B99",
    "radius_card": "8px", "radius_button": "7px", "radius_input": "7px", "radius_chip": "7px",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #292E3D, stop:1 #202531); color: #EEF0F6; border: 1px solid rgba(132,144,234,0.24);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #363C4E, stop:1 #292E3D); color: #FFFFFF; border: 1px solid #8490EA;",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #8490EA, stop:1 #6674D9); color: #FFFFFF; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #9AA5F0, stop:1 #7886E2); color: #FFFFFF;",
})

COLORS_VIOLET, THEME_VIOLET = make_dark_theme({
    "bg": "#17141D", "bg2": "#121017", "surface": "#211C2A", "surface2": "#2C2638",
    "surface3": "#393148", "surface4": "#483E5A", "text": "#F0ECF4", "text2": "#C5BBD0",
    "muted": "#8D809B", "dim": "#62586D", "accent": "#A477C5", "accent_light": "#BE98DA",
    "accent_dark": "#865DA9", "selection": "#654581", "star": "#D8AD54", "delete": "#D76D7B",
    "delete_bg": "#371E25", "surface_combo_selected": "#654581",
    "radius_card": "10px", "radius_button": "7px", "radius_input": "7px", "radius_chip": "8px",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #342D41, stop:1 #29233A); color: #F0ECF4; border: 1px solid rgba(190,152,218,0.24);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #42394F, stop:1 #342D41); color: #FFFFFF; border: 1px solid #BE98DA;",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #BE98DA, stop:1 #A477C5); color: #17111C; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #CBA9E4, stop:1 #B58AD2); color: #17111C;",
})

COLORS_NEW_ORANGE, THEME_ORANGE = make_dark_theme({
    "bg": "#14110F", "bg2": "#0F0D0B", "surface": "#201A16", "surface2": "#2B231D",
    "surface3": "#382D24", "surface4": "#473A2E", "text": "#F3ECE5", "text2": "#CDBBAA",
    "muted": "#927D69", "dim": "#665546", "accent": "#D56A32", "accent_light": "#E5894E",
    "accent_dark": "#AE4E20", "selection": "#853A18", "star": "#D5A43C", "delete": "#D65D5D",
    "delete_bg": "#351C1A", "surface_combo_selected": "#853A18",
    "radius_card": "6px", "radius_button": "6px", "radius_input": "6px", "radius_chip": "6px",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #322820, stop:1 #271F19); color: #F3ECE5; border: 1px solid rgba(229,137,78,0.25);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #403329, stop:1 #322820); color: #FFFFFF; border: 1px solid #E5894E;",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #E5894E, stop:1 #D56A32); color: #190E08; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #F09A62, stop:1 #DF753C); color: #190E08;",
})

COLORS_DEEP_BLUE, THEME_DEEP_BLUE = make_dark_theme({
    "bg": "#0B111A", "bg2": "#080D14", "surface": "#121B27", "surface2": "#192636",
    "surface3": "#223448", "surface4": "#2C425A", "text": "#E8F0F7", "text2": "#B4C7D9",
    "muted": "#758CA1", "dim": "#506477", "accent": "#3F82B8", "accent_light": "#61A0D2",
    "accent_dark": "#2D6595", "selection": "#245172", "star": "#D3A743", "delete": "#D35E68",
    "delete_bg": "#301A1E", "surface_combo_selected": "#245172",
    "radius_card": "8px", "radius_button": "7px", "radius_input": "7px", "radius_chip": "7px",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #1E2D3D, stop:1 #162431); color: #E8F0F7; border: 1px solid rgba(97,160,210,0.25);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #294057, stop:1 #1E2D3D); color: #FFFFFF; border: 1px solid #61A0D2;",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #61A0D2, stop:1 #3F82B8); color: #07121A; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #76B1DE, stop:1 #4D91C4); color: #07121A;",
})

COLORS_NEW_MONO, THEME_MONO = make_dark_theme({
    "bg": "#111214", "bg2": "#0C0D0F", "surface": "#191A1D", "surface2": "#24262A",
    "surface3": "#303238", "surface4": "#3D4047", "text": "#EEEEF0", "text2": "#B2B4BA",
    "muted": "#777A82", "dim": "#50535A", "accent": "#A2A6AE", "accent_light": "#C7CAD0",
    "accent_dark": "#7D8189", "selection": "#50545B", "star": "#C9A85B", "delete": "#D46068",
    "delete_bg": "#321A1D", "surface_combo_selected": "#50545B",
    "radius_card": "5px", "radius_button": "5px", "radius_input": "5px", "radius_chip": "5px",
    "border_card": "1px solid rgba(255,255,255,0.10)",
    "border_button": "1px solid rgba(255,255,255,0.15)",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #292B2F, stop:1 #202226); color: #EEEEF0; border: 1px solid rgba(255,255,255,0.15); font-weight: 650;",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #373A40, stop:1 #292B2F); color: #FFFFFF; border: 1px solid #C7CAD0;",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #C0C4CA, stop:1 #969AA1); color: #101114; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #D0D3D8, stop:1 #A9ADB4); color: #101114;",
})

COLORS_NEW_CYAN, THEME_CYAN = make_dark_theme({
    "bg": "#0A1519", "bg2": "#081115", "surface": "#122027", "surface2": "#192D35",
    "surface3": "#23404A", "surface4": "#2E515C", "text": "#E7F5F7", "text2": "#B2D2D7",
    "muted": "#729AA2", "dim": "#4F7077", "accent": "#299BB0", "accent_light": "#50BDD0",
    "accent_dark": "#1E7487", "selection": "#185B69", "star": "#D2A840", "delete": "#D45E69",
    "delete_bg": "#311A1F", "surface_combo_selected": "#185B69",
    "radius_card": "7px", "radius_button": "6px", "radius_input": "6px", "radius_chip": "6px",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #203841, stop:1 #182A31); color: #E7F5F7; border: 1px solid rgba(80,189,208,0.27);",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #2C4B55, stop:1 #203841); color: #FFFFFF; border: 1px solid #50BDD0;",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #50BDD0, stop:1 #299BB0); color: #061215; font-weight: 750; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #6CCBDD, stop:1 #3AA9BC); color: #061215;",
})

COLORS_NEW_OLED, THEME_OLED = make_dark_theme({
    "bg": "#000000", "bg2": "#030303", "surface": "#08090A", "surface2": "#111315",
    "surface3": "#1A1D20", "surface4": "#25292D", "text": "#F7F8F9", "text2": "#A9ADB2",
    "muted": "#6D7278", "dim": "#41454A", "accent": "#63C7D4", "accent_light": "#86DCE6",
    "accent_dark": "#3894A1", "selection": "#1B5962", "star": "#D5AE43", "delete": "#D85F68",
    "delete_bg": "#260D10", "surface_combo_selected": "#1B5962",
    "radius_card": "6px", "radius_button": "6px", "radius_input": "6px", "radius_chip": "6px",
    "border_card": "1px solid rgba(99,199,212,0.27)",
    "border_button": "1px solid rgba(99,199,212,0.32)",
    "border_input": "1px solid rgba(99,199,212,0.24)",
}, dv={
    "dv_button": "background: qlineargradient(y1:0, y2:1, stop:0 #151719, stop:1 #0C0E10); color: #DDF8FA; border: 1px solid rgba(99,199,212,0.32); font-weight: 650;",
    "dv_button_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #202427, stop:1 #151719); color: #FFFFFF; border: 1px solid #63C7D4;",
    "dv_primary_btn": "background: qlineargradient(y1:0, y2:1, stop:0 #86DCE6, stop:1 #63C7D4); color: #041013; font-weight: 800; border: none;",
    "dv_primary_btn_hover": "background: qlineargradient(y1:0, y2:1, stop:0 #9BE4EC, stop:1 #74CFDA); color: #041013;",
})

THEMES = {
    "NEW WHITE": THEME_WHITE, "SAND": THEME_SAND, "ROSE": THEME_ROSE,
    "YELLOW_HUD": THEME_YELLOW_HUD, "CRIMSON": THEME_CRIMSON, "EMERALD": THEME_EMERALD,
    "NORDIC": THEME_NORDIC, "BROWN": THEME_BROWN, "LAVENDER": THEME_LAVENDER,
    "NEW TEAL": THEME_TEAL, "NEW INDIGO": THEME_INDIGO, "VIOLET": THEME_VIOLET,
    "NEW ORANGE": THEME_ORANGE, "DEEP_BLUE": THEME_DEEP_BLUE, "NEW MONO": THEME_MONO,
    "NEW CYAN": THEME_CYAN, "NEW OLED": THEME_OLED,
}

THEME_DATA = {
    "NEW 화이트": "NEW WHITE", "NEW 틸": "NEW TEAL", "NEW 인디고": "NEW INDIGO",
    "NEW 오렌지": "NEW ORANGE", "NEW 모노": "NEW MONO", "NEW 시안": "NEW CYAN",
    "NEW OLED": "NEW OLED", "샌드": "SAND", "로즈": "ROSE", "옐로우 HUD": "YELLOW_HUD",
    "크림슨": "CRIMSON", "에메랄드": "EMERALD", "노르딕": "NORDIC", "브라운": "BROWN",
    "라벤더": "LAVENDER", "바이올렛": "VIOLET", "딥 블루": "DEEP_BLUE",
}