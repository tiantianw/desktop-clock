"""全局快捷键：RegisterHotKey + Qt 原生事件过滤。"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from PyQt5.QtCore import QAbstractNativeEventFilter
from PyQt5.QtWidgets import QApplication

from core.logger import log_exception

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL


def parse_spec(spec: str) -> tuple[int, int]:
    """'Ctrl+Alt+T' -> (modifiers, virtual_key)。解析失败返回 (0, 0)。"""
    mods = 0
    vk = 0
    for raw in (spec or "").split("+"):
        part = raw.strip().upper()
        if not part:
            continue
        if part in ("CTRL", "CONTROL"):
            mods |= MOD_CONTROL
        elif part == "ALT":
            mods |= MOD_ALT
        elif part == "SHIFT":
            mods |= MOD_SHIFT
        elif part in ("WIN", "META"):
            mods |= MOD_WIN
        elif len(part) == 1 and part.isalnum():
            vk = ord(part)
        elif part.startswith("F") and part[1:].isdigit():
            num = int(part[1:])
            if 1 <= num <= 24:
                vk = 0x70 + num - 1
    if vk == 0:
        return 0, 0
    return mods | MOD_NOREPEAT, vk


class HotkeyManager(QAbstractNativeEventFilter):
    def __init__(self):
        super().__init__()
        self._hwnd = 0
        self._next_id = 0xA100
        self._handlers: dict[int, callable] = {}
        self._installed = False

    def install(self, hwnd: int) -> None:
        self._hwnd = hwnd
        if not self._installed:
            app = QApplication.instance()
            if app is not None:
                app.installNativeEventFilter(self)
                self._installed = True

    def register(self, spec: str, callback) -> bool:
        mods, vk = parse_spec(spec)
        if vk == 0 or not self._hwnd:
            return False
        hid = self._next_id
        self._next_id += 1
        try:
            ok = user32.RegisterHotKey(ctypes.c_void_p(self._hwnd), hid, mods, vk)
        except Exception:
            log_exception("RegisterHotKey")
            return False
        if not ok:
            return False
        self._handlers[hid] = callback
        return True

    def unregister_all(self) -> None:
        for hid in list(self._handlers.keys()):
            try:
                user32.UnregisterHotKey(ctypes.c_void_p(self._hwnd), hid)
            except Exception:
                pass
        self._handlers.clear()

    def nativeEventFilter(self, event_type, message):
        try:
            if event_type in ("windows_generic_MSG", "windows_dispatcher_MSG"):
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    handler = self._handlers.get(int(msg.wParam))
                    if handler is not None:
                        handler()
                        return True, 0
        except Exception:
            log_exception("nativeEventFilter")
        return False, 0
