"""验证「画面定格」是否修复：反复 hide/show 触发 apply_layer，检查窗口内容是否仍在刷新。

hide/show 会走 showEvent → apply_layer → detach_from_desktop，
修复前这里会无条件 SetParent，摧毁 Qt 的 layered 表面，导致画面永久定格。
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as w
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication

from app.window import ClockWindow
from core.config import Config

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

u = ctypes.windll.user32
g = ctypes.windll.gdi32
u.SetProcessDPIAware()


class BMIH(ctypes.Structure):
    _fields_ = [("biSize", w.DWORD), ("biWidth", w.LONG), ("biHeight", w.LONG),
                ("biPlanes", w.WORD), ("biBitCount", w.WORD), ("biCompression", w.DWORD),
                ("biSizeImage", w.DWORD), ("biXPelsPerMeter", w.LONG),
                ("biYPelsPerMeter", w.LONG), ("biClrUsed", w.DWORD), ("biClrImportant", w.DWORD)]


def snap(hwnd, W, H):
    hdc = u.GetWindowDC(ctypes.c_void_p(hwnd))
    mdc = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, W, H)
    g.SelectObject(mdc, bmp)
    u.PrintWindow(ctypes.c_void_p(hwnd), mdc, 2)
    bi = BMIH()
    bi.biSize = ctypes.sizeof(bi)
    bi.biWidth = W
    bi.biHeight = -H
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = 0
    buf = ctypes.create_string_buffer(W * H * 4)
    g.GetDIBits(mdc, bmp, 0, H, buf, ctypes.byref(bi), 0)
    img = QImage(buf.raw, W, H, QImage.Format_ARGB32).copy()
    g.DeleteObject(bmp)
    g.DeleteDC(mdc)
    u.ReleaseDC(ctypes.c_void_p(hwnd), hdc)
    return img


cfg = Config()
cfg.set("content.show_seconds", True)
cfg.set("content.second_style", "tick")
win = ClockWindow(cfg)
win.show()
win.raise_()
app.processEvents()
time.sleep(0.4)

hwnd = int(win.winId())
W, H = win.width(), win.height()

a = snap(hwnd, W, H)
time.sleep(1.6)
b = snap(hwnd, W, H)
print("基线：%s" % ("在刷新" if a != b else "!! 一开始就不刷新"))

for i in range(5):
    win.hide()
    app.processEvents()
    time.sleep(0.25)
    win.show()
    win.raise_()
    app.processEvents()
    time.sleep(0.35)

time.sleep(0.5)
c = snap(hwnd, W, H)
time.sleep(1.6)
d = snap(hwnd, W, H)
ok = c != d
print("5 次 hide/show 之后：%s" % ("仍在刷新 ✓" if ok else "!! 画面定格 ✗"))
print("parent =", u.GetParent(ctypes.c_void_p(hwnd)))
sys.exit(0 if ok else 1)
