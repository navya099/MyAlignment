from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from myalignment.section.projection_builder import SectionProjectionBuilder

if TYPE_CHECKING:
    from cadgeom import Point2d
    from myalignment.alignment.alignment import Alignment
    from myalignment.featureline.feature_line import FeatureLine
    from myalignment.profile.profile import Profile
    from myalignment.section.section_projection import SectionProjection


class SectionProjectionComposer:
    """선형에 등록된 구조물과 외부 객체를 한 횡단면에 투영한다."""

    @classmethod
    def project_all(
        cls, alignment: Alignment, station: float,
        pipes: Sequence[tuple[Point2d, float, float, str]] | None = None,
        points: Sequence[tuple[Point2d, float, str]] | None = None,
        feature_lines: Sequence[FeatureLine] | None = None, *,
        alignments: Sequence[Alignment] = (), profile: Profile | None = None,
        station_tolerance: float = 1.0,
    ) -> list[SectionProjection]:
        """관로는 (중심점, 표고, 관경, 이름), 점은 (좌표, 표고, 이름)으로 받는다."""
        builder = SectionProjectionBuilder
        candidates = [
            *(builder.project_structure(alignment, station, structure, profile=profile)
              for structure in alignment.structures),
            *(builder.project_pipe(alignment, station, *pipe, station_tolerance=station_tolerance)
              for pipe in pipes or ()),
            *(builder.project_point(alignment, station, *point, station_tolerance=station_tolerance)
              for point in points or ()),
            *(builder.project_feature_line(alignment, station, line) for line in feature_lines or ()),
            *(builder.project_alignment(alignment, station, other) for other in alignments),
        ]
        return [candidate for candidate in candidates if candidate is not None]
