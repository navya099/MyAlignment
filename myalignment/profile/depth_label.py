from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
import math
from typing import TYPE_CHECKING

from myalignment.profile.depth_label_style import DepthLabelStyle
from myalignment.profile.station_label import StationElevationLabel

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile


@dataclass(frozen=True, slots=True)
class DepthLabel:
    """한 종단 위의 두 원시 측점 사이에서 표고차와 평균 구배를 계산한다.

    시작 측점과 끝 측점은 유한해야 하며 끝 측점이 더 커야 한다.
    종단 이름을 생략하면 전달한 첫 종단을 사용한다.
    """

    start_station: float = 0.0
    end_station: float = 0.0
    label_style: DepthLabelStyle = field(default_factory=DepthLabelStyle.standard)
    profile_name: str = ""

    def __post_init__(self):
        if not (math.isfinite(self.start_station) and math.isfinite(self.end_station)):
            raise ValueError("start_station and end_station must be finite")
        if self.end_station <= self.start_station:
            raise ValueError("end_station must be greater than start_station")

    def evaluate(self, profiles: Sequence[Profile]) -> dict[str, str]:
        """표시용 필드를 반환한다. 종단이나 표고를 찾지 못하면 빈 딕셔너리를 반환한다."""
        return self._format_fields(self.summary(profiles))

    @staticmethod
    def _format_fields(values: dict[str, float]) -> dict[str, str]:
        if not values:
            return {}
        return {
            "Start Station": f"{values['start_station']:.2f}",
            "End Station": f"{values['end_station']:.2f}",
            "Start Elevation": f"{values['start_elevation']:.3f}",
            "End Elevation": f"{values['end_elevation']:.3f}",
            "Elevation Difference": f"{values['delta_elevation']:+.3f}",
            "Grade": f"{values['grade']:+.2%}",
            "Distance": f"{values['distance']:.2f}",
        }

    def summary(self, profiles: Sequence[Profile]) -> dict[str, float]:
        """두 측점과 표고, 표고차, 거리, 구배를 반환한다.

        구배는 표고차를 측점 차로 나눈 소수 비율이다. 종단이 없거나
        두 측점 중 하나의 표고를 조회할 수 없으면 빈 딕셔너리를 반환한다.
        """
        profile = StationElevationLabel._find_profile(profiles, self.profile_name)
        if profile is None:
            return {}
        try:
            start_elevation = profile.elevation_at(self.start_station)
            end_elevation = profile.elevation_at(self.end_station)
        except ValueError:
            return {}

        distance = self.end_station - self.start_station
        delta = end_elevation - start_elevation
        return {
            "start_station": self.start_station,
            "end_station": self.end_station,
            "start_elevation": start_elevation,
            "end_elevation": end_elevation,
            "delta_elevation": delta,
            "distance": distance,
            "grade": delta / distance,
        }

    def with_style(self, style: DepthLabelStyle) -> DepthLabel:
        """새 스타일을 적용한 레이블을 반환한다."""
        return replace(self, label_style=style)

    def with_profile(self, name: str) -> DepthLabel:
        """지정한 종단 이름을 사용하는 레이블을 반환한다."""
        return replace(self, profile_name=name)

    def __repr__(self) -> str:
        return (
            f"DepthLabel(STA {self.start_station:.2f} → {self.end_station:.2f}, "
            f"profile={self.profile_name!r})"
        )
