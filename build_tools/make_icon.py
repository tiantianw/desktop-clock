"""生成应用图标（ico + png），供 exe 与托盘使用。"""

from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication

SIZE = 512


def draw() -> QPixmap:
    pm = QPixmap(SIZE, SIZE)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    margin = SIZE * 0.06
    rect = QRectF(margin, margin, SIZE - margin * 2, SIZE - margin * 2)
    radius = SIZE * 0.22

    # 暖米底
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#F7F2E7"))
    p.drawRoundedRect(rect, radius, radius)

    c = QPointF(SIZE / 2, SIZE / 2)
    r = SIZE * 0.31

    # 表盘外圈
    p.setPen(QPen(QColor("#2C2C2A"), SIZE * 0.045))
    p.setBrush(QColor("#FFFDF8"))
    p.drawEllipse(c, r, r)

    # 刻度
    for i in range(12):
        p.save()
        p.translate(c)
        p.rotate(i * 30)
        major = (i % 3 == 0)
        p.setPen(QPen(QColor("#2C2C2A"), SIZE * (0.016 if major else 0.008)))
        p.drawLine(QPointF(0, -r * 0.86), QPointF(0, -r * (0.72 if major else 0.79)))
        p.restore()

    # 10:10 指针
    p.save()
    p.translate(c)
    p.rotate(305)
    p.setPen(QPen(QColor("#2C2C2A"), SIZE * 0.030))
    p.drawLine(QPointF(0, r * 0.10), QPointF(0, -r * 0.48))
    p.restore()
    p.save()
    p.translate(c)
    p.rotate(60)
    p.setPen(QPen(QColor("#2C2C2A"), SIZE * 0.022))
    p.drawLine(QPointF(0, r * 0.12), QPointF(0, -r * 0.68))
    p.restore()
    p.save()
    p.translate(c)
    p.rotate(190)
    p.setPen(QPen(QColor("#C08A4E"), SIZE * 0.010))
    p.drawLine(QPointF(0, r * 0.22), QPointF(0, -r * 0.78))
    p.restore()

    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#C08A4E"))
    p.drawEllipse(c, SIZE * 0.028, SIZE * 0.028)
    p.end()
    return pm


def main() -> int:
    app = QApplication(sys.argv)
    assets = os.path.join(BASE, "assets")
    os.makedirs(assets, exist_ok=True)

    pm = draw()
    png = os.path.join(assets, "app.png")
    pm.save(png, "PNG")
    print("png:", png)

    # 用 PIL 生成多尺寸 ico
    try:
        from PIL import Image
        img = Image.open(png).convert("RGBA")
        ico = os.path.join(assets, "app.ico")
        img.save(ico, format="ICO",
                 sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print("ico:", ico)
    except Exception as exc:
        print("ico failed:", exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
