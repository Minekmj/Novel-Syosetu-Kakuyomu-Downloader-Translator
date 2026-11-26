import datetime
import html
import time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStackedWidget, QTextEdit, QWidget
from src.system.BasicUi import ToggleSwitch
from src.system.data import return_theme
from .chunk_log_ui import ChunkBoardWidget
from .ui_factory import create_button, create_combo, create_label, create_layout


def get_brightness(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return 255
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r * 299 + g * 587 + b * 114) / 1000


def determine_log_type(text):
    if '오류' in text or '실패' in text or '에러' in text:
        return 'ERROR'
    elif '경고' in text:
        return 'WARN'
    elif '성공' in text or '완료' in text or '통과' in text:
        return 'SUCCESS'
    elif '시작' in text or '로드' in text or '감지' in text or '중지' in text or '강제분할' in text or '검사' in text:
        return 'INFO'
    return 'NORMAL'


def format_log_html(text, log_type):
    bg_color = return_theme()
    is_dark = get_brightness(bg_color) < 200

    color_map = {
        'DARK': {
            'NORMAL': '#e0e0e0',
            'ERROR': '#ff5555',
            'WARN': '#ffb86c',
            'SUCCESS': '#50fa7b',
            'INFO': '#8be9fd'
        },
        'LIGHT': {
            'NORMAL': '#222222',
            'ERROR': '#d32f2f',
            'WARN': '#e65100',
            'SUCCESS': '#2e7d32',
            'INFO': '#0288d1'
        }
    }

    mode = 'DARK' if is_dark else 'LIGHT'
    color = color_map[mode][log_type]
    safe_text = html.escape(str(text)).replace('\n', '<br>')
    return f'<span style="color: {color}; font-family: Consolas, monospace;">{safe_text}</span>'


def matches_log_filter(log_type, filter_text):
    if filter_text == '전체':
        return True
    elif filter_text == '일반' and log_type in ['NORMAL', 'INFO', 'SUCCESS']:
        return True
    elif filter_text == '경고' and log_type == 'WARN':
        return True
    elif filter_text == '오류' and log_type == 'ERROR':
        return True
    return False


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('no_back-logPanel')
        self.startTime = time.time()
        self.log_history = []
        self.log_follow_enabled = True
        self.init_ui()

    def init_ui(self):
        layout = create_layout('v', spacing=6, parent=self)

        top_bar = create_layout('h', (0, 2, 0, 0), spacing=8)
        self.header_lbl = create_label('작업 현황', 'subLabel')
        top_bar.addWidget(self.header_lbl)
        top_bar.addStretch(1)

        top_bar.addWidget(create_label('청크 UI', 'secondaryInfo'))
        self.view_toggle = ToggleSwitch('', self)
        self.view_toggle.toggled.connect(self._on_mode_toggled)
        top_bar.addWidget(self.view_toggle)
        top_bar.addWidget(create_label('텍스트 로그', 'secondaryInfo'))

        layout.addLayout(top_bar)

        self.view_stack = QStackedWidget()
        self.view_stack.setObjectName('no_back-viewStack')

        self.chunk_board = ChunkBoardWidget(self)
        self.chunk_board.setObjectName('no_back-tabChunkBoard')

        self.log_text_page = QWidget()
        self.log_text_page.setObjectName('no_back-tabTextLog')
        text_lay = create_layout('v', (0, 2, 0, 0), spacing=6, parent=self.log_text_page)

        row = create_layout('h', (0, 2, 0, 4), spacing=8)
        self.log_follow_btn = create_button('로그 추적 ON', self.toggle_log_follow, 'subtleBtn', 34, 104, True)
        row.addWidget(self.log_follow_btn)
        row.addWidget(create_button('지우기', self.clear_logs, 'subtleBtn', w=68, h=34))
        row.addStretch(1)

        self.log_filter_combo = create_combo(['전체', '일반', '경고', '오류'], h=34)
        self.log_filter_combo.setFixedWidth(86)
        self.log_filter_combo.currentTextChanged.connect(self.filter_logs)
        row.addWidget(self.log_filter_combo)
        text_lay.addLayout(row)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setPlaceholderText('번역 로그가 여기에 표시됩니다.')
        self.log_edit.setObjectName('detail_description')
        self.log_edit.viewport().setStyleSheet('background: transparent;')
        text_lay.addWidget(self.log_edit, 1)

        self.view_stack.addWidget(self.chunk_board)
        self.view_stack.addWidget(self.log_text_page)
        layout.addWidget(self.view_stack, 1)

        self.log_follow_btn.setChecked(True)

    def _on_mode_toggled(self, checked: bool):
        if checked:
            self.view_stack.setCurrentWidget(self.log_text_page)
            self.header_lbl.setText('번역 로그')
        else:
            self.view_stack.setCurrentWidget(self.chunk_board)
            self.header_lbl.setText('작업 현황')

    def handle_chunk_event(self, event):
        self.chunk_board.handle_event(event)

    def toggle_log_follow(self, checked):
        self.log_follow_enabled = bool(checked)
        self.log_follow_btn.setText('로그 추적 ON' if self.log_follow_enabled else '로그 추적 OFF')
        self.log_follow_btn.setChecked(self.log_follow_enabled)

        if self.log_follow_enabled:
            scrollbar = self.log_edit.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def scroll_to_bottom(self):
        if not self.log_follow_enabled:
            return

        scrollbar = self.log_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_log(self, text):
        if not text:
            return
        log_type = determine_log_type(text)

        elapsed_seconds = int(time.time() - self.startTime)
        formatted_time = str(datetime.timedelta(seconds=elapsed_seconds))
        formatted_html = format_log_html(f"[{formatted_time}] " + text, log_type)
        self.log_history.append((log_type, formatted_html))

        self.chunk_board.route_log(str(text), formatted_html)

        current_filter = self.log_filter_combo.currentText()
        if matches_log_filter(log_type, current_filter):
            self.log_edit.append(formatted_html)
            self.scroll_to_bottom()

    def reset_time(self):
        self.startTime = time.time()

    def filter_logs(self, filter_text):
        self.log_edit.clear()
        for log_type, formatted_html in self.log_history:
            if matches_log_filter(log_type, filter_text):
                self.log_edit.append(formatted_html)
        self.scroll_to_bottom()

    def clear_logs(self):
        self.log_history.clear()
        self.log_edit.clear()