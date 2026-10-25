"""验证自愈：人为把刷新定时器停掉，看看门狗能否发现并重启。

这模拟了线上出现过的那种失效——事件循环正常、窗口还在，但 QTimer 不再触发。
"""

from __future__ import annotations

import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from app.window import ClockWindow
from core.config import Config
from core.logger import LOG_PATH

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

counter = {"tick": 0}
_orig = ClockWindow._tick


def tick(self):
    counter["tick"] += 1
    _orig(self)


ClockWindow._tick = tick

cfg = Config()
win = ClockWindow(cfg)
win.show()
win._born = time.time() - 60      # 跳过启动宽限期

results = []


def phase1():
    print("阶段 1：正常运行 6 秒")
    time.sleep(0.1)


def kill_timer():
    win._timer.stop()
    print("已人为停止定时器，tick 计数 =", counter["tick"])


def check():
    t = counter["tick"]
    time.sleep(4.5)
    t2 = counter["tick"]
    ok = t2 > t
    results.append(ok)
    print("停止后 4.5 秒内 tick 增量 = %d → %s" % (t2 - t, "已自愈 ✓" if ok else "未恢复 ✗"))


from PyQt5.QtCore import QTimer

state = {"at_kill": 0}


def kill_timer():
    win._timer.stop()
    state["at_kill"] = counter["tick"]
    print("已人为停止定时器，tick 计数 =", counter["tick"])


def check():
    after = counter["tick"]
    ok = after > state["at_kill"]
    results.append(ok)
    print("停止后 9 秒：tick 从 %d 增加到 %d → %s"
          % (state["at_kill"], after, "已自愈 ✓" if ok else "未恢复 ✗"))


QTimer.singleShot(6000, kill_timer)
QTimer.singleShot(15000, check)


def done():
    print("\n--- 日志相关行 ---")
    try:
        for line in open(LOG_PATH, encoding="utf-8").read().splitlines()[-4:]:
            print(" ", line)
    except Exception as e:
        print("  读日志失败", e)
    app.quit()


QTimer.singleShot(16500, done)
app.exec_()
sys.exit(0 if results and results[0] else 1)
