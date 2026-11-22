from __future__ import annotations

import math
from typing import TYPE_CHECKING

from myalignment.profile.profileentitytype import ProfileEntityType
from myalignment.profile.vertical_geometry_point import VerticalGeometryPoint
from myalignment.profile.vertical_geometry_type import VerticalGeometryPointType

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile


class VerticalGeometryExtractor:
    """종단 모델의 접선, 수직 교점과 해석적 종곡선 극점을 읽는다."""

    @classmethod
    def extract(cls, profile: Profile) -> list[VerticalGeometryPoint]:
        entities = profile.entities.entities
        if not entities:
            return []

        kind = VerticalGeometryPointType
        first, last = entities[0], entities[-1]
        points = [
            VerticalGeometryPoint(first.start_station, first.start_elevation, kind.PVI, grade_out=first.start_grade),
            VerticalGeometryPoint(last.end_station, last.end_elevation, kind.PVI, grade_in=last.end_grade),
        ]

        for previous, following in zip(entities, entities[1:]):
            if previous.entity_type is ProfileEntityType.Tangent and following.entity_type is ProfileEntityType.Tangent:
                incoming, outgoing = previous.end_grade, following.start_grade
                if not math.isclose(incoming, outgoing, rel_tol=0.0, abs_tol=1e-9):
                    for point_type in (kind.GRADE_BREAK, kind.PVI):
                        points.append(VerticalGeometryPoint(
                            previous.end_station, previous.end_elevation, point_type, incoming, outgoing,
                        ))

        for entity in entities:
            if entity.entity_type in (ProfileEntityType.ParabolaSymmetric, ProfileEntityType.ParabolaAsymmetric):
                points.extend(cls._curve_points(entity))
        return sorted(points, key=lambda point: (point.station, point.label_text))

    @staticmethod
    def _curve_points(curve):
        kind = VerticalGeometryPointType
        incoming, outgoing = curve.start_grade, curve.end_grade
        radius = abs(curve.k_value)
        parameters = (incoming, outgoing, radius, curve.length)
        yield VerticalGeometryPoint(curve.start_station, curve.start_elevation, kind.VPC, *parameters)
        yield VerticalGeometryPoint(curve.pvi_station, curve.pvi_elevation, kind.PVI, *parameters)
        yield VerticalGeometryPoint(curve.end_station, curve.end_elevation, kind.VPT, *parameters)

        station = curve.extremum_station()
        if station is not None:
            point_type = kind.HIGH_POINT if incoming > outgoing else kind.LOW_POINT
            yield VerticalGeometryPoint(station, curve.elevation_at(station), point_type, *parameters)
