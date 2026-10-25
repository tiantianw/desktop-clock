"""时区城市表。优先用 zoneinfo（tzdata 已安装），失败则退回固定偏移。"""

from __future__ import annotations

import datetime

try:
    from zoneinfo import ZoneInfo
    _HAS_ZONEINFO = True
except Exception:
    _HAS_ZONEINFO = False

# (key, 中文名, 英文缩写, IANA 时区, 标准时偏移小时)
CITIES = [
    ("beijing", "北京", "PEK", "Asia/Shanghai", 8),
    ("shanghai", "上海", "SHA", "Asia/Shanghai", 8),
    ("hongkong", "中国香港", "HKG", "Asia/Hong_Kong", 8),
    ("taipei", "中国台北", "TPE", "Asia/Taipei", 8),
    ("tokyo", "东京", "TYO", "Asia/Tokyo", 9),
    ("seoul", "首尔", "SEL", "Asia/Seoul", 9),
    ("singapore", "新加坡", "SIN", "Asia/Singapore", 8),
    ("dubai", "迪拜", "DXB", "Asia/Dubai", 4),
    ("moscow", "莫斯科", "MOW", "Europe/Moscow", 3),
    ("paris", "巴黎", "PAR", "Europe/Paris", 1),
    ("london", "伦敦", "LDN", "Europe/London", 0),
    ("newyork", "纽约", "NYC", "America/New_York", -5),
    ("chicago", "芝加哥", "CHI", "America/Chicago", -6),
    ("losangeles", "洛杉矶", "LAX", "America/Los_Angeles", -8),
    ("sydney", "悉尼", "SYD", "Australia/Sydney", 10),
    ("saopaulo", "圣保罗", "SAO", "America/Sao_Paulo", -3),
]

CITY_MAP = {c[0]: c for c in CITIES}
DEFAULT_CITIES = ["tokyo", "london", "newyork"]


def city_time(key: str, local_now: datetime.datetime) -> datetime.datetime | None:
    """把本地 naive 时间换算到目标城市。"""
    info = CITY_MAP.get(key)
    if info is None:
        return None
    _, _cn, _abbr, tzname, fallback = info
    if _HAS_ZONEINFO:
        try:
            local_tz = datetime.datetime.now().astimezone().tzinfo
            aware = local_now.replace(tzinfo=local_tz)
            return aware.astimezone(ZoneInfo(tzname))
        except Exception:
            pass
    try:
        return local_now + datetime.timedelta(hours=fallback - _local_offset(local_now))
    except Exception:
        return None


def _local_offset(local_now: datetime.datetime) -> int:
    off = local_now.astimezone().utcoffset()
    return int(off.total_seconds() // 3600) if off else 8


def city_label(key: str) -> str:
    info = CITY_MAP.get(key)
    return info[1] if info else key


def city_abbr(key: str) -> str:
    info = CITY_MAP.get(key)
    return info[2] if info else ""


def format_city_time(key: str, local_now: datetime.datetime, hour24: bool = True) -> str:
    dt = city_time(key, local_now)
    if dt is None:
        return "--:--"
    if hour24:
        return "%02d:%02d" % (dt.hour, dt.minute)
    h = dt.hour % 12 or 12
    return "%02d:%02d %s" % (h, dt.minute, "AM" if dt.hour < 12 else "PM")
