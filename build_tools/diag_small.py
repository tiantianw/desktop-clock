"""按用户真实配置复现：size=103、classic 皮肤，走设置面板与右键菜单两条路径切换。"""

from __future__ import annotations

import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication

from app.window import ClockWindow
from core.config import Config
from render import registry

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

counter = {"tick": 0, "paint": 0, "skin": "-", "err": []}
_orig_tick = ClockWindow._tick
_orig_paint = ClockWindow.paintEvent


def tick(self):
    counter["tick"] += 1
    _orig_tick(self)


def paint(self, ev):
    counter["paint"] += 1
    _orig_paint(self, ev)


ClockWindow._tick = tick
ClockWindow.paintEvent = paint

cfg = Config()
cfg.set("geometry.size", 103)
cfg.set("appearance.shadow_strength", 20)
win = ClockWindow(cfg)
win.show()
print("窗口 %dx%d margin=%d" % (win.width(), win.height(), win._margin))

# 走设置面板
from app.settings_dialog import SettingsDialog

dlg = SettingsDialog(cfg, win)
dlg.show()

ids = [s.id for s in registry.SKINS]
st = {"i": 0, "last_tick": 0, "last_paint": 0, "stall": []}


def step():
    if st["i"] < len(ids):
        sid = ids[st["i"]]
        st["i"] += 1
        counter["skin"] = sid
        dlg._pick_skin(sid)
        print("设置面板切到 %-9s tick=%d paint=%d size=%d"
              % (sid, counter["tick"], counter["paint"], win.width()))
    else:
        # 换成右键菜单路径
        sid = ids[st["i"] % len(ids)]
        st["i"] += 1
        counter["skin"] = sid
        win.set_skin(sid)
        win.apply_config()
        print("菜单路径切到 %-9s tick=%d paint=%d" % (sid, counter["tick"], counter["paint"]))


def watch():
    t, p = counter["tick"], counter["paint"]
    dt, dp = t - st["last_tick"], p - st["last_paint"]
    if st["last_tick"] and dt == 0:
        st["stall"].append(("tick", counter["skin"], round(time.time() - t0, 1)))
        print("  !! 定时器停了 skin=%s" % counter["skin"])
    if st["last_paint"] and dp == 0:
        st["stall"].append(("paint", counter["skin"], round(time.time() - t0, 1)))
        print("  !! 没有重绘 skin=%s" % counter["skin"])
    st["last_tick"], st["last_paint"] = t, p


t0 = time.time()
QTimer(app, timeout=step).start(500)
QTimer(app, timeout=watch).start(2000)


def done():
    print("\n共切 %d 次 tick=%d paint=%d 停滞=%s" % (st["i"], counter["tick"], counter["paint"], st["stall"] or "无"))
    app.quit()


QTimer.singleShot(14000, done)
app.exec_()
