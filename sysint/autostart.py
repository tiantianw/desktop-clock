"""开机自启：写 HKCU\\...\\Run。用 winreg 直接操作注册表，不调用 reg.exe。"""

from __future__ import annotations

import os
import sys

from core.config import app_dir
from core.logger import log_exception

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "DesktopClock"


def launch_command() -> str:
    """启动命令。打包后直接跑 exe；源码运行则用 pythonw 跑 run.pyw。"""
    if getattr(sys, "frozen", False):
        return '"%s"' % sys.executable
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    return '"%s" "%s"' % (pyw, os.path.join(app_dir(), "run.pyw"))


def is_enabled() -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            try:
                value, _ = winreg.QueryValueEx(key, VALUE_NAME)
                return bool(value)
            except FileNotFoundError:
                return False
    except Exception:
        return False


def set_enabled(enabled: bool) -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, launch_command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        log_exception("autostart.set_enabled")
        return False
