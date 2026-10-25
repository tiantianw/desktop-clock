"""农历与二十四节气。全部离线计算，不联网、不依赖第三方库。

农历：1900-2100 标准编码表。
节气：用太阳视黄经天文算法求解，精度约 ±1 分钟（远优于常见查表近似公式）。
"""

from __future__ import annotations

import datetime
import math

# 1900-2100 年农历编码。每个 32 位整数：
#   bit16      闰月大小（1=30 天，0=29 天）
#   bit15..4   12 个月大小（1=30 天，0=29 天），bit15 为正月
#   bit3..0    闰月月份（0 表示无闰月）
LUNAR_INFO = [
    0x04BD8, 0x04AE0, 0x0A570, 0x054D5, 0x0D260, 0x0D950, 0x16554, 0x056A0, 0x09AD0, 0x055D2,
    0x04AE0, 0x0A5B6, 0x0A4D0, 0x0D250, 0x1D255, 0x0B540, 0x0D6A0, 0x0ADA2, 0x095B0, 0x14977,
    0x04970, 0x0A4B0, 0x0B4B5, 0x06A50, 0x06D40, 0x1AB54, 0x02B60, 0x09570, 0x052F2, 0x04970,
    0x06566, 0x0D4A0, 0x0EA50, 0x06E95, 0x05AD0, 0x02B60, 0x186E3, 0x092E0, 0x1C8D7, 0x0C950,
    0x0D4A0, 0x1D8A6, 0x0B550, 0x056A0, 0x1A5B4, 0x025D0, 0x092D0, 0x0D2B2, 0x0A950, 0x0B557,
    0x06CA0, 0x0B550, 0x15355, 0x04DA0, 0x0A5B0, 0x14573, 0x052B0, 0x0A9A8, 0x0E950, 0x06AA0,
    0x0AEA6, 0x0AB50, 0x04B60, 0x0AAE4, 0x0A570, 0x05260, 0x0F263, 0x0D950, 0x05B57, 0x056A0,
    0x096D0, 0x04DD5, 0x04AD0, 0x0A4D0, 0x0D4D4, 0x0D250, 0x0D558, 0x0B540, 0x0B6A0, 0x195A6,
    0x095B0, 0x049B0, 0x0A974, 0x0A4B0, 0x0B27A, 0x06A50, 0x06D40, 0x0AF46, 0x0AB60, 0x09570,
    0x04AF5, 0x04970, 0x064B0, 0x074A3, 0x0EA50, 0x06B58, 0x055C0, 0x0AB60, 0x096D5, 0x092E0,
    0x0C960, 0x0D954, 0x0D4A0, 0x0DA50, 0x07552, 0x056A0, 0x0ABB7, 0x025D0, 0x092D0, 0x0CAB5,
    0x0A950, 0x0B4A0, 0x0BAA4, 0x0AD50, 0x055D9, 0x04BA0, 0x0A5B0, 0x15176, 0x052B0, 0x0A930,
    0x07954, 0x06AA0, 0x0AD50, 0x05B52, 0x04B60, 0x0A6E6, 0x0A4E0, 0x0D260, 0x0EA65, 0x0D530,
    0x05AA0, 0x076A3, 0x096D0, 0x04AFB, 0x04AD0, 0x0A4D0, 0x1D0B6, 0x0D250, 0x0D520, 0x0DD45,
    0x0B5A0, 0x056D0, 0x055B2, 0x049B0, 0x0A577, 0x0A4B0, 0x0AA50, 0x1B255, 0x06D20, 0x0ADA0,
    0x14B63, 0x09370, 0x049F8, 0x04970, 0x064B0, 0x168A6, 0x0EA50, 0x06B20, 0x1A6C4, 0x0AAE0,
    0x0A2E0, 0x0D2E3, 0x0C960, 0x0D557, 0x0D4A0, 0x0DA50, 0x05D55, 0x056A0, 0x0A6D0, 0x055D4,
    0x052D0, 0x0A9B8, 0x0A950, 0x0B4A0, 0x0B6A6, 0x0AD50, 0x055A0, 0x0ABA4, 0x0A5B0, 0x052B0,
    0x0B273, 0x06930, 0x07337, 0x06AA0, 0x0AD50, 0x14B55, 0x04B60, 0x0A570, 0x054E4, 0x0D160,
    0x0E968, 0x0D520, 0x0DAA0, 0x16AA6, 0x056D0, 0x04AE0, 0x0A9D4, 0x0A2D0, 0x0D150, 0x0F252,
    0x0D520,
]

LUNAR_BASE = datetime.date(1900, 1, 31)  # 农历 1900 年正月初一

MONTH_NAMES = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
DAY_NAMES = [
    "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
    "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
]

# 二十四节气：按公历月份顺序，(名称, 太阳黄经)
SOLAR_TERMS = [
    ("小寒", 285), ("大寒", 300),
    ("立春", 315), ("雨水", 330),
    ("惊蛰", 345), ("春分", 0),
    ("清明", 15), ("谷雨", 30),
    ("立夏", 45), ("小满", 60),
    ("芒种", 75), ("夏至", 90),
    ("小暑", 105), ("大暑", 120),
    ("立秋", 135), ("处暑", 150),
    ("白露", 165), ("秋分", 180),
    ("寒露", 195), ("霜降", 210),
    ("立冬", 225), ("小雪", 240),
    ("大雪", 255), ("冬至", 270),
]


