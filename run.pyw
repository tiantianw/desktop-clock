"""桌面时钟入口。用 pythonw 运行，无控制台窗口。"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

user32 = ctypes.windll.user32


def _boot() -> int:
    from core.logger import (
        LOG_PATH, dump_stacks, install_faulthandler, install_global_hook, log, log_exception,
    )
    install_global_hook()
    install_faulthandler()

    from app.single_instance import acquire
    if not acquire():
        log("已有实例在运行，本次启动退出")
        return 0

    from PyQt5.QtCore import QAbstractNativeEventFilter, Qt, QTimer
    from PyQt5.QtWidgets import QApplication, QSystemTrayIcon

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("DesktopClock")
    app.setQuitOnLastWindowClosed(False)

    from core.config import Config
    from core import i18n
    from app.window import ClockWindow
    from app.tray import Tray
    from sysint.hotkey import HotkeyManager

    cfg = Config()
    i18n.set_language(cfg.get("language", "zh"))
    state: dict = {"window": None, "dialog": None, "tray": None}
    hotkeys = HotkeyManager()

    def register_hotkeys() -> None:
        try:
            win = state["window"]
            if win is None:
                return
            hotkeys.unregister_all()
            hotkeys.install(int(win.winId()))
            hotkeys.register(cfg.get("behavior.hotkey_layer", "Ctrl+Alt+T"), win.cycle_layer)
            hotkeys.register(cfg.get("behavior.hotkey_visible", "Ctrl+Alt+H"),
                             lambda: win.setVisible(not win.isVisible()))
        except Exception:
            log_exception("register_hotkeys")

    def open_settings() -> None:
        try:
            dlg = state.get("dialog")
            if dlg is not None:
                dlg.show()
                dlg.raise_()
                dlg.activateWindow()
                return
            from app.settings_dialog import SettingsDialog
            dlg = SettingsDialog(cfg, state["window"])
            dlg.finished.connect(lambda _=0: state.__setitem__("dialog", None))
            state["dialog"] = dlg
            dlg.show()
        except Exception:
            log_exception("open_settings")

    def rebuild_window() -> None:
        """重建窗口。桌面挂件层要改父窗口，会破坏 Qt 的透明表面，只能换新实例。"""
        try:
            old = state["window"]
            if old is None:
                return
            pos = (old.x(), old.y())
            dlg = state.get("dialog")
            if dlg is not None:
                dlg.close()
                state["dialog"] = None

            new = ClockWindow(cfg)
            bind(new)
            new.show()
            new.move(pos[0], pos[1])
            state["window"] = new

            tray = state.get("tray")
            if tray is not None:
                tray.window = new
                tray._rebuild()

            old.hide()
            old.deleteLater()
            register_hotkeys()
            log("窗口已重建 layer=%s" % cfg.get("layer"))
        except Exception:
            log_exception("rebuild_window")

    def refresh_language() -> None:
        try:
            tray = state.get("tray")
            if tray is not None:
                tray.refresh_language()
        except Exception:
            log_exception("refresh_language")

    def bind(win: ClockWindow) -> None:
        win.request_settings.connect(open_settings)
        win.request_quit.connect(app.quit)
        win.request_rebuild.connect(rebuild_window)
        win.request_language.connect(refresh_language)

    window = ClockWindow(cfg)
    bind(window)
    state["window"] = window
    window.show()

    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = Tray(window, cfg)
        tray.show()
        state["tray"] = tray

    register_hotkeys()

    guard = QTimer()
    guard.timeout.connect(lambda: state["window"] and state["window"].guard_topmost())
    guard.start(5000)

    # ---------------------------------------------------------------- 卡死自救
    #
    # 实测过一种失效：进程消息循环正常、窗口还在，但 Qt 定时器不再触发，
    # 于是时间永远停在某一刻，CPU 为 0。这种情况下 QTimer 自己救不了自己，
    # 但窗口消息仍然能送达 —— 所以让后台线程发一条自定义消息，
    # 由 GUI 线程收到后强制重启定时器。
    WM_HEAL = 0x8000 + 0x51

    class _HealFilter(QAbstractNativeEventFilter):
        def nativeEventFilter(self, eventType, message):
            try:
                if bytes(eventType) in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
                    msg = ctypes.wintypes.MSG.from_address(int(message))
                    if msg.message == WM_HEAL:
                        win = state.get("window")
                        if win is not None:
                            win._beat = time.time()
                            win._last_tick = time.time()
                            win._restart_timer()
                            win.update()
                        return False, 0
            except Exception:
                log_exception("heal_filter")
            return False, 0

    _heal = _HealFilter()
    app.installNativeEventFilter(_heal)

    # 后台看门狗：GUI 线程若整体卡住，界面上的自愈定时器也一起停摆，
    # 只能靠独立线程把当时的线程栈写进 logs/crash.log。
    def _stall_watchdog() -> None:
        import threading

        def loop() -> None:
            last = 0.0
            while True:
                time.sleep(2.0)
                try:
                    win = state.get("window")
                    if win is None:
                        continue
                    gap = time.time() - getattr(win, "_beat", time.time())
                    limit = max(12.0, win._alive.interval() / 1000.0 * 3.0)
                    if gap <= limit:
                        continue
                    # 先尝试用窗口消息把定时器救回来
                    hwnd = int(win.winId()) if win else 0
                    if hwnd:
                        user32.PostMessageW(ctypes.c_void_p(hwnd), WM_HEAL, 0, 0)
                    if time.time() - last > 60.0:
                        last = time.time()
                        dump_stacks("GUI 线程卡死 %.0fs skin=%s layer=%s 定时器激活=%s"
                                    % (gap, cfg.get("skin"), cfg.get("layer"),
                                       win._timer.isActive()))
                except Exception:
                    pass

        threading.Thread(target=loop, name="stall-watchdog", daemon=True).start()

    _stall_watchdog()

    def _cleanup() -> None:
        try:
            hotkeys.unregister_all()
        except Exception:
            pass
        try:
            cfg.save()
        except Exception:
            pass

    app.aboutToQuit.connect(_cleanup)
    log("启动完成 skin=%s layer=%s size=%s 窗口=%dx%d 日志=%s"
        % (cfg.get("skin"), cfg.get("layer"), cfg.get("geometry.size"),
           window.width(), window.height(), LOG_PATH))

    # 带 --settings 参数启动时，启动后直接打开设置面板（方便做快捷方式/自检）
    if "--settings" in sys.argv:
        QTimer.singleShot(400, open_settings)

    return app.exec_()


if __name__ == "__main__":
    try:
        sys.exit(_boot())
    except SystemExit:
        raise
    except Exception:
        try:
            from core.logger import log_exception
            log_exception("boot")
        except Exception:
            pass
        sys.exit(1)
