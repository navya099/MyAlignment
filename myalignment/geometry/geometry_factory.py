# geometry/geometry_factory.py
from __future__ import annotations

from myalignment.enum.spiraltype import SpiralType
from myalignment.geometry.arc_geometry import ArcGeometry
from myalignment.geometry.line_geometry import LineGeometry
from myalignment.utils import CurveDirection
from myalignment.geometry.spiral_geometry import SpiralGeometry, SpiralParams


class GeometryFactory:
    """로컬 기하 생성 팩토리."""

    @staticmethod
    def make_line(length: float, start_azimuth: float = 0.0) -> LineGeometry:
        return LineGeometry(start_azimuth=start_azimuth, _length=length)

    @staticmethod
    def make_arc(radius: float, delta: float, direction: CurveDirection,
                 start_azimuth: float = 0.0) -> ArcGeometry:
        return ArcGeometry(
            start_azimuth=start_azimuth,
            _radius=radius,
            _delta=delta,
            direction=direction,
        )

    @staticmethod
    def make_spiral(radius: float, length: float, spiral_type: SpiralType,
                    direction: CurveDirection, start_azimuth: float = 0.0) -> SpiralGeometry:

        return SpiralGeometry(
            start_azimuth=start_azimuth,
            params=SpiralParams(radius=radius, length=length, spiral_type=spiral_type),
            direction=direction,
        )