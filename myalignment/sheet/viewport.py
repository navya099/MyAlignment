from __future__ import annotations

from dataclasses import dataclass
import math

from cadgeom import Point2d

from myalignment.sheet.layout import Viewport


@dataclass(frozen=True, slots=True)
class PlanViewportTransform:
    """월드 XY(m)를 회전하여 도면의 뷰포트(mm)에 배치한다."""

    viewport: Viewport
    world_center: Point2d
    rotation: float = 0.0

    def __post_init__(self):
        if not all(map(math.isfinite, (self.world_center.x, self.world_center.y, self.rotation))):
            raise ValueError("Plan center and rotation must be finite")

    @property
    def sheet_center(self) -> Point2d:
        view = self.viewport
        return Point2d(view.x_mm + view.width_mm / 2, view.y_mm + view.height_mm / 2)

    def to_paper(self, point: Point2d) -> Point2d:
        center = self.sheet_center
        scale = self.viewport.mm_per_m
        cos_r, sin_r = math.cos(self.rotation), math.sin(self.rotation)
        dx, dy = point.x - self.world_center.x, point.y - self.world_center.y
        return Point2d(center.x + scale * (cos_r * dx + sin_r * dy), center.y + scale * (-sin_r * dx + cos_r * dy))

    def to_world(self, point: Point2d) -> Point2d:
        center = self.sheet_center
        scale = self.viewport.mm_per_m
        cos_r, sin_r = math.cos(self.rotation), math.sin(self.rotation)
        x, y = (point.x - center.x) / scale, (point.y - center.y) / scale
        return Point2d(self.world_center.x + cos_r * x - sin_r * y, self.world_center.y + sin_r * x + cos_r * y)


@dataclass(frozen=True, slots=True)
class ProfileViewportTransform:
    """원시 측점과 표고(m)에 수평·수직 축척을 각각 적용한다."""

    viewport: Viewport
    paper_origin: Point2d
    start_station: float
    datum_elevation: float
    vertical_scale: float

    def __post_init__(self):
        if not all(map(math.isfinite, (
            self.paper_origin.x, self.paper_origin.y, self.start_station, self.datum_elevation, self.vertical_scale,
        ))) or self.vertical_scale <= 0:
            raise ValueError("Profile origin, station and datum must be finite and scale positive")

    @property
    def vertical_mm_per_m(self) -> float:
        return 1000.0 / self.vertical_scale

    @property
    def vertical_exaggeration(self) -> float:
        return self.viewport.scale / self.vertical_scale

    def to_paper(self, station: float, elevation: float) -> Point2d:
        return Point2d(
            self.paper_origin.x + (station - self.start_station) * self.viewport.mm_per_m,
            self.paper_origin.y + (elevation - self.datum_elevation) * self.vertical_mm_per_m,
        )

    def to_station_elevation(self, point: Point2d) -> tuple[float, float]:
        return (
            self.start_station + (point.x - self.paper_origin.x) / self.viewport.mm_per_m,
            self.datum_elevation + (point.y - self.paper_origin.y) / self.vertical_mm_per_m,
        )

    def project_rendered(self, point: Point2d) -> Point2d:
        """이미 수직 과장이 적용된 ProfileViewRenderer 좌표를 배치한다."""
        return self.to_paper(point.x, point.y / self.vertical_exaggeration)
