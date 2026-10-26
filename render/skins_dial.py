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
from PyQt5.QtGui import QBrush, QColor, QFont, QPen, QPolygonF, QRadialGradient

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
    name_zh = "经典指针"
    name_en = "Classic Hands"
    desc_zh = "黑框白面、阿拉伯数字、红色秒针，最接近传统挂钟"
    desc_en = "Black rim, white face, Arabic numerals, red second hand."
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
    name_zh = "罗马指针"
    name_en = "Roman Hands"
    desc_zh = "细边框 + 罗马数字，古典钟表气质"
    desc_en = "Thin rim with Roman numerals. Classic watch feel."
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
    name_zh = "极简刻度盘"
    name_en = "Minimal Dial"
    desc_zh = "没有数字，只有刻度与两根细针，最干净的指针款"
    desc_en = "No numerals, just ticks and two slim hands."
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
    name_zh = "双表盘"
    name_en = "Sub-dial"
    desc_zh = "主表盘看时分，下方小表盘走秒"
    desc_en = "Main dial for hours and minutes, a small dial below for seconds."

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
    name_zh = "经典挂钟"
    name_en = "Wall Clock"
    desc_zh = "粗黑外框 + 米白表盘 + 红色秒针，最接近墙上那只实体钟"
    desc_en = "Thick black bezel, cream face, bold hands, red second hand."
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


# ---------------------------------------------------------------- 新增圆形表盘

def _rose_polygons(center, r_long, r_short):
    """罗盘玫瑰的 8 个菱形扇叶，返回 [(角度序号, 顶点列表)]。"""
    out = []
    for i in range(8):
        a = i * 45.0
        rr = r_long if i % 2 == 0 else r_short
        out.append((i, [
            _polar(center, rr, a),
            _polar(center, rr * 0.30, a + 22.5),
            center,
            _polar(center, rr * 0.30, a - 22.5),
        ]))
    return out


