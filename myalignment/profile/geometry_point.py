from dataclasses import dataclass

from myalignment.profile.geometry_point_type import GeometryPointType


@dataclass(frozen=True, slots=True)
class GeometryPoint:
    """전이 측점과 전후 접선 방위각(rad), 원곡선 반경(m)."""

    station: float = 0.0
    point_type: GeometryPointType = GeometryPointType.NONE
    label: str = ""
    tangent_in: float = 0.0
    tangent_out: float = 0.0
    radius: float = 0.0

    def __post_init__(self):
        if self.point_type is GeometryPointType.NONE:
            raise ValueError("point_type이 NONE입니다.")

    @property
    def is_curve_start(self) -> bool:
        return self.point_type in (GeometryPointType.TS, GeometryPointType.BC)

    @property
    def is_curve_end(self) -> bool:
        return self.point_type in (GeometryPointType.ST, GeometryPointType.EC)

    @property
    def is_spiral_point(self) -> bool:
        return self.point_type in (
            GeometryPointType.TS, GeometryPointType.SC, GeometryPointType.CS, GeometryPointType.ST,
        )

    def __repr__(self) -> str:
        return f"GeometryPoint(STA={self.station:.2f}, {self.point_type.value})"
