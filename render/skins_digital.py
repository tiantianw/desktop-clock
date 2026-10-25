"""数字类皮肤：玻璃极简 / 霓虹线框 / 终端 / 三栏分割。"""

from __future__ import annotations

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPainterPath, QPen

from core import lunar
from render.base import (
    Skin, arc_clock, color, date_text, draw_text, hour_minute, hour_minute_sec,
    is_dark, meridiem, mix, num_font, round_rect, top_line, ui_font, weekday_text,
)


class GlassSkin(Skin):
    id = "glass"
    name = "玻璃极简"
    desc = "大号等宽数字 + 秒进度条，浅色壁纸上最干净"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        cx = rect.center().x()
        top = rect.top()
        show_sec = cfg.get("content.show_seconds", True)

        # 顶部日期行
        head = top_line(now, cfg)
        if head:
            f = ui_font(cfg, w * 0.056, 400)
            draw_text(p, QRectF(rect.left(), top + w * 0.115, rect.width(), w * 0.09),
                      head, f, color(cfg, "muted", 230))

        # 主时间
        text = hour_minute_sec(now, cfg) if show_sec else hour_minute(now, cfg)
        px = w * (0.190 if show_sec else 0.220)
        f = num_font(cfg, px, cfg.get("appearance.font_weight", 500))
        draw_text(p, QRectF(rect.left(), top + w * 0.32, rect.width(), w * 0.28),
                  text, f, color(cfg, "text"))

        # 秒进度条
        if show_sec and cfg.get("content.second_style", "tick") != "none":
            bar_w = w * 0.52
            bar_h = max(2.0, w * 0.014)
            x = cx - bar_w / 2.0
            y = top + w * 0.655
            track = mix(color(cfg, "text"), color(cfg, "bg"), 0.86)
            round_rect(p, QRectF(x, y, bar_w, bar_h), bar_h / 2.0, fill=track)
            ratio = now.second / 60.0
            if cfg.get("content.second_style", "tick") == "smooth":
                ratio = (now.second + now.microsecond / 1_000_000.0) / 60.0
            if ratio > 0.001:
                round_rect(p, QRectF(x, y, max(bar_h, bar_w * ratio), bar_h),
                           bar_h / 2.0, fill=color(cfg, "accent"))

        # 农历
        if cfg.get("content.show_lunar", False):
            line = lunar.lunar_line(now.date())
            if line:
                f = ui_font(cfg, w * 0.052, 400)
                draw_text(p, QRectF(rect.left(), top + w * 0.745, rect.width(), w * 0.08),
                          line, f, color(cfg, "muted", 210))


class NeonSkin(Skin):
    id = "neon"
    name = "霓虹线框"
    desc = "暗底发光圆环与数字，深色壁纸上最出彩"
    wants_own_bg = True

    def _glow_text(self, p, rect, text, font, base: QColor):
        """用描边多层递减模拟发光，避免依赖图形特效。"""
        path = QPainterPath()
        fm_h = font.pixelSize() * 1.2
        path.addText(QPointF(0, 0), font, text)
        br = path.boundingRect()
        dx = rect.center().x() - (br.left() + br.width() / 2.0)
        dy = rect.center().y() - (br.top() + br.height() / 2.0)
        path.translate(dx, dy)

        for mult, alpha in ((0.055, 26), (0.035, 52), (0.018, 96)):
            pen = QPen(QColor(base.red(), base.green(), base.blue(), alpha),
                       max(1.0, font.pixelSize() * mult))
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.strokePath(path, pen)
        p.setPen(Qt.NoPen)
        p.setBrush(base)
        p.drawPath(path)

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        accent = color(cfg, "accent")
        dark = mix(QColor("#0B0D12"), accent, 0.10)

        # 深色皮肤自带底色
        p.setPen(Qt.NoPen)
        p.setBrush(dark)
        p.drawRect(rect)

        radius = w * 0.5
        ring_w = max(2.0, w * 0.016)

        # 轨道
        p.setPen(QPen(mix(dark, accent, 0.18), ring_w))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, radius * 0.86, radius * 0.86)

        # 已过部分（按当天进度）
        total = now.hour * 3600 + now.minute * 60 + now.second
        ratio = total / 86400.0
        arc_clock(p, c, radius * 0.86, 0.0, 360.0 * ratio, accent, ring_w)

        # 刻度点
        import math
        for i in range(12):
            a = math.radians(i * 30.0)
            px = c.x() + math.sin(a) * radius * 0.70
            py = c.y() - math.cos(a) * radius * 0.70
            p.setPen(Qt.NoPen)
            p.setBrush(mix(dark, accent, 0.42 if i % 3 else 0.85))
            rr = max(1.0, w * (0.008 if i % 3 else 0.012))
            p.drawEllipse(QPointF(px, py), rr, rr)

        # 中央时间
        show_sec = cfg.get("content.show_seconds", True)
        text = hour_minute_sec(now, cfg) if show_sec else hour_minute(now, cfg)
        px_size = w * (0.135 if show_sec else 0.175)
        f = num_font(cfg, px_size, 400)
        self._glow_text(p, QRectF(c.x() - w * 0.4, c.y() - w * 0.10, w * 0.8, w * 0.20),
                        text, f, mix(accent, QColor("#FFFFFF"), 0.55))

        # 底部日期
        head = top_line(now, cfg)
        if head:
            f2 = ui_font(cfg, w * 0.048, 400)
            draw_text(p, QRectF(rect.left(), c.y() + w * 0.115, rect.width(), w * 0.07),
                      head, f2, mix(accent, QColor("#FFFFFF"), 0.30))


