from __future__ import annotations

from dataclasses import dataclass, field
import math

from myalignment.corridor.slope_pattern_style import SlopePatternStyle
from myalignment.render.primitives_3d import Point3D


@dataclass(frozen=True, slots=True)
class SlopePatternElement:
    """월드 좌표로 표현한 선분, 폴리라인 또는 마커."""

    points: tuple[Point3D, ...]
    element_type: str = "line"

    def __post_init__(self):
        object.__setattr__(self, "points", tuple(self.points))
        count = len(self.points)
        if self.element_type not in ("line", "polyline", "marker"):
            raise ValueError("unknown slope pattern element_type")
        if (
            (self.element_type == "line" and count != 2)
            or (self.element_type == "polyline" and count < 2)
            or (self.element_type == "marker" and count not in (1, 2))
        ):
            raise ValueError("invalid number of slope pattern vertices")


@dataclass(frozen=True, slots=True)
class SlopePattern:
    """한 측점의 사면 링크와 그 위에 표시하는 패턴."""

    region_name: str
    station: float
    side: str
    elements: tuple[SlopePatternElement, ...]
    start_point: Point3D
    end_point: Point3D
    slope: float = 0.0
    style: SlopePatternStyle = field(default_factory=SlopePatternStyle.hatch_style)
    start_offset: float = 0.0
    end_offset: float = 0.0
    baseline_name: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "elements", tuple(self.elements))
        if not all(map(math.isfinite, (self.station, self.slope, self.start_offset, self.end_offset))):
            raise ValueError("station, slope and offsets must be finite")
        if self.side not in ("left", "right"):
            raise ValueError("side must be left or right")

    @property
    def slope_percent(self) -> float:
        """중심 쪽에서 바깥쪽으로 향하는 부호 있는 구배(%)."""
        return 100 * self.slope

    @property
    def element_count(self) -> int:
        return len(self.elements)

    @property
    def label(self) -> str:
        """표시 옵션에 맞춘 패턴 이름과 구배."""
        parts = []
        if self.style.show_label:
            parts.append(self.style.name)
        if self.style.show_slope_value:
            parts.append(f"{self.slope_percent:+.1f}%")
        return " · ".join(parts)


@dataclass(frozen=True, slots=True)
class SlopePatternCollection:
    """코리더 영역과 측점별 사면 패턴 모음."""

    patterns: tuple[SlopePattern, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "patterns", tuple(self.patterns))

    def __len__(self) -> int:
        return len(self.patterns)

    def __iter__(self):
        return iter(self.patterns)

    def total_elements(self) -> int:
        return sum(pattern.element_count for pattern in self)

    def by_region(self, region_name: str) -> tuple[SlopePattern, ...]:
        return tuple(pattern for pattern in self if pattern.region_name == region_name)

    def at_station(
        self, station: float, *, baseline_name: str | None = None, region_name: str | None = None,
    ) -> tuple[SlopePattern, ...]:
        """기하 측점의 패턴을 조회하고 필요하면 기준선이나 영역으로 좁힌다."""
        return tuple(
            pattern for pattern in self
            if math.isclose(station, pattern.station, rel_tol=0, abs_tol=1e-8)
            and (baseline_name is None or pattern.baseline_name == baseline_name)
            and (region_name is None or pattern.region_name == region_name)
        )
