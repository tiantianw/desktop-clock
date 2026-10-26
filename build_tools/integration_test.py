"""集成测试：启动进程，用快捷键循环切换三档层级，逐张截图验证可见性。"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
PYW = os.path.join(os.path.dirname(PY), "pythonw.exe")
if not os.path.exists(PYW):
    PYW = PY
CONFIG = os.path.join(BASE, "config.json")
OUT = os.path.join(BASE, "build_tools")

from PIL import ImageGrab

user32 = ctypes.windll.user32
VK_CONTROL, VK_MENU, VK_T, VK_LWIN, VK_D = 0x11, 0x12, 0x54, 0x5B, 0x44
KU = 0x0002


def tap_layer():
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_T, 0, 0, 0)
    user32.keybd_event(VK_T, 0, KU, 0)
    user32.keybd_event(VK_MENU, 0, KU, 0)
    user32.keybd_event(VK_CONTROL, 0, KU, 0)


def show_desktop():
    user32.keybd_event(VK_LWIN, 0, 0, 0)
    user32.keybd_event(VK_D, 0, 0, 0)
    user32.keybd_event(VK_D, 0, KU, 0)
    user32.keybd_event(VK_LWIN, 0, KU, 0)


def shot(name: str) -> None:
    im = ImageGrab.grab()
    im.crop((180, 180, 760, 760)).save(os.path.join(OUT, name))
    print("  shot ->", name)


def read_layer() -> str:
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f).get("layer", "?")
    except Exception:
        return "?"


def main() -> int:
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump({"geometry": {"x": 300, "y": 260, "size": 240}}, f, ensure_ascii=False)

    proc = subprocess.Popen([PYW, os.path.join(BASE, "run.pyw")])
    time.sleep(3.5)
    print("started pid", proc.pid, "layer", read_layer())
    shot("it_1_topmost.png")

    tap_layer()
    time.sleep(1.6)
    print("after tap1 layer:", read_layer())
    shot("it_2_normal.png")

    tap_layer()
    time.sleep(1.8)
    print("after tap2 layer:", read_layer())
    shot("it_3_desktop.png")

    tap_layer()
    time.sleep(2.2)
    print("after tap3 layer:", read_layer())
    shot("it_4_back_topmost.png")

    show_desktop()
    time.sleep(1.5)
    shot("it_5_desktop_shown.png")

    try:
        proc.terminate()
    except Exception:
        pass
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
