"""皮肤基类与通用绘制工具。

约定：
- rect 为内容区域（不含窗口阴影留白），皮肤自行按 rect 比例排版。
- 皮肤不负责窗口阴影与圆角裁剪，那是窗口层的事。
- wants_own_bg=True 的皮肤自己画底色（深色皮肤），此时窗口不再铺背景。
"""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen

from core import i18n


# ---------------------------------------------------------------- 颜色与字体

def qt_weight(css_weight: float) -> int:
    """CSS 字重(100-900) 映射到 Qt5 的 0-99 刻度。"""
    try:
        return max(0, min(99, int(round(float(css_weight) * 99.0 / 900.0))))
    except Exception:
        return 55


def qcolor(value: str, alpha: int | None = None) -> QColor:
    c = QColor(value)
    if not c.isValid():
        c = QColor("#000000")
    if alpha is not None:
        c.setAlpha(max(0, min(255, int(alpha))))
    return c


def color(cfg, key: str, alpha: int | None = None) -> QColor:
    mapping = {
        "text": "appearance.text_color",
        "muted": "appearance.muted_color",
        "accent": "appearance.accent",
        "bg": "appearance.bg_color",
        "border": "appearance.border_color",
    }
    raw = cfg.get(mapping.get(key, "appearance.text_color"), "#000000")
    return qcolor(raw, alpha)


def num_font(cfg, px: float, weight: float | None = None) -> QFont:
    """数字字体：用用户设定的等宽字体。"""
    f = QFont(cfg.get("appearance.font_family", "Consolas"))
    f.setPixelSize(max(1, int(round(px))))
    f.setWeight(qt_weight(weight if weight is not None else cfg.get("appearance.font_weight", 500)))
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


def ui_font(cfg, px: float, weight: float = 400) -> QFont:
    """中文界面字体：Consolas 没有中文字形，中文单独用雅黑保证观感。"""
    f = QFont("Microsoft YaHei UI")
    f.setPixelSize(max(1, int(round(px))))
    f.setWeight(qt_weight(weight))
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


def mix(c1: QColor, c2: QColor, t: float) -> QColor:
    """线性混合两个颜色，t=0 取 c1，t=1 取 c2。"""
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
        int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
    )


def is_dark(c: QColor) -> bool:
    return (c.red() * 299 + c.green() * 587 + c.blue() * 114) / 1000.0 < 128


# ---------------------------------------------------------------- 比例倍数

SCALE_MIN = 0.5
SCALE_MAX = 3.0


def _scale(cfg, path: str) -> float:
    """读取 0.5–3.0 的倍数设置，非法值一律回落到 1.0。"""
    try:
        v = float(cfg.get(path, 1.0))
    except Exception:
        return 1.0
    if v != v:  # NaN
        return 1.0
    return max(SCALE_MIN, min(SCALE_MAX, v))


def hand_scale(cfg) -> float:
    """指针粗细倍数：只作用于时针/分针/秒针的线宽与中心轴帽。"""
    return _scale(cfg, "appearance.hand_scale")


def dial_scale(cfg) -> float:
    """表盘倍数：作用于刻度线的宽度与长度、以及表盘数字的字号。"""
    return _scale(cfg, "appearance.dial_scale")


def tick_inner(outer: float, inner: float, ds: float, floor: float = 0.58) -> float:
    """按 ds 倍数把刻度往里延长，但不越过 floor 半径，免得戳到数字上。"""
    return max(floor, outer - (outer - inner) * ds)



# ---------------------------------------------------------------- 绘制工具

def draw_text(p: QPainter, rect: QRectF, text: str, font: QFont, fill: QColor,
              align=Qt.AlignCenter) -> None:
    p.setFont(font)
    p.setPen(fill)
    p.drawText(rect, int(align), text)


def round_rect(p: QPainter, rect: QRectF, radius: float,
               fill: QColor | None = None, stroke: QColor | None = None,
               width: float = 1.0) -> None:
    p.setPen(QPen(stroke, width) if stroke is not None else Qt.NoPen)
    p.setBrush(fill if fill is not None else Qt.NoBrush)
    p.drawRoundedRect(rect, radius, radius)


