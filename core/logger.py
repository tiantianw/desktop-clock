"""异常兜底日志。任何未捕获异常都落盘，绝不静默退出。"""

from __future__ import annotations

import datetime
import os
import sys
import traceback

from core.config import app_dir

LOG_DIR = os.path.join(app_dir(), "logs")
LOG_PATH = os.path.join(LOG_DIR, "desktopclock.log")
MAX_BYTES = 512 * 1024


def _ensure_dir() -> None:
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception:
        pass


def _rotate_if_needed() -> None:
    try:
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > MAX_BYTES:
            os.replace(LOG_PATH, LOG_PATH + ".1")
    except Exception:
        pass


def log(message: str) -> None:
    _ensure_dir()
    _rotate_if_needed()
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (ts, message))
    except Exception:
        pass


def log_exception(tag: str, exc: BaseException | None = None) -> None:
    """记录异常完整堆栈。tag 用来说明发生位置。"""
    _ensure_dir()
    _rotate_if_needed()
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if exc is not None:
            detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        else:
            detail = traceback.format_exc()
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("[%s] !! %s\n%s\n" % (ts, tag, detail))
    except Exception:
        pass


def install_global_hook() -> None:
    """接管未捕获异常，保证进程不因意外异常直接崩掉。"""

    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log_exception("uncaught", exc_value)

    sys.excepthook = _hook


# ---------------------------------------------------------------- 崩溃 / 卡死取证

CRASH_PATH = os.path.join(LOG_DIR, "crash.log")
_dump_file = None


def install_faulthandler() -> bool:
    """开启 faulthandler。

    Python 层捕获不到的硬崩溃（访问违例、abort、栈溢出）会在这里留下
    C 层堆栈，写进 logs/crash.log，而不是无声消失。
    """
    global _dump_file
    try:
        import faulthandler

        _ensure_dir()
        _dump_file = open(CRASH_PATH, "a", encoding="utf-8", errors="replace")
        _dump_file.write("\n===== 进程启动 %s =====\n"
                         % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        _dump_file.flush()
        faulthandler.enable(_dump_file, all_threads=True)
        return True
    except Exception:
        return False


def dump_stacks(reason: str) -> None:
    """把所有线程当前的 Python 栈转储到日志，用于定位卡死。

    由后台线程调用；写文件失败也不抛异常。
    """
    try:
        import faulthandler

        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if _dump_file is not None:
            _dump_file.write("\n[%s] !! %s\n" % (ts, reason))
            _dump_file.flush()
            faulthandler.dump_traceback(file=_dump_file, all_threads=True)
            _dump_file.flush()
        log("!! %s（线程栈见 crash.log）" % reason)
    except Exception:
        pass
