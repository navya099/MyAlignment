# entity/arc_entity.py
from __future__ import annotations
from dataclasses import dataclass, replace
import math

from cadgeom import Point2d

from myalignment.enitity.alignment_entity import AlignmentEntity
from myalignment.enum.alignmententitytype import AlignmentEntityType
from myalignment.geometry.arc_geometry import ArcGeometry
from myalignment.utils import CurveDirection


@dataclass(frozen=True, slots=True)
class ArcEntity(AlignmentEntity):
    """원곡선 Entity (C3D AlignmentArc)."""
    entity_type: AlignmentEntityType = AlignmentEntityType.Arc

    @classmethod
    def create(
        cls,
        start_coord: Point2d,
        start_azimuth: float,
        radius: float,
        delta: float,
        direction: CurveDirection,
        start_station: float = 0.0,
    ) -> "ArcEntity":
        """원곡선 Entity 생성."""
        geometry = ArcGeometry(
            start_azimuth=start_azimuth,
            _radius=radius,
            _delta=delta,
            direction=direction,
        )
        return cls(
            geometry=geometry,
            start_station=start_station,
            start_coord=start_coord,
            start_azimuth=start_azimuth,
        )

    @classmethod
    def create_from_bc_ec(
        cls,
        bc: Point2d,
        ec: Point2d,
        radius: float,
        direction: CurveDirection,
        start_station: float = 0.0,
        start_azimuth: float | None = None,
    ) -> "ArcEntity":
        """
        BC(시작점)/EC(끝점)/radius/direction으로 원곡선 생성.
        start_azimuth가 None이면 BC에서의 접선 방위각을 역산.
        """
        # BC → EC 현의 방위각/길이
        dx = ec.x - bc.x
        dy = ec.y - bc.y
        chord_len = math.hypot(dx, dy)
        chord_az = math.atan2(dy, dx)

        if chord_len > 2 * radius:
            raise ValueError(f"BC-EC 거리가 2R 초과: {chord_len} > {2*radius}")

        # delta: chord_len = 2R·sin(delta/2)
        delta = 2 * math.asin(min(1.0, chord_len / (2 * radius)))

        # start_azimuth 역산
        if start_azimuth is None:
            if direction == CurveDirection.LEFT:
                start_azimuth = chord_az - delta / 2
            else:
                start_azimuth = chord_az + delta / 2

        geometry = ArcGeometry(
            start_azimuth=start_azimuth,
            _radius=radius,
            _delta=delta,
            direction=direction,
        )
        return cls(
            geometry=geometry,
            start_station=start_station,
            start_coord=bc,
            start_azimuth=start_azimuth,
        )

    def reversed(self) -> "ArcEntity":
        """뒤집힌 원곡선 Entity."""
        new_geometry = self.geometry.reversed()
        return ArcEntity(
            entity_id=self.entity_id,
            geometry=new_geometry,
            start_station=self.start_station,
            start_coord=self.end_coord,
            start_azimuth=(self.end_azimuth + math.pi) % math.tau,
        )

    def offset_by(self, distance: float) -> "ArcEntity":
        """평행 이동한 원곡선 Entity."""
        return replace(
            self,
            geometry=self.geometry.offset_by(distance),
            start_coord=self.point_at(self.start_station, distance),
        )

    def _replace(self, **kwargs) -> "ArcEntity":
        return replace(self, **kwargs)