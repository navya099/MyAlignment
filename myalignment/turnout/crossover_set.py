# turnout/crossover_set.py
from __future__ import annotations
from dataclasses import dataclass, field

from myalignment.turnout.crossover import Crossover


@dataclass(frozen=True, slots=True)
class CrossoverSet:
    """Crossover 집합 (불변)."""
    crossovers: tuple[Crossover, ...] = field(default_factory=tuple)

    def __len__(self) -> int:
        return len(self.crossovers)

    def __iter__(self):
        return iter(self.crossovers)

    def by_alignment(self, name: str) -> tuple[Crossover, ...]:
        """특정 선형이 관련된 Crossover."""
        return tuple(
            c for c in self.crossovers
            if c.source_alignment1_name == name or c.source_alignment2_name == name
        )

    def valid_only(self) -> tuple[Crossover, ...]:
        return tuple(c for c in self.crossovers if c.is_valid)

    def add(self, crossover: Crossover) -> "CrossoverSet":
        return CrossoverSet(crossovers=self.crossovers + (crossover,))

    def remove(self, name: str) -> "CrossoverSet":
        return CrossoverSet(
            crossovers=tuple(c for c in self.crossovers if c.name != name)
        )

    def __repr__(self) -> str:
        return (
            f"CrossoverSet(n={len(self.crossovers)}, "
            f"valid={len(self.valid_only())})"
        )