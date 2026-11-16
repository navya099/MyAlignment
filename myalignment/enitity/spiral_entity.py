# entity/spiral_entity.py
from __future__ import annotations
from dataclasses import dataclass, replace
import math

from cadgeom import Point2d

from myalignment.enitity.alignment_entity import AlignmentEntity
from myalignment.enum.alignmententitytype import AlignmentEntityType
from myalignment.enum.spiraltype import SpiralType
from myalignment.geometry.spiral_geometry import SpiralParams
from myalignment.utils import CurveDirection
from myalignment.geometry.spiral_geometry import SpiralGeometry

@dataclass(frozen=True, slots=True)
class SpiralEntity(AlignmentEntity):
    """완화곡선 Entity (C3D AlignmentSpiral)."""
    entity_type: AlignmentEntityType = AlignmentEntityType.Spiral

    @classmethod
    def create(
        cls,
        start_coord: Point2d,
        start_azimuth: float,
        radius: float,
        length: float,
        spiral_type: SpiralType,
        direction: CurveDirection,
        start_station: float = 0.0,
    ) -> "SpiralEntity":
        """완화곡선 Entity 생성."""

        geometry = SpiralGeometry(
            start_azimuth=start_azimuth,
            params=SpiralParams(
                radius=radius,
                length=length,
                spiral_type=spiral_type,
            ),
            direction=direction,
        )
        return cls(
            geometry=geometry,
            start_station=start_station,
            start_coord=start_coord,
            start_azimuth=start_azimuth,
        )

    def reversed(self) -> "SpiralEntity":
        """뒤집힌 완화곡선 Entity."""
        new_geometry = self.geometry.reversed()
        return SpiralEntity(
            entity_id=self.entity_id,
            geometry=new_geometry,
            start_station=self.start_station,
            start_coord=self.end_coord,
            start_azimuth=new_geometry.start_azimuth,
        )

    def offset_by(self, distance: float) -> "SpiralEntity":
        """평행 이동한 완화곡선 Entity."""
        new_geometry = self.geometry.offset_by(distance)
        sign = +1.0 if self.geometry.direction == CurveDirection.LEFT else -1.0
        nx = -math.sin(self.start_azimuth) * sign
        ny = math.cos(self.start_azimuth) * sign
        new_start = Point2d(
            self.start_coord.x - distance * nx,
            self.start_coord.y - distance * ny,
        )
        return SpiralEntity(
            entity_id=self.entity_id,
            geometry=new_geometry,
            start_station=self.start_station,
            start_coord=new_start,
            start_azimuth=self.start_azimuth,
        )

    def _replace(self, **kwargs) -> "SpiralEntity":
        return replace(self, **kwargs)