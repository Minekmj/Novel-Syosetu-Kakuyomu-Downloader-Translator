import copy, re
from PySide6.QtWidgets import (
    QToolButton, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel,
    QFrame, QDialog, QCheckBox, QComboBox, QScrollArea, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontDatabase

DEFAULT_EPUB_DATA = {
    "global": {
        "font": "Malgun Gothic"
    },
    "body": {
        "subtitle": {"size": "h2", "align": "center", "bold": True, "italic": False},
        "spacing_dialogue": True,
        "spacing_dialogue_continuous": False,
        "spacing_dialogue_parenthesis": False,
        "spacing_dash": True,
        "spacing_parenthesis": True,
        "spacing_transition": True,
        "spacing_general": True,
        "separator": {"spacing": True, "center": True}
    }
}

def merge_epub_data(user_data):
    def _merge(default, user):
        if not isinstance(user, dict):
            return copy.deepcopy(default)
        res = copy.deepcopy(default)
        for k, v in user.items():
            if k in res and isinstance(res[k], dict) and isinstance(v, dict):
                res[k] = _merge(res[k], v)
            else:
                res[k] = copy.deepcopy(v)
        return res
    if not isinstance(user_data, dict):
        return copy.deepcopy(DEFAULT_EPUB_DATA)
    merged = _merge(DEFAULT_EPUB_DATA, user_data.get("epub_data", user_data))
    return {"epub_data": merged}

def calculate_epub_breaks(lines, b_conf):
    transition_words = (
        "어느 날", "어느날", "그날", "다음 날", "다음날", "며칠 후", "며칠 뒤",
        "그 후", "잠시 후", "한편", "그때", "얼마 후", "얼마 뒤", "다음 순간", "그 순간"
    )
    back_mark = -1
    in_dialogue = False
    in_parenthesis = False
    dialogue_context = False
    data = []
    for line in lines:
        cleaned = line.replace('「', '“').replace('」', '”').replace("｢", "“").replace("｣", "”").replace("<", "〈").replace(">", "〉")
        stripped = re.sub(r'\s+', '', cleaned)
        if not stripped:
            data.append(False)
            continue
        start = False
        first_char = cleaned[0]
        if not in_dialogue and not in_parenthesis:
            if first_char in ('“', '"', '『'):
                if back_mark == 1:
                    if b_conf.get("spacing_dialogue_continuous", False):
                        start = True
                elif back_mark == 3 and dialogue_context:
                    if b_conf.get("spacing_dialogue_continuous", False):
                        start = True
                else:
                    if b_conf.get("spacing_dialogue", True):
                        start = True
                if not ('”' in cleaned or '"' in cleaned[1:] or '』' in cleaned):
                    in_dialogue = True
                back_mark = 1
                dialogue_context = True
            elif first_char in ('(', '（'):
                if dialogue_context:
                    if b_conf.get("spacing_dialogue_parenthesis", False):
                        start = True
                else:
                    if back_mark != 3 and b_conf.get("spacing_parenthesis", True):
                        start = True
                if not (')' in cleaned or '）' in cleaned):
                    in_parenthesis = True
                back_mark = 3
            elif first_char in ('-', '—', '―'):
                dialogue_context = False
                if back_mark != 2 and b_conf.get("spacing_dash", True):
                    start = True
                back_mark = 2
            else:
                dialogue_context = False
                is_trans = any(cleaned.startswith(tw) for tw in transition_words)
                if is_trans:
                    if b_conf.get("spacing_transition", True):
                        start = True
                elif back_mark != 0:
                    if b_conf.get("spacing_general", True):
                        start = True
                back_mark = 0
        else:
            if in_dialogue and ('”' in cleaned or '"' in cleaned or '』' in cleaned):
                in_dialogue = False
            if in_parenthesis and (')' in cleaned or '）' in cleaned):
                in_parenthesis = False
        if re.fullmatch(r'''[^\w.\"'\'「」『』“”‘’!?。…]{1,}''', stripped):
            start = True
            back_mark = -1
            dialogue_context = False
        data.append(start)
    return data

class SubtitleElement(QWidget):
    changed = Signal()
    opened = Signal(object)
    def __init__(self, text, config, parent=None):
        super().__init__(parent)
        self.text = text
        self.config = config
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.preview_btn = QPushButton(self.text, self)
        self.preview_btn.setCursor(Qt.PointingHandCursor)
        self.preview_btn.setCheckable(True)
        self.preview_btn.clicked.connect(self.on_btn_click)
        layout.addWidget(self.preview_btn)
        self.panel = QWidget(self)
        self.panel.setStyleSheet("QWidget { border: None; } QToolButton { background-color: #3c3f41; color: #fff; border: 1px solid #555; border-radius: 3px; padding: 3px 7px; } QToolButton:checked { background-color: #007acc; border-color: #0098ff; }")
        panel_layout = QHBoxLayout(self.panel)
        panel_layout.setContentsMargins(8, 6, 8, 6)
        panel_layout.setSpacing(6)
        self.size_group = QButtonGroup(self)
        for s in ["h1", "h2", "h3"]:
            b = QToolButton()
            b.setText(s.upper())
            b.setCheckable(True)
            if self.config.get("size", "h2") == s:
                b.setChecked(True)
            b.clicked.connect(lambda _, val=s: self.set_size(val))
            self.size_group.addButton(b)
            panel_layout.addWidget(b)
        panel_layout.addSpacing(6)
        self.align_group = QButtonGroup(self)
        aligns = [("좌", "left"), ("중", "center"), ("우", "right")]
        for label, val in aligns:
            b = QToolButton()
            b.setText(label)
            b.setCheckable(True)
            if self.config.get("align", "center") == val:
                b.setChecked(True)
            b.clicked.connect(lambda _, a=val: self.set_align(a))
            self.align_group.addButton(b)
            panel_layout.addWidget(b)
        panel_layout.addSpacing(6)
        self.bold_btn = QToolButton()
        self.bold_btn.setText("B")
        self.bold_btn.setStyleSheet("font-weight: bold;")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setChecked(self.config.get("bold", True))
        self.bold_btn.clicked.connect(self.set_bold)
        panel_layout.addWidget(self.bold_btn)
        self.italic_btn = QToolButton()
        self.italic_btn.setText("I")
        self.italic_btn.setStyleSheet("font-style: italic;")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setChecked(self.config.get("italic", False))
        self.italic_btn.clicked.connect(self.set_italic)
        panel_layout.addWidget(self.italic_btn)
        panel_layout.addStretch()
        self.panel.setVisible(False)
        layout.addWidget(self.panel)
        self.update_view()
    def on_btn_click(self, checked):
        self.panel.setVisible(checked)
        if checked:
            self.opened.emit(self)
    def close_panel(self):
        self.preview_btn.setChecked(False)
        self.panel.setVisible(False)
    def set_size(self, val):
        self.config["size"] = val
        self.changed.emit()
    def set_align(self, val):
        self.config["align"] = val
        self.changed.emit()
    def set_bold(self):
        self.config["bold"] = self.bold_btn.isChecked()
        self.changed.emit()
    def set_italic(self):
        self.config["italic"] = self.italic_btn.isChecked()
        self.changed.emit()
    def update_view(self, inherited_font="serif"):
        size_px = {"h1": 24, "h2": 20, "h3": 16}.get(self.config.get("size", "h2"), 20)
        bold = "bold" if self.config.get("bold") else "normal"
        italic = "italic" if self.config.get("italic") else "normal"
        align = self.config.get("align", "center")
        self.preview_btn.setStyleSheet(f"QPushButton {{ border: 1px dashed transparent; border-radius: 4px; background: transparent; color: #111111; font-size: {size_px}px; font-weight: {bold}; font-style: {italic}; font-family: '{inherited_font}'; text-align: {align}; padding: 8px 4px; }} QPushButton:hover {{ border: 1px dashed #007acc; background: rgba(0, 122, 204, 0.08); }} QPushButton:checked {{ border: 1px solid #007acc; background: rgba(0, 122, 204, 0.12); }}")

class BodyBreakElement(QWidget):
    changed = Signal()
    opened = Signal(object)
    def __init__(self, text, config, key, label_text, parent=None):
        super().__init__(parent)
        self.text = text
        self.config = config
        self.key = key
        self.spacing = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.preview_btn = QPushButton(self.text, self)
        self.preview_btn.setCursor(Qt.PointingHandCursor)
        self.preview_btn.setCheckable(True)
        self.preview_btn.clicked.connect(self.on_btn_click)
        layout.addWidget(self.preview_btn)
        self.panel = QWidget(self)
        self.panel.setStyleSheet("QWidget { border: None; border-radius: 4px; color:black; }")
        panel_layout = QHBoxLayout(self.panel)
        panel_layout.setContentsMargins(8, 6, 8, 6)
        panel_layout.setSpacing(6)
        self.spacing_chk = QCheckBox(label_text)
        self.spacing_chk.setChecked(self.config.get(self.key, True))
        self.spacing_chk.toggled.connect(self.on_chk_toggle)
        panel_layout.addWidget(self.spacing_chk)
        panel_layout.addStretch()
        self.panel.setVisible(False)
        layout.addWidget(self.panel)
        self.update_view()
    def on_btn_click(self, checked):
        self.panel.setVisible(checked)
        if checked:
            self.opened.emit(self)
    def close_panel(self):
        self.preview_btn.setChecked(False)
        self.panel.setVisible(False)
    def on_chk_toggle(self, checked):
        self.config[self.key] = checked
        self.changed.emit()
    def set_spacing(self, spacing):
        self.spacing = spacing
    def update_view(self, inherited_font="serif"):
        self.spacing_chk.blockSignals(True)
        self.spacing_chk.setChecked(self.config.get(self.key, True))
        self.spacing_chk.blockSignals(False)
        mt = "16px" if self.spacing else "1px"
        self.preview_btn.setStyleSheet(f"QPushButton {{ border: 1px dashed transparent; border-radius: 3px; background: transparent; color: #111111; font-size: 13px; font-family: '{inherited_font}'; text-align: left; margin-top: {mt}; padding: 3px 4px; line-height: 1.5; }} QPushButton:hover {{ border: 1px dashed #007acc; background: rgba(0, 122, 204, 0.08); }} QPushButton:checked {{ border: 1px solid #007acc; background: rgba(0, 122, 204, 0.12); }}")

class SeparatorElement(QWidget):
    changed = Signal()
    opened = Signal(object)
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.preview_btn = QPushButton("◇ ◇ ◇", self)
        self.preview_btn.setCursor(Qt.PointingHandCursor)
        self.preview_btn.setCheckable(True)
        self.preview_btn.clicked.connect(self.on_btn_click)
        layout.addWidget(self.preview_btn)
        self.panel = QWidget(self)
        self.panel.setStyleSheet("QWidget { border: None; border-radius: 4px; color:black; }")
        panel_layout = QHBoxLayout(self.panel)
        panel_layout.setContentsMargins(8, 6, 8, 6)
        panel_layout.setSpacing(6)
        self.spacing_chk = QCheckBox("위아래 간격")
        self.spacing_chk.setChecked(self.config.get("spacing", True))
        self.spacing_chk.toggled.connect(self.on_val_change)
        panel_layout.addWidget(self.spacing_chk)
        self.center_chk = QCheckBox("가운데 정렬")
        self.center_chk.setChecked(self.config.get("center", True))
        self.center_chk.toggled.connect(self.on_val_change)
        panel_layout.addWidget(self.center_chk)
        panel_layout.addStretch()
        self.panel.setVisible(False)
        layout.addWidget(self.panel)
        self.update_view()
    def on_btn_click(self, checked):
        self.panel.setVisible(checked)
        if checked:
            self.opened.emit(self)
    def close_panel(self):
        self.preview_btn.setChecked(False)
        self.panel.setVisible(False)
    def on_val_change(self):
        self.config["spacing"] = self.spacing_chk.isChecked()
        self.config["center"] = self.center_chk.isChecked()
        self.changed.emit()
    def update_view(self, inherited_font="serif"):
        align = "center" if self.config.get("center") else "left"
        pad = "18px 0" if self.config.get("spacing") else "2px 0"
        self.preview_btn.setStyleSheet(f"QPushButton {{ border: 1px dashed transparent; border-radius: 3px; background: transparent; color: #888888; font-size: 12px; font-family: '{inherited_font}'; text-align: {align}; padding: {pad}; }} QPushButton:hover {{ border: 1px dashed #007acc; background: rgba(0, 122, 204, 0.08); }} QPushButton:checked {{ border: 1px solid #007acc; background: rgba(0, 122, 204, 0.12); }}")

class EpubSettingsDialog(QDialog):
    def __init__(self, epub_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EPUB 본문 설정")
        self.resize(580, 780)
        self.data = copy.deepcopy(epub_data.get("epub_data", epub_data))
        m = QVBoxLayout(self)
        m.setContentsMargins(14, 14, 14, 14)
        m.setSpacing(10)
        desc = QLabel("저장 될 epub의 본문을 설정. 각 요소를 눌러 설정 가능.")
        desc.setObjectName("lbl_original_title")
        m.addWidget(desc)
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("글꼴:"))
        self.font_combo = QComboBox()
        families = sorted(QFontDatabase.families())
        self.font_combo.addItems(families)
        cur_font = self.data.get("global", {}).get("font", "serif")
        idx = self.font_combo.findText(cur_font)
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)
        elif "serif" in families:
            self.font_combo.setCurrentText("serif")
        self.font_combo.currentTextChanged.connect(self.on_font_change)
        top_bar.addWidget(self.font_combo, stretch=1)
        m.addLayout(top_bar)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: #1a1a1a; }")
        page_wrapper = QWidget()
        page_wrapper.setStyleSheet("background: transparent;")
        pw_layout = QVBoxLayout(page_wrapper)
        pw_layout.setContentsMargins(20, 20, 20, 20)
        pw_layout.setAlignment(Qt.AlignCenter)
        self.page = QFrame()
        self.page.setFixedWidth(450)
        self.page.setMinimumHeight(680)
        self.page.setStyleSheet("QFrame { background-color: #F8F6F1; border-radius: 4px; border: 1px solid #d4cebe; }")
        self.page_layout = QVBoxLayout(self.page)
        self.page_layout.setContentsMargins(26, 30, 26, 30)
        self.page_layout.setSpacing(1)
        b_conf = self.data["body"]
        self.all_elements = []
        self.sub_el = SubtitleElement("새로운 시작", b_conf["subtitle"])
        self.sub_el.changed.connect(self.on_ui_refresh)
        self.sub_el.opened.connect(self.on_element_opened)
        self.page_layout.addWidget(self.sub_el)
        self.all_elements.append(self.sub_el)
        self.page_layout.addSpacing(10)
        self.items_info = [
            ("이것은 나의 이야기다.", "spacing_general", "일반 본문 서술 전환 시 문단 띄우기"),
            ("“그날 이후로 모든 것이 완전히 바뀌기 시작했다.”", "spacing_dialogue", "대화문(「」, “”, 『』) 진입 시 문단 띄우기"),
            ("(조용히 한숨을 내쉬며 창밖을 응시했다.)", "spacing_dialogue_parenthesis", "대화 사이 괄호문((), （）) 진입 시 문단 띄우기"),
            ("“아직 남아 있는 시간이 별로 없어.”", "spacing_dialogue_continuous", "연속된 대화문 사이 문단 띄우기"),
            ("― 골목 저편에서 거친 바람 소리가 들려왔다.", "spacing_dash", "대시(-, —, ―) 문장 진입 시 문단 띄우기"),
            ("(그때 내가 다른 선택을 했더라면 어떻게 되었을까?)", "spacing_parenthesis", "일반 괄호문((), （）) 진입 시 문단 띄우기"),
            ("차가운 바람이 옷깃을 스쳤지만 발걸음은 멈추지 않았다.", "spacing_general", "일반 본문 서술 전환 시 문단 띄우기"),
            ("그 후, 새로운 목적지가 눈앞에 희미하게 보이기 시작했다.", "spacing_transition", "전환 어구(그 후, 다음 날 등) 시작 시 문단 띄우기"),
            ("어둠 속에서 작은 등불이 홀로 흔들리고 있었다.", "spacing_general", "일반 본문 서술 전환 시 문단 띄우기")
        ]
        self.line_elements = []
        for text, key, label in self.items_info:
            el = BodyBreakElement(text, b_conf, key, label)
            el.changed.connect(self.on_ui_refresh)
            el.opened.connect(self.on_element_opened)
            self.page_layout.addWidget(el)
            self.line_elements.append(el)
            self.all_elements.append(el)
        self.sep_el = SeparatorElement(b_conf["separator"])
        self.sep_el.changed.connect(self.on_ui_refresh)
        self.sep_el.opened.connect(self.on_element_opened)
        self.page_layout.addWidget(self.sep_el)
        self.all_elements.append(self.sep_el)
        
        self.bottom_label = QPushButton("그렇게 또 하나의 이야기가 조용히 막을 내렸다.", self.page)
        self.bottom_label.setFocusPolicy(Qt.NoFocus)
        self.bottom_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.page_layout.addWidget(self.bottom_label)
        
        self.page_layout.addStretch()
        pw_layout.addWidget(self.page)
        scroll.setWidget(page_wrapper)
        m.addWidget(scroll, stretch=1)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("취소")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("저장")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        m.addLayout(btn_layout)
        self.on_ui_refresh()

    def on_element_opened(self, opened_widget):
        for el in self.all_elements:
            if el != opened_widget:
                el.close_panel()

    def on_font_change(self, font_name):
        self.data["global"]["font"] = font_name
        self.on_ui_refresh()

    def on_ui_refresh(self):
        f = self.data.get("global", {}).get("font", "serif")
        self.sub_el.update_view(f)
        lines = [item[0] for item in self.items_info]
        breaks = calculate_epub_breaks(lines, self.data["body"])
        for i, el in enumerate(self.line_elements):
            el.set_spacing(breaks[i])
            el.update_view(f)
        self.sep_el.update_view(f)
        
        self.bottom_label.setStyleSheet(
            f"QPushButton {{ "
            f"border: 1px dashed transparent; "
            f"border-radius: 3px; "
            f"background: transparent; "
            f"color: #111111; "
            f"font-size: 13px; "
            f"font-family: '{f}'; "
            f"text-align: left; "
            f"margin-top: 1px; "
            f"padding: 3px 4px; "
            f"line-height: 1.5; "
            f"}}"
        )

    def get_config(self):
        return {"epub_data": self.data}