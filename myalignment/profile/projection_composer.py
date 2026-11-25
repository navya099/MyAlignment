from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import TYPE_CHECKING

from myalignment.profile.projection_builder import ProjectionBuilder
from myalignment.profile.projection_object_type import ProjectionObjectType as Kind

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.featureline.feature_line import FeatureLine
    from myalignment.profile.profile import Profile
    from myalignment.profile.projection_style import ProjectionReference
    from myalignment.profile.view_projection import ProfileViewProjection


class ProjectionComposer:
    """선형의 구조물과 지정한 객체를 한 번에 투영한다."""

    @classmethod
    def project_all_structures(cls, alignment: Alignment, profile: Profile) -> list[ProfileViewProjection]:
        """선형과 종단의 공통 범위에 있는 구조물의 투영을 만든다."""
        start = max(alignment.start_station, profile.start_station)
        end = min(alignment.end_station, profile.end_station)
        return [
            ProjectionBuilder.project_structure(alignment, profile, structure)
            for structure in alignment.structures
            if start <= end and structure.start_station <= end and structure.end_station >= start
        ]

    @classmethod
    def project_all(
        cls, alignment: Alignment, profile: Profile,
        cross_alignments: Sequence[Alignment] | None = None,
        feature_lines: Sequence[FeatureLine] | None = None,
        *,
        references: Sequence[ProjectionReference] | None = None,
    ) -> list[ProfileViewProjection]:
        """구조물, 교차 선형, 형상선 및 스타일이 지정된 참조를 투영한다."""
        result = cls.project_all_structures(alignment, profile)
        for crossing in cross_alignments or ():
            result.extend(ProjectionBuilder.project_alignment_crossings(alignment, profile, crossing))
        result.extend(ProjectionBuilder.project_feature_line(alignment, profile, line) for line in feature_lines or ())
        for reference in references or ():
            kind, source, style = reference.style.object_type, reference.object, reference.style
            if kind is Kind.ALIGNMENT:
                result.extend(
                    replace(item, name=reference.name)
                    for item in ProjectionBuilder.project_alignment_crossings(alignment, profile, source, style)
                )
                continue
            if kind is Kind.STRUCTURE:
                projection = ProjectionBuilder.project_structure(alignment, profile, source, style)
            elif kind is Kind.FEATURE_LINE:
                projection = ProjectionBuilder.project_feature_line(alignment, profile, source, style)
            elif kind is Kind.PIPE:
                projection = ProjectionBuilder.project_pipe(alignment, source, reference.name, style)
            else:
                projection = ProjectionBuilder.project_point(alignment, profile, source, reference.name, style)
            result.append(replace(projection, name=reference.name))
        return result
