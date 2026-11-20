from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
import math
import re
from typing import TYPE_CHECKING

from myalignment.profile.label_style import LabelStyle

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile


_FIELD = re.compile(r"<\[([^\[\]]+)\]>")


@dataclass(frozen=True, slots=True)
class StationElevationLabel:
    """지정한 측점에서 최대 두 종단의 이름과 표고를 평가한다."""

    station: float = 0.0
    label_style: LabelStyle = field(default_factory=LabelStyle)
    profile_name: str = ""
    profile1_name: str = ""
    profile2_name: str = ""

    def __post_init__(self):
        if not math.isfinite(self.station):
            raise ValueError("station must be finite")

    def primary_profile(self, profiles: Sequence[Profile]) -> Profile | None:
        return self._find_profile(profiles, self.profile1_name or self.profile_name)

    @staticmethod
    def _find_profile(profiles: Sequence[Profile], name: str) -> Profile | None:
        if not name:
            return profiles[0] if profiles else None
        return next((profile for profile in profiles if profile.name == name), None)

    def evaluate(self, profiles: Sequence[Profile]) -> dict[str, str]:
        """필드의 측점과 표고를 포맷한다. 평가할 수 없는 값은 ???로 표시한다."""
        first = self.primary_profile(profiles)
        second = self._find_profile(profiles, self.profile2_name) if self.profile2_name else None
        values = {"Station Value": f"{self.station:.2f}"}
        for index, profile in enumerate((first, second), start=1):
            elevation = "???"
            if profile is not None:
                try:
                    elevation = f"{profile.elevation_at(self.station):.3f}"
                except ValueError:
                    pass
            values[f"Profile {index} Name"] = profile.name if profile is not None else "???"
            values[f"Profile {index} Elevation"] = elevation

        return {
            template: _FIELD.sub(lambda match: values.get(match[1], match[0]), template)
            for template in self.label_style.fields
        }

    def with_profile1(self, name: str) -> StationElevationLabel:
        return replace(self, profile1_name=name)

    def with_profile2(self, name: str) -> StationElevationLabel:
        return replace(self, profile2_name=name)
