from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from myalignment.surface.tin_surface import TinSurface


@dataclass(frozen=True, slots=True)
class CorridorSurfaceSet:
    """코리더에서 추출한 표면의 불변 집합."""

    surfaces: tuple[TinSurface, ...] = ()

    def __len__(self) -> int:
        return len(self.surfaces)

    def __iter__(self) -> Iterator[TinSurface]:
        return iter(self.surfaces)

    def get(self, name: str) -> TinSurface | None:
        return next((surface for surface in self if surface.name == name), None)

    def add(self, surface: TinSurface) -> CorridorSurfaceSet:
        return CorridorSurfaceSet(self.surfaces + (surface,))

    def __repr__(self) -> str:
        return f"CorridorSurfaceSet(n={len(self)})"
