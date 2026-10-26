"""时钟主窗口：无边框透明窗口、自绘阴影、拖动缩放、三档层级。"""

from __future__ import annotations

import datetime
import time

from PyQt5.QtCore import QPoint, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPainterPath
from PyQt5.QtWidgets import QApplication, QMenu, QWidget

from core import i18n
from core.i18n import t
from core.logger import log, log_exception
from render import registry
from render.base import color, is_dark
from sysint import win32

MARGIN = 26  # 窗口为阴影预留的透明边距（大尺寸下的上限，小尺寸会按比例收缩）

MENU_QSS = """
QMenu {
    background: #FFFFFF;
    border: 1px solid #E3DACA;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    padding: 6px 26px 6px 12px;
    border-radius: 5px;
    color: #2C2C2A;
    font-size: 12px;
}
QMenu::item:selected { background: #F3EDE2; }
QMenu::item:disabled { color: #B4B2A9; }
QMenu::separator { height: 1px; background: #EFE9DE; margin: 5px 8px; }
QMenu::indicator { width: 12px; height: 12px; }
"""


class ClockWindow(QWidget):
    request_settings = pyqtSignal()
    request_language = pyqtSignal()
    request_quit = pyqtSignal()
    request_rebuild = pyqtSignal()

    def __init__(self, cfg):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.cfg = cfg
        self._size = int(cfg.get("geometry.size", 140))
        self._margin = MARGIN
        self._dragging = False
        self._drag_offset = QPoint()
        self._last_key = None
        self._hwnd = 0
        self._blur_on = False
        self._hotkeys = None
        self._beat = time.time()        # 事件循环是否还活着
        self._last_tick = time.time()   # 时钟刷新定时器上次触发
        self._born = time.time()

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        self.setWindowTitle("DesktopClock")

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._tick)

        # 存活心跳：只证明事件循环还在转，与「显不显示秒」无关
        self._alive = QTimer(self)
        self._alive.setInterval(1000)
        self._alive.timeout.connect(self._beat_once)
        self._alive.start()

        # 卡死自愈：事件循环恢复正常后发现时钟停摆，强制重启定时器
        self._watchdog = QTimer(self)
        self._watchdog.setInterval(2500)
        self._watchdog.timeout.connect(self._check_stall)
        self._watchdog.start()

        self.apply_size(self._size, keep_pos=False)
        self._restore_position()
        self._restart_timer()

    # ------------------------------------------------------------ 存活监控

    def _beat_once(self) -> None:
        self._beat = time.time()

    def _check_stall(self) -> None:
        """时钟刷新定时器停摆就记一笔并重启它。

        注意这里看的是 _last_tick（刷新定时器），不是 _beat（事件循环心跳）。
        线上遇到过事件循环完全正常、窗口也在，但刷新定时器不再触发的情况，
        只看心跳是发现不了的。
        """
        try:
            # 刚启动时事件循环还没跑起来，别误报
            if time.time() - self._born < 15.0:
                self._last_tick = time.time()
                return
            expected = max(0.033, self._timer.interval() / 1000.0)
            gap = time.time() - self._last_tick
            if gap <= expected * 2.5 + 3.0:
                return
            log("!! 刷新停摆 %.1fs，重启定时器 skin=%s layer=%s 定时器激活=%s 间隔=%dms"
                % (gap, self.cfg.get("skin"), self.cfg.get("layer"),
                   self._timer.isActive(), self._timer.interval()))
            self._last_tick = time.time()
            self._timer.stop()
            self._restart_timer()
            self.update()
        except Exception:
            log_exception("check_stall")

    # ------------------------------------------------------------ 尺寸与位置

    def apply_size(self, size: int, keep_pos: bool = True) -> None:
        size = max(80, min(600, int(size)))
        self._size = size
        # 小尺寸下阴影留白按比例收缩，否则 140px 的表盘会被 26px 边距撑得很难看
        self._margin = int(max(8, min(MARGIN, round(size * 0.11))))
        old_center = self.geometry().center() if keep_pos else None
        total = size + self._margin * 2
        self.setFixedSize(total, total)
        if old_center is not None:
            self.move(old_center.x() - total // 2, old_center.y() - total // 2)
        self._apply_blur()
        self.update()

    def _restore_position(self) -> None:
        x = self.cfg.get("geometry.x")
        y = self.cfg.get("geometry.y")
        if x is None or y is None:
            self._move_to_default_corner()
            return
        screen = QApplication.screenAt(QPoint(int(x), int(y))) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        # 防止上次位置落在已断开的显示器上
        if not area.contains(QPoint(int(x), int(y))):
            self._move_to_default_corner()
        else:
            self.move(int(x), int(y))

    def _move_to_default_corner(self) -> None:
        area = QApplication.primaryScreen().availableGeometry()
        self.move(area.right() - self.width() - 40, area.top() + 40)

    def reset_position(self) -> None:
        self._move_to_default_corner()
        self._save_geometry()

    def _save_geometry(self) -> None:
        self.cfg.set("geometry.x", self.x())
        self.cfg.set("geometry.y", self.y())
        self.cfg.set("geometry.size", self._size)
        self.cfg.save()

    # ------------------------------------------------------------ 绘制

    def _content_rect(self) -> QRectF:
        m = self._margin
        return QRectF(m, m, self.width() - m * 2, self.height() - m * 2)

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setRenderHint(QPainter.TextAntialiasing, True)
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)

            content = self._content_rect()
            skin = registry.get_skin(self.cfg.get("skin", "glass"))
            circle = getattr(skin, "shape", "rect") == "circle"
            # 圆形皮肤：把圆角半径顶到半边宽，圆角矩形就退化成正圆，
            # 背景和投影都自然变成圆形，圆外不再有任何着色。
            if circle:
                radius = content.width() / 2.0
            else:
                radius = float(self.cfg.get("appearance.radius", 18))

            self._paint_shadow(p, content, radius)
            if not skin.wants_own_bg:
                self._paint_background(p, content, radius, circle)

            p.save()
            if circle:
                # 注意不要裁成圆：Qt 的裁剪路径是硬边的，会把表盘边缘啃出锯齿。
                # 皮肤自己画的圆正好内切于内容区，只按方框裁掉溢出即可。
                p.setClipRect(content)
            else:
                path = QPainterPath()
                path.addRoundedRect(content, radius, radius)
                p.setClipPath(path)
            skin.draw(p, content, datetime.datetime.now(), self.cfg)
            p.restore()
            p.end()
        except Exception:
            log_exception("paintEvent")

    def _paint_shadow(self, p: QPainter, rect: QRectF, radius: float) -> None:
        if not self.cfg.get("appearance.shadow", True):
            return
        strength = float(self.cfg.get("appearance.shadow_strength", 20))
        if strength <= 0:
            return
        # 阴影不能超出窗口留白，否则小尺寸下会被裁成硬边
        limit = max(2.0, self._margin - 2.0)
        strength = min(strength, limit)
        layers = 12
        per_alpha = max(2, int(strength * 0.22))
        p.setPen(Qt.NoPen)
        for i in range(layers, 0, -1):
            grow = strength * i / layers
            p.setBrush(QColor(0, 0, 0, per_alpha))
            p.drawRoundedRect(rect.adjusted(-grow, -grow, grow, grow),
                              radius + grow, radius + grow)

    def _paint_background(self, p: QPainter, rect: QRectF, radius: float,
                          circle: bool = False) -> None:
        mode = self.cfg.get("appearance.bg_mode", "solid")
        if mode == "none":
            return
        if mode == "blur" and circle:
            # 模糊作用于整个窗口矩形，圆形皮肤下会糊出一个方块，退回填充
            mode = "solid"
        bg = color(self.cfg, "bg")
        opacity = int(self.cfg.get("appearance.bg_opacity", 92))
        if mode == "blur":
            opacity = min(opacity, 55)
        bg.setAlpha(max(0, min(255, int(opacity * 255 / 100))))
        p.setBrush(bg)
        if self.cfg.get("appearance.border", True):
            p.setPen(color(self.cfg, "border", 150))
            r = max(0.0, radius - 0.5)
            p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), r, r)
        else:
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(rect, radius, radius)

    # ------------------------------------------------------------ 定时刷新

    def _restart_timer(self) -> None:
        # 心跳频率跟着刷新频率走：不显示秒时没必要每秒唤醒进程
        try:
            self._alive.setInterval(1000 if self.cfg.get("content.show_seconds", True) else 15000)
        except Exception:
            pass
        self._schedule_next()

    def _schedule_next(self) -> None:
        """把下次重绘对齐到时间变化的边界，避免无意义的高频唤醒。"""
        try:
            show_sec = self.cfg.get("content.show_seconds", True)
            style = self.cfg.get("content.second_style", "tick")
            if show_sec and style == "smooth":
                self._timer.start(33)
                return
            now = datetime.datetime.now()
            if show_sec:
                # 距下一个整秒的毫秒数
                delay = 1000 - now.microsecond // 1000
            else:
                # 不显示秒时每分钟刷新一次即可
                delay = 60000 - (now.second * 1000 + now.microsecond // 1000)
            self._timer.start(max(20, int(delay) + 6))
        except Exception:
            log_exception("schedule_next")
            self._timer.start(1000)

    def _tick(self) -> None:
        self._last_tick = time.time()
        try:
            self.update()
        except Exception:
            log_exception("tick")
        finally:
            self._schedule_next()

    # ------------------------------------------------------------ 交互

    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                if self.cfg.get("behavior.lock_position", False):
                    return
                self._dragging = True
                self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
        except Exception:
            log_exception("mousePressEvent")

    def mouseMoveEvent(self, event):
        try:
            if self._dragging:
                self.move(event.globalPos() - self._drag_offset)
        except Exception:
            log_exception("mouseMoveEvent")

    def mouseReleaseEvent(self, event):
        try:
            if self._dragging:
                self._dragging = False
                if self.cfg.get("behavior.edge_snap", True):
                    self._snap_to_edge()
                self._save_geometry()
        except Exception:
            log_exception("mouseReleaseEvent")

    def mouseDoubleClickEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                new_value = not self.cfg.get("content.hour24", True)
                self.cfg.set("content.hour24", new_value)
                self.cfg.save()
                self.update()
        except Exception:
            log_exception("mouseDoubleClickEvent")

    def wheelEvent(self, event):
        try:
            delta = event.angleDelta().y()
            if delta == 0:
                return
            step = 14 if delta > 0 else -14
            self.apply_size(self._size + step)
            self.cfg.set("geometry.size", self._size)
            self.cfg.save()
        except Exception:
            log_exception("wheelEvent")

    def _snap_to_edge(self) -> None:
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        threshold = 20
        x, y = self.x(), self.y()
        if abs(x - area.left()) < threshold:
            x = area.left()
        if abs(area.right() - (x + self.width())) < threshold:
            x = area.right() - self.width()
        if abs(y - area.top()) < threshold:
            y = area.top()
        if abs(area.bottom() - (y + self.height())) < threshold:
            y = area.bottom() - self.height()
        self.move(x, y)

    def contextMenuEvent(self, event):
        try:
            # 用 popup 而不是 exec_：exec_ 会开一个嵌套事件循环，
            # 在菜单回调里重建窗口（切层级）等于在嵌套循环里销毁菜单的父对象，
            # 属于未定义行为，轻则卡死重则崩溃。
            old = getattr(self, "_menu", None)
            if old is not None:
                old.close()
                old.deleteLater()
            self._menu = self.build_menu()
            self._menu.popup(event.globalPos())
        except Exception:
            log_exception("contextMenuEvent")

    # ------------------------------------------------------------ 菜单

    def build_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet(MENU_QSS)

        skin_menu = menu.addMenu(t("皮肤", "Skin"))
        skin_menu.setStyleSheet(MENU_QSS)
        current_skin = self.cfg.get("skin", "glass")
        for sid, name in registry.skin_choices():
            act = skin_menu.addAction(name)
            act.setCheckable(True)
            act.setChecked(sid == current_skin)
            act.triggered.connect(lambda _=False, s=sid: self.set_skin(s))

        layer_menu = menu.addMenu(t("层级", "Layer"))
        layer_menu.setStyleSheet(MENU_QSS)
        current_layer = self.cfg.get("layer", "topmost")
        for key, label in i18n.layer_choices():
            act = layer_menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(key == current_layer)
            act.triggered.connect(lambda _=False, k=key: self.set_layer(k))

        menu.addSeparator()
        sec_act = menu.addAction(t("显示秒", "Show seconds"))
        sec_act.setCheckable(True)
        sec_act.setChecked(self.cfg.get("content.show_seconds", True))
        sec_act.triggered.connect(lambda checked: self._toggle("content.show_seconds", checked))

        h24_act = menu.addAction(t("24 小时制", "24-hour clock"))
        h24_act.setCheckable(True)
        h24_act.setChecked(self.cfg.get("content.hour24", True))
        h24_act.triggered.connect(lambda checked: self._toggle("content.hour24", checked))

        lunar_act = menu.addAction(t("显示农历/节气", "Show lunar date / solar term"))
        lunar_act.setCheckable(True)
        lunar_act.setChecked(self.cfg.get("content.show_lunar", False))
        lunar_act.triggered.connect(lambda checked: self._toggle("content.show_lunar", checked))

        menu.addSeparator()
        lock_act = menu.addAction(t("锁定位置", "Lock position"))
        lock_act.setCheckable(True)
        lock_act.setChecked(self.cfg.get("behavior.lock_position", False))
        lock_act.triggered.connect(lambda checked: self._toggle("behavior.lock_position", checked))

        through_act = menu.addAction(t("点击穿透", "Click-through"))
        through_act.setCheckable(True)
        through_act.setChecked(self.cfg.get("behavior.click_through", False))
        through_act.triggered.connect(lambda checked: self._toggle("behavior.click_through", checked))

        menu.addSeparator()
        menu.addAction(t("设置…", "Settings…")).triggered.connect(self.request_settings.emit)
        menu.addAction(t("重置到右上角", "Reset to top-right")).triggered.connect(self.reset_position)
        menu.addSeparator()
        menu.addAction(t("退出", "Quit")).triggered.connect(self.request_quit.emit)
        return menu

    def _toggle(self, path: str, value) -> None:
        try:
            self.cfg.set(path, value)
            self.cfg.save()
            self.apply_config()
        except Exception:
            log_exception("toggle")

    # ------------------------------------------------------------ 配置应用

    def set_skin(self, skin_id: str) -> None:
        try:
            self.cfg.set("skin", skin_id)
            self.cfg.save()
            self.update()
        except Exception:
            log_exception("set_skin")

    def set_layer(self, layer: str) -> None:
        """切换层级。

        桌面挂件层要用 SetParent 改父窗口，这会破坏 Qt 的透明表面，
        切回来时无法恢复，所以只要涉及 desktop 档就重建窗口。
        """
        old = self.cfg.get("layer", "topmost")
        self.cfg.set("layer", layer)
        self.cfg.save()
        if old == "desktop" or layer == "desktop":
            self.request_rebuild.emit()
        else:
            self.apply_layer()

    def apply_config(self) -> None:
        """设置面板任何改动后调用，立即生效。"""
        try:
            new_size = int(self.cfg.get("geometry.size", 220))
            if new_size != self._size:
                self.apply_size(new_size)
            self._restart_timer()
            self.apply_click_through()
            self._apply_blur()
            self.update()
        except Exception:
            log_exception("apply_config")

    # ------------------------------------------------------------ Win32 集成

    def showEvent(self, event):
        super().showEvent(event)
        try:
            if not self._hwnd:
                self._hwnd = win32.hwnd_of(self)
                win32.set_tool_window(self._hwnd)
            self.apply_layer()
            self._apply_blur()
            self.apply_click_through()
        except Exception:
            log_exception("showEvent")

    def apply_layer(self) -> None:
        """应用层级：置顶 / 普通 / 桌面挂件。"""
        try:
            if not self._hwnd:
                self._hwnd = win32.hwnd_of(self)
            if not self._hwnd:
                return
            layer = self.cfg.get("layer", "topmost")
            pos = self.pos()
            self._last_pos = QPoint(pos.x(), pos.y())
            w, h = self.width(), self.height()

            win32.detach_from_desktop(self._hwnd, pos.x(), pos.y(), w, h)
            if layer == "desktop":
                ok = win32.attach_to_desktop(self._hwnd, pos.x(), pos.y(), w, h)
                if not ok:
                    # 桌面层挂载失败，降级为置顶
                    win32.set_topmost(self._hwnd)
                    self.cfg.set("layer", "topmost")
                    self.cfg.save()
            elif layer == "topmost":
                win32.set_topmost(self._hwnd)
            else:
                win32.set_normal(self._hwnd)
            # 改父窗口后 Qt 的坐标需要重新校正
            QTimer.singleShot(40, self._reposition_after_layer)
        except Exception:
            log_exception("apply_layer")

    def _reposition_after_layer(self) -> None:
        try:
            pos = getattr(self, "_last_pos", None)
            if pos is not None:
                self.move(pos)
            self.raise_()
            self._apply_blur()
            self.update()
        except Exception:
            log_exception("reposition_after_layer")

    def _apply_blur(self) -> None:
        try:
            if not self._hwnd:
                return
            skin = registry.get_skin(self.cfg.get("skin", "glass"))
            circle = getattr(skin, "shape", "rect") == "circle"
            want = self.cfg.get("appearance.bg_mode", "solid") == "blur" and not circle
            if want == self._blur_on:
                return
            abgr = win32.hex_to_abgr(self.cfg.get("appearance.bg_color", "#FAF6EE"), 0xAA)
            win32.set_blur(self._hwnd, want, abgr)
            self._blur_on = want
        except Exception:
            log_exception("apply_blur")

    def apply_click_through(self) -> None:
        try:
            if not self._hwnd:
                return
            win32.set_click_through(self._hwnd, bool(self.cfg.get("behavior.click_through", False)))
        except Exception:
            log_exception("apply_click_through")

    def guard_topmost(self) -> None:
        """周期性校验置顶状态，防止被其它置顶窗口挤下去。"""
        try:
            if self.cfg.get("layer") != "topmost":
                return
            if not self.cfg.get("behavior.topmost_guard", True):
                return
            if self._hwnd and not win32.is_topmost(self._hwnd):
                win32.set_topmost(self._hwnd)
        except Exception:
            log_exception("guard_topmost")

    def cycle_layer(self) -> None:
        order = ["topmost", "normal", "desktop"]
        current = self.cfg.get("layer", "topmost")
        try:
            idx = order.index(current)
        except ValueError:
            idx = 0
        self.set_layer(order[(idx + 1) % len(order)])
