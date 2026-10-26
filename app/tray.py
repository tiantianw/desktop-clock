"""系统托盘图标与菜单。"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMenu, QSystemTrayIcon

from app.icon import build_icon
from core import i18n
from core.i18n import t
from core.logger import log_exception
from render import registry
from sysint import autostart

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
QMenu::separator { height: 1px; background: #EFE9DE; margin: 5px 8px; }
"""


class Tray(QSystemTrayIcon):
    def __init__(self, window, cfg, parent=None):
        self.window = window
        self.cfg = cfg
        icon = build_icon(cfg.get("appearance.text_color", "#2C2C2A"),
                          cfg.get("appearance.accent", "#C08A4E"),
                          cfg.get("appearance.bg_color", "#FFFFFF"))
        super().__init__(icon, parent or window)
        self.setToolTip(t("桌面时钟", "Desktop Clock"))
        self._menu = QMenu()
        self._menu.setStyleSheet(MENU_QSS)
        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)
        self._rebuild()

    def _on_activated(self, reason):
        try:
            if reason == QSystemTrayIcon.Trigger:
                self.window.setVisible(not self.window.isVisible())
                self._rebuild()
        except Exception:
            log_exception("tray activated")

    def refresh_icon(self) -> None:
        try:
            self.setIcon(build_icon(self.cfg.get("appearance.text_color", "#2C2C2A"),
                                    self.cfg.get("appearance.accent", "#C08A4E"),
                                    self.cfg.get("appearance.bg_color", "#FFFFFF")))
        except Exception:
            log_exception("refresh_icon")

    def _rebuild(self) -> None:
        try:
            self._menu.clear()

            visible = self.window.isVisible()
            act_show = self._menu.addAction(t("隐藏时钟", "Hide clock") if visible
                                            else t("显示时钟", "Show clock"))
            act_show.triggered.connect(lambda: (self.window.setVisible(not self.window.isVisible()),
                                                self._rebuild()))

            self._menu.addSeparator()

            skin_menu = self._menu.addMenu(t("皮肤", "Skin"))
            skin_menu.setStyleSheet(MENU_QSS)
            current = self.cfg.get("skin", "glass")
            for sid, name in registry.skin_choices():
                act = skin_menu.addAction(name)
                act.setCheckable(True)
                act.setChecked(sid == current)
                act.triggered.connect(lambda _=False, s=sid: self._pick_skin(s))

            layer_menu = self._menu.addMenu(t("层级", "Layer"))
            layer_menu.setStyleSheet(MENU_QSS)
            layer = self.cfg.get("layer", "topmost")
            for key, label in i18n.layer_choices():
                act = layer_menu.addAction(label)
                act.setCheckable(True)
                act.setChecked(key == layer)
                act.triggered.connect(lambda _=False, k=key: self._pick_layer(k))

            self._menu.addSeparator()
            self._menu.addAction(t("设置…", "Settings…")).triggered.connect(
                self.window.request_settings.emit)
            self._menu.addAction(t("重置到右上角", "Reset to top-right")).triggered.connect(
                self.window.reset_position)

            act_start = self._menu.addAction(t("开机自启", "Start with Windows"))
            act_start.setCheckable(True)
            act_start.setChecked(autostart.is_enabled())
            act_start.triggered.connect(self._toggle_autostart)

            self._menu.addSeparator()
            self._menu.addAction(t("退出", "Quit")).triggered.connect(self.window.request_quit.emit)
        except Exception:
            log_exception("tray rebuild")

    def refresh_language(self) -> None:
        """切了界面语言之后，把提示文字和菜单都重建成新语言。"""
        try:
            self.setToolTip(t("桌面时钟", "Desktop Clock"))
            self._rebuild()
        except Exception:
            log_exception("refresh_language")

    def _pick_skin(self, skin_id: str) -> None:
        self.window.set_skin(skin_id)
        self._rebuild()

    def _pick_layer(self, layer: str) -> None:
        self.window.set_layer(layer)
        self._rebuild()

    def _toggle_autostart(self, checked: bool) -> None:
        try:
            autostart.set_enabled(checked)
            self.cfg.set("behavior.autostart", checked)
            self.cfg.save()
        except Exception:
            log_exception("toggle_autostart")
        self._rebuild()

    def show_message(self, title: str, text: str) -> None:
        try:
            self.showMessage(title, text, QSystemTrayIcon.Information, 3000)
        except Exception:
            pass
