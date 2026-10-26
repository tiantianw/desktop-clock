"""应用图标的唯一绘制来源：托盘图标、exe 图标都从这里出，保证长得一样。

设计要点：圆形图标天然比方形图标"看起来小一圈"（内切圆面积只有正方形的
78.5%），所以这里让表盘**顶满画布**，只在最外圈留 0.5px 防止抗锯齿被裁掉。
小尺寸另外单独画，笔画加粗、去掉多余刻度，避免 16px 下糊成一团。
"""

from __future__ import annotations

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

# 需要哪些尺寸就画哪些，交给 Windows 自己挑最合适的那张，不要让它缩放大图
ICON_SIZES = (16, 20, 24, 32, 48, 64, 128, 256)


def draw_clock(size: int, text_color: str = "#2C2C2A", accent: str = "#C08A4E",
               bg: str = "#FFFFFF") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        s = float(size)
        half = s / 2.0
        # 0.5px 内缩：既顶满画布，又不让最外圈像素被裁掉
        box = QRectF(0.5, 0.5, s - 1.0, s - 1.0)
        # 小图标下圆环不能按比例加粗，否则盘面被吃掉、整只表看起来是一坨黑的
        ring = max(1.0, s * (0.062 if size < 24 else 0.095))

        # 盘面：先填满整圆，圆环再压在外缘上
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(bg))
        p.drawEllipse(box)

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(text_color), ring))
        r = half - ring / 2.0 - 0.5
        p.drawEllipse(QPointF(half, half), r, r)

        center = QPointF(half, half)
        ink = QColor(text_color)

        # 刻度：16px 干脆不画（只会糊成一圈噪点），24px 给 4 个，32px 起给 12 个
        count = 0 if size < 22 else (4 if size < 32 else 12)
        step = 360 // count if count else 0
        tick_w = max(1.0, s * (0.055 if count <= 4 else 0.030))
        outer = r * 0.80
        inner = r * (0.56 if count <= 4 else 0.66)
        for i in range(count):
            p.save()
            p.translate(center)
            p.rotate(i * step)
            p.setPen(QPen(ink, tick_w))
            p.drawLine(QPointF(0, -outer), QPointF(0, -inner))
            p.restore()

        # 10:10 指针，小图标下加粗，否则 16px 里根本看不见
        hw = max(1.5, s * 0.078)
        mw = max(1.2, s * 0.060)
        p.save()
        p.translate(center)
        p.rotate(305)
        p.setPen(QPen(ink, hw))
        p.drawLine(QPointF(0, r * 0.14), QPointF(0, -r * 0.56))
        p.restore()
        p.save()
        p.translate(center)
        p.rotate(60)
        p.setPen(QPen(ink, mw))
        p.drawLine(QPointF(0, r * 0.18), QPointF(0, -r * 0.78))
        p.restore()

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(accent))
        dot = max(1.2, s * (0.075 if size < 24 else 0.058))
        p.drawEllipse(center, dot, dot)
    finally:
        p.end()
    return pm


def build_icon(text_color: str = "#2C2C2A", accent: str = "#C08A4E",
               bg: str = "#FFFFFF") -> QIcon:
    """多尺寸 QIcon：托盘、任务栏、Alt-Tab 各取所需，不用缩放糊掉。"""
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(draw_clock(size, text_color, accent, bg))
    return icon
