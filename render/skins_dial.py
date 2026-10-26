"""指针类皮肤：经典指针 / 罗马指针 / 极简刻度盘 / 双表盘 / 经典挂钟。

这五个皮肤都是圆形表盘，shape = "circle"，圆外区域完全透明，
窗口层不会再在背后铺一张圆角卡片。

两个倍数设置：
- appearance.hand_scale  指针粗细，作用于三根针的线宽与中心轴帽
- appearance.dial_scale  表盘刻度与数字，作用于刻度线宽/长度、数字字号
"""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPen, QRadialGradient

from render.base import (
    Skin, clock_angles, color, dial_scale, dot, draw_text, hand, hand_scale,
    is_dark, mix, num_font, tick_inner,
)


def _face_colors(cfg):
    """表盘填充色：浅色主题提亮、深色主题略微提亮，保证与卡片有层次。"""
    bg = color(cfg, "bg")
    if is_dark(bg):
        return mix(bg, QColor("#FFFFFF"), 0.10)
    return mix(bg, QColor("#FFFFFF"), 0.55)


def _polar(center: QPointF, radius: float, angle_deg: float) -> QPointF:
    a = math.radians(angle_deg)
    return QPointF(center.x() + math.sin(a) * radius, center.y() - math.cos(a) * radius)


def _num_px(r: float, base: float, ds: float, cap: float) -> float:
    """数字字号：随 ds 放大，但不超过表盘半径的 cap，也不小于 7.5%，防止糊成一团或消失。"""
    return max(r * 0.075, min(r * cap, r * base * ds))


def _hub(r: float, base: float, hs: float, cap: float = 0.085) -> float:
    """中心轴帽半径：跟着指针一起变粗，但有上限。"""
    return max(1.5, min(r * cap, r * base * hs))


def _draw_minute_ticks(p, center, radius, cfg, ds=1.0,
                       outer=0.96, inner_bold=0.88, inner_thin=0.92):
    txt = color(cfg, "text", 150)
    for i in range(60):
        ang = i * 6.0
        bold = (i % 5 == 0)
        pen = QPen(txt, max(1.0, radius * (0.014 if bold else 0.006) * ds))
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(_polar(center, radius * tick_inner(outer, inner_bold if bold else inner_thin, ds), ang),
                   _polar(center, radius * outer, ang))


class ClassicSkin(Skin):
    id = "classic"
    name = "经典指针"
    desc = "黑框白面、阿拉伯数字、红色秒针，最接近传统挂钟"
    shape = "circle"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        r = w * 0.5
        hs = hand_scale(cfg)
        ds = dial_scale(cfg)
        ring = max(2.0, r * 0.045)

        # 表盘底与外框
        p.setPen(QPen(color(cfg, "text"), ring))
        p.setBrush(_face_colors(cfg))
        p.drawEllipse(c, r - ring / 2.0, r - ring / 2.0)

        # 12 根主刻度（贴在表盘外缘）
        for i in range(12):
            ang = i * 30.0
            major = (i % 3 == 0)
            pen = QPen(color(cfg, "text", 240 if major else 175),
                       max(1.0, r * (0.024 if major else 0.012) * ds))
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(_polar(c, r * tick_inner(0.91, 0.82 if major else 0.85, ds), ang),
                       _polar(c, r * 0.91, ang))

        # 阿拉伯数字：放在刻度内侧，指针够不到
        style = cfg.get("appearance.dial_style", "arabic")
        if style != "none":
            f = num_font(cfg, _num_px(r, 0.130, ds, 0.30),
                         cfg.get("appearance.font_weight", 500))
            for i in range(1, 13):
                pt = _polar(c, r * 0.680, i * 30.0)
                box = QRectF(pt.x() - r * 0.16, pt.y() - r * 0.16, r * 0.32, r * 0.32)
                draw_text(p, box, str(i), f, color(cfg, "text", 240))

        h_ang, m_ang, s_ang = clock_angles(now, cfg)
        hand(p, c, h_ang, r * 0.40, max(1.2, r * 0.062 * hs), color(cfg, "text"), tail=r * 0.08)
        hand(p, c, m_ang, r * 0.55, max(1.0, r * 0.042 * hs), color(cfg, "text"), tail=r * 0.10)
        if cfg.get("content.show_seconds", True) and cfg.get("content.second_style", "tick") != "none":
            hand(p, c, s_ang, r * 0.66, max(0.8, r * 0.020 * hs), color(cfg, "accent"), tail=r * 0.18)
        dot(p, c, _hub(r, 0.036, hs), color(cfg, "text"))
        dot(p, c, max(1.2, r * 0.016), color(cfg, "accent"))


ROMAN = ["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"]


