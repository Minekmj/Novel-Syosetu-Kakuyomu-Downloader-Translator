import re
from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QCheckBox, QListWidget, QScrollArea


class SmoothScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.anim = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setDuration(250)
        self.target_scroll_value = 0

    def wheelEvent(self, event):
        num_degrees = event.angleDelta().y()
        if num_degrees == 0:
            super().wheelEvent(event)
            return

        bar = self.verticalScrollBar()
        step = -int(num_degrees * 0.9)

        if self.anim.state() == QPropertyAnimation.State.Running:
            start_val = self.anim.currentValue()
            target_val = self.target_scroll_value + step
        else:
            start_val = bar.value()
            target_val = bar.value() + step

        target_val = max(0, min(bar.maximum(), target_val))
        self.target_scroll_value = target_val

        self.anim.stop()
        self.anim.setStartValue(int(start_val))
        self.anim.setEndValue(target_val)
        self.anim.start()

        event.accept()


class SmoothListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.anim = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setDuration(250)
        self.target_scroll_value = 0

    def wheelEvent(self, event):
        num_degrees = event.angleDelta().y()
        if num_degrees == 0:
            super().wheelEvent(event)
            return

        bar = self.verticalScrollBar()
        step = -int(num_degrees * 0.9)

        if self.anim.state() == QPropertyAnimation.State.Running:
            start_val = self.anim.currentValue()
            target_val = self.target_scroll_value + step
        else:
            start_val = bar.value()
            target_val = bar.value() + step

        target_val = max(bar.minimum(), min(bar.maximum(), target_val))
        self.target_scroll_value = target_val

        self.anim.stop()
        self.anim.setStartValue(int(start_val))
        self.anim.setEndValue(target_val)
        self.anim.start()
        event.accept()


class ToggleSwitch(QCheckBox):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._track_w = 38
        self._track_h = 20
        self._knob_margin = 3
        self._knob_pos = 1.0 if self.isChecked() else 0.0
        self._anim = QPropertyAnimation(self, b"knob_pos", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setDuration(160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._animate_knob)

    def _get_knob_pos(self) -> float:
        return self._knob_pos

    def _set_knob_pos(self, val: float):
        self._knob_pos = float(val)
        self.update()

    knob_pos = Property(float, _get_knob_pos, _set_knob_pos)

    def _animate_knob(self, checked: bool):
        self._anim.stop()
        self._anim.setStartValue(self._knob_pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    @staticmethod
    def _parse_color(val: str, fallback: QColor) -> QColor:
        s = str(val or "").strip()
        if not s:
            return fallback
        c = QColor(s)
        if c.isValid():
            return c
        m_rgba = re.search(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)", s)
        if m_rgba:
            r, g, b, a = int(m_rgba.group(1)), int(m_rgba.group(2)), int(m_rgba.group(3)), float(m_rgba.group(4))
            alpha = int(a * 255) if a <= 1.0 else int(a)
            return QColor(r, g, b, max(0, min(255, alpha)))
        m_hex = re.search(r"#[0-9a-fA-F]{6}", s)
        if m_hex:
            c2 = QColor(m_hex.group(0))
            if c2.isValid():
                return c2
        return fallback

    def _resolve_colors(self):
        accent = QColor("#8e7cf5")
        off_bg = QColor(255, 255, 255, 36)
        off_border = QColor(255, 255, 255, 42)
        knob_color = QColor("#ffffff")
        text_color = self.palette().text().color()

        try:
            import src.system.data as sys_data
            from src.system.theme import THEMES, THEME_DATA, THEME_LAVENDER

            raw_theme = str(getattr(sys_data, "THEME_NAME", "") or sys_data.load_data().get("theme", "LAVENDER")).strip()
            theme_key = THEME_DATA.get(raw_theme, raw_theme)
            tdict = THEMES.get(theme_key) or THEMES.get(theme_key.upper()) or THEME_LAVENDER

            accent = self._parse_color(
                tdict.get("border_input_focus") or tdict.get("chip_checked") or tdict.get("primary_bg"),
                accent,
            )
            bg_c = self._parse_color(tdict.get("bg"), QColor("#1e1e26"))
            is_dark = (bg_c.red() * 299 + bg_c.green() * 587 + bg_c.blue() * 114) / 1000 < 200

            off_bg = self._parse_color(tdict.get("checkbox_bg"), QColor(255, 255, 255, 36) if is_dark else QColor(0, 0, 0, 32))
            off_border = self._parse_color(tdict.get("border_subtle"), QColor(255, 255, 255, 42) if is_dark else QColor(0, 0, 0, 42))
            text_color = self._parse_color(tdict.get("text"), text_color)
        except Exception:
            pass

        return accent, off_bg, off_border, knob_color, text_color

    def sizeHint(self) -> QSize:
        text = self.text()
        w = self._track_w + 4
        if text:
            fm = QFontMetrics(self.font())
            w += 8 + fm.horizontalAdvance(text)
        h = max(self._track_h + 4, QFontMetrics(self.font()).height() + 4)
        return QSize(w, h)

    def hitButton(self, pos) -> bool:
        return self.rect().contains(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        accent, off_bg, off_border, knob_color, text_color = self._resolve_colors()

        y = (self.height() - self._track_h) / 2.0
        track_rect = QRectF(1.0, y, self._track_w, self._track_h)
        radius = self._track_h / 2.0

        t = self._knob_pos
        bg = QColor(
            int(off_bg.red() + (accent.red() - off_bg.red()) * t),
            int(off_bg.green() + (accent.green() - off_bg.green()) * t),
            int(off_bg.blue() + (accent.blue() - off_bg.blue()) * t),
            int(off_bg.alpha() + (255 - off_bg.alpha()) * t),
        )
        border = accent if self.isChecked() else off_border

        painter.setPen(QPen(border, 1.0))
        painter.setBrush(bg)
        painter.drawRoundedRect(track_rect, radius, radius)

        knob_d = self._track_h - 2 * self._knob_margin
        min_x = track_rect.left() + self._knob_margin
        max_x = track_rect.right() - self._knob_margin - knob_d
        knob_x = min_x + (max_x - min_x) * t
        knob_y = track_rect.top() + self._knob_margin

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(knob_color)
        painter.drawEllipse(QRectF(knob_x, knob_y, knob_d, knob_d))

        text = self.text()
        if text:
            painter.setPen(text_color)
            painter.setFont(self.font())
            text_x = int(track_rect.right()) + 8
            text_rect = QRectF(text_x, 0, self.width() - text_x, self.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
