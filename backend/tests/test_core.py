from __future__ import annotations

import itertools
import random
from copy import deepcopy
from collections import Counter

import pytest

from backend.catalog import HexagramCatalog, load_catalog
from backend.core.casting import cast_line, cast_six_lines
from backend.core.hexagram import binary_code, calculate_hexagram, validate_lines


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


def test_catalog_is_complete_and_matches_wenwang_sequence(catalog):
    expected_names = (
        "乾 坤 屯 蒙 需 讼 师 比 小畜 履 泰 否 同人 大有 谦 豫 随 蛊 临 观 噬嗑 贲 剥 复 无妄 大畜 颐 大过 坎 离 "
        "咸 恒 遁 大壮 晋 明夷 家人 睽 蹇 解 损 益 夬 姤 萃 升 困 井 革 鼎 震 艮 渐 归妹 丰 旅 巽 兑 涣 节 中孚 小过 既济 未济"
    ).split()
    trigram_bottom_to_top = {
        "乾": "111", "兑": "110", "离": "101", "震": "100",
        "巽": "011", "坎": "010", "艮": "001", "坤": "000",
    }

    assert len(catalog.entries) == 64
    assert len(catalog.by_code) == 64
    assert set(catalog.by_id) == set(range(1, 65))
    assert [catalog.by_id[index]["name"] for index in range(1, 65)] == expected_names
    assert len({entry["name"] for entry in catalog.entries}) == 64
    for entry in catalog.entries:
        upper = entry["upper_trigram"]
        lower = entry["lower_trigram"]
        assert entry["binary_code"] == trigram_bottom_to_top[upper["name"]][::-1] + trigram_bottom_to_top[lower["name"]][::-1]
        expected_title = (
            f"{entry['name']}为{upper['image']}"
            if upper["name"] == lower["name"]
            else f"{upper['image']}{lower['image']}{entry['name']}"
        )
        assert entry["title"] == expected_title
        assert len(entry["line_texts"]) == 6
        assert all(line for line in entry["line_texts"])
        assert entry["judgment"]
        assert type(entry["source_revision_id"]) is int
        assert entry["source_revision_id"] > 0
        assert entry["source_url"].endswith(f"oldid={entry['source_revision_id']}")


def test_special_line_data_is_complete_and_keeps_six_regular_lines(catalog):
    qian = catalog.by_id[1]
    kun = catalog.by_id[2]

    assert len(qian["line_texts"]) == len(kun["line_texts"]) == 6
    assert qian["special_line"] == {
        "name": "用九",
        "text": "用九：見羣龍无首，吉。",
        "source_url": qian["source_url"],
    }
    assert kun["special_line"] == {
        "name": "用六",
        "text": "用六：利永貞。",
        "source_url": kun["source_url"],
    }
    assert all("special_line" not in entry for entry in catalog.entries[2:])


def test_catalog_rejects_special_line_on_other_hexagrams(catalog):
    entries = deepcopy(catalog.entries)
    entries[2]["special_line"] = {
        "name": "用九",
        "text": "用九：不应属于第三卦。",
        "source_url": entries[2]["source_url"],
    }

    with pytest.raises(ValueError, match="不能配置乾坤特殊爻辞"):
        HexagramCatalog(entries)


def test_catalog_rejects_special_line_with_wrong_label(catalog):
    entries = deepcopy(catalog.entries)
    entries[0]["special_line"]["name"] = "用六"

    with pytest.raises(ValueError, match="特殊爻辞或出处无效"):
        HexagramCatalog(entries)


def test_key_source_text_is_transcribed_from_the_hexagram_pages(catalog):
    qian = catalog.by_id[1]
    gou = catalog.by_id[44]
    assert qian["judgment"] == "乾：元亨。利貞。"
    assert qian["line_texts"][0] == "初九：潛龍勿用。"
    assert gou["title"] == "天风姤"
    assert gou["judgment"] == "姤：女壯，勿用取女。"
    assert gou["line_texts"][0] == "初六：系于金柅，貞吉，有攸往，見凶，羸豕孚踟躅。"


