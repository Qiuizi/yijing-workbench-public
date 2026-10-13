from __future__ import annotations

import pytest

from backend.catalog import load_catalog
from backend.core.hexagram import calculate_hexagram
from backend.core.reading_rules import choose_traditional_reading


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


def read(lines: list[int], catalog):
    calculation = calculate_hexagram(lines, catalog.by_code)
    return calculation, choose_traditional_reading(
        calculation,
        catalog.by_id[calculation.base_id],
        catalog.by_id[calculation.changed_id],
    )


def test_no_moving_lines_uses_original_judgment(catalog):
    calculation, reading = read([7] * 6, catalog)
    assert calculation.base_id == calculation.changed_id == 1
    assert reading.moving_count == 0
    assert [(p.kind, p.text) for p in reading.passages] == [
        ("judgment", catalog.by_id[1]["judgment"])
    ]
    assert "内卦为贞" in reading.rationale


def test_one_moving_line_uses_that_base_line(catalog):
    _, reading = read([9, 7, 7, 7, 7, 7], catalog)
    assert [(p.kind, p.line_position, p.text) for p in reading.passages] == [
        ("line", 1, catalog.by_id[1]["line_texts"][0])
    ]


def test_two_moving_lines_use_both_with_upper_line_primary(catalog):
    _, reading = read([7, 6, 7, 7, 9, 7], catalog)
    assert [(p.line_position, p.primary) for p in reading.passages] == [(2, False), (5, True)]
    assert "据例推定" in reading.rationale


@pytest.mark.parametrize(
    ("lines", "primary"),
    [([6, 7, 6, 9, 7, 7], "base"), ([7, 6, 7, 6, 7, 6], "changed")],
)
def test_three_moving_lines_use_both_judgments_with_documented_priority(
    catalog, lines, primary
):
    calculation, reading = read(lines, catalog)
    assert len(reading.passages) == 2
    assert reading.passages[0].primary is True
    expected_order = calculation.base_id if primary == "base" else calculation.changed_id
    assert reading.passages[0].hexagram_order == expected_order
    assert all(p.kind == "judgment" for p in reading.passages)


def test_four_moving_lines_use_changed_hexagrams_two_unchanging_lines(catalog):
    _, reading = read([6, 9, 7, 7, 9, 6], catalog)
    assert [(p.line_position, p.primary) for p in reading.passages] == [(3, True), (4, False)]
    assert all("之卦" in p.label for p in reading.passages)
    assert "据例推定" in reading.rationale


def test_five_moving_lines_use_the_single_unchanging_line_on_changed_hexagram(catalog):
    _, reading = read([6, 7, 9, 6, 9, 6], catalog)
    assert len(reading.passages) == 1
    assert reading.passages[0].kind == "line"
    assert reading.passages[0].line_position == 2
    assert reading.passages[0].hexagram_order != 0


@pytest.mark.parametrize(
    ("lines", "order", "special_name"),
    [([9] * 6, 1, "用九"), ([6] * 6, 2, "用六")],
)
def test_six_moving_qian_kun_use_the_special_line(catalog, lines, order, special_name):
    _, reading = read(lines, catalog)
    assert reading.moving_count == 6
    assert len(reading.passages) == 1
    assert reading.passages[0].kind == "special_line"
    assert reading.passages[0].label == special_name
    assert reading.passages[0].hexagram_order == order


def test_six_moving_other_hexagram_uses_changed_judgment(catalog):
    _, reading = read([9, 9, 9, 9, 9, 6], catalog)
    assert reading.moving_count == 6
    assert reading.passages[0].kind == "judgment"
    assert reading.passages[0].hexagram_order != 1
    assert reading.passages[0].hexagram_order != 2


def test_rule_result_keeps_originals_and_plain_rule_note_separate(catalog):
    _, reading = read([9, 7, 7, 7, 7, 7], catalog)
    assert reading.ruleset_id == "qiming-tongshi"
    assert reading.ruleset_version == "1.0.0"
    assert reading.source_revision_id > 0
    assert reading.passages[0].source_revision_id is not None
    assert "本卦有1条动爻" in reading.plain_rule_explanation
    assert "不构成对原文义理" in reading.interpretation_limit
