"""验证 detach_from_desktop 的守卫是否真的能防住「画面定格」。

设环境变量 DC_NO_GUARD=1 可复现旧行为（无条件 SetParent），用来确认测试有效。
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as w
import hashlib
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
from sysint import win32

if os.environ.get("DC_NO_GUARD") == "1":
    # 还原旧行为：不判断父窗口，直接 SetParent
    def _old_detach(hwnd, x=0, y=0, w_=0, h_=0):
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(ctypes.c_void_p(hwnd), -16)
        style = (style & ~0x40000000) | 0x80000000
        user32.SetWindowLongW(ctypes.c_void_p(hwnd), -16, style)
        user32.SetParent(ctypes.c_void_p(hwnd), None)
        flags = 0x0004 | 0x0010 | 0x0020
        if w_ > 0 and h_ > 0:
            user32.SetWindowPos(ctypes.c_void_p(hwnd), None, x, y, w_, h_, flags)
        user32.ShowWindow(ctypes.c_void_p(hwnd), 8)
        return True

    win32.detach_from_desktop = _old_detach
    print("[复现模式] 已禁用守卫")

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

cfg = Config()
cfg.set("content.show_seconds", True)
cfg.set("content.second_style", "tick")
cfg.set("geometry.size", 110)
cfg.set("layer", "topmost")

win = ClockWindow(cfg)
win.show()
win.raise_()
app.processEvents()
time.sleep(0.6)


def hash_region():
    """抓窗口所在区域的屏幕像素（背景是静止壁纸，变化只可能来自时钟本身）。"""
    geo = win.geometry()
    pm = app.primaryScreen().grabWindow(0, geo.x() + 8, geo.y() + 8,
                                        geo.width() - 16, geo.height() - 16)
    img = pm.toImage()
    return hashlib.md5(img.bits().asstring(img.byteCount())).hexdigest()[:10]


def live() -> bool:
    a = hash_region()
    time.sleep(2.2)
    b = hash_region()
    return a != b


print("基线是否在刷新:", "是" if live() else "否")

for i in range(10):
    win.apply_layer()
    app.processEvents()
    time.sleep(0.08)

time.sleep(0.5)
alive = live()
print("10 次 apply_layer 之后:", "仍在刷新 ✓" if alive else "画面定格 ✗")
sys.exit(0 if alive else 1)
