"""Source-labelled line-count interpretation rules for the Zhouyi text."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from backend.core.hexagram import HexagramCalculation


RULESET_ID = "qiming-tongshi"
RULESET_VERSION = "1.0.0"
RULESET_NAME = "启蒙占法（据《易学启蒙通释·考变占第四》）"
RULESET_SOURCE_TITLE = "《易学启蒙通释》（四库全书本）卷下·考变占第四"
RULESET_SOURCE_URL = (
    "https://zh.wikisource.org/w/index.php?title=易學啟蒙通釋_%28四庫全書本%29/卷下&oldid=529701"
)


@dataclass(frozen=True)
class ReadingPassage:
    kind: str
    hexagram_order: int
    hexagram_title: str
    label: str
    text: str
    line_position: int | None
    primary: bool
    source_url: str
    source_revision_id: int | None


@dataclass(frozen=True)
class TraditionalReading:
    ruleset_id: str
    ruleset_version: str
    ruleset_name: str
    source_title: str
    source_url: str
    source_revision_id: int
    moving_count: int
    passages: tuple[ReadingPassage, ...]
    rationale: str
    plain_rule_explanation: str
    interpretation_limit: str


def _passage(
    entry: dict[str, Any],
    *,
    kind: str,
    label: str,
    text: str,
    line_position: int | None = None,
    primary: bool = True,
) -> ReadingPassage:
    return ReadingPassage(
        kind=kind,
        hexagram_order=int(entry["wenwang_order"]),
        hexagram_title=entry["title"],
        label=label,
        text=text,
        line_position=line_position,
        primary=primary,
        source_url=entry["source_url"],
        source_revision_id=entry.get("source_revision_id"),
    )


def choose_traditional_reading(
    calculation: HexagramCalculation,
    base: dict[str, Any],
    changed: dict[str, Any],
) -> TraditionalReading:
    """Select original passages using one explicitly named, source-labelled rule set.

    Lines and positions use the backend's canonical bottom-to-top order. The result
    reports which text to consult; it does not infer a divinatory outcome.
    """
    positions = calculation.moving_positions
    moving_count = len(positions)
    passages: list[ReadingPassage] = []
    if moving_count == 0:
        passages.append(_passage(base, kind="judgment", label="本卦卦辞", text=base["judgment"]))
        rationale = "六爻皆不变，取本卦卦辞；本体系另以本卦内卦为贞、外卦为悔。"
    elif moving_count == 1:
        position = positions[0]
        passages.append(
            _passage(
                base,
                kind="line",
                label=f"本卦第{position}爻",
                text=base["line_texts"][position - 1],
                line_position=position,
            )
        )
        rationale = "一爻变，取本卦该动爻爻辞。"
    elif moving_count == 2:
        lower, upper = sorted(positions)
        passages.extend(
            [
                _passage(
                    base,
                    kind="line",
                    label=f"本卦第{lower}爻",
                    text=base["line_texts"][lower - 1],
                    line_position=lower,
                    primary=False,
                ),
                _passage(
                    base,
                    kind="line",
                    label=f"本卦第{upper}爻",
                    text=base["line_texts"][upper - 1],
                    line_position=upper,
                    primary=True,
                ),
            ]
        )
        rationale = "二爻变，两条动爻都取本卦爻辞，以上位动爻为主。此细则在通释中注明为据例推定。"
    elif moving_count == 3:
        base_primary = 1 in positions
        primary_entry = base if base_primary else changed
        secondary_entry = changed if base_primary else base
        passages.extend(
            [
                _passage(
                    primary_entry,
                    kind="judgment",
                    label="主参考卦辞",
                    text=primary_entry["judgment"],
                    primary=True,
                ),
                _passage(
                    secondary_entry,
                    kind="judgment",
                    label="参照卦辞",
                    text=secondary_entry["judgment"],
                    primary=False,
                ),
            ]
        )
        side = "本卦为主" if base_primary else "之卦为主"
        subset = "前十" if base_primary else "后十"
        rationale = f"三爻变，参考本卦与之卦卦辞；本例属于{subset}组合，按本体系以{side}。"
    elif moving_count == 4:
        unchanged_positions = [position for position in range(1, 7) if position not in positions]
        lower, upper = unchanged_positions
        passages.extend(
            [
                _passage(
                    changed,
                    kind="line",
                    label=f"之卦第{lower}爻（不变爻）",
                    text=changed["line_texts"][lower - 1],
                    line_position=lower,
                    primary=True,
                ),
                _passage(
                    changed,
                    kind="line",
                    label=f"之卦第{upper}爻（不变爻）",
                    text=changed["line_texts"][upper - 1],
                    line_position=upper,
                    primary=False,
                ),
            ]
        )
        rationale = "四爻变，取之卦两条不变爻爻辞，以下位不变爻为主；该主次细则在通释中注明为据例推定。"
    elif moving_count == 5:
        position = next(position for position in range(1, 7) if position not in positions)
        passages.append(
            _passage(
                changed,
                kind="line",
                label=f"之卦第{position}爻（不变爻）",
                text=changed["line_texts"][position - 1],
                line_position=position,
            )
        )
        rationale = "五爻变，取之卦唯一不变爻的爻辞。"
    else:
        if base["wenwang_order"] in (1, 2):
            special = base.get("special_line")
            expected = "用九" if base["wenwang_order"] == 1 else "用六"
            if not isinstance(special, dict) or special.get("name") != expected:
                raise ValueError(f"六爻皆变时目录缺少{expected}原文")
            passages.append(
                _passage(
                    base,
                    kind="special_line",
                    label=expected,
                    text=special["text"],
                )
            )
            rationale = f"六爻皆变且本卦为{'乾' if expected == '用九' else '坤'}，取该卦独立收录的{expected}。"
        else:
            passages.append(
                _passage(changed, kind="judgment", label="之卦卦辞", text=changed["judgment"])
            )
            rationale = "六爻皆变且本卦非乾、坤，取之卦卦辞。"

    plain_rule_explanation = f"本卦有{moving_count}条动爻。{rationale}"
    return TraditionalReading(
        ruleset_id=RULESET_ID,
        ruleset_version=RULESET_VERSION,
        ruleset_name=RULESET_NAME,
        source_title=RULESET_SOURCE_TITLE,
        source_url=RULESET_SOURCE_URL,
        source_revision_id=529701,
        moving_count=moving_count,
        passages=tuple(passages),
        rationale=rationale,
        plain_rule_explanation=plain_rule_explanation,
        interpretation_limit=(
            "本结果解释的是取辞依据，不构成对原文义理或现实结果的定论。"
            "二爻、四爻变的主次在通释中说明为据例推定；其他传统可采用不同占法。"
        ),
    )


def reading_as_dict(reading: TraditionalReading) -> dict[str, Any]:
    """Return a JSON-safe response payload."""
    return asdict(reading)
