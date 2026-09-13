import os
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QScrollArea, QFrame, QWidget, QMenu, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QAction, QCursor

from src.qr.make_qr import Make_Qrcode


down = None #외부 주입용


def get_epub_metadata_title(epub_path: str) -> str:
    try:
        with zipfile.ZipFile(epub_path, 'r') as z:
            container_xml = z.read("META-INF/container.xml")
            c_root = ET.fromstring(container_xml)
            opf_path = None

            for elem in c_root.iter():
                if elem.tag.endswith("rootfile"):
                    opf_path = elem.attrib.get("full-path")
                    if opf_path:
                        break

            if not opf_path:
                for name in z.namelist():
                    if name.lower().endswith(".opf"):
                        opf_path = name
                        break

            if opf_path and opf_path in z.namelist():
                opf_xml = z.read(opf_path)
                opf_root = ET.fromstring(opf_xml)
                for elem in opf_root.iter():
                    if elem.tag.endswith("title") and elem.text:
                        return elem.text.strip()
    except Exception:
        pass

    return os.path.splitext(os.path.basename(epub_path))[0]


def parse_title_and_episode(raw_title: str) -> tuple[str, str]:
    matches = list(re.finditer(r'((?:_복원)*_번역\s*\|\s*)', raw_title))
    if matches:
        last_m = matches[-1]
        group_title = raw_title[:last_m.start()].strip()
        episode = raw_title[last_m.end():].strip()
        return group_title, episode

    if " | " in raw_title:
        idx = raw_title.rfind(" | ")
        group_title = raw_title[:idx].strip()
        episode = raw_title[idx + 3:].strip()
        return group_title, episode

    return raw_title.strip(), ""


def parse_raw_txt_file(txt_path: str) -> tuple[str, str]:
    try:
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [f.readline().strip() for _ in range(10)]
            lines = [line for line in lines if line]

            if any("+---+" in l for l in lines):
                header_lines = []
                for line in lines:
                    if "+---+" in line:
                        break
                    header_lines.append(line)

                if len(header_lines) >= 2:
                    group_title = header_lines[0].strip()
                    episode = header_lines[1].strip()
                    return group_title, episode
                elif len(header_lines) == 1:
                    return parse_title_and_episode(header_lines[0])

            for line in lines:
                if " | " in line:
                    return parse_title_and_episode(line)
    except Exception:
        pass

    file_name = os.path.splitext(os.path.basename(txt_path))[0]
    return parse_title_and_episode(file_name)


