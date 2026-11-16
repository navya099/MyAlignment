# entity/line_entity.py
from __future__ import annotations
from dataclasses import dataclass, replace
import math

from cadgeom import Point2d

from myalignment.enitity.alignment_entity import AlignmentEntity
from myalignment.enum.alignmententitytype import AlignmentEntityType
from myalignment.geometry.line_geometry import LineGeometry


@dataclass(frozen=True, slots=True)
class LineEntity(AlignmentEntity):
    """직선 Entity (C3D AlignmentLine)."""
    entity_type: AlignmentEntityType = AlignmentEntityType.Line

    @classmethod
    def create(
        cls,
        start_coord: Point2d,
        end_coord: Point2d,
        start_station: float = 0.0,
    ) -> "LineEntity":
        """두 점으로 직선 Entity 생성."""
        dx = end_coord.x - start_coord.x
        dy = end_coord.y - start_coord.y
        length = math.hypot(dx, dy)
        if length <= 0:
            raise ValueError("시작점과 끝점이 같습니다.")
        azimuth = math.atan2(dy, dx)

        geometry = LineGeometry(
            start_azimuth=azimuth,
            _length=length,
        )
        return cls(
            geometry=geometry,
            start_station=start_station,
            start_coord=start_coord,
            start_azimuth=azimuth,
        )

    def reversed(self) -> "LineEntity":
        """뒤집힌 직선 Entity."""
        new_geometry = self.geometry.reversed()
        return LineEntity(
            entity_id=self.entity_id,
            geometry=new_geometry,
            start_station=self.start_station,
            start_coord=self.end_coord,
            start_azimuth=(self.start_azimuth + math.pi) % (2 * math.pi),
        )

    def offset_by(self, distance: float) -> "LineEntity":
        """평행 이동한 직선 Entity."""
        # offset: 좌(-)/우(+) → 월드 수직 벡터
        nx = -math.sin(self.start_azimuth)
        ny = math.cos(self.start_azimuth)
        # 좌(-) → +n, 우(+) → -n
        new_start = Point2d(
            self.start_coord.x - distance * nx,
            self.start_coord.y - distance * ny,
        )
        new_geometry = LineGeometry(
            start_azimuth=self.start_azimuth,
            _length=self.length,
        )
        return LineEntity(
            entity_id=self.entity_id,
            geometry=new_geometry,
            start_station=self.start_station,
            start_coord=new_start,
            start_azimuth=self.start_azimuth,
        )

    def _replace(self, **kwargs) -> "LineEntity":
        return replace(self, **kwargs)