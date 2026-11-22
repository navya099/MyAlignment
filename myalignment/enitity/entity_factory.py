# entity/entity_factory.py
from __future__ import annotations
import math
from typing import Sequence

from cadgeom import Point2d

from myalignment.enitity.alignment_entity import AlignmentEntity
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.entity_collection import AlignmentEntityCollection
from myalignment.enitity.line_entity import LineEntity
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.enum.spiraltype import SpiralType
from myalignment.exception.alignment_error import NotEnoughPIPointError, InvalidGeometryError, DuplicatePIError
from myalignment.ipdata.ipdata import PIInput, PICurveSpec
from myalignment.utils import CurveDirection


class EntityFactory:
    """
    PI 좌표/곡선 사양 → Entity 시퀀스 생성기.

    C3D의 Alignment.CreateFromPolyline 등에 대응.

    생성 규칙:
        - PI[i]가 직선 → LineEntity (PI[i-1] → PI[i])
        - PI[i]가 곡선 → [Spiral(entry)]? + Arc + [Spiral(exit)]?
        - 마지막 PI → LineEntity
    """
    MIN_TANGENT_LENGTH = 1e-6

    @classmethod
    def build(cls, pi_input: PIInput) -> AlignmentEntityCollection:
        """PI 접선 위에 곡선군을 배치하고 남은 접선 구간만 직선으로 잇는다."""
        points, specs = pi_input.pi_coords, pi_input.curve_specs
        if len(points) < 2:
            raise NotEnoughPIPointError()
        cls._check_duplicates(points)
        segments = cls._compute_segments(points)
        if any(spec.has_spiral and spec.radius is None for spec in specs):
            raise InvalidGeometryError("완화곡선에는 원곡선 반경이 필요합니다")

        curves = [
            cls._curve_at_pi(i, specs[i], segments[i - 1][1], segments[i][1])
            if specs[i].radius is not None else (0.0, 0.0, ())
            for i in range(1, len(points) - 1)
        ]
        curves = [(0.0, 0.0, ()), *curves, (0.0, 0.0, ())]
        entities: list[AlignmentEntity] = []
        station = pi_input.start_station
        current = points[0]

        for i, (length, azimuth) in enumerate(segments):
            outgoing = curves[i][1]
            incoming, _, group = curves[i + 1]
            if length - outgoing - incoming < -cls.MIN_TANGENT_LENGTH:
                raise InvalidGeometryError(f"PI[{i}]→PI[{i + 1}] 접선장 부족 또는 곡선군 중첩")
            start_of_curve = cls._interpolate(points[i + 1], azimuth, -incoming)
            if current.distance_to(start_of_curve) > cls.MIN_TANGENT_LENGTH:
                line = LineEntity.create(current, start_of_curve, station)
                entities.append(line)
                station = line.end_station
                current = line.end_coord
            for template in group:
                entity = template.with_start(current, station)
                entities.append(entity)
                current, station = entity.end_coord, entity.end_station

        return AlignmentEntityCollection(tuple(entities))

    # ---- 헬퍼 ----
    @staticmethod
    def _check_duplicates(pts: Sequence[Point2d]):
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                if pts[i].distance_to(pts[j]) < 1e-6:
                    raise DuplicatePIError(i)

    @staticmethod
    def _compute_segments(pts: Sequence[Point2d]) -> list[tuple[float, float]]:
        """인접 PI 사이 (길이, 방위각) 리스트."""
        result = []
        for i in range(len(pts) - 1):
            dx = pts[i + 1].x - pts[i].x
            dy = pts[i + 1].y - pts[i].y
            length = math.hypot(dx, dy)
            if length < 1e-9:
                raise InvalidGeometryError(f"PI[{i}]→PI[{i + 1}] 길이 0")
            azimuth = math.atan2(dy, dx)
            result.append((length, azimuth))
        return result

    @staticmethod
    def _interpolate(p: Point2d, azimuth: float, distance: float) -> Point2d:
        """점에서 방위각 방향으로 distance만큼 이동한 점."""
        return Point2d(
            p.x + distance * math.cos(azimuth),
            p.y + distance * math.sin(azimuth),
        )

    @classmethod
    def _curve_at_pi(cls, index, spec: PICurveSpec, incoming: float, outgoing: float):
        turn = math.remainder(outgoing - incoming, math.tau)
        if abs(turn) < 1e-10 or abs(turn) >= math.pi - 1e-10:
            raise InvalidGeometryError(f"PI[{index}] 교각이 유효하지 않습니다")
        if not math.isfinite(spec.radius):
            raise InvalidGeometryError(f"PI[{index}] 반경이 유효하지 않습니다")

        direction = CurveDirection.LEFT if turn > 0 else CurveDirection.RIGHT
        opposite = CurveDirection.RIGHT if turn > 0 else CurveDirection.LEFT
        origin = Point2d(0, 0)
        group = []
        point, azimuth = origin, incoming
        if spec.entry_length:
            entry = SpiralEntity.create(point, azimuth, spec.radius, spec.entry_length, spec.spiral_type, direction)
            group.append(entry)
            point, azimuth = entry.end_coord, entry.end_azimuth

        exit_spiral = None
        arc_end_azimuth = outgoing
        if spec.exit_length:
            # 접선에서 원곡선을 향해 만든 완화곡선을 뒤집으면 진출 곡률 순서가 된다.
            exit_spiral = SpiralEntity.create(
                origin, outgoing + math.pi, spec.radius, spec.exit_length, spec.spiral_type, opposite,
            ).reversed()
            arc_end_azimuth = exit_spiral.start_azimuth

        arc_turn = math.remainder(arc_end_azimuth - azimuth, math.tau)
        delta = (1 if turn > 0 else -1) * arc_turn
        if delta <= 1e-10 or delta > abs(turn) + 1e-10:
            raise InvalidGeometryError(f"PI[{index}] 완화곡선에 비해 원곡선 교각 부족")
        arc = ArcEntity.create(point, azimuth, spec.radius, delta, direction)
        group.append(arc)
        end = arc.end_coord
        if exit_spiral is not None:
            exit_spiral = exit_spiral.with_start(end, 0.0)
            group.append(exit_spiral)
            end = exit_spiral.end_coord

        # 곡선군 변위를 진입·진출 접선 벡터의 선형 결합으로 분해한다.
        determinant = math.sin(turn)
        before = (end.x * math.sin(outgoing) - end.y * math.cos(outgoing)) / determinant
        after = (math.cos(incoming) * end.y - math.sin(incoming) * end.x) / determinant
        if min(before, after) <= 0:
            raise InvalidGeometryError(f"PI[{index}] 곡선군 접선장 부족")
        return before, after, tuple(group)


# ---- 편의 함수 ----
def build_alignment_entities(
        coords: list[tuple[float, float]] | list[Point2d],
        radii: list[float | None],
        start_station: float = 0.0,
        spiral_type: SpiralType = SpiralType.Clothoid,
        entry_lengths: list[float] | None = None,
        exit_lengths: list[float] | None = None,
) -> AlignmentEntityCollection:
    """편의: 좌표/반경으로 바로 Entity 시퀀스 생성."""
    pi_input = PIInput.from_coords_and_radii(
        coords=coords,
        radii=radii,
        start_station=start_station,
        spiral_type=spiral_type,
        entry_lengths=entry_lengths,
        exit_lengths=exit_lengths,
    )
    return EntityFactory.build(pi_input)