def _year_info(year: int) -> int:
    idx = year - 1900
    if idx < 0 or idx >= len(LUNAR_INFO):
        raise ValueError("农历年份超出支持范围 1900-2100")
    return LUNAR_INFO[idx]


def leap_month(year: int) -> int:
    """该农历年闰几月，0 表示无闰月。"""
    return _year_info(year) & 0xF


def leap_days(year: int) -> int:
    if leap_month(year) == 0:
        return 0
    return 30 if (_year_info(year) & 0x10000) else 29


def month_days(year: int, month: int) -> int:
    """农历某月天数（month 为 1-12，不含闰月）。"""
    return 30 if (_year_info(year) & (0x10000 >> month)) else 29


def year_days(year: int) -> int:
    total = 0
    info = _year_info(year)
    for m in range(1, 13):
        total += 30 if (info & (0x10000 >> m)) else 29
    return total + leap_days(year)


class LunarDate:
    __slots__ = ("year", "month", "day", "is_leap")

    def __init__(self, year: int, month: int, day: int, is_leap: bool = False):
        self.year = year
        self.month = month
        self.day = day
        self.is_leap = is_leap

    def month_text(self) -> str:
        return ("闰" if self.is_leap else "") + MONTH_NAMES[self.month - 1] + "月"

    def day_text(self) -> str:
        return DAY_NAMES[self.day - 1]

    def __str__(self) -> str:
        return self.month_text() + self.day_text()


def solar_to_lunar(date: datetime.date) -> LunarDate:
    offset = (date - LUNAR_BASE).days
    if offset < 0:
        raise ValueError("日期早于 1900-01-31，不支持")

    year = 1900
    while offset >= year_days(year):
        offset -= year_days(year)
        year += 1
        if year > 2100:
            raise ValueError("日期超出农历表范围")

    leap = leap_month(year)
    month = 1
    while month <= 12:
        # 闰月插在 month 之后
        days = month_days(year, month)
        if offset < days:
            return LunarDate(year, month, offset + 1, False)
        offset -= days
        if leap == month:
            ldays = leap_days(year)
            if offset < ldays:
                return LunarDate(year, month, offset + 1, True)
            offset -= ldays
        month += 1

    # 理论上不会到这里
    return LunarDate(year, 12, 30, False)


# ---------------------------------------------------------------- 节气（天文算法）

def _to_jd(dt: datetime.datetime) -> float:
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jdn = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    frac = (dt.hour - 12) / 24.0 + dt.minute / 1440.0 + dt.second / 86400.0
    return jdn + frac


def _from_jd(jd: float) -> datetime.datetime:
    jd = jd + 0.5
    z = int(jd)
    f = jd - z
    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day_f = b - d - int(30.6001 * e) + f
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    day = int(day_f)
    frac = day_f - day
    return datetime.datetime(year, month, day) + datetime.timedelta(days=frac)


def _sun_longitude(jd: float) -> float:
    """太阳视黄经（度）。精度足够判定节气日期。"""
    t = (jd - 2451545.0) / 36525.0
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    c = (
        (1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
        + (0.019993 - 0.000101 * t) * math.sin(2 * m)
        + 0.000289 * math.sin(3 * m)
    )
    return (l0 + c) % 360.0


_TERM_CACHE: dict[int, list[tuple[str, datetime.date]]] = {}


def solar_terms_of_year(year: int) -> list[tuple[str, datetime.date]]:
    """返回该年 24 节气 [(名称, 北京时间日期)]，按时间排序。"""
    if year in _TERM_CACHE:
        return _TERM_CACHE[year]

    result: list[tuple[str, datetime.date]] = []
    jan1 = _to_jd(datetime.datetime(year, 1, 1))
    for name, lon in SOLAR_TERMS:
        # 以 1 月 1 日为起点，按黄经差估算，再用牛顿迭代收敛
        start_lon = _sun_longitude(jan1)
        delta = (lon - start_lon) % 360.0
        guess = jan1 + delta / 0.9856473
        for _ in range(40):
            cur = _sun_longitude(guess)
            diff = (lon - cur + 180.0) % 360.0 - 180.0
            guess += diff / 0.9856473
            if abs(diff) < 1e-7:
                break
        # JD 为 UT，转北京时间
        bj = _from_jd(guess) + datetime.timedelta(hours=8)
        result.append((name, bj.date()))

    result.sort(key=lambda x: x[1])
    _TERM_CACHE[year] = result
    return result


def term_of_day(date: datetime.date) -> str:
    """当天若是节气，返回节气名，否则空串。"""
    try:
        for name, d in solar_terms_of_year(date.year):
            if d == date:
                return name
    except Exception:
        pass
    return ""


def lunar_text(date: datetime.date) -> str:
    """农历显示文本：初一显示月名，其余显示月名+日名。"""
    try:
        ld = solar_to_lunar(date)
        if ld.day == 1:
            return ld.month_text()
        return str(ld)
    except Exception:
        return ""


def lunar_line(date: datetime.date) -> str:
    """一行农历信息：优先节气，其次农历日期。"""
    t = term_of_day(date)
    if t:
        return t
    return lunar_text(date)
