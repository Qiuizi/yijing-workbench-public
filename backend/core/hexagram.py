"""Pure six-line calculation. Line arrays are always stored bottom to top."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


VALID_LINE_VALUES = frozenset({6, 7, 8, 9})


@dataclass(frozen=True)
class HexagramCalculation:
    lines: tuple[int, ...]
    changed_lines: tuple[int, ...]
    moving_positions: tuple[int, ...]
    base_code: str
    changed_code: str
    base_id: int
    changed_id: int


def line_is_yang(value: int) -> bool:
    if value not in VALID_LINE_VALUES:
        raise ValueError(f"无效爻值：{value}；只允许 6、7、8、9")
    return value in (7, 9)


def binary_code(values: Sequence[int]) -> str:
    """Return the conventional six-bit integer string; 初爻 is its least-significant bit."""
    validate_lines(values)
    return "".join("1" if line_is_yang(value) else "0" for value in reversed(values))


def validate_lines(values: Sequence[int]) -> tuple[int, ...]:
    if len(values) != 6:
        raise ValueError("必须恰好提供六爻，顺序为自下而上")
    lines = tuple(values)
    if any(type(value) is not int or value not in VALID_LINE_VALUES for value in lines):
        raise ValueError("每一爻只能是整数 6、7、8 或 9")
    return lines


def calculate_hexagram(
    values: Sequence[int], binary_to_id: Mapping[str, int]
) -> HexagramCalculation:
    """Calculate original/changed hexagrams using an explicit King Wen lookup."""
    lines = validate_lines(values)
    base_code = binary_code(lines)
    changed = tuple(15 - value if value in (6, 9) else value for value in lines)
    changed_code = binary_code(changed)
    if len(binary_to_id) != 64 or base_code not in binary_to_id or changed_code not in binary_to_id:
        raise ValueError("六十四卦编码映射不完整")
    return HexagramCalculation(
        lines=lines,
        changed_lines=changed,
        moving_positions=tuple(i + 1 for i, value in enumerate(lines) if value in (6, 9)),
        base_code=base_code,
        changed_code=changed_code,
        base_id=binary_to_id[base_code],
        changed_id=binary_to_id[changed_code],
    )
