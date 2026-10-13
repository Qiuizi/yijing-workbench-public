"""Three-coin line generation, isolated from the API and persistence layers."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol


class CoinRandomSource(Protocol):
    def choice(self, sequence: tuple[int, int]) -> int: ...


@dataclass(frozen=True)
class CastLine:
    value: int
    coins: tuple[int, int, int]


def cast_line(source: CoinRandomSource | None = None) -> CastLine:
    """Cast one line; 2 is yin, 3 is yang, so the natural 1:3:3:1 odds hold."""
    rng = source if source is not None else random.SystemRandom()
    coins = (rng.choice((2, 3)), rng.choice((2, 3)), rng.choice((2, 3)))
    return CastLine(sum(coins), coins)


def cast_six_lines(source: CoinRandomSource | None = None) -> tuple[CastLine, ...]:
    """Generate six lines in canonical internal order: bottom (初爻) to top."""
    rng = source if source is not None else random.SystemRandom()
    return tuple(cast_line(rng) for _ in range(6))

