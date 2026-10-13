from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest

from backend.catalog import load_catalog
from backend.core.hexagram import calculate_hexagram
from backend.core.najia import (
    PALACE_POSITION_NAMES,
    SPIRIT_START,
    SEXAGENARY_CYCLE,
    SOURCE_RECORDS,
    TRIGRAM_NAJIA,
    _palace_members,
    build_najia_chart,
    validate_day_ganzhi,
    xunkong_for_day,
)


EXPECTED_PALACES = {
    "乾": ["乾为天", "天风姤", "天山遁", "天地否", "风地观", "山地剥", "火地晋", "火天大有"],
    "坎": ["坎为水", "水泽节", "水雷屯", "水火既济", "泽火革", "雷火丰", "地火明夷", "地水师"],
    "艮": ["艮为山", "山火贲", "山天大畜", "山泽损", "火泽睽", "天泽履", "风泽中孚", "风山渐"],
    "震": ["震为雷", "雷地豫", "雷水解", "雷风恒", "地风升", "水风井", "泽风大过", "泽雷随"],
    "巽": ["巽为风", "风天小畜", "风火家人", "风雷益", "天雷无妄", "火雷噬嗑", "山雷颐", "山风蛊"],
    "离": ["离为火", "火山旅", "火风鼎", "火水未济", "山水蒙", "风水涣", "天水讼", "天火同人"],
    "坤": ["坤为地", "地雷复", "地泽临", "地天泰", "雷天大壮", "泽天夬", "水天需", "水地比"],
    "兑": ["兑为泽", "泽水困", "泽地萃", "泽山咸", "水山蹇", "地山谦", "雷山小过", "雷泽归妹"],
}

# Independent transcription of the eight-trigram table shown in the cited source.
EXPECTED_PURE_NAJIA = {
    "乾": ("甲", ("子", "寅", "辰"), "壬", ("午", "申", "戌")),
    "震": ("庚", ("子", "寅", "辰"), "庚", ("午", "申", "戌")),
    "坎": ("戊", ("寅", "辰", "午"), "戊", ("申", "戌", "子")),
    "艮": ("丙", ("辰", "午", "申"), "丙", ("戌", "子", "寅")),
    "坤": ("乙", ("未", "巳", "卯"), "癸", ("丑", "亥", "酉")),
    "巽": ("辛", ("丑", "亥", "酉"), "辛", ("未", "巳", "卯")),
    "离": ("己", ("卯", "丑", "亥"), "己", ("酉", "未", "巳")),
    "兑": ("丁", ("巳", "卯", "丑"), "丁", ("亥", "酉", "未")),
}


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


def values_for_code(code: str) -> tuple[int, ...]:
    return tuple(7 if bit == "1" else 8 for bit in reversed(code))


def chart_for_entry(entry, catalog, lines=None, day="甲子", month="子"):
    line_values = tuple(lines or values_for_code(entry["binary_code"]))
    calculation = calculate_hexagram(line_values, catalog.by_code)
    return build_najia_chart(
        calculation=calculation,
        base_hexagram=catalog.by_id[calculation.base_id],
        changed_hexagram=catalog.by_id[calculation.changed_id],
        day_ganzhi=day,
        month_branch=month,
        catalog=catalog,
    )


def test_all_eight_palace_sequences_match_the_published_table(catalog):
    members = _palace_members(catalog)
    assert len(members) == 64
    for palace, titles in EXPECTED_PALACES.items():
        actual = sorted(
            (assignment.position_index, catalog.by_id[catalog.by_code[code]]["title"])
            for code, assignment in members.items()
            if assignment.palace == palace
        )
        assert [title for _, title in actual] == titles
        assert [position for position, _ in actual] == list(range(8))
        assert all(name == PALACE_POSITION_NAMES[index] for index, name in enumerate(PALACE_POSITION_NAMES))
        expected_world_by_position = (6, 1, 2, 3, 4, 5, 4, 3)
        assert all(
            assignment.world_position == expected_world_by_position[assignment.position_index]
            and assignment.response_position == (assignment.world_position - 1 + 3) % 6 + 1
            for code, assignment in members.items()
            if assignment.palace == palace
        )


