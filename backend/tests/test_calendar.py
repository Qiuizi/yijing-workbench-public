from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services.calendar import CalendarInputError, calculate_calendar_inputs, parse_local_datetime


REFERENCE = json.loads(
    (Path(__file__).parent / "data" / "hko_calendar_reference.json").read_text(encoding="utf-8")
)


def test_pinned_hko_lunar_day_ganzhi_reference():
    for day, expected in REFERENCE["day_ganzhi"].items():
        result = calculate_calendar_inputs(f"{day}T12:00", "Asia/Hong_Kong")
        assert result.day_ganzhi == expected


def test_hko_lichun_minute_switches_month_branch_on_the_reported_boundary():
    date = REFERENCE["solar_terms"][0]["local_datetime_minute"]
    before = calculate_calendar_inputs(f"{date[:-2]}09", REFERENCE["timezone"])
    after = calculate_calendar_inputs(f"{date[:-2]}11", REFERENCE["timezone"])
    assert before.month_branch == REFERENCE["solar_terms"][0]["month_branch_before"]
    assert after.month_branch == REFERENCE["solar_terms"][0]["month_branch_after"]
    assert before.day_ganzhi == after.day_ganzhi == REFERENCE["day_ganzhi"]["2025-02-03"]


def test_day_ganzhi_uses_selected_zone_civil_date_and_late_zi_same_day():
    at_2300 = calculate_calendar_inputs("2025-02-03T23:00", "Asia/Shanghai")
    at_2359 = calculate_calendar_inputs("2025-02-03T23:59", "Asia/Shanghai")
    after_midnight = calculate_calendar_inputs("2025-02-04T00:00", "Asia/Shanghai")
    assert at_2300.day_ganzhi == at_2359.day_ganzhi == "癸卯"
    assert after_midnight.day_ganzhi == "甲辰"


def test_same_instant_has_same_month_term_across_zones_but_local_civil_day_is_explicit():
    shanghai = calculate_calendar_inputs("2025-02-04T00:30", "Asia/Shanghai")
    utc = calculate_calendar_inputs("2025-02-03T16:30", "UTC")
    assert shanghai.context["utc_instant"] == utc.context["utc_instant"]
    assert shanghai.month_branch == utc.month_branch == "寅"
    assert shanghai.day_ganzhi == "甲辰"
    assert utc.day_ganzhi == "癸卯"


@pytest.mark.parametrize(
    "local_datetime",
    ["2025-03-09T02:30", "2025-11-02T01:30"],
)
def test_daylight_saving_gap_and_fold_are_rejected(local_datetime):
    with pytest.raises(CalendarInputError, match="夏令时"):
        calculate_calendar_inputs(local_datetime, "America/New_York")


def test_unknown_zone_offset_input_and_out_of_range_date_are_rejected():
    with pytest.raises(CalendarInputError, match="IANA"):
        calculate_calendar_inputs("2025-02-03T12:00", "Fake/Nowhere")
    with pytest.raises(CalendarInputError, match="UTC 偏移"):
        parse_local_datetime("2025-02-03T12:00+08:00")
    with pytest.raises(CalendarInputError, match="1901–2100"):
        parse_local_datetime("2101-01-01T12:00")


def test_calendar_result_pins_engine_timezone_database_and_input_provenance():
    result = calculate_calendar_inputs("2025-02-03T22:12", "Asia/Shanghai")
    assert result.context["engine"] == "lunar_python"
    assert result.context["engine_version"] == "1.4.8"
    assert result.context["timezone_database"] == "tzdata"
    assert result.context["timezone_database_version"] == "2026.4"
    assert result.context["timezone"] == "Asia/Shanghai"
    assert result.context["utc_offset"] == "+08:00"
    assert result.context["day_ganzhi"] == result.day_ganzhi
    assert result.context["month_branch"] == result.month_branch


def test_calendar_context_preserves_exact_datetime_input():
    value = "2025-02-03T22:09"
    result = calculate_calendar_inputs(value, "Asia/Shanghai")
    assert result.context["local_datetime"] == value
