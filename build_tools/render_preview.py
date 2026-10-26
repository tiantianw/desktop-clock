"""离屏渲染全部皮肤，生成一张对比图用于检查绘制效果。

用法：python build_tools/render_preview.py
"""

from __future__ import annotations

import datetime
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import QApplication

from core.config import Config
from render import registry

SIZE = 236
PAD = 18
LABEL_H = 26
COLS = 4


def render_one(cfg, skin, size: int, wall: QColor) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(wall)
    p = QPainter(pm)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        rect = QRectF(0, 0, size, size)
        circle = getattr(skin, "shape", "rect") == "circle"
        radius = size / 2.0 if circle else float(cfg.get("appearance.radius", 18))

        # 阴影
        if cfg.get("appearance.shadow", True):
            strength = float(cfg.get("appearance.shadow_strength", 20)) * 0.7
            layers = 12
            per = max(2, int(strength * 0.30))
            p.setPen(Qt.NoPen)
            for i in range(layers, 0, -1):
                grow = strength * i / layers
                p.setBrush(QColor(0, 0, 0, per))
                p.drawRoundedRect(rect.adjusted(-grow, -grow, grow, grow),
                                  radius + grow, radius + grow)

        # 背景
        if not skin.wants_own_bg:
            mode = cfg.get("appearance.bg_mode", "solid")
            if mode != "none":
                bg = QColor(cfg.get("appearance.bg_color", "#FAF6EE"))
                bg.setAlpha(int(int(cfg.get("appearance.bg_opacity", 92)) * 255 / 100))
                p.setBrush(bg)
                if cfg.get("appearance.border", True):
                    p.setPen(QPen(QColor(cfg.get("appearance.border_color", "#E7DFD2")), 1))
                else:
                    p.setPen(Qt.NoPen)
                p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

        if circle:
            p.setClipRect(rect)
        else:
            path = QPainterPath()
            path.addRoundedRect(rect, radius, radius)
            p.setClipPath(path)
        skin.draw(p, rect, datetime.datetime.now(), cfg)
    finally:
        p.end()
    return pm


def main() -> int:
    app = QApplication(sys.argv)
    lang = "zh"
    for arg in sys.argv[1:]:
        if arg in ("zh", "en"):
            lang = arg
    from core import i18n
    i18n.set_language(lang)
    cfg = Config()

    skins = registry.SKINS
    rows = (len(skins) + COLS - 1) // COLS
    cell_w = SIZE + PAD
    cell_h = SIZE + PAD + LABEL_H
    sheet = QPixmap(cell_w * COLS + PAD, cell_h * rows + PAD)
    sheet.fill(QColor("#D6C9B6"))

    sp = QPainter(sheet)
    sp.setRenderHint(QPainter.Antialiasing, True)
    font = QFont("Microsoft YaHei UI")
    font.setPixelSize(13)

    wall = QColor("#D6C9B6")
    for i, skin in enumerate(skins):
        r, c = divmod(i, COLS)
        x = PAD + c * cell_w
        y = PAD + r * cell_h
        thumb = render_one(cfg, skin, SIZE, wall)
        sp.drawPixmap(x, y, thumb)
        sp.setFont(font)
        sp.setPen(QColor("#3A342C"))
        sp.drawText(QRectF(x, y + SIZE + 4, SIZE, LABEL_H), int(Qt.AlignCenter),
                    "%s  (%s)" % (skin.name, skin.id))
    sp.end()

    out = os.path.join(BASE, "assets",
                       "preview_all.png" if lang == "zh" else "preview_all_en.png")
    sheet.save(out, "PNG")
    print("saved:", out, sheet.width(), "x", sheet.height())
    return 0


if __name__ == "__main__":
    sys.exit(main())
