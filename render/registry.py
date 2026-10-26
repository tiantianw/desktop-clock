"""皮肤注册表。"""

from __future__ import annotations

from render.base import Skin
from render.skins_dial import (
    ClassicSkin, CompassSkin, DotsSkin, MinimalSkin, PocketSkin, RomanSkin,
    SubdialSkin, SunburstSkin, WallSkin,
)
from render.skins_digital import GlassSkin, NeonSkin, SplitSkin, TerminalSkin
from render.skins_shape import FlipSkin, RingSkin, SegmentSkin, WorldSkin

# 顺序即设置面板里的展示顺序：先浅色数字，再圆形指针，再图形，最后深色
SKINS: list[Skin] = [
    GlassSkin(),
    ClassicSkin(),
    WallSkin(),
    CompassSkin(),
    PocketSkin(),
    SunburstSkin(),
    RomanSkin(),
    MinimalSkin(),
    DotsSkin(),
    SubdialSkin(),
    RingSkin(),
    SegmentSkin(),
    WorldSkin(),
    SplitSkin(),
    FlipSkin(),
    NeonSkin(),
    TerminalSkin(),
]

SKIN_MAP: dict[str, Skin] = {s.id: s for s in SKINS}


def get_skin(key: str) -> Skin:
    return SKIN_MAP.get(key, SKINS[0])


def skin_ids() -> list[str]:
    return [s.id for s in SKINS]


def skin_choices() -> list[tuple[str, str]]:
    """[(id, 显示名)]"""
    return [(s.id, s.name) for s in SKINS]
