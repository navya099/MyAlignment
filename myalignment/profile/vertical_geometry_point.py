from dataclasses import dataclass
import math

from myalignment.profile.vertical_geometry_type import VerticalGeometryPointType


@dataclass(frozen=True, slots=True)
class VerticalGeometryPoint:
    """측점, 표고와 구배를 가진 종단 기하점. radius는 등가 반경이다."""

    station: float = 0.0
    elevation: float = 0.0
    point_type: VerticalGeometryPointType = VerticalGeometryPointType.NONE
    grade_in: float = 0.0
    grade_out: float = 0.0
    radius: float = 0.0
    curve_length: float = 0.0

    def __post_init__(self):
        if self.point_type is VerticalGeometryPointType.NONE:
            raise ValueError("point_type이 NONE입니다.")
        if not math.isfinite(self.station):
            raise ValueError("station must be finite")

    @property
    def grade_change(self) -> float:
        return self.grade_out - self.grade_in

    @property
    def label_text(self) -> str:
        return self.point_type.value

    def __repr__(self) -> str:
        return f"VerticalPoint(STA={self.station:.2f}, EL={self.elevation:.3f}, {self.label_text})"
