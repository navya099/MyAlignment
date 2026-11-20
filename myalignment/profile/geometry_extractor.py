from __future__ import annotations

import math
from typing import TYPE_CHECKING

from myalignment.enum.alignmententitytype import AlignmentEntityType
from myalignment.profile.geometry_point import GeometryPoint
from myalignment.profile.geometry_point_type import GeometryPointType

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment


_TRANSITIONS = {
    (AlignmentEntityType.Line, AlignmentEntityType.Spiral): GeometryPointType.TS,
    (AlignmentEntityType.Spiral, AlignmentEntityType.Arc): GeometryPointType.SC,
    (AlignmentEntityType.Arc, AlignmentEntityType.Spiral): GeometryPointType.CS,
    (AlignmentEntityType.Spiral, AlignmentEntityType.Line): GeometryPointType.ST,
    (AlignmentEntityType.Line, AlignmentEntityType.Arc): GeometryPointType.BC,
    (AlignmentEntityType.Arc, AlignmentEntityType.Line): GeometryPointType.EC,
}


class GeometryPointExtractor:
    """연속된 선형 요소의 경계에서 지오메트리 점을 추출한다."""

    @staticmethod
    def extract(alignment: Alignment) -> list[GeometryPoint]:
        entities = alignment.entities.entities
        points = []
        for current, following in zip(entities, entities[1:]):
            transition = (current.entity_type, following.entity_type)
            tangent_in, tangent_out = current.end_azimuth, following.start_azimuth
            point_type = _TRANSITIONS.get(transition)
            if point_type is None and transition == (AlignmentEntityType.Line, AlignmentEntityType.Line):
                turn = math.remainder(tangent_out - tangent_in, math.tau)
                if abs(turn) > 1e-8:
                    point_type = GeometryPointType.PI
            if point_type is None:
                continue

            radius = 0.0
            if following.entity_type is AlignmentEntityType.Arc:
                radius = following.geometry.radius
            elif current.entity_type is AlignmentEntityType.Arc:
                radius = current.geometry.radius

            label = point_type.value
            if radius > 0:
                label += f"\\PR={radius:g}"
            points.append(GeometryPoint(
                station=current.end_station,
                point_type=point_type,
                label=label,
                tangent_in=tangent_in,
                tangent_out=tangent_out,
                radius=radius,
            ))
        return points
