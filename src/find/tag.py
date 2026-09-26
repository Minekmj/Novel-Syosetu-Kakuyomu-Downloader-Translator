from PySide6.QtCore import Qt, QSize, QRect, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, 
    QComboBox, QDialog,
    QScrollArea, QSizePolicy,
    QLayout, QFrame, QTabWidget, QMenu,
    QMessageBox, QInputDialog
)
from PySide6.QtGui import QAction

from src.system.load_save import load_data, save_data

USER_TAGS_SRC = "./tag_user.json"

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=4):
        super().__init__(parent)
        self.itemList = []
        self.m_hSpace = spacing
        self.m_vSpace = spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        while self.takeAt(0):
            pass

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        return self.itemList[index] if 0 <= index < len(self.itemList) else None

    def takeAt(self, index):
        return self.itemList.pop(index) if 0 <= index < len(self.itemList) else None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom()
        )
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            spaceX = self.m_hSpace
            spaceY = self.m_vSpace
            hint = item.sizeHint()
            nextX = x + hint.width() + spaceX

            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y += lineHeight + spaceY
                nextX = x + hint.width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), hint))

            x = nextX
            lineHeight = max(lineHeight, hint.height())

        return y + lineHeight - rect.y()


class TagFlowWidget(QWidget):
    def __init__(self, target_line_edit, categories_data, parent=None):
        super().__init__(parent)
        self.target_line_edit = target_line_edit
        self.categories_data = categories_data or {}
        self.buttons = {}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 6, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setObjectName('tag_container')
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(10)
        container_layout.setContentsMargins(4, 4, 4, 4)

        for category_name, tag_map in self.categories_data.items():
            if not isinstance(tag_map, dict):
                continue
            cat_label = QLabel(category_name)
            cat_label.setObjectName('cat_label')
            container_layout.addWidget(cat_label)

            tag_container = QWidget()
            tag_container.setObjectName('tag_container')
            flow_layout = FlowLayout(tag_container, margin=0, spacing=4)

            for ko_name, jp_word in tag_map.items():
                btn = QPushButton(f'+ {ko_name}')
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setObjectName('btn')
                btn.clicked.connect(
                    lambda checked, j=jp_word, b=btn, k=ko_name:
                    self.toggle_tag(j, b, k)
                )
                flow_layout.addWidget(btn)
                self.buttons[jp_word] = (btn, ko_name)

            container_layout.addWidget(tag_container)

        container_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.target_line_edit.textChanged.connect(self.sync_buttons_from_text)
        self.sync_buttons_from_text(self.target_line_edit.text())

    def toggle_tag(self, jp_word, button, ko_name):
        current_text = self.target_line_edit.text().strip()
        words = current_text.split() if current_text else []

        if jp_word in words:
            words.remove(jp_word)
            button.setChecked(False)
            button.setText(f'+ {ko_name}')
        else:
            words.append(jp_word)
            button.setChecked(True)
            button.setText(f'✓ {ko_name}')

        self.target_line_edit.setText(' '.join(words))

    def sync_buttons_from_text(self, text):
        words = text.strip().split()

        for jp_word, (btn, ko_name) in self.buttons.items():
            if jp_word in words:
                btn.setChecked(True)
                btn.setText(f'✓ {ko_name}')
            else:
                btn.setChecked(False)
                btn.setText(f'+ {ko_name}')


