"""Automatic civil-time to 六爻 calendar inputs.

This service owns timezone and calendar conventions. The Najia engine receives
only the resolved day Ganzhi and month branch and remains calendar-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from importlib import metadata, resources
from zoneinfo import ZoneInfo

from lunar_python import Solar


CALENDAR_RULESET_ID = "yijing-local-civil-calendar"
CALENDAR_RULESET_VERSION = "1.0.0"
MIN_SUPPORTED_YEAR = 1901
MAX_SUPPORTED_YEAR = 2100
_UTC = timezone.utc
_BEIJING_STANDARD_TIME = timezone(timedelta(hours=8), name="UTC+08:00")


class CalendarInputError(ValueError):
    """A user-visible error that must not silently fall back to another clock."""


@dataclass(frozen=True)
class CalendarResult:
    day_ganzhi: str
    month_branch: str
    context: dict[str, str]


def load_iana_timezone(name: str) -> ZoneInfo:
    """Load the exact pinned PyPI tzdata database, including on Windows."""
    if not name or len(name) > 100 or "\\" in name or name.startswith("/"):
        raise CalendarInputError("请输入有效的 IANA 时区标识，例如 Asia/Shanghai")
    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise CalendarInputError("请输入有效的 IANA 时区标识，例如 Asia/Shanghai")
    try:
        zone_file = resources.files("tzdata.zoneinfo").joinpath(*parts)
        with zone_file.open("rb") as file:
            return ZoneInfo.from_file(file, key=name)
    except (ModuleNotFoundError, FileNotFoundError, OSError, ValueError) as exc:
        raise CalendarInputError("未找到该 IANA 时区，请检查时区名称或使用手动排盘") from exc


def parse_local_datetime(value: str) -> datetime:
    """Parse a local wall-clock value; offsets are forbidden by contract."""
    if not isinstance(value, str):
        raise CalendarInputError("请选择本地日期和时间")
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.strftime(fmt) == value:
                if not MIN_SUPPORTED_YEAR <= parsed.year <= MAX_SUPPORTED_YEAR:
                    raise CalendarInputError(
                        f"自动历法仅接受 {MIN_SUPPORTED_YEAR}–{MAX_SUPPORTED_YEAR} 年；请改用手动排盘"
                    )
                return parsed
        except CalendarInputError:
            raise
        except ValueError:
            continue
    raise CalendarInputError("日期时间格式应为 YYYY-MM-DDTHH:MM，且不附带 UTC 偏移")


def _resolve_local_instant(local: datetime, zone: ZoneInfo) -> datetime:
    candidates: dict[timedelta | None, datetime] = {}
    for fold in (0, 1):
        aware = local.replace(tzinfo=zone, fold=fold)
        utc_value = aware.astimezone(_UTC)
        round_trip = utc_value.astimezone(zone)
        if round_trip.replace(tzinfo=None) == local:
            candidates[aware.utcoffset()] = aware
    if not candidates:
        raise CalendarInputError("该本地时间因夏令时调整而不存在；请选择其他时间或手动排盘")
    if len(candidates) > 1:
        raise CalendarInputError("该本地时间因夏令时回拨出现两次；请选择无歧义时间或手动排盘")
    return next(iter(candidates.values()))


def calculate_calendar_inputs(local_datetime: str, timezone_name: str) -> CalendarResult:
    local = parse_local_datetime(local_datetime)
    zone = load_iana_timezone(timezone_name)
    aware_local = _resolve_local_instant(local, zone)
    instant_utc = aware_local.astimezone(_UTC)

    # The published lunar-python solar-term table is expressed as Beijing time.
    # Resolve month建 against the same absolute instant, converted to fixed UTC+08.
    beijing = instant_utc.astimezone(_BEIJING_STANDARD_TIME)
    term_lunar = Solar.fromYmdHms(
        beijing.year, beijing.month, beijing.day, beijing.hour, beijing.minute, beijing.second
    ).getLunar()

    # Day Ganzhi follows the selected zone's civil date. Exact2 assigns the
    # 23:00–23:59 late-Zi hour to that same civil date; the date turns at 00:00.
    day_lunar = Solar.fromYmdHms(
        local.year, local.month, local.day, local.hour, local.minute, local.second
    ).getLunar()
    day_ganzhi = day_lunar.getDayInGanZhiExact2()
    month_branch = term_lunar.getMonthZhiExact()
    if len(day_ganzhi) != 2 or month_branch not in "子丑寅卯辰巳午未申酉戌亥":
        raise CalendarInputError("历法计算未返回有效干支，请改用手动排盘")

    offset = aware_local.strftime("%z")
    offset = f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"
    context = {
        "ruleset_id": CALENDAR_RULESET_ID,
        "ruleset_version": CALENDAR_RULESET_VERSION,
        "engine": "lunar_python",
        "engine_version": metadata.version("lunar_python"),
        "timezone_database": "tzdata",
        "timezone_database_version": metadata.version("tzdata"),
        # Preserve the exact user input for historical audit and replay.
        "local_datetime": local_datetime,
        "timezone": timezone_name,
        "utc_offset": offset,
        "utc_instant": instant_utc.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "day_ganzhi": day_ganzhi,
        "day_rule": "按所选 IANA 时区的民用日期；00:00 换日；23:00–23:59 子时仍计当日。",
        "month_branch": month_branch,
        "month_rule": "按该绝对时刻换算为固定 UTC+08:00 后，以节气交接计算月建。",
        "jieqi_reference_timezone": "UTC+08:00",
    }
    return CalendarResult(day_ganzhi=day_ganzhi, month_branch=month_branch, context=context)