class QRCodeDialog(QDialog):
    def __init__(self, file_path: str, display_name: str, parent=None, out_time: int = 30):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle(f"QR 코드 다운로드 - {display_name}")
        self.setFixedSize(360, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.title_lbl = QLabel(f"파일 : {display_name}", self)
        self.title_lbl.setObjectName("title")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setWordWrap(True)
        layout.addWidget(self.title_lbl)

        qr_card = QFrame(self)
        qr_card.setObjectName("CardFrame")
        qr_layout = QVBoxLayout(qr_card)
        qr_layout.setContentsMargins(16, 16, 16, 16)
        qr_layout.setSpacing(0)
        qr_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.qr_lbl = QLabel(self)
        self.qr_lbl.setFixedSize(220, 220)
        self.qr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_layout.addWidget(self.qr_lbl)
        layout.addWidget(qr_card)

        self.timer_lbl = QLabel(f"({out_time}초)", self)
        self.timer_lbl.setObjectName("prograss")
        self.timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_lbl.setFixedHeight(24)
        layout.addWidget(self.timer_lbl)

        try:
            import io
            pil_img = Make_Qrcode(self.file_path, timer=self.timer_lbl, out_time=out_time)

            buffer = io.BytesIO()
            pil_img.save(buffer, format="PNG")
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())

            self.qr_lbl.setPixmap(pixmap.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        except Exception as e:
            self.qr_lbl.setText("QR 생성 실패")
            self.timer_lbl.setText("오류 발생")
            QMessageBox.critical(self, "오류", f"QR 생성 도중 오류가 발생했습니다:\n{e}")


class FileCardWidget(QWidget):
    def __init__(self, file_path: str, episode: str, mtime: float, size_bytes: int, file_type: str = "EPUB", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.episode = episode if episode else self.file_name
        self.mtime = mtime
        self.file_type = file_type

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 2, 0, 2)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("CardFrame")

        card_layout = QHBoxLayout(self.main_frame)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(16)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.name_lbl = QLabel(self.episode)
        self.name_lbl.setObjectName("title_lbl")
        self.name_lbl.setWordWrap(True)
        self.name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        size_kb = size_bytes / 1024
        size_str = f"{size_kb / 1024:.2f} MB" if size_kb >= 1024 else f"{size_kb:.1f} KB"
        self.size_lbl = QLabel(f"[{self.file_type}] {size_str}")
        self.size_lbl.setObjectName("new_and_now")

        date_str = datetime.fromtimestamp(self.mtime).strftime("%Y-%m-%d %H:%M") if self.mtime else "-"
        self.file_info_lbl = QLabel(f"{self.file_name} | {date_str}")
        self.file_info_lbl.setObjectName("url_lbl")
        self.file_info_lbl.setWordWrap(True)
        self.file_info_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        info_layout.addWidget(self.name_lbl)
        info_layout.addWidget(self.size_lbl)
        info_layout.addWidget(self.file_info_lbl)

        card_layout.addLayout(info_layout, stretch=1)

        self.qr_btn = QPushButton("QR 생성")
        self.qr_btn.setObjectName("secondaryBtn")
        self.qr_btn.setFixedSize(85, 32)
        self.qr_btn.clicked.connect(self.open_qr)
        card_layout.addWidget(self.qr_btn)

        main_layout.addWidget(self.main_frame)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        qr_action = QAction("qrcode 생성", self)
        qr_action.triggered.connect(self.open_qr)
        menu.addAction(qr_action)
        menu.exec(QCursor.pos())

    def open_qr(self):
        dialog = QRCodeDialog(self.file_path, os.path.splitext(os.path.basename(self.file_path))[0], self, out_time=30)
        dialog.show()


class GroupCardWidget(QWidget):
    clicked = Signal(str)

    def __init__(self, group_name: str, count: int, latest_mtime: float, parent=None):
        super().__init__(parent)
        self.group_name = group_name
        self.count = count
        self.latest_mtime = latest_mtime

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 2, 0, 2)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("CardFrame")
        self.main_frame.setCursor(Qt.PointingHandCursor)

        card_layout = QHBoxLayout(self.main_frame)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(16)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_lbl = QLabel(self.group_name)
        self.title_lbl.setObjectName("title_lbl")
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(12)
        sub_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.count_lbl = QLabel(f"총 {self.count:02d}개")
        self.count_lbl.setObjectName("new_and_now")

        date_str = datetime.fromtimestamp(self.latest_mtime).strftime("%Y-%m-%d %H:%M") if self.latest_mtime else "-"
        self.date_lbl = QLabel(f"최근 수정: {date_str}")
        self.date_lbl.setObjectName("url_lbl")

        sub_layout.addWidget(self.count_lbl)
        sub_layout.addWidget(self.date_lbl)
        sub_layout.addStretch()

        info_layout.addWidget(self.title_lbl)
        info_layout.addLayout(sub_layout)

        card_layout.addLayout(info_layout, stretch=1)

        self.open_btn = QPushButton("목록 보기")
        self.open_btn.setObjectName("secondaryBtn")
        self.open_btn.setFixedSize(85, 32)
        self.open_btn.clicked.connect(lambda: self.clicked.emit(self.group_name))
        card_layout.addWidget(self.open_btn)

        main_layout.addWidget(self.main_frame)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.group_name)
        super().mousePressEvent(event)


class EpisodeListDialog(QDialog):
    def __init__(self, group_name: str, file_list: list, parent=None):
        super().__init__(parent)
        self.group_name = group_name
        self.file_list = file_list

        self.setWindowTitle(f"{group_name} - 회차 목록")
        self.resize(680, 580)
        self.setMinimumSize(480, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header_lbl = QLabel(f"{group_name} (총 {len(file_list):02d}개)", self)
        header_lbl.setObjectName("app_title")
        header_lbl.setWordWrap(True)
        layout.addWidget(header_lbl)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setObjectName("tag_container")
        self.cards_layout = QVBoxLayout(container)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.setContentsMargins(0, 8, 8, 8)
        self.cards_layout.setSpacing(8)

        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)

        self.populate_cards()

    def populate_cards(self):
        sorted_files = sorted(self.file_list, key=lambda f: f["mtime"], reverse=True)
        for item in sorted_files:
            file_card = FileCardWidget(
                item["path"],
                item["episode"],
                item["mtime"],
                item["size"],
                file_type=item.get("type", "EPUB"),
                parent=self
            )
            self.cards_layout.addWidget(file_card)


class QRViewDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("번역 목록")
        self.resize(720, 640)
        self.setMinimumSize(540, 480)

        self.groups_data = {}
        self.group_widgets = []

        self.init_ui()
        self.load_epubs()

    def get_base_dir(self) -> str:
        base_dir = ""
        if down.downin.base_data:
            base_dir = down.downin.base_data.OUTFOLDER

        if not base_dir:
            base_dir = os.path.abspath(".")
        return base_dir

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header_layout.setSpacing(8)

        title_lbl = QLabel("번역 목록", self)
        title_lbl.setObjectName("app_title")

        refresh_btn = QPushButton("새로고침", self)
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.setFixedHeight(32)
        refresh_btn.clicked.connect(self.load_epubs)

        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)
        root_layout.addLayout(header_layout)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("번역 작품 검색...")
        self.search_edit.textChanged.connect(self.apply_group_filter_and_sort)

        self.sort_combo = QComboBox(self)
        self.sort_combo.addItems(["최근 항목순", "역 최근 항목순", "이름순", "역이름순", "파일 많은순"])
        self.sort_combo.currentIndexChanged.connect(self.apply_group_filter_and_sort)

        control_layout.addWidget(self.search_edit, stretch=1)
        control_layout.addWidget(self.sort_combo)
        root_layout.addLayout(control_layout)

        self.scroll_groups = QScrollArea(self)
        self.scroll_groups.setWidgetResizable(True)
        self.scroll_groups.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_groups.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container_groups = QWidget()
        self.container_groups.setObjectName("tag_container")
        self.layout_groups = QVBoxLayout(self.container_groups)
        self.layout_groups.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout_groups.setContentsMargins(0, 8, 8, 8)
        self.layout_groups.setSpacing(8)

        self.scroll_groups.setWidget(self.container_groups)
        root_layout.addWidget(self.scroll_groups)

    def load_epubs(self):
        self.groups_data.clear()
        self.group_widgets.clear()
        self.clear_layout(self.layout_groups)

        base_dir = self.get_base_dir()
        epub_dir = os.path.join(base_dir, "epub")
        raw_txt_dir = os.path.join(epub_dir, "raw_txt")

        if os.path.exists(epub_dir):
            for root, _, files in os.walk(epub_dir):
                for file in files:
                    if file.lower().endswith(".epub"):
                        full_path = os.path.join(root, file)
                        raw_title = get_epub_metadata_title(full_path)
                        group_name, episode = parse_title_and_episode(raw_title)

                        try:
                            stat = os.stat(full_path)
                            mtime = stat.st_mtime
                            size_bytes = stat.st_size
                        except Exception:
                            mtime = 0
                            size_bytes = 0

                        if group_name not in self.groups_data:
                            self.groups_data[group_name] = []

                        self.groups_data[group_name].append({
                            "path": full_path,
                            "episode": episode,
                            "mtime": mtime,
                            "size": size_bytes,
                            "type": "EPUB"
                        })

        if os.path.exists(raw_txt_dir):
            for root, _, files in os.walk(raw_txt_dir):
                for file in files:
                    if file.lower().endswith(".txt"):
                        full_path = os.path.join(root, file)
                        group_name, episode = parse_raw_txt_file(full_path)

                        try:
                            stat = os.stat(full_path)
                            mtime = stat.st_mtime
                            size_bytes = stat.st_size
                        except Exception:
                            mtime = 0
                            size_bytes = 0

                        if group_name not in self.groups_data:
                            self.groups_data[group_name] = []

                        self.groups_data[group_name].append({
                            "path": full_path,
                            "episode": episode,
                            "mtime": mtime,
                            "size": size_bytes,
                            "type": "RAW"
                        })

        if not self.groups_data:
            empty_frame = QFrame()
            empty_frame.setObjectName("CardFrame")
            empty_layout = QVBoxLayout(empty_frame)
            empty_layout.setContentsMargins(20, 24, 20, 24)
            empty_layout.setSpacing(6)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            msg_title = QLabel("번역 파일이 없습니다")
            msg_title.setObjectName("title_lbl")
            msg_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            msg_sub = QLabel("번역 또는 epub 제작을 통해 추가하세요.")
            msg_sub.setObjectName("url_lbl")
            msg_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

            empty_layout.addWidget(msg_title)
            empty_layout.addWidget(msg_sub)
            self.layout_groups.addWidget(empty_frame)
            return

        for group_name, file_list in self.groups_data.items():
            latest_mtime = max((f["mtime"] for f in file_list), default=0)
            card = GroupCardWidget(group_name, len(file_list), latest_mtime, self)
            card.clicked.connect(self.open_detail_dialog)
            self.group_widgets.append(card)

        self.apply_group_filter_and_sort()

    def apply_group_filter_and_sort(self):
        query = self.search_edit.text().strip().lower()
        sort_mode = self.sort_combo.currentIndex()

        visible_widgets = []
        for widget in self.group_widgets:
            if query and query not in widget.group_name.lower():
                widget.hide()
                continue
            widget.show()
            visible_widgets.append(widget)

        if sort_mode == 0:
            visible_widgets.sort(key=lambda w: w.latest_mtime, reverse=True)
        elif sort_mode == 1:
            visible_widgets.sort(key=lambda w: w.latest_mtime)
        elif sort_mode == 2:
            visible_widgets.sort(key=lambda w: w.group_name)
        elif sort_mode == 3:
            visible_widgets.sort(key=lambda w: w.group_name, reverse=True)
        elif sort_mode == 4:
            visible_widgets.sort(key=lambda w: w.count, reverse=True)

        for widget in visible_widgets:
            self.layout_groups.addWidget(widget)

    def open_detail_dialog(self, group_name: str):
        file_list = self.groups_data.get(group_name, [])
        dialog = EpisodeListDialog(group_name, file_list, self)
        dialog.show()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()