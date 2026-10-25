"""单实例锁：防止重复启动多个时钟。"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = ctypes.c_void_p

ERROR_ALREADY_EXISTS = 183

_handle = None


def acquire(name: str = "Local\\DesktopClock_SingleInstance") -> bool:
    """返回 True 表示抢到锁（首次启动），False 表示已有实例在跑。"""
    global _handle
    try:
        # 必须先清零：ctypes 会缓存上一次 Win32 调用的错误码，
        # 若不清理，前面任何一次"文件已存在"之类的调用都会留下 183，
        # 导致这里误判成"已有实例在运行"而直接退出。
        ctypes.set_last_error(0)
        _handle = kernel32.CreateMutexW(None, False, name)
        err = ctypes.get_last_error()
        return err != ERROR_ALREADY_EXISTS
    except Exception:
        # 拿不到锁也允许启动，宁可多开也不要起不来
        return True
