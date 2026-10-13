from __future__ import annotations

from copy import deepcopy
from itertools import product

import pytest

from backend.catalog import load_catalog
from backend.core.hexagram import calculate_hexagram
from backend.core.najia import BRANCH_ELEMENTS, build_najia_chart
from backend.core.najia_analysis import (
    LIU_CHONG,
    LIU_HE,
    QUESTION_CATEGORIES,
    RULESET_ID,
    RULESET_VERSION,
    SOURCE_RECORDS_ANALYSIS,
    analyze_branch_relations,
    analyze_moving_changes,
    analyze_najia_chart,
    analyze_time_relations,
    analyze_use_god_assist,
    earthly_branch_relation,
    five_element_relation,
)


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


def make_chart(catalog, title: str, moving_positions: tuple[int, ...] = ()):
    entry = next(item for item in catalog.entries if item["title"] == title)
    values = tuple(
        (9 if position in moving_positions else 7) if bit == "1"
        else (6 if position in moving_positions else 8)
        for position, bit in enumerate(reversed(entry["binary_code"]), start=1)
    )
    calculation = calculate_hexagram(values, catalog.by_code)
    return build_najia_chart(
        calculation=calculation,
        base_hexagram=catalog.by_id[calculation.base_id],
        changed_hexagram=catalog.by_id[calculation.changed_id],
        day_ganzhi="甲子",
        month_branch="午",
        catalog=catalog,
    )


def test_rule_ids_and_use_god_candidates_are_source_labelled_and_not_auto_selected(catalog):
    chart = make_chart(catalog, "乾为天")
    result = analyze_use_god_assist(
        chart["base"], question_category="wealth_spouse", manual_candidate=None
    )
    assert result["ruleset"] == {"id": RULESET_ID, "version": RULESET_VERSION}
    assert result["results"]["candidate_relative"] == "妻财"
    assert [(item["position"], item["relative"]) for item in result["results"]["candidates"]] == [(2, "妻财")]
    assert result["results"]["manual_selection"] is None
    assert result["results"]["selection_basis"] == "未指定"
    assert result["sources"][0]["revision_id"] == 2100700
    assert "不自动裁定唯一" in result["explanation"]


def test_every_analysis_citation_uses_a_fixed_wikisource_revision():
    assert SOURCE_RECORDS_ANALYSIS
    for source in SOURCE_RECORDS_ANALYSIS:
        assert source["url"].endswith(f"oldid={source['revision_id']}")
        assert source["revision_id"] > 0


def test_use_god_support_lists_existing_and_hidden_candidates_and_honors_manual_choice(catalog):
    chart = make_chart(catalog, "天风姤")
    result = analyze_use_god_assist(
        chart["base"], question_category="wealth_spouse", manual_candidate="hidden:2"
    )
    candidates = result["results"]["candidates"]
    assert any(item["kind"] == "伏神候选" and item["branch"] == "寅" for item in candidates)
    assert result["results"]["manual_selection"]["id"] == "hidden:2"
    assert result["results"]["manual_selection"]["branch"] == "寅"
    assert result["results"]["manual_selection"]["flying_element_relation"] == "source_generates_target"
    assert result["results"]["selection_basis"] == "manual"
    assert result["inputs"]["manual_candidate"] == "hidden:2"

    dun = make_chart(catalog, "天山遁")
    dun_result = analyze_use_god_assist(
        dun["base"], question_category="descendant_student", manual_candidate="hidden:1"
    )
    assert dun_result["results"]["manual_selection"]["flying_element_relation"] == "source_controls_target"


def test_question_category_table_stays_with_the_cited_text_scope():
    expected = {
        "parent_elder_document": "父母",
        "sibling": "兄弟",
        "wealth_spouse": "妻财",
        "descendant_student": "子孙",
        "official_career": "官鬼",
        "medicine": "子孙",
    }
    assert {key: value["relative"] for key, value in QUESTION_CATEGORIES.items()} == expected
    assert all(value["source_id"] == "zengshan-use-god-chapter-8" for value in QUESTION_CATEGORIES.values())


def test_element_relation_is_directional_and_covers_all_25_pairs():
    elements = ("木", "火", "土", "金", "水")
    results = {(source, target): five_element_relation(source, target) for source, target in product(elements, repeat=2)}
    assert len(results) == 25
    assert all(results[(element, element)] == "比和" for element in elements)
    assert results[("木", "火")] == "source_generates_target"
    assert results[("火", "木")] == "target_generates_source"
    assert results[("木", "土")] == "source_controls_target"
    assert results[("土", "木")] == "target_controls_source"
    assert set(results.values()) == {
        "比和", "source_generates_target", "target_generates_source",
        "source_controls_target", "target_controls_source",
    }


