"""检查 ClockWindow 的刷新定时器到底有没有在跑。"""

from __future__ import annotations

import datetime
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

counter = {"tick": 0, "paint": 0, "skin": "-"}

# 在创建窗口之前打补丁，确保信号连接到打过补丁的方法
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
print("配置: show_seconds=%s second_style=%s skin=%s size=%s"
      % (cfg.get("content.show_seconds"), cfg.get("content.second_style"),
         cfg.get("skin"), cfg.get("geometry.size")))

win = ClockWindow(cfg)
win.show()

print("初始 _timer.isActive=%s interval=%d" % (win._timer.isActive(), win._timer.interval()))

skin_ids = [s.id for s in registry.SKINS]
state = {"i": 0}


def report(tag):
    print("%-14s tick=%-3d paint=%-3d timer_active=%-5s interval=%-5d skin=%s"
          % (tag, counter["tick"], counter["paint"],
             win._timer.isActive(), win._timer.interval(), counter["skin"]))


def switch():
    sid = skin_ids[state["i"] % len(skin_ids)]
    state["i"] += 1
    counter["skin"] = sid
    win.set_skin(sid)
    win.apply_config()
    report("切到 " + sid)


sw = QTimer()
sw.timeout.connect(switch)
sw.start(600)

QTimer.singleShot(1500, lambda: report("静置 1.5s"))
QTimer.singleShot(3000, lambda: report("静置 3s"))
QTimer.singleShot(9000, lambda: (report("切完 12 套"), app.quit()))
app.exec_()
