import ctypes

import src.main.home as main_ui

import sys
from PySide6.QtWidgets import (
    QApplication
)
from PySide6.QtGui import QFont
from PySide6.QtGui import QIcon

from src.system.load import resource_path

app = None
close_event = None

def main(callback = None):
    global app, close_event
    if sys.platform == "win32":
        try:
            myappid = 'mine.mn.downloader.v1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
        
    app = QApplication(sys.argv)
    
    app.setWindowIcon(QIcon(resource_path("main.ico")))

    font = QFont("Pretendard", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    app.setStyleSheet(main_ui.data_iteam.MINIMAL_DARK_THEME)

    window = main_ui.MainWindow(app=app)
    window.setWindowIcon(QIcon(resource_path("main.ico")))
    callback()
    window.show()
    sys.exit(app.exec())
    
if __name__ == "__main__":
    main()