class TerminalSkin(Skin):
    id = "terminal"
    name = "终端"
    desc = "等宽绿字、命令行风格，带闪烁光标"
    wants_own_bg = True

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        accent = color(cfg, "accent")
        fg = mix(QColor("#00E08A"), accent, 0.45)
        dim = QColor(fg.red(), fg.green(), fg.blue(), 130)

        # 深色皮肤自带底色
        p.setPen(Qt.NoPen)
        p.setBrush(mix(QColor("#08120E"), accent, 0.07))
        p.drawRect(rect)

        left = rect.left() + w * 0.10

        # 主时间行
        text = hour_minute_sec(now, cfg) if cfg.get("content.show_seconds", True) else hour_minute(now, cfg)
        f = num_font(cfg, w * 0.145, 500)
        y_time = rect.top() + w * 0.34
        draw_text(p, QRectF(left, y_time, rect.width() * 0.86, w * 0.20),
                  text, f, fg, int(Qt.AlignLeft | Qt.AlignVCenter))

        # 光标
        if cfg.get("content.blink_cursor", True) and now.second % 2 == 0:
            fm_w = w * 0.145 * 0.60 * len(text)
            cw = max(2.0, w * 0.012)
            ch = w * 0.13
            p.setPen(Qt.NoPen)
            p.setBrush(fg)
            p.drawRect(QRectF(left + fm_w + w * 0.02, y_time + w * 0.045, cw, ch))

        # 分隔线
        p.setPen(QPen(QColor(fg.red(), fg.green(), fg.blue(), 60), max(1.0, w * 0.004)))
        p.drawLine(QPointF(left, rect.top() + w * 0.56),
                   QPointF(rect.right() - w * 0.10, rect.top() + w * 0.56))

        # 信息行
        f2 = num_font(cfg, w * 0.052, 400)
        line1 = date_text(now, cfg) + "  " + weekday_text(now, cfg)
        draw_text(p, QRectF(left, rect.top() + w * 0.60, rect.width() * 0.86, w * 0.07),
                  line1, f2, dim, int(Qt.AlignLeft | Qt.AlignVCenter))

        if cfg.get("content.show_lunar", False):
            line2 = lunar.lunar_line(now.date())
            if line2:
                draw_text(p, QRectF(left, rect.top() + w * 0.70, rect.width() * 0.86, w * 0.07),
                          line2, f2, dim, int(Qt.AlignLeft | Qt.AlignVCenter))

        # 左上角提示符
        f3 = num_font(cfg, w * 0.042, 500)
        draw_text(p, QRectF(left, rect.top() + w * 0.13, w * 0.6, w * 0.06),
                  "> clock --live", f3, QColor(fg.red(), fg.green(), fg.blue(), 150),
                  int(Qt.AlignLeft | Qt.AlignVCenter))


class SplitSkin(Skin):
    id = "split"
    name = "三栏分割"
    desc = "时 / 分 / 秒 三个独立方块，信息密度高"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        show_sec = cfg.get("content.show_seconds", True)

        margin = w * 0.06
        gap = w * 0.025
        count = 3 if show_sec else 2
        bw = (w - margin * 2 - gap * (count - 1)) / count
        bh = w * 0.46
        by = rect.top() + w * 0.20

        units = [("%02d" % now.hour, "HOUR"), ("%02d" % now.minute, "MIN")]
        if show_sec:
            units.append(("%02d" % now.second, "SEC"))

        block = mix(color(cfg, "text"), color(cfg, "bg"), 0.90)
        for i, (val, label) in enumerate(units):
            x = rect.left() + margin + i * (bw + gap)
            round_rect(p, QRectF(x, by, bw, bh), w * 0.055, fill=block)
            # 顶部强调条
            round_rect(p, QRectF(x + bw * 0.28, by, bw * 0.44, max(1.6, w * 0.010)),
                       w * 0.005, fill=color(cfg, "accent"))
            f = num_font(cfg, bw * 0.58, cfg.get("appearance.font_weight", 500))
            draw_text(p, QRectF(x, by + bh * 0.06, bw, bh * 0.88), val, f, color(cfg, "text"))
            fl = ui_font(cfg, w * 0.036, 400)
            draw_text(p, QRectF(x, by + bh + w * 0.025, bw, w * 0.05),
                      label, fl, color(cfg, "muted", 235))

        # 顶部日期
        head = top_line(now, cfg)
        if head:
            f = ui_font(cfg, w * 0.048, 400)
            draw_text(p, QRectF(rect.left(), rect.top() + w * 0.10, rect.width(), w * 0.08),
                      head, f, color(cfg, "muted", 220))

        if cfg.get("content.show_lunar", False):
            line = lunar.lunar_line(now.date())
            if line:
                f = ui_font(cfg, w * 0.044, 400)
                draw_text(p, QRectF(rect.left(), by + bh + w * 0.085, rect.width(), w * 0.07),
                          line, f, color(cfg, "muted", 180))
