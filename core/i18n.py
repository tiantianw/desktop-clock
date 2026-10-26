"""界面语言：中文 / English。

刻意不维护 key 表：直接 t("中文", "English") 二选一。
好处是漏翻的地方一眼就能在原处看见，也不用担心 key 写错导致空字符串。
"""

from __future__ import annotations

LANGUAGES = (("zh", "简体中文"), ("en", "English"))

_LANG = "zh"


def normalize(value) -> str:
    """把配置里可能出现的各种写法归一成 "zh" / "en"。"""
    v = str(value or "").strip().lower().replace("_", "-")
    if v.startswith("en"):
        return "en"
    return "zh"


def set_language(value) -> str:
    global _LANG
    _LANG = normalize(value)
    return _LANG


def current() -> str:
    return _LANG


def is_en() -> bool:
    return _LANG == "en"


def t(zh: str, en: str) -> str:
    """按当前语言二选一。"""
    return en if _LANG == "en" else zh


def layer_choices() -> list[tuple[str, str]]:
    """三档窗口层级的 (key, 显示名)，托盘菜单和右键菜单共用。"""
    return [
        ("topmost", t("始终置顶", "Always on top")),
        ("normal", t("普通窗口", "Normal window")),
        ("desktop", t("桌面挂件层", "Desktop widget layer")),
    ]
