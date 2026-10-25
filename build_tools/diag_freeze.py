"""复现「切换皮肤后卡死」：逐个切 12 套皮肤，同时监控 timer / paint 是否还在跑。

用法：
    .venvbuild/Scripts/python.exe build_tools/diag_freeze.py
"""

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
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

cfg = Config()
win = ClockWindow(cfg)
win.show()

stats = {"tick": 0, "paint": 0, "skin": "-", "last": time.time()}
_orig_tick = win._tick
_orig_paint = win.paintEvent


def tick():
    stats["tick"] += 1
    stats["last"] = time.time()
    _orig_tick()


def paint(ev):
    stats["paint"] += 1
    _orig_paint(ev)


win._tick = tick
win.paintEvent = paint

skin_ids = [s.id for s in registry.SKINS]
state = {"i": 0, "last_tick": 0, "last_paint": 0, "stalls": []}


def switch():
    sid = skin_ids[state["i"] % len(skin_ids)]
    state["i"] += 1
    stats["skin"] = sid
    win.set_skin(sid)          # 走右键菜单那条路径
    win.apply_config()         # 走设置面板那条路径
    print("切到 %-9s tick=%d paint=%d" % (sid, stats["tick"], stats["paint"]))


def watch():
    t, pt = stats["tick"], stats["paint"]
    dt = t - state["last_tick"]
    dp = pt - state["last_paint"]
    age = time.time() - stats["last"]
    flag = ""
    if dt == 0 and state["last_tick"]:
        flag = "  <<< 定时器停了"
        state["stalls"].append(("tick", stats["skin"], age))
    if dp == 0 and state["last_paint"]:
        flag += "  <<< 没有重绘"
        state["stalls"].append(("paint", stats["skin"], age))
    print("  监测 %-9s tick+%d paint+%d 距上次 tick %.1fs%s"
          % (stats["skin"], dt, dp, age, flag))
    state["last_tick"], state["last_paint"] = t, pt


sw = QTimer()
sw.timeout.connect(switch)
sw.start(700)

wt = QTimer()
wt.timeout.connect(watch)
wt.start(1500)


def done():
    print("\n=== 结果 ===")
    print("共切换 %d 次，tick %d 次，paint %d 次" % (state["i"], stats["tick"], stats["paint"]))
    if state["stalls"]:
        print("检测到停滞：")
        for item in state["stalls"]:
            print("   ", item)
    else:
        print("没有检测到停滞")
    app.quit()


QTimer.singleShot(11000, done)
app.exec_()
