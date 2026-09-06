import os
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QScrollArea,QWidget,QLineEdit,QPushButton,QMessageBox
from PySide6.QtCore import Qt
from data import load_data,save_data


class GlossaryManagerDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.data=load_data()
        self.dictionaries=self.data.get('dictionary',{})
        if not isinstance(self.dictionaries,dict):
            self.dictionaries={}
        self.rows=[]
        self.current_glossary=''
        self.setWindowTitle('용어집 관리')
        self.resize(620,560)
        self.setMinimumSize(500,450)
        self.setObjectName('dictionaryDialog')
        self.init_ui()
        self.load_glossary_list()

    def init_ui(self):
        layout=QVBoxLayout(self)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(10)

        header_layout=QHBoxLayout()
        header_layout.setSpacing(8)

        title_label=QLabel('용어집 관리')
        title_label.setObjectName('dictionaryTitle')
        layout.addWidget(title_label)

        self.glossary_combo=QComboBox()
        self.glossary_combo.setObjectName('dictionaryCombo')
        self.glossary_combo.currentIndexChanged.connect(self.on_glossary_changed)
        header_layout.addWidget(self.glossary_combo)

        layout.addLayout(header_layout)


        self.scroll=QScrollArea()
        self.scroll.setObjectName('dictionaryScroll')
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.container=QWidget()
        self.container.setObjectName('dictionaryContainer')
        self.container_layout=QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(2,4,2,4)
        self.container_layout.setSpacing(7)
        self.container_layout.addStretch()

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll,1)

        action_layout=QHBoxLayout()
        action_layout.setSpacing(7)

        add_btn=QPushButton('+ 용어집 내용 추가')
        add_btn.setObjectName('dictionaryAdd')
        add_btn.setMinimumHeight(36)
        add_btn.clicked.connect(lambda: self.add_row('',''))

        clear_btn=QPushButton('용어집 내용 전체 삭제')
        clear_btn.setObjectName('dictionaryAdd')
        clear_btn.setMinimumHeight(36)
        clear_btn.clicked.connect(self.clear_all_rows)

        action_layout.addWidget(add_btn,1)
        action_layout.addWidget(clear_btn,1)
        layout.addLayout(action_layout)

        bottom_layout=QHBoxLayout()
        bottom_layout.setSpacing(8)

        delete_btn=QPushButton('용어집 삭제')
        delete_btn.setObjectName('secondaryBtn')
        delete_btn.setFixedHeight(40)
        delete_btn.clicked.connect(self.delete_glossary)

        save_btn=QPushButton('저장')
        save_btn.setObjectName('primaryBtn')
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.save_all)

        bottom_layout.addWidget(delete_btn)
        layout.addLayout(bottom_layout)
        layout.addWidget(save_btn)

    def load_glossary_list(self):
        self.glossary_combo.blockSignals(True)
        self.glossary_combo.clear()

        for name in self.dictionaries.keys():
            self.glossary_combo.addItem(str(name))

        self.glossary_combo.blockSignals(False)

        if self.glossary_combo.count()>0:
            self.glossary_combo.setCurrentIndex(0)
            self.current_glossary=self.glossary_combo.currentText()
            self.load_current_glossary()
        else:
            self.current_glossary=''
            self.clear_rows()

    def on_glossary_changed(self,index):
        if index<0:
            return

        if self.current_glossary:
            result=self.get_rows_data()
            if result is None:
                self.glossary_combo.blockSignals(True)
                old_index=self.glossary_combo.findText(self.current_glossary)
                if old_index>=0:
                    self.glossary_combo.setCurrentIndex(old_index)
                self.glossary_combo.blockSignals(False)
                return
            self.dictionaries[self.current_glossary]=result

        self.current_glossary=self.glossary_combo.itemText(index)
        self.load_current_glossary()

    def load_current_glossary(self):
        self.clear_rows()

        if not self.current_glossary:
            return

        glossary=self.dictionaries.get(self.current_glossary,{})
        if not isinstance(glossary,dict):
            glossary={}

        for src,dst in glossary.items():
            self.add_row(src,dst)

    def clear_rows(self):
        for widget,source_edit,target_edit in self.rows:
            widget.deleteLater()

        self.rows.clear()

    def add_row(self,src='',dst=''):
        row_widget=QWidget()
        row_widget.setObjectName('dictionaryItem')

        row_layout=QHBoxLayout(row_widget)
        row_layout.setContentsMargins(10,4,6,4)
        row_layout.setSpacing(4)

        source_edit=QLineEdit()
        source_edit.setObjectName('dictionarySource')
        source_edit.setPlaceholderText('일본어')
        source_edit.setText(str(src))

        arrow=QLabel('→')
        arrow.setObjectName('dictionaryArrow')
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)

        target_edit=QLineEdit()
        target_edit.setObjectName('dictionaryTarget')
        target_edit.setPlaceholderText('한국어')
        target_edit.setText(str(dst))

        remove_btn=QPushButton('×')
        remove_btn.setObjectName('dictionaryRemove')
        remove_btn.setFixedSize(30,30)
        remove_btn.clicked.connect(lambda checked=False,widget=row_widget:self.remove_row(widget))

        row_layout.addWidget(source_edit,1)
        row_layout.addWidget(arrow)
        row_layout.addWidget(target_edit,1)
        row_layout.addWidget(remove_btn)

        self.container_layout.insertWidget(self.container_layout.count()-1,row_widget)
        self.rows.append((row_widget,source_edit,target_edit))

        if not src and not dst:
            source_edit.setFocus()

    def remove_row(self,widget):
        for index,row in enumerate(self.rows):
            if row[0] is widget:
                self.rows.pop(index)
                widget.deleteLater()
                return

    def get_rows_data(self):
        result={}

        for widget,source_edit,target_edit in self.rows:
            source=source_edit.text().strip()
            target=target_edit.text().strip()

            if not source and not target:
                continue

            if source and not target:
                QMessageBox.warning(self,'알림',f"'{source}'의 한국어 번역을 입력하세요.")
                source_edit.setFocus()
                return None

            if not source:
                QMessageBox.warning(self,'알림','일본어 용어를 입력하세요.')
                source_edit.setFocus()
                return None

            if source in result:
                QMessageBox.warning(self,'알림',f"'{source}' 용어가 중복되었습니다.")
                source_edit.setFocus()
                return None

            result[source]=target

        return result

    def clear_all_rows(self):
        if not self.rows:
            return

        result=QMessageBox.question(
            self,
            '전체 삭제',
            f'현재 등록된 용어 {len(self.rows)}개를 모두 삭제하시겠습니까?\n\n이 작업은 저장하기 전까지 실제로 저장되지 않습니다.',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if result!=QMessageBox.StandardButton.Yes:
            return

        self.clear_rows()

    def save_all(self):
        if not self.current_glossary:
            QMessageBox.warning(self,'알림','선택된 용어집이 없습니다.')
            return

        result=self.get_rows_data()

        if result is None:
            return

        self.dictionaries[self.current_glossary]=result
        self.data['dictionary']=self.dictionaries

        try:
            save_data(self.data)
        except TypeError:
            try:
                save_data()
            except Exception as e:
                QMessageBox.critical(self,'저장 오류',f'용어집 저장에 실패했습니다.\n\n{e}')
                return
        except Exception as e:
            QMessageBox.critical(self,'저장 오류',f'용어집 저장에 실패했습니다.\n\n{e}')
            return

        QMessageBox.information(self,'저장 완료','용어집이 저장되었습니다.')

    def delete_glossary(self):
        if not self.current_glossary:
            return

        result=QMessageBox.question(
            self,
            '용어집 삭제',
            f"'{self.current_glossary}' 용어집을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if result!=QMessageBox.StandardButton.Yes:
            return

        name=self.current_glossary

        if name in self.dictionaries:
            del self.dictionaries[name]

        self.data['dictionary']=self.dictionaries

        try:
            save_data(self.data)
        except TypeError:
            try:
                save_data()
            except Exception as e:
                QMessageBox.critical(self,'삭제 오류',f'용어집 삭제에 실패했습니다.\n\n{e}')
                return
        except Exception as e:
            QMessageBox.critical(self,'삭제 오류',f'용어집 삭제에 실패했습니다.\n\n{e}')
            return

        self.current_glossary=''
        self.load_glossary_list()

        QMessageBox.information(self,'삭제 완료',f"'{name}' 용어집이 삭제되었습니다.")

    def closeEvent(self,event):
        event.accept()
