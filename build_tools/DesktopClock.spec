# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（精简版）

要点：
1. 用 pip 版 PyQt5（官方 Windows wheel 不带 ICU），省掉 32MB 的 icudt 数据 DLL；
2. Analysis 之后对 binaries / datas 做白名单过滤，剔掉 opengl32sw、d3dcompiler、
   Qt5Quick/Qml/Network 等本程序用不到的二进制；
3. 只保留 qwindows 平台插件、qico 图标插件，丢掉全部 Qt 翻译文件。
"""

import os
import re

BASE = os.path.dirname(os.path.abspath(SPECPATH))
# SPECPATH 在不同 PyInstaller 版本/调用方式下可能指向 spec 目录或其父目录，
# 这里用 run.pyw 是否存在来自动定位项目根目录。
ROOT = BASE if os.path.exists(os.path.join(BASE, 'run.pyw')) else os.path.dirname(BASE)
ENTRY = os.path.join(ROOT, 'run.pyw')
ICON = os.path.join(ROOT, 'assets', 'app.ico')

BLOCK_BIN = {
    # 软件 OpenGL / ANGLE：QWidget 走 raster 绘制，用不到
    "opengl32sw.dll",
    "d3dcompiler_47.dll",
    "libglesv2.dll",
    "libegl.dll",
    "libegl.dll".upper(),
    # 只有 Qt5Network 才需要的 OpenSSL
    "libcrypto-3-x64.dll",
    "libssl-3-x64.dll",
    "libcrypto-1_1-x64.dll",
    "libssl-1_1-x64.dll",
    "libeay32.dll",
    "ssleay32.dll",
    # 不联网，ssl/hashlib 的 C 扩展也不需要
    "_ssl.pyd",
    "_hashlib.pyd",
    # 本程序不用的 Qt 模块
    "qt5quick.dll",
    "qt5qml.dll",
    "qt5qmlmodels.dll",
    "qt5network.dll",
    "qt5dbus.dll",
    "qt5designer.dll",
    "qt5xmlpatterns.dll",
    "qt5location.dll",
    "qt5multimedia.dll",
    "qt5bluetooth.dll",
    "qt5quick3d.dll",
    "qt5quick3druntimerender.dll",
    "qt5quicktemplates2.dll",
    "qt5test.dll",
    "qt5sql.dll",
    "qt5websockets.dll",
    "qt5virtualkeyboard.dll",
    "qt5printsupport.dll",
}

# 插件目录白名单：只留这些子目录，且只留列出的文件
PLUGIN_KEEP = {
    "platforms": {"qwindows.dll"},
    "styles": None,           # 整个 styles 目录保留（体积很小）
    "imageformats": {"qico.dll"},
    "iconengines": {"qico.dll", "qsvgicon.dll"},
}

BLOCK_DATA_DIR = (
    "PyQt5/Qt5/translations",
    "PyQt5\\Qt5\\translations",
)

# tzdata 只保留城市表里真正用到的时区文件（默认会带 600 个文件）
TZ_KEEP = {
    "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Taipei", "Asia/Tokyo",
    "Asia/Seoul", "Asia/Singapore", "Asia/Dubai",
    "Europe/Moscow", "Europe/Paris", "Europe/London",
    "America/New_York", "America/Chicago", "America/Los_Angeles",
    "America/Sao_Paulo", "Australia/Sydney",
}


def _norm(p):
    return p.replace("\\", "/")


def _plugin_group(dest):
    """dest 形如 PyQt5/Qt5/plugins/platforms/qwindows.dll -> 'platforms'"""
    d = _norm(dest)
    m = re.search(r"/plugins/([^/]+)/", d)
    return m.group(1) if m else None


def keep_binary(entry):
    dest = _norm(entry[0])
    base = os.path.basename(dest).lower()
    if base in BLOCK_BIN:
        return False
    group = _plugin_group(dest)
    if group is not None:
        allow = PLUGIN_KEEP.get(group)
        if allow is None:
            return False
        return base in allow
    return True


def keep_data(entry):
    dest = _norm(entry[0])
    for prefix in BLOCK_DATA_DIR:
        if dest.startswith(_norm(prefix)):
            return False
    # tzdata 白名单
    m = re.search(r"tzdata/zoneinfo/(.+)$", dest)
    if m:
        return m.group(1) in TZ_KEEP
    group = _plugin_group(dest)
    if group is not None:
        allow = PLUGIN_KEEP.get(group)
        if allow is None:
            return False
        return os.path.basename(dest).lower() in allow
    return True


a = Analysis(
    [ENTRY],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5.QtNetwork', 'PyQt5.QtQml', 'PyQt5.QtQuick', 'PyQt5.QtWebEngine',
        'PyQt5.QtWebEngineCore', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtMultimedia',
        'PyQt5.QtSql', 'PyQt5.QtTest', 'PyQt5.QtBluetooth', 'PyQt5.QtXml',
        'PyQt5.QtPrintSupport', 'PyQt5.QtSvg', 'PyQt5.QtDBus', 'PyQt5.QtOpenGL',
        'tkinter', 'numpy', 'pandas', 'matplotlib', 'PIL', 'psutil', 'scipy',
        'IPython', 'unittest', 'pydoc', 'doctest', 'email', 'http', 'xml',
        'asyncio', 'multiprocessing', 'sqlite3', 'curses', 'distutils',
        'setuptools', 'lib2to3', 'pdb', 'difflib', 'argparse',
    ],
    noarchive=False,
    optimize=0,
)

a.binaries = [b for b in a.binaries if keep_binary(b)]
a.datas = [d for d in a.datas if keep_data(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DesktopClock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[ICON],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='DesktopClock',
)
