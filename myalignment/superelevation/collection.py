# superelevation/collection.py
from __future__ import annotations
from dataclasses import dataclass, field

from myalignment.superelevation.curve import SuperelevationCurve


@dataclass(frozen=True, slots=True)
class SuperelevationCollection:
    """
    편구배 곡선 컬렉션 (불변).

    C3D의 Alignment.SuperelevationCurves와 호환.
    """
    curves: tuple[SuperelevationCurve, ...] = field(default_factory=tuple)

    def __len__(self) -> int:
        return len(self.curves)

    def __iter__(self):
        return iter(self.curves)

    def curve_at_station(self, station: float) -> SuperelevationCurve | None:
        """측점이 속한 편구배 곡선."""
        for c in self.curves:
            if c.start_station <= station <= c.end_station:
                return c
        return None

    def add(self, curve: SuperelevationCurve) -> "SuperelevationCollection":
        """새 곡선 추가한 새 컬렉션."""
        new_list = list(self.curves) + [curve]
        new_list.sort(key=lambda c: c.start_station)
        return SuperelevationCollection(curves=tuple(new_list))