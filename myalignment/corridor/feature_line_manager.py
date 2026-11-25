from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from myalignment.assembly.codes import PointCode
from myalignment.corridor.corridor_feature_line import CorridorFeatureLine
from myalignment.corridor.feature_line_extractor import CorridorFeatureLineExtractor
from myalignment.corridor.feature_line_spec import CorridorFeatureLineSpec

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.profile.profile import Profile


@dataclass(frozen=True, slots=True)
class CorridorFeatureLineManager:
    """추출한 코리더 종방향 선을 이름으로 관리한다."""

    feature_lines: tuple[CorridorFeatureLine, ...] = ()
    corridor_name: str = ""

    def __post_init__(self):
        object.__setattr__(self, "feature_lines", tuple(self.feature_lines))

    def __len__(self) -> int:
        return len(self.feature_lines)

    def __iter__(self):
        return iter(self.feature_lines)

    def get(self, name: str) -> CorridorFeatureLine | None:
        """해당 이름의 첫 번째 선을 반환한다."""
        return next((line for line in self if line.name == name), None)

    def add(self, line: CorridorFeatureLine) -> CorridorFeatureLineManager:
        """선을 추가한 새 관리자를 반환한다."""
        return replace(self, feature_lines=(*self.feature_lines, line))

    @property
    def total_length(self) -> float:
        return sum(line.length for line in self)

    @classmethod
    def from_corridor(
        cls, corridor: Corridor, specs: Sequence[CorridorFeatureLineSpec], *,
        alignments: Mapping[str, Alignment], profiles: Mapping[str, Profile] | None = None,
        sample_frequency: float | None = None, baseline_name: str | None = None,
    ) -> CorridorFeatureLineManager:
        """주어진 사양에 따라 추출한다."""
        lines = CorridorFeatureLineExtractor.extract_multiple(
            corridor, specs, alignments=alignments, profiles=profiles,
            sample_frequency=sample_frequency, baseline_name=baseline_name,
        )
        return cls(tuple(lines), corridor.name)

    @classmethod
    def extract_standard_road(
        cls, corridor: Corridor, *, alignments: Mapping[str, Alignment],
        profiles: Mapping[str, Profile] | None = None, sample_frequency: float | None = None,
        baseline_name: str | None = None,
    ) -> CorridorFeatureLineManager:
        """도로의 좌우 경계, 크라운과 차로 끝을 표준 코드로 추출한다."""
        specs = (
            CorridorFeatureLineSpec("Top_Left_Edge", point_code=PointCode.EDGE, side="left", color=3),
            CorridorFeatureLineSpec("Top_Right_Edge", point_code=PointCode.EDGE, side="right", color=3),
            CorridorFeatureLineSpec("Top_Crown", point_code=PointCode.CROWN),
            CorridorFeatureLineSpec("Left_LaneEdge", point_code=PointCode.LANE_EDGE, side="left", color=1),
            CorridorFeatureLineSpec("Right_LaneEdge", point_code=PointCode.LANE_EDGE, side="right", color=1),
        )
        return cls.from_corridor(
            corridor, specs, alignments=alignments, profiles=profiles,
            sample_frequency=sample_frequency, baseline_name=baseline_name,
        )

    @classmethod
    def extract_standard_rail(
        cls, corridor: Corridor, *, alignments: Mapping[str, Alignment],
        profiles: Mapping[str, Profile] | None = None, sample_frequency: float | None = None,
        baseline_name: str | None = None,
    ) -> CorridorFeatureLineManager:
        """표준 궤도의 좌우 레일과 도상 경계를 추출한다."""
        specs = (
            CorridorFeatureLineSpec("Left_Rail", point_code=PointCode.LEFT_RAIL, color=1),
            CorridorFeatureLineSpec("Right_Rail", point_code=PointCode.RIGHT_RAIL, color=5),
            CorridorFeatureLineSpec("Left_Ballast", point_code=PointCode.EDGE, side="left", color=8),
            CorridorFeatureLineSpec("Right_Ballast", point_code=PointCode.EDGE, side="right", color=8),
        )
        return cls.from_corridor(
            corridor, specs, alignments=alignments, profiles=profiles,
            sample_frequency=sample_frequency, baseline_name=baseline_name,
        )
