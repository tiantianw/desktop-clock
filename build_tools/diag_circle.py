"""检查圆形皮肤在窗口层的表现：圆外是否真的透明、投影是否跟着变圆。

把窗口的 paintEvent 渲染到棋盘格背景上，肉眼一看就知道有没有残留底色。
用法：python build_tools/diag_circle.py
"""

from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication

from core.config import Config
from render import registry

CHECK = 12


def checkerboard(w: int, h: int) -> QPixmap:
    pm = QPixmap(w, h)
    p = QPainter(pm)
    p.fillRect(0, 0, w, h, QColor("#FFFFFF"))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#E2E2E2"))
    for y in range(0, h, CHECK):
        for x in range(0, w, CHECK):
            if ((x // CHECK) + (y // CHECK)) % 2 == 0:
                p.drawRect(x, y, CHECK, CHECK)
    p.end()
    return pm


def main() -> int:
    app = QApplication(sys.argv)
    cfg = Config()

    from app.window import ClockWindow

    ids = [s.id for s in registry.SKINS if getattr(s, "shape", "rect") == "circle"]
    size = 150
    cell = size + 60
    cols = len(ids)
    sheet = checkerboard(cell * cols, cell + 24)
    sp = QPainter(sheet)
    sp.setRenderHint(QPainter.Antialiasing, True)

    for i, sid in enumerate(ids):
        cfg.set("skin", sid)
        cfg.set("geometry.size", size)
        cfg.set("appearance.hand_scale", 1.0)
        cfg.set("appearance.dial_scale", 1.0)
        win = ClockWindow(cfg)
        win.setAttribute(Qt.WA_TranslucentBackground, True)
        win.apply_size(size, keep_pos=False)
        win.show()
        app.processEvents()
        pm = win.grab()
        x = i * cell + (cell - pm.width()) // 2
        y = 20 + (cell - 24 - pm.height()) // 2
        sp.drawPixmap(x, y, pm)
        sp.setPen(QPen(QColor("#333333"), 1))
        sp.drawText(QRect(x, 0, pm.width(), 18), int(Qt.AlignCenter), sid)
        win.close()
        win.deleteLater()
        app.processEvents()

    sp.end()
    out = os.path.join(BASE, "build_tools", "diag_circle.png")
    sheet.save(out, "PNG")
    print("saved:", out, sheet.width(), "x", sheet.height())
    return 0


if __name__ == "__main__":
    sys.exit(main())