@pytest.mark.parametrize("trigram", EXPECTED_PURE_NAJIA)
def test_eight_pure_trigram_najia_rows_match_the_reference_table(catalog, trigram):
    pure_code = next(code for code, record in TRIGRAM_NAJIA.items() if record["name"] == trigram) * 2
    entry = catalog.by_id[catalog.by_code[pure_code]]
    chart = chart_for_entry(entry, catalog)
    stem_inner, branches_inner, stem_outer, branches_outer = EXPECTED_PURE_NAJIA[trigram]
    lines = chart["base"]["lines"]
    assert [(line["stem"], line["branch"]) for line in lines] == [
        *[(stem_inner, branch) for branch in branches_inner],
        *[(stem_outer, branch) for branch in branches_outer],
    ]


def test_all_64_hexagrams_have_six_valid_najia_lines(catalog):
    seen: set[str] = set()
    for entry in catalog.entries:
        chart = chart_for_entry(entry, catalog)
        seen.add(chart["base"]["binary_code"])
        assert chart["base"]["hexagram_order"] == entry["wenwang_order"]
        assert len(chart["base"]["lines"]) == 6
        assert [line["position"] for line in chart["base"]["lines"]] == [1, 2, 3, 4, 5, 6]
        assert all(line["stem"] and line["branch"] and line["element"] and line["relative"] for line in chart["base"]["lines"])
    assert len(seen) == 64


def test_all_4096_line_values_keep_changed_board_in_sync(catalog):
    for lines in itertools.product((6, 7, 8, 9), repeat=6):
        calculation = calculate_hexagram(lines, catalog.by_code)
        chart = build_najia_chart(
            calculation=calculation,
            base_hexagram=catalog.by_id[calculation.base_id],
            changed_hexagram=catalog.by_id[calculation.changed_id],
            day_ganzhi="甲子",
            month_branch="寅",
            catalog=catalog,
        )
        assert chart["base"]["binary_code"] == calculation.base_code
        assert chart["changed"]["binary_code"] == calculation.changed_code
        assert [line["position"] for line in chart["changed"]["lines"]] == [1, 2, 3, 4, 5, 6]
        assert [line["moving"] for line in chart["base"]["lines"]] == [value in (6, 9) for value in lines]


@pytest.mark.parametrize(
    ("ganzhi", "expected"),
    [("甲子", ("戌", "亥")), ("甲戌", ("申", "酉")), ("甲申", ("午", "未")),
     ("甲午", ("辰", "巳")), ("甲辰", ("寅", "卯")), ("甲寅", ("子", "丑"))],
)
def test_xunkong_for_all_six_decade_heads(ganzhi, expected):
    assert xunkong_for_day(ganzhi) == expected


def test_manual_ganzhi_validation_and_no_automatic_calendar_guess(catalog):
    assert len([validate_day_ganzhi(ganzhi) for ganzhi in SEXAGENARY_CYCLE]) == 60
    with pytest.raises(ValueError, match="六十甲子"):
        validate_day_ganzhi("甲丑")
    with pytest.raises(ValueError, match="月建"):
        chart_for_entry(catalog.by_id[1], catalog, month="未知")


def test_six_relatives_six_spirits_and_world_response_are_explicit(catalog):
    chart = chart_for_entry(catalog.by_id[1], catalog, day="甲子", month="子")
    lines = chart["base"]["lines"]
    assert [line["relative"] for line in lines] == ["子孙", "妻财", "父母", "官鬼", "兄弟", "父母"]
    assert [line["spirit"] for line in lines] == ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"]
    assert chart["world_position"] == 6
    assert chart["response_position"] == 3
    assert lines[5]["role"] == "世"
    assert lines[2]["role"] == "应"