def arc_clock(p: QPainter, center: QPointF, radius: float,
              start_deg: float, span_deg: float, stroke: QColor,
              width: float, round_cap: bool = True) -> None:
    """按钟表角度画弧：0 度指向 12 点，正角度顺时针。"""
    pen = QPen(stroke, width)
    pen.setCapStyle(Qt.RoundCap if round_cap else Qt.FlatCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
    p.drawArc(rect, int((90.0 - start_deg) * 16), int(-span_deg * 16))


def hand(p: QPainter, center: QPointF, angle_deg: float, length: float,
         width: float, stroke: QColor, tail: float = 0.0,
         round_cap: bool = True) -> None:
    """画指针：angle 0 指向 12 点，顺时针。tail 为尾部长度（可指向反方向）。"""
    p.save()
    p.translate(center)
    p.rotate(angle_deg)
    pen = QPen(stroke, width)
    pen.setCapStyle(Qt.RoundCap if round_cap else Qt.FlatCap)
    p.setPen(pen)
    p.drawLine(QPointF(0, tail), QPointF(0, -length))
    p.restore()


def dot(p: QPainter, center: QPointF, radius: float, fill: QColor) -> None:
    p.setPen(Qt.NoPen)
    p.setBrush(fill)
    p.drawEllipse(center, radius, radius)


def clock_angles(now, cfg):
    """返回 (时针角度, 分针角度, 秒针角度)，秒可含小数实现平滑扫秒。"""
    sec_style = cfg.get("content.second_style", "tick")
    if sec_style == "smooth":
        sec = now.second + now.microsecond / 1_000_000.0
    else:
        sec = float(now.second)
    minute = now.minute + sec / 60.0
    hour = (now.hour % 12) + minute / 60.0
    return hour * 30.0, minute * 6.0, sec * 6.0


# ---------------------------------------------------------------- 时间文本

WEEKDAY_FULL = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
WEEKDAY_SHORT = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEKDAY_EN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
WEEKDAY_SHORT_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAY_FULL_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                   "Saturday", "Sunday"]
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def hour_minute(now, cfg) -> str:
    if cfg.get("content.hour24", True):
        return "%02d:%02d" % (now.hour, now.minute)
    h = now.hour % 12
    if h == 0:
        h = 12
    return "%02d:%02d" % (h, now.minute)


def hour_minute_sec(now, cfg) -> str:
    base = hour_minute(now, cfg)
    if cfg.get("content.show_seconds", True):
        return "%s:%02d" % (base, now.second)
    return base


def meridiem(now) -> str:
    return "AM" if now.hour < 12 else "PM"


def date_text(now, cfg) -> str:
    fmt = cfg.get("content.date_format", "MM月DD日")
    # 默认格式是中文的「10月25日」，英文界面下换成「Oct 25」
    if i18n.is_en() and "月" in fmt:
        return "%s %d" % (MONTHS_EN[now.month - 1], now.day)
    try:
        return fmt.replace("YYYY", "%04d" % now.year) \
                  .replace("MM", "%02d" % now.month) \
                  .replace("DD", "%02d" % now.day)
    except Exception:
        return "%02d月%02d日" % (now.month, now.day)


def weekday_text(now, cfg) -> str:
    mode = cfg.get("content.show_weekday", "short")
    if mode == "none":
        return ""
    if i18n.is_en():
        if mode == "full":
            return WEEKDAY_FULL_EN[now.weekday()]
        if mode == "en":
            return WEEKDAY_EN[now.weekday()]
        return WEEKDAY_SHORT_EN[now.weekday()]
    if mode == "full":
        return WEEKDAY_FULL[now.weekday()]
    if mode == "en":
        return WEEKDAY_EN[now.weekday()]
    return WEEKDAY_SHORT[now.weekday()]


def top_line(now, cfg) -> str:
    """「周日 · 10月25日」这类顶部小字。"""
    parts = []
    wd = weekday_text(now, cfg)
    if wd:
        parts.append(wd)
    parts.append(date_text(now, cfg))
    return " · ".join(parts)


# ---------------------------------------------------------------- 基类

class Skin:
    id = "base"
    name_zh = "基础"
    name_en = "Base"
    desc_zh = ""
    desc_en = ""
    wants_own_bg = False
    # "rect" 铺满整个内容区的圆角卡片；"circle" 只画圆形表盘，圆外完全透明
    shape = "rect"

    @property
    def name(self) -> str:
        return self.name_en if i18n.is_en() else self.name_zh

    @property
    def desc(self) -> str:
        return self.desc_en if i18n.is_en() else self.desc_zh

    def draw(self, p: QPainter, rect: QRectF, now, cfg) -> None:
        raise NotImplementedError

    # 供设置面板展示
    def sample_theme(self) -> str:
        return "warm"
