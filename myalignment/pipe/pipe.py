from __future__ import annotations

from dataclasses import dataclass, field
import math

from cadgeom import Point2d

from myalignment.pipe.pipe_part import PipePart
from myalignment.render.primitives_3d import Point3D


@dataclass(frozen=True, slots=True)
class Pipe:
    """양 끝 구조물을 잇는 직선 관과 내측 관저고."""

    id: str = ""
    name: str = ""
    part: PipePart = field(default_factory=PipePart)
    start_structure_id: str = ""
    end_structure_id: str = ""
    start_point: Point2d | None = None
    end_point: Point2d | None = None
    start_invert: float = 0.0
    end_invert: float = 0.0
    alignment_name: str = ""
    surface_name: str = ""
    start_surface_elevation: float | None = None
    end_surface_elevation: float | None = None

    def __post_init__(self):
        if not all(math.isfinite(value) for value in (self.start_invert, self.end_invert)):
            raise ValueError("pipe inverts must be finite")
        for value in (self.start_surface_elevation, self.end_surface_elevation):
            if value is not None and not math.isfinite(value):
                raise ValueError("pipe elevations must be finite")
        for point in (self.start_point, self.end_point):
            if point is not None and not (math.isfinite(point.x) and math.isfinite(point.y)):
                raise ValueError("pipe coordinates must be finite")

    @property
    def length(self) -> float:
        """평면상 관의 길이."""
        if self.start_point is None or self.end_point is None:
            return 0.0
        return self.start_point.distance_to(self.end_point)

    @property
    def slope(self) -> float:
        """시점에서 종점으로 내려가면 양수이다."""
        length = self.length
        return (self.start_invert - self.end_invert) / length if length > 0 else 0.0

    @property
    def slope_percent(self) -> float:
        return self.slope * 100

    def _cover(self, surface_elevation: float | None, invert: float) -> float | None:
        if surface_elevation is None:
            return None
        outer_crown = invert + self.part.diameter_m + self.part.wall_thickness_mm / 1000
        return surface_elevation - outer_crown

    @property
    def cover_start(self) -> float | None:
        """시점의 지표 표고에서 외측 관정고를 뺀 값."""
        return self._cover(self.start_surface_elevation, self.start_invert)

    @property
    def cover_end(self) -> float | None:
        return self._cover(self.end_surface_elevation, self.end_invert)

    @property
    def centerline(self) -> tuple[Point3D, ...]:
        """종단 투영에 전달할 관 중심의 시점·종점."""
        if self.start_point is None or self.end_point is None:
            return ()
        radius = self.part.diameter_m / 2
        return (
            Point3D(self.start_point.x, self.start_point.y, self.start_invert + radius),
            Point3D(self.end_point.x, self.end_point.y, self.end_invert + radius),
        )