@pytest.mark.parametrize("stem", ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"))
def test_six_spirit_starts_follow_all_ten_day_stems(catalog, stem):
    day_ganzhi = next(item for item in SEXAGENARY_CYCLE if item.startswith(stem))
    chart = chart_for_entry(catalog.by_id[1], catalog, day=day_ganzhi)
    expected = ("青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武")
    start = SPIRIT_START[stem]
    assert [line["spirit"] for line in chart["base"]["lines"]] == [expected[(start + index) % 6] for index in range(6)]


def test_cited_sources_are_fixed_revisions_and_identify_editorial_material():
    assert all(source["url"].endswith(f"oldid={source['revision_id']}") for source in SOURCE_RECORDS)
    supplements = [source for source in SOURCE_RECORDS if "增补" in source["title"]]
    assert supplements and all(source["revision_id"] == 2572918 for source in supplements)


def test_all_64_najia_boards_match_pinned_ichingpy_reference(catalog):
    reference_path = Path(__file__).parent / "data" / "ichingpy_najia_reference.json"
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    assert reference["commit"] == "01e50a25d7b1d696ff9c8b9fa5d718a5ca0f63a8"
    assert reference["license"] == "MIT"
    assert len(reference["cases"]) == 64
    for expected in reference["cases"]:
        entry_id = catalog.by_code[expected["code"]]
        chart = chart_for_entry(catalog.by_id[entry_id], catalog)
        actual_lines = [
            f"{line['stem']}{line['branch']}|{line['relative']}|{line['role'] or ''}"
            for line in chart["base"]["lines"]
        ]
        assert chart["palace"] == expected["palace"]
        assert actual_lines == expected["lines"]


def test_fushen_and_flying_line_match_the_published_examples(catalog):
    # 天风姤: missing 妻财, with 寅木伏在二爻亥水下.
    gua = next(entry for entry in catalog.entries if entry["title"] == "天风姤")
    chart = chart_for_entry(gua, catalog)
    second = chart["base"]["lines"][1]
    assert (second["hidden_relative"], second["hidden_branch"], second["hidden_element"]) == ("妻财", "寅", "木")
    assert (second["branch"], second["flying_relative"]) == ("亥", "子孙")
    assert second["branch"] == "亥" and second["hidden_branch"] == "寅"  # 飞水生伏木

    # 天山遁: missing 子孙 uses Qian palace's 初爻子水, hidden below its first line.
    dun = next(entry for entry in catalog.entries if entry["title"] == "天山遁")
    chart = chart_for_entry(dun, catalog)
    first = chart["base"]["lines"][0]
    assert (first["hidden_relative"], first["hidden_branch"], first["hidden_element"]) == ("子孙", "子", "水")
    assert (first["branch"], first["element"], first["flying_relative"]) == ("辰", "土", "父母")  # 飞土克伏水


def test_fushen_cases_match_the_pinned_primary_text_transcription(catalog):
    source_path = Path(__file__).parent / "data" / "najia_fushen_reference.json"
    reference = json.loads(source_path.read_text(encoding="utf-8"))
    assert reference["source"]["revision_id"] == 2572918
    assert len(reference["cases"]) == 4
    for expected in reference["cases"]:
        entry = next(item for item in catalog.entries if item["title"] == expected["hexagram"])
        lines = chart_for_entry(entry, catalog)["base"]["lines"]
        actual = next(item for item in lines if item["position"] == expected["position"])
        assert {
            "hidden_relative": actual["hidden_relative"],
            "hidden_branch": actual["hidden_branch"],
            "hidden_element": actual["hidden_element"],
            "flying_branch": actual["branch"],
            "flying_element": actual["element"],
        } == {
            "hidden_relative": expected["hidden_relative"],
            "hidden_branch": expected["hidden_branch"],
            "hidden_element": expected["hidden_element"],
            "flying_branch": expected["flying_branch"],
            "flying_element": expected["flying_element"],
        }


def test_chart_labels_month_build_xunkong_and_changed_hexagram(catalog):
    chart = chart_for_entry(catalog.by_id[1], catalog, lines=[9, 7, 7, 7, 7, 7], day="甲子", month="子")
    assert chart["xunkong"] == ["戌", "亥"]
    assert chart["base"]["lines"][0]["month_build"] is True
    assert chart["changed"]["hexagram_title"] == "天风姤"
    assert chart["changed"]["lines"][0]["moving"] is True
    assert chart["changed"]["lines"][0]["role"] is None
    assert chart["timestamp_source"] == "manual"