def test_six_pairs_are_complete_symmetric_and_disjoint():
    assert len(LIU_HE) == len(LIU_CHONG) == 6
    assert LIU_HE.isdisjoint(LIU_CHONG)
    for pair in LIU_HE:
        left, right = tuple(pair)
        assert earthly_branch_relation(left, right) == earthly_branch_relation(right, left) == "六合"
    for pair in LIU_CHONG:
        left, right = tuple(pair)
        assert earthly_branch_relation(left, right) == earthly_branch_relation(right, left) == "六冲"
    assert earthly_branch_relation("子", "卯") is None


def test_month_break_day_clash_and_xunkong_are_reported_separately(catalog):
    chart = make_chart(catalog, "乾为天")
    result = analyze_time_relations(
        chart["base"], day_ganzhi=chart["day_ganzhi"], month_branch=chart["month_branch"], xunkong=chart["xunkong"]
    )
    lines = {line["position"]: line for line in result["results"]["lines"]}
    assert lines[1]["month_break"] is True  # 午月冲子爻
    assert lines[4]["day_clash"] is True    # 甲子日冲午爻
    assert lines[6]["xunkong"] is True      # 甲子旬空戌亥
    assert "日冲不自动判作暗动或日破" in result["explanation"]
    assert result["inputs"]["day_ganzhi"] == "甲子"
    assert any(source["revision_id"] == 2100331 for source in result["sources"])

    gou = make_chart(catalog, "天风姤")
    gou_lines = analyze_time_relations(
        gou["base"], day_ganzhi=gou["day_ganzhi"], month_branch=gou["month_branch"], xunkong=gou["xunkong"]
    )["results"]["lines"]
    assert gou_lines[0]["branch"] == "丑"
    assert gou_lines[0]["day_branch_relation"] == "六合"


def test_hexagram_pairing_matches_published_liuhe_and_liuchong_examples(catalog):
    liuhe = analyze_branch_relations(make_chart(catalog, "天地否")["base"], make_chart(catalog, "天地否")["changed"])
    liuchong = analyze_branch_relations(make_chart(catalog, "乾为天")["base"], make_chart(catalog, "乾为天")["changed"])
    assert liuhe["results"]["base_hexagram_relation"]["kind"] == "六合卦"
    assert [line["relation"] for line in liuhe["results"]["base_hexagram_relation"]["paired_lines"]] == ["六合"] * 3
    assert liuchong["results"]["base_hexagram_relation"]["kind"] == "六冲卦"
    assert [line["relation"] for line in liuchong["results"]["base_hexagram_relation"]["paired_lines"]] == ["六冲"] * 3
    assert liuhe["sources"][0]["revision_id"] == 2100447


def test_all_64_hexagrams_have_only_expected_ten_liuchong_and_eight_liuhe(catalog):
    found = {"六合卦": set(), "六冲卦": set()}
    for entry in catalog.entries:
        chart = make_chart(catalog, entry["title"])
        analysis = analyze_branch_relations(chart["base"], chart["changed"])
        kind = analysis["results"]["base_hexagram_relation"]["kind"]
        if kind:
            found[kind].add(entry["title"])
    assert found["六合卦"] == {
        "天地否", "地天泰", "水泽节", "泽水困", "山火贲", "火山旅", "雷地豫", "地雷复",
    }
    assert found["六冲卦"] == {
        "乾为天", "坤为地", "坎为水", "离为火", "震为雷", "巽为风", "艮为山", "兑为泽",
        "天雷无妄", "雷天大壮",
    }


def test_moving_line_reports_corresponding_changed_branch_without_interpreting_outcome(catalog):
    chart = make_chart(catalog, "乾为天", moving_positions=(1,))
    result = analyze_moving_changes(chart["base"], chart["changed"])
    transition, = result["results"]["transitions"]
    assert transition["position"] == 1
    assert transition["from"] == {"relative": "子孙", "branch": "子", "element": "水"}
    assert transition["to"]["branch"] == "丑"
    assert transition["branch_relation"] == "六合"
    assert transition["element_relation"] == "target_controls_source"
    assert "不据此自动判定" in result["explanation"]


def test_each_analysis_can_be_independently_disabled_and_never_mutates_chart(catalog):
    chart = make_chart(catalog, "天风姤", moving_positions=(1,))
    before = deepcopy(chart)
    result = analyze_najia_chart(
        chart,
        enabled={"use_god": True, "time_relations": False, "branch_relations": True, "moving_changes": False},
        question_category="wealth_spouse",
    )
    assert result["modules"]["use_god"] is not None
    assert result["modules"]["branch_relations"] is not None
    assert result["modules"]["time_relations"] is None
    assert result["modules"]["moving_changes"] is None
    assert chart == before


@pytest.mark.parametrize(
    "left,right",
    [("未知", "子"), ("木", "未知")],
)
def test_unknown_symbols_raise_instead_of_silently_generating_rules(left, right):
    with pytest.raises(ValueError):
        if left in BRANCH_ELEMENTS:
            earthly_branch_relation(left, right)
        else:
            five_element_relation(left, right)