class RomanSkin(Skin):
    id = "roman"
    name = "罗马指针"
    desc = "细边框 + 罗马数字，古典钟表气质"
    shape = "circle"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        r = w * 0.5
        hs = hand_scale(cfg)
        ds = dial_scale(cfg)
        ring = max(1.4, r * 0.018)

        p.setPen(QPen(color(cfg, "text", 190), ring))
        p.setBrush(_face_colors(cfg))
        p.drawEllipse(c, r - ring / 2.0, r - ring / 2.0)

        # 内圈细线（放在罗马数字内侧）
        p.setPen(QPen(color(cfg, "text", 50), max(1.0, r * 0.007)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, r * 0.52, r * 0.52)

        _draw_minute_ticks(p, c, r, cfg, ds=ds, outer=0.94, inner_bold=0.86, inner_thin=0.90)

        f = num_font(cfg, _num_px(r, 0.095, ds, 0.26), 500)
        for i in range(12):
            pt = _polar(c, r * 0.720, i * 30.0)
            box = QRectF(pt.x() - r * 0.17, pt.y() - r * 0.12, r * 0.34, r * 0.24)
            draw_text(p, box, ROMAN[i], f, color(cfg, "text", 235))

        h_ang, m_ang, s_ang = clock_angles(now, cfg)
        hand(p, c, h_ang, r * 0.38, max(1.2, r * 0.038 * hs), color(cfg, "text"), tail=r * 0.06)
        hand(p, c, m_ang, r * 0.54, max(1.0, r * 0.026 * hs), color(cfg, "text"), tail=r * 0.08)
        if cfg.get("content.show_seconds", True) and cfg.get("content.second_style", "tick") != "none":
            hand(p, c, s_ang, r * 0.62, max(0.8, r * 0.013 * hs), color(cfg, "accent"), tail=r * 0.15)
        dot(p, c, _hub(r, 0.024, hs, 0.070), color(cfg, "text"))


class MinimalSkin(Skin):
    id = "minimal"
    name = "极简刻度盘"
    desc = "没有数字，只有刻度与两根细针，最干净的指针款"
    shape = "circle"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        r = w * 0.5
        hs = hand_scale(cfg)
        ds = dial_scale(cfg)

        p.setPen(QPen(color(cfg, "text", 45), max(1.0, r * 0.010)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, r * 0.94, r * 0.94)

        _draw_minute_ticks(p, c, r, cfg, ds=ds, outer=0.90, inner_bold=0.80, inner_thin=0.85)

        h_ang, m_ang, s_ang = clock_angles(now, cfg)
        hand(p, c, h_ang, r * 0.50, max(1.2, r * 0.036 * hs), color(cfg, "text"), tail=r * 0.06)
        hand(p, c, m_ang, r * 0.70, max(1.0, r * 0.024 * hs), color(cfg, "text"), tail=r * 0.08)
        if cfg.get("content.show_seconds", True) and cfg.get("content.second_style", "tick") != "none":
            hand(p, c, s_ang, r * 0.78, max(0.8, r * 0.011 * hs), color(cfg, "accent"), tail=r * 0.14)
        dot(p, c, _hub(r, 0.020, hs, 0.065), color(cfg, "accent"))


class SubdialSkin(Skin):
    id = "subdial"
    name = "双表盘"
    desc = "主表盘看时分，下方小表盘走秒"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        cx = c.x()
        cy = c.y()
        hs = hand_scale(cfg)
        ds = dial_scale(cfg)

        main_c = QPointF(cx, cy - w * 0.13)
        main_r = w * 0.35
        sub_c = QPointF(cx, cy + w * 0.33)
        sub_r = w * 0.13

        face = _face_colors(cfg)

        # 主表盘
        p.setPen(QPen(color(cfg, "text", 200), max(1.4, main_r * 0.022)))
        p.setBrush(face)
        p.drawEllipse(main_c, main_r, main_r)

        for i in range(12):
            ang = i * 30.0
            major = (i % 3 == 0)
            pen = QPen(color(cfg, "text", 215 if major else 145),
                       max(1.0, main_r * (0.020 if major else 0.009) * ds))
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(_polar(main_c, main_r * tick_inner(0.90, 0.80 if major else 0.84, ds), ang),
                       _polar(main_c, main_r * 0.90, ang))

        if cfg.get("appearance.dial_style", "arabic") != "none":
            f = num_font(cfg, _num_px(main_r, 0.135, ds, 0.30), 500)
            for i in range(1, 13):
                pt = _polar(main_c, main_r * 0.660, i * 30.0)
                box = QRectF(pt.x() - main_r * 0.16, pt.y() - main_r * 0.16, main_r * 0.32, main_r * 0.32)
                draw_text(p, box, str(i), f, color(cfg, "text", 230))

        h_ang, m_ang, _ = clock_angles(now, cfg)
        hand(p, main_c, h_ang, main_r * 0.39, max(1.2, main_r * 0.054 * hs), color(cfg, "text"), tail=main_r * 0.07)
        hand(p, main_c, m_ang, main_r * 0.56, max(1.0, main_r * 0.036 * hs), color(cfg, "text"), tail=main_r * 0.09)
        dot(p, main_c, _hub(main_r, 0.034, hs, 0.080), color(cfg, "accent"))

        # 小秒盘
        p.setPen(QPen(color(cfg, "text", 170), max(1.2, sub_r * 0.045)))
        p.setBrush(face)
        p.drawEllipse(sub_c, sub_r, sub_r)

        for i in range(0, 60, 5):
            ang = i * 6.0
            pen = QPen(color(cfg, "text", 130), max(0.8, sub_r * 0.028 * ds))
            p.setPen(pen)
            p.drawLine(_polar(sub_c, sub_r * tick_inner(0.90, 0.74, ds, 0.50), ang),
                       _polar(sub_c, sub_r * 0.90, ang))

        if cfg.get("content.show_seconds", True) and cfg.get("content.second_style", "tick") != "none":
            _, _, s_ang = clock_angles(now, cfg)
            hand(p, sub_c, s_ang, sub_r * 0.70, max(0.9, sub_r * 0.045 * hs), color(cfg, "accent"), tail=sub_r * 0.16)
            dot(p, sub_c, max(1.2, sub_r * 0.075), color(cfg, "text"))
        else:
            f = num_font(cfg, sub_r * 0.42, 500)
            draw_text(p, QRectF(sub_c.x() - sub_r, sub_c.y() - sub_r, sub_r * 2, sub_r * 2),
                      "%02d" % now.second, f, color(cfg, "text", 200))


# ---------------------------------------------------------------- 挂钟

BEZEL = QColor("#25231F")
FACE_HI = QColor("#FCF8EC")
FACE_LO = QColor("#E9E0C9")
INK = QColor("#1C1A17")


def _bold_font(px: float, weight: int = QFont.Bold) -> QFont:
    """表盘数字用无衬线粗体，比等宽字体更像实体挂钟。"""
    f = QFont("Segoe UI")
    f.setPixelSize(max(1, int(round(px))))
    f.setWeight(weight)
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


class WallSkin(Skin):
    id = "wall"
    name = "经典挂钟"
    desc = "粗黑外框 + 米白表盘 + 红色秒针，最接近墙上那只实体钟"
    shape = "circle"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        r = w * 0.5
        hs = hand_scale(cfg)
        ds = dial_scale(cfg)

        # 外框
        p.setPen(Qt.NoPen)
        p.setBrush(BEZEL)
        p.drawEllipse(c, r * 0.995, r * 0.995)
        # 外框内侧的高光，做出金属圈厚度
        p.setPen(QPen(QColor(255, 255, 255, 42), max(1.0, r * 0.014)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, r * 0.908, r * 0.908)

        # 表盘：中心亮、边缘略暗，模拟弧面玻璃
        grad = QRadialGradient(c, r * 0.88)
        grad.setColorAt(0.0, FACE_HI)
        grad.setColorAt(0.70, QColor("#F7F1E0"))
        grad.setColorAt(1.0, FACE_LO)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(c, r * 0.878, r * 0.878)

        # 60 格分刻度
        for i in range(60):
            ang = i * 6.0
            major = (i % 5 == 0)
            pen = QPen(INK if major else QColor(60, 55, 48, 150),
                       max(0.9, r * (0.011 if major else 0.006) * ds))
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(_polar(c, r * tick_inner(0.855, 0.800 if major else 0.818, ds, 0.60), ang),
                       _polar(c, r * 0.855, ang))

        # 数字：12/3/6/9 略大
        for i in range(1, 13):
            big = (i % 3 == 0)
            f = _bold_font(_num_px(r, 0.200 if big else 0.176, ds, 0.34))
            pt = _polar(c, r * 0.645, i * 30.0)
            box = QRectF(pt.x() - r * 0.17, pt.y() - r * 0.15, r * 0.34, r * 0.30)
            draw_text(p, box, str(i), f, INK)

        h_ang, m_ang, s_ang = clock_angles(now, cfg)
        # 粗黑时针分针
        hand(p, c, h_ang, r * 0.425, max(1.4, r * 0.076 * hs), INK, tail=r * 0.075)
        hand(p, c, m_ang, r * 0.600, max(1.2, r * 0.052 * hs), INK, tail=r * 0.095)

        # 红秒针：细长、带尾部配重
        if cfg.get("content.show_seconds", True) and cfg.get("content.second_style", "tick") != "none":
            red = mix(QColor("#C0392B"), color(cfg, "accent"), 0.30)
            hand(p, c, s_ang, r * 0.660, max(0.8, r * 0.017 * hs), red, tail=r * 0.165)
            dot(p, _polar(c, r * 0.165, s_ang + 180.0), max(1.2, r * 0.026 * hs), red)

        # 中心轴帽
        dot(p, c, _hub(r, 0.048, hs, 0.100), INK)
        dot(p, c, max(1.2, r * 0.017), QColor("#C0392B"))
