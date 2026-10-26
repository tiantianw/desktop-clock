"""配置管理：JSON 持久化 + 默认值深度合并 + 点路径读写。"""

from __future__ import annotations

import copy
import json
import os
import sys
import threading

from core import i18n

APP_NAME = "DesktopClock"


def app_dir() -> str:
    """程序目录。打包成 exe 后取 exe 所在目录，否则取源码根目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CONFIG_PATH = os.path.join(app_dir(), "config.json")

DEFAULTS = {
    "version": 1,
    "language": "zh",
    "skin": "glass",
    "theme": "warm",
    "geometry": {
        "x": None,
        "y": None,
        "size": 110,
    },
    "layer": "topmost",
    "appearance": {
        "radius": 18,
        "bg_mode": "solid",
        "bg_color": "#FAF6EE",
        "bg_opacity": 92,
        "accent": "#C08A4E",
        "text_color": "#2C2C2A",
        "muted_color": "#A0937F",
        "font_family": "Consolas",
        "font_weight": 500,
        "shadow": True,
        "shadow_strength": 20,
        "border": True,
        "border_color": "#E7DFD2",
        "dial_style": "arabic",
        "hand_scale": 1.0,
        "dial_scale": 1.0,
    },
    "content": {
        "hour24": True,
        "show_seconds": True,
        "second_style": "tick",
        "date_format": "MM月DD日",
        "show_weekday": "short",
        "show_lunar": False,
        "sub_timezones": [],
        "blink_cursor": True,
    },
    "behavior": {
        "lock_position": False,
        "click_through": False,
        "edge_snap": True,
        "autostart": False,
        "topmost_guard": True,
        "hotkey_layer": "Ctrl+Alt+T",
        "hotkey_visible": "Ctrl+Alt+H",
    },
}

# 主题预设：name -> (显示名, bg, text, muted, accent, border)
THEMES = {
    "warm": ("暖米", "#FAF6EE", "#2C2C2A", "#A0937F", "#C08A4E", "#E7DFD2"),
    "ink": ("墨黑", "#1F1F1D", "#F2EEE5", "#8A8375", "#C08A4E", "#3A3A34"),
    "slate": ("冷灰", "#F4F6F8", "#1E2A32", "#7A8A96", "#378ADD", "#DCE3E8"),
    "celadon": ("青瓷", "#EDF4F0", "#1D3B33", "#6E8A80", "#1D9E75", "#CFE0D7"),
    "amber": ("琥珀", "#2A1E14", "#F7E9D2", "#A8865E", "#EF9F27", "#4A3623"),
    "sakura": ("樱粉", "#FDF2F5", "#3A2028", "#A8818E", "#D4537E", "#F0D6DF"),
    "ocean": ("深海", "#0E1B26", "#DCE9F2", "#6C8A9A", "#5DCAA5", "#22333F"),
    "plain": ("极简白", "#FFFFFF", "#111111", "#999999", "#111111", "#E8E8E8"),
    "graphite": ("石墨", "#2B2B2E", "#EDEDED", "#8E8E93", "#7F77DD", "#3F3F45"),
    "paper": ("纸白", "#F7F4EC", "#22201C", "#8C8578", "#993C1D", "#DED7C6"),
}

THEME_ORDER = ["warm", "ink", "slate", "celadon", "amber", "sakura", "ocean", "plain", "graphite", "paper"]

# 英文界面下的主题名
THEME_EN = {
    "warm": "Warm beige",
    "ink": "Ink black",
    "slate": "Cool grey",
    "celadon": "Celadon",
    "amber": "Amber",
    "sakura": "Sakura",
    "ocean": "Deep sea",
    "plain": "Pure white",
    "graphite": "Graphite",
    "paper": "Paper white",
}


def theme_name(key: str) -> str:
    if i18n.is_en():
        return THEME_EN.get(key, key)
    return THEMES[key][0] if key in THEMES else key


def deep_merge(base: dict, override: dict) -> dict:
    """把 override 合并进 base 的副本，缺失键用默认值补齐。"""
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


class Config:
    """线程安全的配置对象，支持 'appearance.accent' 形式的点路径访问。"""

    def __init__(self, path: str = CONFIG_PATH):
        self.path = path
        self.data = copy.deepcopy(DEFAULTS)
        self._lock = threading.RLock()
        self.load()

    def load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            with self._lock:
                self.data = deep_merge(DEFAULTS, raw)
        except FileNotFoundError:
            with self._lock:
                self.data = copy.deepcopy(DEFAULTS)
        except Exception:
            # 配置损坏时回退默认值，绝不让程序起不来
            with self._lock:
                self.data = copy.deepcopy(DEFAULTS)

    def save(self) -> None:
        try:
            with self._lock:
                snapshot = copy.deepcopy(self.data)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            pass

    def get(self, dotted: str, default=None):
        node = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted: str, value) -> None:
        parts = dotted.split(".")
        with self._lock:
            node = self.data
            for part in parts[:-1]:
                if part not in node or not isinstance(node[part], dict):
                    node[part] = {}
                node = node[part]
            node[parts[-1]] = value

    def apply_theme(self, theme_key: str) -> None:
        """套用主题预设，写入 appearance 的颜色项。"""
        if theme_key not in THEMES:
            return
        _, bg, text, muted, accent, border = THEMES[theme_key]
        self.set("theme", theme_key)
        self.set("appearance.bg_color", bg)
        self.set("appearance.text_color", text)
        self.set("appearance.muted_color", muted)
        self.set("appearance.accent", accent)
        self.set("appearance.border_color", border)

    def reset(self) -> None:
        with self._lock:
            # 界面语言是用户偏好，不该被「恢复默认」顺手改掉
            keep = self.data.get("language", DEFAULTS["language"])
            self.data = copy.deepcopy(DEFAULTS)
            self.data["language"] = keep
