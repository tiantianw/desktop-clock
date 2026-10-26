"""离屏渲染「指针粗细 × 表盘刻度」的倍数矩阵，用来核对两个滑杆的实际效果。

用法：python build_tools/preview_scale.py [skin_id]
"""

from __future__ import annotations

import datetime
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication

from core.config import Config
from render import registry

SIZE = 150
PAD = 14
LABEL_H = 22
STEPS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]


def render_one(cfg, skin, size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(QColor("#D6C9B6"))
    p = QPainter(pm)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        rect = QRectF(0, 0, size, size)
        circle = getattr(skin, "shape", "rect") == "circle"
        radius = size / 2.0 if circle else float(cfg.get("appearance.radius", 18))
        if not skin.wants_own_bg:
            bg = QColor(cfg.get("appearance.bg_color", "#FAF6EE"))
            bg.setAlpha(int(int(cfg.get("appearance.bg_opacity", 92)) * 255 / 100))
            p.setBrush(bg)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(rect, radius, radius)
        if circle:
            p.setClipRect(rect)
        else:
            p.setClipRect(rect)
        skin.draw(p, rect, datetime.datetime.now(), cfg)
    finally:
        p.end()
    return pm


def main() -> int:
    app = QApplication(sys.argv)
    cfg = Config()
    skin_id = sys.argv[1] if len(sys.argv) > 1 else "classic"
    skin = registry.get_skin(skin_id)

    cell = SIZE + PAD
    sheet = QPixmap(cell * len(STEPS) + PAD, cell * len(STEPS) + PAD + LABEL_H * 2)
    sheet.fill(QColor("#EFE7DA"))

    sp = QPainter(sheet)
    sp.setRenderHint(QPainter.Antialiasing, True)
    font = QFont("Microsoft YaHei UI")
    font.setPixelSize(11)

    for row, hs in enumerate(STEPS):          # 行 = 指针粗细
        for col, ds in enumerate(STEPS):      # 列 = 表盘刻度
            cfg.set("appearance.hand_scale", hs)
            cfg.set("appearance.dial_scale", ds)
            x = PAD + col * cell
            y = PAD + row * cell
            sp.drawPixmap(x, y, render_one(cfg, skin, SIZE))
            sp.setFont(font)
            sp.setPen(QColor("#5C5346"))
            if row == 0:
                sp.drawText(QRectF(x, 0, SIZE, PAD), int(Qt.AlignCenter), "刻度 %.1f" % ds)
            if col == 0:
                sp.drawText(QRectF(0, y, PAD + 2, SIZE), int(Qt.AlignCenter),
                            "针 %.1f" % hs)
    sp.end()

    out = os.path.join(BASE, "build_tools", "preview_scale.png")
    sheet.save(out, "PNG")
    print("saved:", out, sheet.width(), "x", sheet.height())
    return 0


if __name__ == "__main__":
    sys.exit(main())