class UserTagWidget(QWidget):
    def __init__(self, target_line_edit, parent=None):
        super().__init__(parent)
        self.target_line_edit = target_line_edit
        self.buttons = {}
        self.user_tags = {}
        self.init_ui()
        self.load_user_tags()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 8, 0, 0)
        main_layout.setSpacing(8)

        panel = QFrame()
        panel.setStyleSheet("""
            QLineEdit, QComboBox {
                border-radius: 7px;
                padding: 4px 8px;
                min-height: 22px;
                font-size: 12px;
            }
            QPushButton {
                border-radius: 7px;
                min-height: 22px;
                font-size: 12px;
            }
            QFrame {background: transparent;}
        """)

        p_layout = QVBoxLayout(panel)
        p_layout.setContentsMargins(10, 10, 10, 10)
        p_layout.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        cat_title = QLabel('분류')
        cat_title.setObjectName('cat_label')
        row1.addWidget(cat_title)

        self.combo_category = QComboBox()
        self.combo_category.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row1.addWidget(self.combo_category)

        btn_new_cat = QPushButton('+ 분류 추가')
        btn_new_cat.setObjectName('secondaryBtn')
        btn_new_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_cat.clicked.connect(self.prompt_add_category)
        row1.addWidget(btn_new_cat)

        btn_del_cat = QPushButton('분류 삭제')
        btn_del_cat.setObjectName('secondaryBtn')
        btn_del_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del_cat.clicked.connect(self.delete_current_category)
        row1.addWidget(btn_del_cat)

        p_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)

        self.input_jp = QLineEdit()
        self.input_jp.setPlaceholderText('일본어(입력 용)')
        row2.addWidget(self.input_jp)

        self.input_ko = QLineEdit()
        self.input_ko.setPlaceholderText('한국어(보이는 용)')
        row2.addWidget(self.input_ko)
        p_layout.addLayout(row2)
        
        p_layout.addStretch(1)
        
        row3 = QHBoxLayout()
        row3.setSpacing(6)

        self.btn_add_tag = QPushButton('태그 추가')
        self.btn_add_tag.setObjectName('secondaryBtn')
        self.btn_add_tag.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_tag.clicked.connect(self.add_tag)
        row2.addWidget(self.btn_add_tag)

        p_layout.addLayout(row3)
        main_layout.addWidget(panel)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.container = QWidget()
        self.container.setObjectName('tag_container')
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setSpacing(10)
        self.container_layout.setContentsMargins(4, 4, 4, 4)

        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll, stretch=1)

        self.target_line_edit.textChanged.connect(self.sync_buttons_from_text)

    def load_user_tags(self):
        try:
            loaded = load_data(USER_TAGS_SRC)
            if isinstance(loaded, dict):
                self.user_tags = loaded
            else:
                self.user_tags = {}
        except Exception:
            self.user_tags = {}

        self.refresh_ui()

    def save_user_tags(self):
        try:
            save_data(self.user_tags, USER_TAGS_SRC)
        except Exception as e:
            print(f'사용자 태그 저장 실패: {e}')

    def prompt_add_category(self):
        cat_name, ok = QInputDialog.getText(self, '분류 추가', '새로운 분류(카테고리) 이름을 입력하세요:')
        if ok and cat_name.strip():
            c = cat_name.strip()
            if c not in self.user_tags:
                self.user_tags[c] = {}
                self.save_user_tags()
                self.refresh_ui()
                self.combo_category.setCurrentText(c)
            else:
                self.combo_category.setCurrentText(c)

    def delete_current_category(self):
        cur_cat = self.combo_category.currentText().strip()
        if not cur_cat:
            return

        confirm = QMessageBox.question(
            self, '분류 삭제',
            f"'{cur_cat}' 분류와 그 안의 모든 태그를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            if cur_cat in self.user_tags:
                del self.user_tags[cur_cat]
                self.save_user_tags()
                self.refresh_ui()

    def refresh_ui(self):
        cur_selected = self.combo_category.currentText().strip()
        self.combo_category.blockSignals(True)
        self.combo_category.clear()

        categories = list(self.user_tags.keys())
        if categories:
            self.combo_category.addItems(categories)
            if cur_selected in categories:
                self.combo_category.setCurrentText(cur_selected)
        self.combo_category.blockSignals(False)

        self.buttons.clear()
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.user_tags:
            no_tag = QLabel('등록된 사용자 태그가 없습니다.\n위에서 분류를 추가하고 원하는 태그를 등록해보세요.')
            no_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_tag.setObjectName('new_and_now')
            self.container_layout.addWidget(no_tag)
            self.container_layout.addStretch()
            return

        for category_name, tag_map in self.user_tags.items():
            cat_label = QLabel(category_name)
            cat_label.setObjectName('cat_label')
            self.container_layout.addWidget(cat_label)

            tag_container = QWidget()
            tag_container.setObjectName('tag_container')
            flow_layout = FlowLayout(tag_container, margin=0, spacing=4)

            if isinstance(tag_map, dict) and tag_map:
                for ko_name, jp_word in tag_map.items():
                    btn = QPushButton(f'+ {ko_name}')
                    btn.setCheckable(True)
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setObjectName('btn')
                    btn.setToolTip(f'원문: {jp_word}\n(우클릭 시 태그 삭제)')

                    btn.clicked.connect(
                        lambda checked, j=jp_word, b=btn, k=ko_name:
                        self.toggle_tag(j, b, k)
                    )

                    btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                    btn.customContextMenuRequested.connect(
                        lambda pos, c=category_name, k=ko_name, j=jp_word, b=btn:
                        self.show_tag_context_menu(pos, c, k, j, b)
                    )

                    flow_layout.addWidget(btn)
                    self.buttons[jp_word] = (btn, ko_name)
            else:
                hint = QLabel('(비어있는 분류)')
                hint.setObjectName('new_and_now')
                flow_layout.addWidget(hint)

            self.container_layout.addWidget(tag_container)

        self.container_layout.addStretch()
        self.sync_buttons_from_text(self.target_line_edit.text())

    def add_tag(self):
        category = self.combo_category.currentText().strip()
        jp_word = self.input_jp.text().strip()
        ko_name = self.input_ko.text().strip()

        if not category:
            QMessageBox.warning(self, '경고', '분류를 선택하거나 [+ 분류 추가]를 눌러 분류를 먼저 만들어주세요.')
            return
        if not jp_word or not ko_name:
            QMessageBox.warning(self, '경고', '일본어 원문과 한국어 표기를 모두 입력해주세요.')
            return

        if category not in self.user_tags:
            self.user_tags[category] = {}

        self.user_tags[category][ko_name] = jp_word
        self.save_user_tags()

        self.input_jp.clear()
        self.input_ko.clear()
        self.refresh_ui()

    def show_tag_context_menu(self, pos, category, ko_name, jp_word, button):
        menu = QMenu(self)
        delete_action = QAction(f"'{ko_name}' 삭제", self)
        delete_action.triggered.connect(lambda: self.delete_tag(category, ko_name, jp_word))
        menu.addAction(delete_action)
        menu.exec(button.mapToGlobal(pos))

    def delete_tag(self, category, ko_name, jp_word):
        if category in self.user_tags and ko_name in self.user_tags[category]:
            del self.user_tags[category][ko_name]
            self.save_user_tags()

            current_text = self.target_line_edit.text().strip()
            words = current_text.split() if current_text else []
            if jp_word in words:
                words.remove(jp_word)
                self.target_line_edit.setText(' '.join(words))

            self.refresh_ui()

    def toggle_tag(self, jp_word, button, ko_name):
        current_text = self.target_line_edit.text().strip()
        words = current_text.split() if current_text else []

        if jp_word in words:
            words.remove(jp_word)
            button.setChecked(False)
            button.setText(f'+ {ko_name}')
        else:
            words.append(jp_word)
            button.setChecked(True)
            button.setText(f'✓ {ko_name}')

        self.target_line_edit.setText(' '.join(words))

    def sync_buttons_from_text(self, text):
        words = text.strip().split()

        for jp_word, (btn, ko_name) in self.buttons.items():
            if jp_word in words:
                btn.setChecked(True)
                btn.setText(f'✓ {ko_name}')
            else:
                btn.setChecked(False)
                btn.setText(f'+ {ko_name}')


class TagSelectDialog(QDialog):
    def __init__(self, target_line_edit, categories_data, title='태그 선택', parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(540, 520)
        self.setMinimumSize(480, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName('detail_dialog_title')
        top_row.addWidget(title_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        desc = QLabel('클릭하여 검색어에 반영하고, 사용자 태그는 우클릭하여 삭제할 수 있습니다.')
        desc.setObjectName('dialog_hint')
        layout.addWidget(desc)

        self.tabs = QTabWidget()
        self.tabs.setObjectName('settingsTab')
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar {
                background: transparent;
            }
            QTabBar::tab {
                background: transparent;
                border: none;
                padding: 6px 14px;
                margin-right: 4px;
                font-weight: 600;
            }
        """)

        self.tag_panel = TagFlowWidget(target_line_edit, categories_data, self)
        self.user_tag_panel = UserTagWidget(target_line_edit, self)

        self.tabs.addTab(self.tag_panel, '기본 태그')
        self.tabs.addTab(self.user_tag_panel, '사용자 태그')
        layout.addWidget(self.tabs, 1)

        bottom_line = QFrame()
        bottom_line.setObjectName('dialog_separator')
        bottom_line.setFixedHeight(1)
        layout.addWidget(bottom_line)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 2, 0, 0)

        selected_label = QLabel('입력란에 태그가 실시간 반영됩니다.')
        selected_label.setObjectName('dialog_hint')
        bottom_layout.addWidget(selected_label, 1)

        btn_close = QPushButton('완료')
        btn_close.setObjectName('primaryBtn')
        btn_close.setMinimumWidth(80)
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)

        layout.addLayout(bottom_layout)