@pytest.mark.parametrize(
    ("lines", "base_name", "changed_name"),
    [
        ([7, 7, 7, 7, 7, 7], "乾", "乾"),
        ([8, 8, 8, 8, 8, 8], "坤", "坤"),
        ([9, 9, 9, 9, 9, 9], "乾", "坤"),
        ([9, 7, 7, 7, 7, 7], "乾", "姤"),
    ],
)
def test_acceptance_examples(lines, base_name, changed_name, catalog):
    result = calculate_hexagram(lines, catalog.by_code)
    assert catalog.by_id[result.base_id]["name"] == base_name
    assert catalog.by_id[result.changed_id]["name"] == changed_name


def test_all_64_yin_yang_patterns_map_to_unique_hexagrams(catalog):
    seen = set()
    for bits in itertools.product((0, 1), repeat=6):
        values = tuple(7 if bit else 8 for bit in bits)
        code = binary_code(values)
        result = calculate_hexagram(values, catalog.by_code)
        assert result.base_code == code
        assert result.base_id == catalog.by_code[code]
        assert result.base_id == result.changed_id
        assert result.moving_positions == ()
        seen.add(result.base_id)
    assert seen == set(range(1, 65))


def test_all_4096_line_value_combinations_identify_changes(catalog):
    combinations = itertools.product((6, 7, 8, 9), repeat=6)
    count = 0
    for lines in combinations:
        result = calculate_hexagram(lines, catalog.by_code)
        expected_changed = tuple(15 - value if value in (6, 9) else value for value in lines)
        expected_positions = tuple(index + 1 for index, value in enumerate(lines) if value in (6, 9))
        assert result.changed_lines == expected_changed
        assert result.moving_positions == expected_positions
        assert result.changed_code == binary_code(expected_changed)
        assert result.base_id == catalog.by_code[binary_code(lines)]
        assert result.changed_id == catalog.by_code[binary_code(expected_changed)]
        count += 1
    assert count == 4096


class FixedCoinSource:
    def __init__(self, outcomes: tuple[int, ...]):
        self._outcomes = iter(outcomes)

    def choice(self, options: tuple[int, int]) -> int:
        outcome = next(self._outcomes)
        assert outcome in options
        return outcome


def test_controlled_coin_source_maps_all_eight_coin_patterns_to_line_values():
    sums = Counter()
    for outcomes in itertools.product((2, 3), repeat=3):
        result = cast_line(FixedCoinSource(outcomes))
        assert result.coins == outcomes
        assert result.value == sum(outcomes)
        sums[result.value] += 1
    assert sums == {6: 1, 7: 3, 8: 3, 9: 1}


def test_seeded_source_is_repeatable_and_six_lines_are_bottom_to_top():
    first = cast_six_lines(random.Random(20260924))
    second = cast_six_lines(random.Random(20260924))
    assert first == second
    assert len(first) == 6
    assert all(line.value == sum(line.coins) for line in first)
    assert all(face in (2, 3) for line in first for face in line.coins)


def test_coin_sum_probabilities_follow_three_independent_fair_coins():
    rng = random.Random(20260924)
    sample_size = 100_000
    counts = Counter(cast_line(rng).value for _ in range(sample_size))
    expected_probabilities = {6: 0.125, 7: 0.375, 8: 0.375, 9: 0.125}
    chi_square = sum(
        (counts[value] - sample_size * probability) ** 2 / (sample_size * probability)
        for value, probability in expected_probabilities.items()
    )
    assert chi_square < 16.27  # chi-square(3 df), p = 0.001


@pytest.mark.parametrize("lines", [[], [7] * 5, [7] * 7, [7, 7, 7, 7, 7, 7.0], [True, 7, 7, 7, 7, 7], [5, 7, 7, 7, 7, 7]])
def test_manual_line_validation_rejects_invalid_values(lines):
    with pytest.raises(ValueError):
        validate_lines(lines)
