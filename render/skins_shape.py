"""图形类皮肤：同心圆环 / 分段刻度环 / 机械翻页 / 世界时钟。"""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPen

from core import lunar, timezones
from render.base import (
    Skin, arc_clock, color, date_text, draw_text, hour_minute, hour_minute_sec,
    is_dark, mix, num_font, round_rect, top_line, ui_font, weekday_text,
)


class RingSkin(Skin):
    id = "ring"
    name = "同心圆环"
    desc = "三段圆弧分别表示时 / 分 / 秒，中心读数字"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        accent = color(cfg, "accent")
        text = color(cfg, "text")
        track = mix(text, color(cfg, "bg"), 0.88)
        lw = max(2.0, w * 0.024)

        show_sec = cfg.get("content.show_seconds", True)
        rings = [
            (0.455, (now.hour * 3600 + now.minute * 60 + now.second) / 86400.0, mix(accent, text, 0.55)),
            (0.375, (now.minute * 60 + now.second) / 60.0 / 60.0, mix(accent, text, 0.25)),
        ]
        if show_sec:
            sec_ratio = now.second / 60.0
            if cfg.get("content.second_style", "tick") == "smooth":
                sec_ratio = (now.second + now.microsecond / 1_000_000.0) / 60.0
            rings.append((0.295, sec_ratio, accent))

        for radius, ratio, col in rings:
            p.setPen(QPen(track, lw))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(c, w * radius, w * radius)
            if ratio > 0.002:
                arc_clock(p, c, w * radius, 0.0, 360.0 * min(1.0, ratio), col, lw)

        # 中心时间
        txt = hour_minute_sec(now, cfg) if show_sec else hour_minute(now, cfg)
        px = w * (0.092 if show_sec else 0.135)
        f = num_font(cfg, px, cfg.get("appearance.font_weight", 500))
        draw_text(p, QRectF(c.x() - w * 0.3, c.y() - w * 0.09, w * 0.6, w * 0.18), txt, f, text)

        if cfg.get("content.show_lunar", False):
            line = lunar.lunar_line(now.date())
            if line:
                f2 = ui_font(cfg, w * 0.042, 400)
                draw_text(p, QRectF(c.x() - w * 0.3, c.y() + w * 0.105, w * 0.6, w * 0.06),
                          line, f2, color(cfg, "muted", 200))


class SegmentSkin(Skin):
    id = "segment"
    name = "分段刻度环"
    desc = "60 格刻度环，已走过的秒逐格点亮"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        accent = color(cfg, "accent")
        text = color(cfg, "text")

        r_out = w * 0.455
        r_in = w * 0.355
        bw = w * 0.030
        sec = now.second
        if cfg.get("content.second_style", "tick") == "smooth":
            sec = now.second + now.microsecond / 1_000_000.0

        for i in range(60):
            p.save()
            p.translate(c)
            p.rotate(i * 6.0)
            active = i <= sec
            if active:
                col = accent if i == int(sec) else mix(accent, color(cfg, "bg"), 0.35)
            else:
                col = mix(text, color(cfg, "bg"), 0.86)
            round_rect(p, QRectF(-bw / 2.0, -r_out, bw, r_out - r_in), bw * 0.45, fill=col)
            p.restore()

        # 中心时间
        txt = hour_minute(now, cfg)
        f = num_font(cfg, w * 0.155, cfg.get("appearance.font_weight", 500))
        draw_text(p, QRectF(c.x() - w * 0.3, c.y() - w * 0.105, w * 0.6, w * 0.17), txt, f, text)

        head = top_line(now, cfg)
        if head:
            f2 = ui_font(cfg, w * 0.042, 400)
            draw_text(p, QRectF(c.x() - w * 0.3, c.y() + w * 0.105, w * 0.6, w * 0.06),
                      head, f2, color(cfg, "muted", 210))


