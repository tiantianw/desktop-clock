"""Win32 集成：置顶、桌面挂件层、点击穿透、毛玻璃、DWM 检测。

全部用 ctypes 直接调用，不依赖 pywin32。
所有函数都做了异常保护，失败时返回 False 而不是抛出，避免影响主程序。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from core.logger import log_exception

user32 = ctypes.WinDLL("user32", use_last_error=True)

# ---- 常量 ----
HWND_TOPMOST = ctypes.c_void_p(-1)
HWND_NOTOPMOST = ctypes.c_void_p(-2)

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000

SMTO_NORMAL = 0x0000
WM_SPAWN_WORKER = 0x052C

ACCENT_DISABLED = 0
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19

# ---- 函数签名 ----
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                ctypes.c_uint]
user32.SetWindowPos.restype = wintypes.BOOL

user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long

user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = ctypes.c_void_p
user32.FindWindowExW.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                 wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = ctypes.c_void_p

user32.SendMessageTimeoutW.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                       ctypes.c_size_t, ctypes.c_ssize_t,
                                       ctypes.c_uint, ctypes.c_uint,
                                       ctypes.POINTER(ctypes.c_size_t)]
user32.SendMessageTimeoutW.restype = ctypes.c_void_p

user32.SetParent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.SetParent.restype = ctypes.c_void_p

user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL

user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

SW_SHOWNA = 8


def hwnd_of(widget) -> int:
    """取 Qt 窗口的 HWND。"""
    try:
        return int(widget.winId())
    except Exception:
        return 0


# ---------------------------------------------------------------- 层级控制

def set_topmost(hwnd: int) -> bool:
    try:
        user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        return True
    except Exception:
        log_exception("set_topmost")
        return False


def set_normal(hwnd: int) -> bool:
    try:
        user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_NOTOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        return True
    except Exception:
        log_exception("set_normal")
        return False


def is_topmost(hwnd: int) -> bool:
    try:
        return bool(user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE) & WS_EX_TOPMOST)
    except Exception:
        return False


def set_tool_window(hwnd: int) -> bool:
    """不出现在 Alt+Tab 和任务栏。"""
    try:
        ex = user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE)
        ex = (ex | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        user32.SetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE, ex)
        return True
    except Exception:
        log_exception("set_tool_window")
        return False


def set_no_activate(hwnd: int, enabled: bool = True) -> bool:
    try:
        ex = user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE)
        ex = (ex | WS_EX_NOACTIVATE) if enabled else (ex & ~WS_EX_NOACTIVATE)
        user32.SetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE, ex)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- 点击穿透

def set_click_through(hwnd: int, enabled: bool) -> bool:
    try:
        ex = user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE)
        if enabled:
            ex |= (WS_EX_TRANSPARENT | WS_EX_LAYERED)
        else:
            ex &= ~WS_EX_TRANSPARENT
        user32.SetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE, ex)
        return True
    except Exception:
        log_exception("set_click_through")
        return False


# ---------------------------------------------------------------- 桌面挂件层

def _find_wallpaper_workerw() -> int:
    """触发 Progman 分裂出 WorkerW，返回承载壁纸的那个 WorkerW。"""
    progman = user32.FindWindowW("Progman", None)
    if not progman:
        return 0
    result = ctypes.c_size_t(0)
    user32.SendMessageTimeoutW(ctypes.c_void_p(progman), WM_SPAWN_WORKER, 0, 0,
                               SMTO_NORMAL, 1000, ctypes.byref(result))

    found: list[int] = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, ctypes.c_void_p, ctypes.c_void_p)

    def _cb(hwnd, _lparam):
        shell_view = user32.FindWindowExW(ctypes.c_void_p(hwnd), None, "SHELLDLL_DefView", None)
        if shell_view:
            worker = user32.FindWindowExW(None, ctypes.c_void_p(hwnd), "WorkerW", None)
            if worker:
                found.append(int(worker))
        return True

    try:
        user32.EnumWindows(WNDENUMPROC(_cb), None)
    except Exception:
        log_exception("enum_windows")
    return found[0] if found else 0


def attach_to_desktop(hwnd: int, x: int = 0, y: int = 0, w: int = 0, h: int = 0) -> bool:
    """把窗口挂到壁纸之上、桌面图标之下。

    注意：只调 SetParent 不够，窗口仍是 WS_POPUP，系统会继续把它当顶层窗口。
    必须同时把样式改成 WS_CHILD，否则层级不会生效。
    """
    try:
        target = _find_wallpaper_workerw()
        if not target:
            progman = user32.FindWindowW("Progman", None)
            target = int(progman) if progman else 0
        if not target:
            return False

        user32.SetParent(ctypes.c_void_p(hwnd), ctypes.c_void_p(target))

        style = user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_STYLE)
        style = (style & ~WS_POPUP) | WS_CHILD
        user32.SetWindowLongW(ctypes.c_void_p(hwnd), GWL_STYLE, style)

        flags = SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
        if w > 0 and h > 0:
            user32.SetWindowPos(ctypes.c_void_p(hwnd), None, x, y, w, h, flags)
        else:
            user32.SetWindowPos(ctypes.c_void_p(hwnd), None, 0, 0, 0, 0,
                                flags | SWP_NOMOVE | SWP_NOSIZE)
        user32.ShowWindow(ctypes.c_void_p(hwnd), SW_SHOWNA)
        return True
    except Exception:
        log_exception("attach_to_desktop")
        return False


def detach_from_desktop(hwnd: int, x: int = 0, y: int = 0, w: int = 0, h: int = 0) -> bool:
    """恢复成独立顶层窗口。

    注意：SetParent 会摧毁 Qt 给透明窗口准备的 layered 表面，之后 Qt 再也画不出
    新内容——表现就是「窗口还在、程序也活着，但画面永久定格」。
    所以这里必须先判断是否真的挂在桌面层，没挂就直接返回，绝不能无条件改样式。
    """
    try:
        parent = user32.GetParent(ctypes.c_void_p(hwnd))
        if not parent:
            return True  # 本来就是顶层窗口，什么都不用做
        style = user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_STYLE)
        style = (style & ~WS_CHILD) | WS_POPUP
        user32.SetWindowLongW(ctypes.c_void_p(hwnd), GWL_STYLE, style)
        user32.SetParent(ctypes.c_void_p(hwnd), None)
        flags = SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
        if w > 0 and h > 0:
            user32.SetWindowPos(ctypes.c_void_p(hwnd), None, x, y, w, h, flags)
        # 从子窗口变回顶层窗口后必须显式显示，否则会变成不可见
        user32.ShowWindow(ctypes.c_void_p(hwnd), SW_SHOWNA)
        return True
    except Exception:
        log_exception("detach_from_desktop")
        return False


# ---------------------------------------------------------------- 毛玻璃

class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int),
    ]


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


def set_blur(hwnd: int, enabled: bool, abgr: int = 0x99F0EAE0) -> bool:
    """开启系统级背景模糊。abgr 为 0xAABBGGRR 格式。"""
    try:
        fn = getattr(user32, "SetWindowCompositionAttribute", None)
        if fn is None:
            return False
        fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
        fn.restype = wintypes.BOOL
        policy = ACCENT_POLICY()
        policy.AccentState = ACCENT_ENABLE_BLURBEHIND if enabled else ACCENT_DISABLED
        policy.AccentFlags = 0
        policy.GradientColor = abgr if enabled else 0
        policy.AnimationId = 0
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.byref(policy), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(policy)
        return bool(fn(ctypes.c_void_p(hwnd), ctypes.byref(data)))
    except Exception:
        log_exception("set_blur")
        return False


def dwm_enabled() -> bool:
    """DWM 关闭时透明与模糊都失效（远程桌面场景常见）。"""
    try:
        dwmapi = ctypes.WinDLL("dwmapi")
        value = ctypes.c_int(1)
        dwmapi.DwmIsCompositionEnabled(ctypes.byref(value))
        return bool(value.value)
    except Exception:
        return True


def hex_to_abgr(hex_color: str, alpha: int = 0x99) -> int:
    try:
        s = hex_color.lstrip("#")
        r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        return (alpha << 24) | (b << 16) | (g << 8) | r
    except Exception:
        return 0x99F0EAE0
