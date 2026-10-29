import src.down.down as down
import src.system.data as data_iteam
import src.find.findsyou as findsyou
import src.main.thread_pyqt as thread_pyqt
import src.trans.trans_view as trans_view
import src.qr.qr_view as qr_view
import src.main.setting as setting_ui
import src.recommend.recommend as recommend

data_iteam.rest()
thread_pyqt.DOWN = down
qr_view.down = down

findsyou.detail_ui.DOWN = down.downin
setting_ui.data_iteam = data_iteam
trans_view.OUT = down.downin.base_data.OUTFOLDER

recommend.detail_ui = findsyou.detail_ui

from .main_window import MainWindow