class FlipSkin(Skin):
    id = "flip"
    name = "机械翻页"
    desc = "深色翻页卡片，经典机场翻牌钟质感"
    wants_own_bg = True

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        accent = color(cfg, "accent")
        base = mix(QColor("#17171B"), accent, 0.05)
        card_top = mix(QColor("#34343D"), accent, 0.05)
        card_bot = mix(QColor("#1E1E24"), accent, 0.05)
        digit = QColor("#F6F2E9")

        p.setPen(Qt.NoPen)
        p.setBrush(base)
        p.drawRect(rect)

        bw = w * 0.335
        bh = w * 0.44
        gap = w * 0.068
        total = bw * 2 + gap
        x0 = rect.center().x() - total / 2.0
        y0 = rect.top() + w * 0.155
        radius = w * 0.045

        halves = [("%02d" % now.hour, x0), ("%02d" % now.minute, x0 + bw + gap)]
        for val, x in halves:
            mid = y0 + bh / 2.0
            round_rect(p, QRectF(x, y0, bw, bh / 2.0), radius, fill=card_top)
            round_rect(p, QRectF(x, mid, bw, bh / 2.0), radius, fill=card_bot)
            # 上半遮掉下圆角，下半遮掉上圆角，形成整块
            p.setPen(Qt.NoPen)
            p.setBrush(card_top)
            p.drawRect(QRectF(x, mid - radius, bw, radius))
            p.setBrush(card_bot)
            p.drawRect(QRectF(x, mid, bw, radius))
            # 铰链
            p.setBrush(QColor(0, 0, 0, 150))
            p.drawRect(QRectF(x, mid - max(1.0, w * 0.006), bw, max(2.0, w * 0.012)))

            f = num_font(cfg, bw * 0.72, 500)
            draw_text(p, QRectF(x, y0, bw, bh), val, f, digit)

        # 分隔冒号（框要比 gap 宽，否则 Qt 会省略不画）
        f_colon = num_font(cfg, bw * 0.36, 500)
        draw_text(p, QRectF(x0 + bw - w * 0.03, y0, gap + w * 0.06, bh),
                  ":", f_colon, QColor(246, 242, 233, 155))

        # 底部信息
        info = date_text(now, cfg)
        wd = weekday_text(now, cfg)
        if wd:
            info = wd + "  " + info
        if cfg.get("content.show_lunar", False):
            line = lunar.lunar_line(now.date())
            if line:
                info = info + "  " + line
        f2 = ui_font(cfg, w * 0.046, 400)
        draw_text(p, QRectF(rect.left(), y0 + bh + w * 0.055, rect.width(), w * 0.07),
                  info, f2, QColor(246, 242, 233, 150))

        # 秒：底部细进度
        if cfg.get("content.show_seconds", True):
            bar_w = w * 0.34
            bar_h = max(2.0, w * 0.010)
            x = rect.center().x() - bar_w / 2.0
            y = y0 + bh + w * 0.135
            round_rect(p, QRectF(x, y, bar_w, bar_h), bar_h / 2.0, fill=QColor(255, 255, 255, 30))
            ratio = now.second / 60.0
            if ratio > 0.002:
                round_rect(p, QRectF(x, y, max(bar_h, bar_w * ratio), bar_h), bar_h / 2.0, fill=accent)


class WorldSkin(Skin):
    id = "world"
    name = "世界时钟"
    desc = "主时间 + 最多 4 个城市，出差跨时区必备"

    def draw(self, p, rect, now, cfg):
        w = min(rect.width(), rect.height())
        c = rect.center()
        text = color(cfg, "text")
        muted = color(cfg, "muted")

        show_sec = cfg.get("content.show_seconds", True)
        txt = hour_minute_sec(now, cfg) if show_sec else hour_minute(now, cfg)
        px = w * (0.128 if show_sec else 0.180)
        f = num_font(cfg, px, cfg.get("appearance.font_weight", 500))
        draw_text(p, QRectF(rect.left(), rect.top() + w * 0.115, rect.width(), w * 0.20),
                  txt, f, text)

        # 本地日期行
        head = top_line(now, cfg)
        f2 = ui_font(cfg, w * 0.046, 400)
        draw_text(p, QRectF(rect.left(), rect.top() + w * 0.315, rect.width(), w * 0.06),
                  head, f2, muted)

        # 分隔线
        p.setPen(QPen(mix(text, color(cfg, "bg"), 0.82), max(1.0, w * 0.004)))
        p.drawLine(QPointF(rect.left() + w * 0.12, rect.top() + w * 0.405),
                   QPointF(rect.right() - w * 0.12, rect.top() + w * 0.405))

        keys = cfg.get("content.sub_timezones") or []
        keys = [k for k in keys if k in timezones.CITY_MAP][:4]
        if not keys:
            keys = timezones.DEFAULT_CITIES[:3]

        row_h = w * 0.105
        y = rect.top() + w * 0.455
        f_name = ui_font(cfg, w * 0.046, 400)
        f_time = num_font(cfg, w * 0.052, 400)
        for key in keys:
            label = timezones.city_label(key)
            abbr = timezones.city_abbr(key)
            tval = timezones.format_city_time(key, now, cfg.get("content.hour24", True))
            box = QRectF(rect.left() + w * 0.13, y, rect.width() * 0.74, row_h)
            draw_text(p, box, label + "  " + abbr, f_name, muted, int(Qt.AlignLeft | Qt.AlignVCenter))
            draw_text(p, box, tval, f_time, text, int(Qt.AlignRight | Qt.AlignVCenter))
            y += row_h