class CompassSkin(Skin):
    id = "compass"
    name_zh = "航海罗盘"
    name_en = "Compass"
    desc_zh = "深藏青盘面 + 金色罗盘玫瑰，夜里最好看的一款"
    desc_en = "Deep navy face with a gold compass rose. Best after dark."
    shape = "circle"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        r = w * 0.5
        hs = hand_scale(cfg)
        ds = dial_scale(cfg)

        navy_hi = QColor("#1B2C47")
        navy_lo = QColor("#0B1421")
        gold = QColor("#C9A227")
        gold_soft = QColor("#8E7420")
        bone = QColor("#F2EAD3")

        # 金属外圈
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#15171C"))
        p.drawEllipse(c, r * 0.998, r * 0.998)
        p.setPen(QPen(QColor("#3A3F4A"), max(1.0, r * 0.020)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, r * 0.930, r * 0.930)

        # 盘面：中心亮、边缘沉
        grad = QRadialGradient(c, r * 0.95)
        grad.setColorAt(0.0, navy_hi)
        grad.setColorAt(0.72, QColor("#142138"))
        grad.setColorAt(1.0, navy_lo)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(c, r * 0.905, r * 0.905)

        # 罗盘玫瑰（画在指针下面）
        for i, pts in _rose_polygons(c, r * 0.52, r * 0.30):
            p.setBrush(gold if i % 2 == 0 else gold_soft)
            p.drawPolygon(QPolygonF(pts))
        p.setPen(QPen(gold, max(0.8, r * 0.008)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, r * 0.54, r * 0.54)

        # 60 格刻度
        for i in range(60):
            ang = i * 6.0
            major = (i % 5 == 0)
            pen = QPen(bone if major else QColor(242, 234, 211, 120),
                       max(0.8, r * (0.010 if major else 0.005) * ds))
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(_polar(c, r * tick_inner(0.878, 0.812 if major else 0.836, ds, 0.66), ang),
                       _polar(c, r * 0.878, ang))

        # 四个方向只标 12/3/6/9，字体用金色
        if cfg.get("appearance.dial_style", "arabic") != "none":
            f = num_font(cfg, _num_px(r, 0.105, ds, 0.24),
                         cfg.get("appearance.font_weight", 500))
            for i in (12, 3, 6, 9):
                pt = _polar(c, r * 0.735, (i % 12) * 30.0)
                box = QRectF(pt.x() - r * 0.13, pt.y() - r * 0.13, r * 0.26, r * 0.26)
                draw_text(p, box, str(i), f, gold)

        h_ang, m_ang, s_ang = clock_angles(now, cfg)
        hand(p, c, h_ang, r * 0.44, max(1.2, r * 0.052 * hs), bone, tail=r * 0.07)
        hand(p, c, m_ang, r * 0.62, max(1.0, r * 0.034 * hs), bone, tail=r * 0.09)
        if cfg.get("content.show_seconds", True) and cfg.get("content.second_style", "tick") != "none":
            hand(p, c, s_ang, r * 0.70, max(0.8, r * 0.013 * hs), gold, tail=r * 0.16)
        dot(p, c, _hub(r, 0.032, hs, 0.075), gold)
        dot(p, c, max(1.0, r * 0.012), navy_lo)


class DotsSkin(Skin):
    id = "dots"
    name_zh = "圆点刻度"
    name_en = "Dot Dial"
    desc_zh = "60 个圆点代替刻度线，没有一条直线，柔和干净"
    desc_en = "Sixty dots instead of tick marks. No straight lines at all."
    shape = "circle"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        r = w * 0.5
        hs = hand_scale(cfg)
        ds = dial_scale(cfg)

        # 无描边盘面，直接靠底色的明度差和圆点撑起形状
        p.setPen(QPen(color(cfg, "text", 55), max(1.0, r * 0.012)))
        p.setBrush(_face_colors(cfg))
        p.drawEllipse(c, r - max(0.5, r * 0.006), r - max(0.5, r * 0.006))

        for i in range(60):
            ang = i * 6.0
            major = (i % 5 == 0)
            rad = r * (0.030 if major else 0.012) * (0.55 + 0.45 * ds)
            rad = max(0.8, rad)
            fill = color(cfg, "text", 235) if major else color(cfg, "text", 120)
            dot(p, _polar(c, r * 0.855, ang), rad, fill)

        if cfg.get("appearance.dial_style", "arabic") != "none":
            f = num_font(cfg, _num_px(r, 0.115, ds, 0.26),
                         cfg.get("appearance.font_weight", 500))
            for i in range(1, 13):
                pt = _polar(c, r * 0.690, i * 30.0)
                box = QRectF(pt.x() - r * 0.15, pt.y() - r * 0.15, r * 0.30, r * 0.30)
                draw_text(p, box, str(i), f, color(cfg, "text", 230))

        h_ang, m_ang, s_ang = clock_angles(now, cfg)
        hand(p, c, h_ang, r * 0.46, max(1.2, r * 0.048 * hs), color(cfg, "text"), tail=r * 0.08)
        hand(p, c, m_ang, r * 0.66, max(1.0, r * 0.032 * hs), color(cfg, "text"), tail=r * 0.10)
        if cfg.get("content.show_seconds", True) and cfg.get("content.second_style", "tick") != "none":
            hand(p, c, s_ang, r * 0.74, max(0.8, r * 0.012 * hs), color(cfg, "accent"), tail=r * 0.15)
        dot(p, c, _hub(r, 0.026, hs, 0.062), color(cfg, "text"))
        dot(p, c, max(1.0, r * 0.011), color(cfg, "accent"))


class PocketSkin(Skin):
    id = "pocket"
    name_zh = "怀表"
    name_en = "Pocket Watch"
    desc_zh = "象牙盘 + 衬线罗马数字 + 蓝钢针，6 点位小秒盘"
    desc_en = "Ivory face, serif Roman numerals, blued hands, seconds sub-dial at six."
    shape = "circle"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        r = w * 0.5
        hs = hand_scale(cfg)
        ds = dial_scale(cfg)

        ivory_hi = QColor("#FBF6E9")
        ivory_lo = QColor("#E6DCC3")
        steel = QColor("#8D8F94")
        blue = QColor("#2E4C7E")
        ink = QColor("#242220")

        # 抛光外壳
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#B9BCC2"))
        p.drawEllipse(c, r * 0.998, r * 0.998)
        p.setBrush(QColor("#D7D9DD"))
        p.drawEllipse(c, r * 0.960, r * 0.960)

        # 盘面
        grad = QRadialGradient(c, r * 0.90)
        grad.setColorAt(0.0, ivory_hi)
        grad.setColorAt(0.75, QColor("#F3EBD8"))
        grad.setColorAt(1.0, ivory_lo)
        p.setPen(QPen(steel, max(1.0, r * 0.010)))
        p.setBrush(QBrush(grad))
        p.drawEllipse(c, r * 0.905, r * 0.905)

        # 分钟轨
        for i in range(60):
            ang = i * 6.0
            major = (i % 5 == 0)
            pen = QPen(ink if major else QColor(60, 55, 48, 150),
                       max(0.8, r * (0.008 if major else 0.004) * ds))
            p.setPen(pen)
            p.drawLine(_polar(c, r * tick_inner(0.870, 0.838 if major else 0.856, ds, 0.70), ang),
                       _polar(c, r * 0.870, ang))

        # 衬线罗马数字
        serif = QFont("Times New Roman")
        serif.setPixelSize(max(1, int(round(_num_px(r, 0.108, ds, 0.24)))))
        serif.setWeight(QFont.Normal)
        serif.setStyleStrategy(QFont.PreferAntialias)
        for i in range(12):
            pt = _polar(c, r * 0.755, i * 30.0)
            box = QRectF(pt.x() - r * 0.15, pt.y() - r * 0.11, r * 0.30, r * 0.22)
            draw_text(p, box, ROMAN[i], serif, ink)

        h_ang, m_ang, s_ang = clock_angles(now, cfg)
        hand(p, c, h_ang, r * 0.42, max(1.2, r * 0.040 * hs), blue, tail=r * 0.07)
        hand(p, c, m_ang, r * 0.60, max(1.0, r * 0.028 * hs), blue, tail=r * 0.09)
        dot(p, c, _hub(r, 0.026, hs, 0.060), blue)

        # 6 点位小秒盘
        sub_c = QPointF(c.x(), c.y() + r * 0.34)
        sub_r = r * 0.195
        p.setPen(QPen(color(cfg, "text", 60), max(0.8, r * 0.006)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(sub_c, sub_r, sub_r)
        for i in range(0, 60, 5):
            ang = i * 6.0
            p.setPen(QPen(color(cfg, "text", 120), max(0.6, r * 0.004)))
            p.drawLine(_polar(sub_c, sub_r * tick_inner(0.86, 0.72, ds, 0.55), ang),
                       _polar(sub_c, sub_r * 0.86, ang))

        if cfg.get("content.show_seconds", True) and cfg.get("content.second_style", "tick") != "none":
            hand(p, sub_c, s_ang, sub_r * 0.78, max(0.8, r * 0.012 * hs), blue, tail=sub_r * 0.20)
            dot(p, sub_c, max(0.9, r * 0.010), blue)
        else:
            f = num_font(cfg, sub_r * 0.55, 500)
            draw_text(p, QRectF(sub_c.x() - sub_r, sub_c.y() - sub_r, sub_r * 2, sub_r * 2),
                      "%02d" % now.second, f, color(cfg, "text", 200))


class SunburstSkin(Skin):
    id = "sunburst"
    name_zh = "香槟放射"
    name_en = "Champagne Sunburst"
    desc_zh = "香槟色放射纹盘面 + 金针，随主题色变化"
    desc_en = "Champagne sunburst face with gold hands. Follows the theme colour."
    shape = "circle"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        r = w * 0.5
        hs = hand_scale(cfg)
        ds = dial_scale(cfg)

        base = color(cfg, "bg")
        accent = color(cfg, "accent")
        deep = mix(base, QColor("#000000"), 0.30) if not is_dark(base) else mix(base, QColor("#000000"), 0.35)
        light = mix(base, QColor("#FFFFFF"), 0.35)
        gold = mix(accent, QColor("#B8912F"), 0.55)
        ink = color(cfg, "text")

        # 金圈
        p.setPen(Qt.NoPen)
        p.setBrush(gold)
        p.drawEllipse(c, r * 0.998, r * 0.998)
        p.setBrush(deep)
        p.drawEllipse(c, r * 0.948, r * 0.948)

        # 盘面渐变
        grad = QRadialGradient(c, r * 0.92)
        grad.setColorAt(0.0, light)
        grad.setColorAt(0.55, base)
        grad.setColorAt(1.0, mix(base, deep, 0.55))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(c, r * 0.905, r * 0.905)

        # 72 根放射细线，深浅交替做出缎面质感
        for i in range(72):
            ang = i * 5.0
            pen = QPen(QColor(255, 255, 255, 46 if i % 2 == 0 else 0),
                       max(0.6, r * 0.006 * ds))
            p.setPen(pen)
            p.drawLine(_polar(c, r * 0.20, ang), _polar(c, r * 0.90, ang))
            pen = QPen(QColor(0, 0, 0, 26), max(0.6, r * 0.005 * ds))
            p.setPen(pen)
            p.drawLine(_polar(c, r * 0.20, ang + 2.5), _polar(c, r * 0.90, ang + 2.5))

        # 12 个金点刻度
        for i in range(12):
            ang = i * 30.0
            major = (i % 3 == 0)
            dot(p, _polar(c, r * 0.845, ang),
                max(0.9, r * (0.020 if major else 0.010) * (0.6 + 0.4 * ds)), gold)

        if cfg.get("appearance.dial_style", "arabic") != "none":
            f = num_font(cfg, _num_px(r, 0.112, ds, 0.26),
                         cfg.get("appearance.font_weight", 500))
            for i in range(1, 13):
                pt = _polar(c, r * 0.700, i * 30.0)
                box = QRectF(pt.x() - r * 0.15, pt.y() - r * 0.15, r * 0.30, r * 0.30)
                draw_text(p, box, str(i), f, ink)

        h_ang, m_ang, s_ang = clock_angles(now, cfg)
        hand(p, c, h_ang, r * 0.44, max(1.2, r * 0.046 * hs), ink, tail=r * 0.07)
        hand(p, c, m_ang, r * 0.62, max(1.0, r * 0.030 * hs), ink, tail=r * 0.09)
        if cfg.get("content.show_seconds", True) and cfg.get("content.second_style", "tick") != "none":
            hand(p, c, s_ang, r * 0.70, max(0.8, r * 0.012 * hs), gold, tail=r * 0.15)
        dot(p, c, _hub(r, 0.028, hs, 0.065), gold)
