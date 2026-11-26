from __future__ import annotations

from dataclasses import dataclass
import math

from myalignment.alignment.profile_geometry_label_type import ProfileGeometryPointLabelType


@dataclass(frozen=True, slots=True)
class ProfileGeometryLabel:
    """원시 측점, 표고와 진입·진출 구배를 가진 종단 기하점."""

    point_type: ProfileGeometryPointLabelType
    station: float = 0.0
    elevation: float = 0.0
    grade_in: float | None = None
    grade_out: float | None = None
    profile_name: str = ""
    curve_length: float = 0.0
    k_value: float | None = None

    def __post_init__(self):
        if not isinstance(self.point_type, ProfileGeometryPointLabelType):
            raise ValueError("point_type must be a ProfileGeometryPointLabelType")
        if not all(map(math.isfinite, (self.station, self.elevation, self.curve_length))):
            raise ValueError("station, elevation and curve_length must be finite")
        if self.curve_length < 0 or any(
            value is not None and not math.isfinite(value) for value in (self.grade_in, self.grade_out, self.k_value)
        ):
            raise ValueError("invalid curve length, grade or K value")

    @property
    def label_text(self) -> str:
        return self.point_type.value

    def to_fields(self, display_station: float | None = None) -> dict[str, str]:
        """레이블 템플릿에 들어갈 측점, 표고와 구배를 반환한다."""
        station = self.station if display_station is None else display_station

        def grade(value):
            return f"{value * 100:+.2f}%" if value is not None else "—"

        return {
            "Point Type": self.label_text,
            "Station Value": f"{station:.2f}",
            "Raw Station": f"{self.station:.2f}",
            "Elevation Value": f"{self.elevation:.3f}",
            "Grade In": grade(self.grade_in),
            "Grade Out": grade(self.grade_out),
            "Profile Name": self.profile_name,
            "Curve Length": f"{self.curve_length:.3f}" if self.curve_length else "—",
            "K Value": f"{self.k_value:.3f}" if self.k_value is not None else "—",
        }
