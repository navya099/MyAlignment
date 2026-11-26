from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import math
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.profile.profile import Profile
    from myalignment.surface.tin_surface import TinSurface


@dataclass(frozen=True, slots=True)
class SectionContext:
    """한 기하 측점에서 조건 평가에 사용하는 설계 표고, 구배와 타깃 값."""

    station: float = 0.0
    base_elevation: float | None = None
    grade: float | None = None
    surface_elevation_at: Callable[[str, float], float | None] | None = None
    target_offsets: Mapping[str, float] = field(default_factory=dict)
    values: Mapping[str, float | bool | None] = field(default_factory=dict)

    def __post_init__(self):
        if not math.isfinite(self.station):
            raise ValueError("station must be finite")
        if self.base_elevation is not None and not math.isfinite(self.base_elevation):
            raise ValueError("base_elevation must be finite")
        if self.grade is not None and not math.isfinite(self.grade):
            raise ValueError("grade must be finite")
        offsets = dict(self.target_offsets)
        if any(not math.isfinite(value) for value in offsets.values()):
            raise ValueError("target offsets must be finite")
        object.__setattr__(self, "target_offsets", MappingProxyType(offsets))
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    @classmethod
    def from_alignment(
        cls, alignment: Alignment, station: float, *, profile: Profile | None = None,
        surfaces: Mapping[str, TinSurface] | None = None, target_offsets: Mapping[str, float] | None = None,
        values: Mapping[str, float | bool | None] | None = None,
    ) -> SectionContext:
        """횡거의 월드 위치에서 이름으로 TIN 표고를 조회하는 컨텍스트를 만든다."""
        surfaces = dict(surfaces or {})

        def sample(name: str, offset: float) -> float | None:
            surface = surfaces.get(name)
            if surface is None:
                return None
            point = alignment.point_at(station, offset)
            if surface.triangle_at(point.x, point.y) is None:
                return None
            return surface.elevation_at(point.x, point.y)

        return cls(
            station=station,
            base_elevation=profile.elevation_at(station) if profile is not None else 0.0,
            grade=profile.grade_at(station) if profile is not None else None,
            surface_elevation_at=sample if surfaces else None,
            target_offsets=target_offsets or {}, values=values or {},
        )
