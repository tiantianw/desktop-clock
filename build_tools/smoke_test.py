"""冒烟测试：真实创建窗口 / 托盘 / 设置面板，截图后退出。"""

from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from core.config import Config
from core.logger import install_global_hook, log

install_global_hook()

app = QApplication(sys.argv)

cfg = Config()
log("smoke: config loaded")

from app.window import ClockWindow

win = ClockWindow(cfg)
win.show()
app.processEvents()
log("smoke: window shown")

from app.tray import Tray

tray = Tray(win, cfg)
tray.show()
log("smoke: tray ok")

from app.settings_dialog import SettingsDialog

dlg = SettingsDialog(cfg, win)
dlg.show()
app.processEvents()
log("smoke: settings ok")

out_dir = os.path.join(BASE, "build_tools")


def shoot():
    try:
        win.grab().save(os.path.join(out_dir, "shot_window.png"), "PNG")
        dlg.grab().save(os.path.join(out_dir, "shot_settings.png"), "PNG")
        log("smoke: screenshots saved")

        for i in range(4):
            dlg.tabs.setCurrentIndex(i)
            app.processEvents()
            dlg.grab().save(os.path.join(out_dir, "shot_tab%d.png" % i), "PNG")
        dlg.tabs.setCurrentIndex(0)
        log("smoke: tab screenshots saved")

        # 逐个皮肤切换，确认都不崩
        from render import registry
        for skin in registry.SKINS:
            win.set_skin(skin.id)
            win.repaint()
            app.processEvents()
        log("smoke: all skins drawn ok")

        # 三层级切换
        for layer in ("topmost", "normal", "desktop", "topmost"):
            win.set_layer(layer)
            app.processEvents()
        log("smoke: layer switching ok")

        # 尺寸边界
        for size in (80, 600, 220):
            win.apply_size(size)
            win.repaint()
            app.processEvents()
        log("smoke: size range ok")

        cfg.set("skin", "glass")
        win.set_skin("glass")
        win.repaint()
        app.processEvents()
        win.grab().save(os.path.join(out_dir, "shot_window_final.png"), "PNG")
    except Exception as exc:
        log("smoke FAILED: %r" % (exc,))
        import traceback
        log(traceback.format_exc())
    finally:
        app.quit()


QTimer.singleShot(500, shoot)
sys.exit(app.exec_())
