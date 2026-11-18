# surface/breakline_set.py
from __future__ import annotations
from dataclasses import dataclass, field

from myalignment.surface.breakline import Breakline
from myalignment.surface.breakline_type import BreaklineType


@dataclass(frozen=True, slots=True)
class BreaklineSet:
    """Breakline 집합 (불변)."""
    breaklines: tuple[Breakline, ...] = field(default_factory=tuple)
    _standard: tuple[Breakline, ...] = field(
        init=False, repr=False, compare=False, default=()
    )
    _proximity: tuple[Breakline, ...] = field(
        init=False, repr=False, compare=False, default=()
    )
    _walls: tuple[Breakline, ...] = field(
        init=False, repr=False, compare=False, default=()
    )

    def __post_init__(self):
        std, prox, walls = [], [], []
        for b in self.breaklines:
            bt = b.breakline_type
            if bt == BreaklineType.STANDARD:
                std.append(b)
            elif bt == BreaklineType.PROXIMITY:
                prox.append(b)
            elif bt == BreaklineType.WALL:
                walls.append(b)
        object.__setattr__(self, "_standard", tuple(std))
        object.__setattr__(self, "_proximity", tuple(prox))
        object.__setattr__(self, "_walls", tuple(walls))

    def __len__(self) -> int:
        return len(self.breaklines)

    def __iter__(self):
        return iter(self.breaklines)

    @property
    def standard(self) -> tuple[Breakline, ...]:
        return self._standard

    @property
    def proximity(self) -> tuple[Breakline, ...]:
        return self._proximity

    @property
    def walls(self) -> tuple[Breakline, ...]:
        return self._walls

    def total_length(self) -> float:
        return sum(b.length_2d for b in self.breaklines)

    def add(self, breakline: Breakline) -> "BreaklineSet":
        return BreaklineSet(breaklines=self.breaklines + (breakline,))

    def remove(self, name: str) -> "BreaklineSet":
        return BreaklineSet(
            breaklines=tuple(b for b in self.breaklines if b.name != name)
        )

    def __repr__(self) -> str:
        return f"BreaklineSet(n={len(self.breaklines)}, L={self.total_length():.1f}m)"