"""找出从桌面挂件层切回顶层后恢复显示的有效方法。"""

from __future__ import annotations

import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PIL import ImageGrab

from core.config import Config
from app.window import ClockWindow
from sysint import win32

app = QApplication([])
cfg = Config()
cfg.set("layer", "topmost")
w = ClockWindow(cfg)
w.show()
app.processEvents()
time.sleep(0.5)
app.processEvents()

h = int(w.winId())
pos = (w.x(), w.y(), w.width(), w.height())
print("window rect:", pos)


def center_visible() -> bool:
    """窗口中心像素是否接近卡片底色。"""
    app.processEvents()
    time.sleep(0.25)
    im = ImageGrab.grab()
    cx = pos[0] + pos[2] // 2
    cy = pos[1] + pos[3] // 2
    r, g, b = im.getpixel((cx, cy))[:3]
    # 卡片底色 #FAF6EE 附近，或者深色文字
    return (r > 225 and g > 215 and b > 200) or (r < 80 and g < 80 and b < 80)


print("A. 初始 topmost 可见:", center_visible())

cfg.set("layer", "desktop")
w.apply_layer()
for _ in range(8):
    app.processEvents()
    time.sleep(0.1)
print("B. desktop 可见:", center_visible())

cfg.set("layer", "topmost")
w.apply_layer()
for _ in range(6):
    app.processEvents()
    time.sleep(0.1)
print("C. 切回 topmost 可见:", center_visible())

# 方法1：hide / show
w.hide()
app.processEvents()
w.show()
app.processEvents()
time.sleep(0.3)
print("M1 hide/show        ->", center_visible())

# 方法2：opacity 抖动
w.setWindowOpacity(0.995)
app.processEvents()
w.setWindowOpacity(1.0)
app.processEvents()
time.sleep(0.3)
print("M2 opacity toggle   ->", center_visible())

# 方法3：resize 抖动
w.resize(w.width() + 1, w.height() + 1)
app.processEvents()
w.resize(w.width() - 1, w.height() - 1)
app.processEvents()
time.sleep(0.3)
print("M3 resize toggle    ->", center_visible())

# 方法4：重建窗口
flags = w.windowFlags()
w.setWindowFlags(flags)
w.show()
app.processEvents()
time.sleep(0.4)
w._hwnd = int(w.winId())
win32.set_tool_window(w._hwnd)
win32.set_topmost(w._hwnd)
w.move(pos[0], pos[1])
w.update()
app.processEvents()
time.sleep(0.3)
print("M4 rebuild flags    ->", center_visible())

# 方法5：重建 + 重新设 translucent
w.hide()
w.setAttribute(Qt.WA_TranslucentBackground, False)
w.setAttribute(Qt.WA_TranslucentBackground, True)
w.show()
app.processEvents()
time.sleep(0.4)
w._hwnd = int(w.winId())
win32.set_tool_window(w._hwnd)
win32.set_topmost(w._hwnd)
w.move(pos[0], pos[1])
w.update()
app.processEvents()
time.sleep(0.3)
print("M5 rebuild+attr     ->", center_visible())

ImageGrab.grab().crop((pos[0] - 60, 0, pos[0] + pos[2] + 60, pos[1] + pos[3] + 60)).save(
    os.path.join(BASE, "build_tools", "diag_fix.png"))
print("done")
