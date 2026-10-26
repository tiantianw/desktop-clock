"""生成应用图标（ico + png），供 exe 与托盘使用。

ico 里每个尺寸都是**单独渲染**的，不是把 512px 缩下去 —— 16px 下缩放的
结果是一团糊，单独画才能把笔画和刻度调到看得清。
"""

from __future__ import annotations

import os
import struct
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from PyQt5.QtCore import QBuffer, QByteArray, QIODevice
from PyQt5.QtWidgets import QApplication

from app.icon import ICON_SIZES, draw_clock

TEXT = "#2C2C2A"
ACCENT = "#C08A4E"
BG = "#FFFFFF"


def _png_bytes(pm) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    pm.save(buf, "PNG")
    data = bytes(buf.data())
    buf.close()
    return data


def save_ico(path: str, pixmaps) -> None:
    """手写 ICO 容器，每帧放一张原生渲染的 PNG。"""
    blobs = [_png_bytes(pm) for pm in pixmaps]
    count = len(blobs)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    entries = b""
    for pm, blob in zip(pixmaps, blobs):
        w = 0 if pm.width() >= 256 else pm.width()
        h = 0 if pm.height() >= 256 else pm.height()
        entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    with open(path, "wb") as fh:
        fh.write(header + entries + b"".join(blobs))


def main() -> int:
    app = QApplication(sys.argv)
    assets = os.path.join(BASE, "assets")
    os.makedirs(assets, exist_ok=True)

    big = draw_clock(256, TEXT, ACCENT, BG)
    png = os.path.join(assets, "app.png")
    big.save(png, "PNG")
    print("png:", png)

    frames = [draw_clock(s, TEXT, ACCENT, BG) for s in ICON_SIZES]
    ico = os.path.join(assets, "app.ico")
    save_ico(ico, frames)
    print("ico:", ico, "sizes:", ICON_SIZES)

    # 把 16px 放大 8 倍存一张对照图，方便肉眼确认小图标是否清楚
    prev = frames[0].scaled(128, 128)
    out = os.path.join(tempfile.gettempdir(), "desktopclock_icon16.png")
    prev.save(out, "PNG")
    print("16px preview:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
