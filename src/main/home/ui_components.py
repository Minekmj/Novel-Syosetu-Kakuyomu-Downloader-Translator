from PySide6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QComboBox,
    QCheckBox, QProgressBar, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
import src.find.site_list as sl
import src.find.findsyou as findsyou
from .custom_widgets import MarqueeLabel

class HomeHeaderBar(QWidget):
    reco_clicked = Signal()
    gloss_clicked = Signal()
    epub_clicked = Signal()
    trans_clicked = Signal()
    qr_clicked = Signal()
    setting_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        app_title = QLabel("목록")
        app_title.setObjectName("app_title")
        layout.addWidget(app_title)
        layout.addStretch()

        def make_spacer():
            lbl = QLabel("‖")
            lbl.setObjectName("lbl_original_title")
            return lbl

        self.reco_bt = QPushButton("AI 작품 추천")
        self.reco_bt.setObjectName("secondaryBtn")
        self.reco_bt.clicked.connect(self.reco_clicked.emit)
        layout.addWidget(self.reco_bt)

        layout.addWidget(make_spacer())

        self.gloss_bt = QPushButton("용어집 관리")
        self.gloss_bt.setObjectName("secondaryBtn")
        self.gloss_bt.clicked.connect(self.gloss_clicked.emit)
        layout.addWidget(self.gloss_bt)

        layout.addWidget(make_spacer())

        self.epub_btn = QPushButton("EPUB 변환")
        self.epub_btn.setObjectName("secondaryBtn")
        self.epub_btn.clicked.connect(self.epub_clicked.emit)
        layout.addWidget(self.epub_btn)

        self.translate_btn = QPushButton("AI 번역")
        self.translate_btn.setObjectName("secondaryBtn")
        self.translate_btn.clicked.connect(self.trans_clicked.emit)
        layout.addWidget(self.translate_btn)

        self.qr_btn = QPushButton("번역 목록")
        self.qr_btn.setObjectName("secondaryBtn")
        self.qr_btn.clicked.connect(self.qr_clicked.emit)
        layout.addWidget(self.qr_btn)

        layout.addWidget(make_spacer())

        self.manager_path_btn = QPushButton("환경 설정")
        self.manager_path_btn.setObjectName("secondaryBtn")
        self.manager_path_btn.clicked.connect(self.setting_clicked.emit)
        layout.addWidget(self.manager_path_btn)

class SiteSearchBar(QFrame):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.setObjectName("CardFrame_ui")
        self.main_window = main_window

        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()

        for site_key in sl.Sites:
            btn = QPushButton(f"{sl.SITES.get(site_key, {}).get('name')} 검색")
            btn.setObjectName("secondaryBtn")
            btn.clicked.connect(lambda _, k=site_key: self.open_search_window(k))
            layout.addWidget(btn)

        layout.addStretch()

    def open_search_window(self, site_key):
        dialog = findsyou.MainWindow_Find(site_key, self.main_window)
        dialog.show()

class UrlInputBar(QWidget):
    submitted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.address_edit = QLineEdit(self)
        self.address_edit.setPlaceholderText("작품 URL을 입력하세요")
        self.address_edit.setFixedHeight(40)
        self.address_edit.returnPressed.connect(self.submitted.emit)

        self.add_btn = QPushButton("추가")
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.setFixedSize(90, 40)
        self.add_btn.clicked.connect(self.submitted.emit)

        layout.addWidget(self.address_edit, 1)
        layout.addWidget(self.add_btn)

class ListControlBar(QWidget):
    filter_changed = Signal()
    sort_changed = Signal()
    refresh_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("목록에서 작품 검색")
        self.search_edit.setFixedHeight(36)
        self.search_edit.textChanged.connect(lambda *_: self.filter_changed.emit())

        self.sort_combo = QComboBox(self)
        self.sort_combo.setFixedHeight(36)
        self.sort_combo.addItems([
            "이름순", "역이름순", "남은 화수순", "역 남은 화수순",
            "최근 다운로드순", "역 최근 다운로드순", "최신화 날짜순", "역 최신화 날짜순"
        ])
        self.sort_combo.currentIndexChanged.connect(lambda *_: self.sort_changed.emit())

        self.refresh_btn = QPushButton("새로고침", self)
        self.refresh_btn.setObjectName("secondaryBtn")
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)

        self.filter_chk = QCheckBox("남은 화수 있음", self)
        self.filter_chk.setObjectName("isCo")
        self.filter_chk.stateChanged.connect(lambda *_: self.filter_changed.emit())

        layout.addWidget(self.search_edit, 1)
        layout.addWidget(self.sort_combo)
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.filter_chk)

class DownloadBottomBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardFrame_ui")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        self.title_lbl = MarqueeLabel("작품...")
        self.title_lbl.setObjectName("title_lbl")
        self.title_lbl.setMinimumWidth(150)
        self.title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.progress_lbl = QLabel("0.0%")
        self.progress_lbl.setObjectName("prograss")
        self.progress_lbl.setFixedWidth(65)
        self.progress_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.queue_lbl = QLabel("대기: 0건")
        self.queue_lbl.setObjectName("lbl_original_title")
        self.queue_lbl.setFixedWidth(75)
        self.queue_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self.title_lbl, 2)
        layout.addWidget(self.progress_bar, 3)
        layout.addWidget(self.progress_lbl)
        layout.addWidget(self.queue_lbl)

    def set_task_info(self, title_text, start, end):
        self.title_lbl.setText(f"{title_text} ({start}~{end}화)")
        self.progress_lbl.setText("0.0%")
        self.progress_bar.setValue(0)

    def update_progress(self, text, val=None):
        self.progress_lbl.setText(text)
        if val is not None:
            self.progress_bar.setValue(val)

    def update_queue_count(self, count):
        self.queue_lbl.setText(f"대기: {count}건")