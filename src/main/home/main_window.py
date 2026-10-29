from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QMessageBox, QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon

from src.system.data import load_data
import src.main.thread_pyqt as thread_pyqt
import src.trans.trans_view as trans_view
import src.glossary.glossary_manager as glossary_manager
import src.qr.qr_view as qr_view
import src.recommend.recommend as recommend
from src.system.src import resource_path
import src.system.v as vsc

from .custom_widgets import SmoothScrollArea
from .row_widget import AddressRowWidget
from .ui_components import (
    HomeHeaderBar, SiteSearchBar, UrlInputBar,
    ListControlBar, DownloadBottomBar
)
from .download_manager import DownloadManager
from .list_service import (
    normalize_site_url, filter_and_sort_rows,
    save_novel_entry, delete_novel_entry
)
from .handlers import (
    init_system_config, check_app_version,
    handle_settings_dialog, convert_txt_to_epub_flow
)

class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.row_widgets = []
        self.newly_added_widget = None

        self.setWindowTitle(f"MINE DOWNLOADER - {vsc.V}")
        self.resize(1000, 750)
        self.setMinimumSize(820, 600)
        self.setWindowIcon(QIcon(resource_path("main.ico")))

        self._setup_ui()
        self._setup_services()
        self._load_initial_data()

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(24, 22, 24, 24)
        self.main_layout.setSpacing(12)

        self.header_bar = HomeHeaderBar(self)
        self.header_bar.reco_clicked.connect(lambda: recommend.NovelRecommendDialog(self).show())
        self.header_bar.gloss_clicked.connect(lambda: glossary_manager.GlossaryManagerDialog(self).show())
        self.header_bar.epub_clicked.connect(lambda: convert_txt_to_epub_flow(self, self.header_bar.epub_btn))
        self.header_bar.trans_clicked.connect(lambda: trans_view.TranslateDialog(self).show())
        self.header_bar.qr_clicked.connect(lambda: qr_view.QRViewDialog(self).show())
        self.header_bar.setting_clicked.connect(lambda: handle_settings_dialog(self))
        self.main_layout.addWidget(self.header_bar)

        self.site_search_bar = SiteSearchBar(self, self)
        self.main_layout.addWidget(self.site_search_bar)

        self.url_bar = UrlInputBar(self)
        self.url_bar.submitted.connect(self.add_address_row)
        self.main_layout.addWidget(self.url_bar)

        self.control_bar = ListControlBar(self)
        self.control_bar.filter_changed.connect(self.apply_filter_and_sort)
        self.control_bar.sort_changed.connect(self.on_sort_changed)
        self.control_bar.refresh_clicked.connect(self.refresh_all_rows)
        self.main_layout.addWidget(self.control_bar)

        self.scroll_area = SmoothScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("tag_container")

        self.rows_layout = QVBoxLayout(self.scroll_widget)
        self.rows_layout.setContentsMargins(0, 4, 8, 8)
        self.rows_layout.setSpacing(8)
        self.rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll_area, 1)

        self.bottom_bar = DownloadBottomBar(self)
        self.main_layout.addWidget(self.bottom_bar)
        self.bottom_bar.hide()

        self.main_address_edit = self.url_bar.address_edit
        self.add_btn = self.url_bar.add_btn
        self.search_edit = self.control_bar.search_edit
        self.sort_combo = self.control_bar.sort_combo
        self.refresh_btn = self.control_bar.refresh_btn
        self.filter_chk = self.control_bar.filter_chk
        self.epub_btn = self.header_bar.epub_btn

        self.is_first_massage = AddressRowWidget("")
        self.is_first_massage.hide()
        self.rows_layout.addWidget(self.is_first_massage)

    def _setup_services(self):
        self.download_manager = DownloadManager(self, self.bottom_bar)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(lambda: self.refresh_btn.setEnabled(True))

        self.click_watcher = thread_pyqt.ClickWatcher()
        self.click_watcher.update_address.connect(self.main_address_edit.setText)
        self.click_watcher.add_address.connect(self.add_address_row)
        self.click_watcher.start()

    def _load_initial_data(self):
        init_system_config()
        self.load_widgets_from_json()
        check_app_version(self)

    def add_download_task(self, task):
        self.download_manager.add_task(task)

    def check_all_fetched(self):
        if not self.row_widgets:
            return
        if not any(getattr(r, "is_loading", False) for r in self.row_widgets):
            self.refresh_timer.start(1000)

    def refresh_all_rows(self):
        if not self.row_widgets:
            return
        self.refresh_btn.setEnabled(False)
        self.refresh_timer.stop()
        for row in self.row_widgets:
            row.start_async_fetch()

    def on_sort_changed(self):
        self.newly_added_widget = None
        self.apply_filter_and_sort()

    def apply_filter_and_sort(self):
        query = self.search_edit.text().strip().lower()
        mode = self.sort_combo.currentIndex()
        only_rem = self.filter_chk.isChecked()

        visible_widgets = filter_and_sort_rows(
            self.row_widgets, query, mode, only_rem, self.newly_added_widget
        )
        for row in visible_widgets:
            self.rows_layout.addWidget(row)

    def load_widgets_from_json(self):
        data = load_data()
        items = data.get("list", {})

        for title, item in items.items():
            row = AddressRowWidget(
                item.get("src", ""),
                title_text=title,
                parent=self,
                last=item.get("down", "0"),
                down_time=item.get("down_time", "0"),
                act_massage=item.get("act_masseage", ""),
                title_raw_text=item.get("original_title", ""),
                main_window=self
            )
            row.del_btn.clicked.connect(lambda _, r=row: self.delete_row(r))
            row.status_updated.connect(self.apply_filter_and_sort)
            row.fetch_finished.connect(self.check_all_fetched)

            self.rows_layout.addWidget(row)
            self.row_widgets.append(row)

        if not self.row_widgets:
            self.is_first_massage.show()
        else:
            self.is_first_massage.hide()

        self.apply_filter_and_sort()

    def add_address_row(self):
        url = normalize_site_url(self.main_address_edit.text())
        if not url:
            return

        data = load_data()
        if any(item.get("src") == url for item in data.get("list", {}).values()):
            QMessageBox.warning(self, "알림", "이미 등록된 주소입니다.")
            self.main_address_edit.clear()
            return

        self.main_address_edit.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.add_btn.setText("...")
        QApplication.processEvents()

        temp_row = AddressRowWidget(url, main_window=self)
        title_text = temp_row.title_text

        save_novel_entry(title_text, url)

        self.main_address_edit.clear()
        self.main_address_edit.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.add_btn.setText("추가")

        row = temp_row
        row.setParent(self)
        row.del_btn.clicked.connect(lambda _, r=row: self.delete_row(r))
        row.status_updated.connect(self.apply_filter_and_sort)
        row.fetch_finished.connect(self.check_all_fetched)

        self.refresh_btn.setEnabled(False)
        self.refresh_timer.stop()

        self.row_widgets.insert(0, row)
        self.newly_added_widget = row
        self.is_first_massage.hide()

        if self.search_edit.text():
            self.search_edit.blockSignals(True)
            self.search_edit.clear()
            self.search_edit.blockSignals(False)

        self.apply_filter_and_sort()
        self.scroll_area.target_scroll_value = 0
        self.scroll_area.verticalScrollBar().setValue(0)

        QMessageBox.information(self, "완료", "주소가 성공적으로 추가되었습니다.")

    def delete_row(self, row_widget):
        if self.newly_added_widget == row_widget:
            self.newly_added_widget = None

        self.download_manager.remove_tasks_by_widget(row_widget)
        delete_novel_entry(row_widget.title_text)

        if row_widget in self.row_widgets:
            self.row_widgets.remove(row_widget)

        if not self.row_widgets:
            self.is_first_massage.show()

        row_widget.deleteLater()
        self.check_all_fetched()

    def closeEvent(self, event):
        thread_pyqt.STOP_CLICK = True
        self.click_watcher.stop()
        super().closeEvent(event)