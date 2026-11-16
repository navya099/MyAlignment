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
from myalignment.utils.math_utils import find_curve_direction, is_invalid_arc, calculator_internal_angle, \
    calculate_bearing


class EntityFactory:
    """
    PI 좌표/곡선 사양 → Entity 시퀀스 생성기.

    C3D의 Alignment.CreateFromPolyline 등에 대응.

    생성 규칙:
        - PI[i]가 직선 → LineEntity (PI[i-1] → PI[i])
        - PI[i]가 곡선 → [Spiral(entry)]? + Arc + [Spiral(exit)]?
        - 마지막 PI → LineEntity
    """
    # 최소 곡선 길이 (수치 안정성)
    MIN_TANGENT_LENGTH = 1e-6
    # 최대 완화곡선 길이 비율 (delta > 0 보장)
    MAX_SPIRAL_RATIO = 0.9

    @classmethod
    def build(cls, pi_input: PIInput) -> AlignmentEntityCollection:
        """PIInput → AlignmentEntityCollection."""
        pts = pi_input.pi_coords
        specs = pi_input.curve_specs

        if len(pts) < 2:
            raise NotEnoughPIPointError()

        # 1) 중복 좌표 검사
        cls._check_duplicates(pts)

        # 2) 각 구간 길이/방위각 계산
        segments = cls._compute_segments(pts)  # [(length, azimuth), ...]

        # 3) Entity 생성
        entities: list[AlignmentEntity] = []
        current_station = pi_input.start_station
        current_coord = pts[0]

        # [수정] 첫 번째 PI(specs[0])에 진입 완화곡선이 설정되어 있는 경우 차단
        if specs[0].has_spiral and specs[0].entry_length > 0:
            raise InvalidGeometryError("첫 PI에 완화곡선 불가")

        for i in range(len(pts) - 1):
            spec_a = specs[i]  # 현재 PI
            spec_b = specs[i + 1]  # 다음 PI
            seg_len, seg_az = segments[i]
            next_pt = pts[i + 1]

            # 진입 완화곡선이 필요한 경우 (다음 PI의 entry)
            entry_spec = spec_b if spec_b.has_spiral and spec_b.entry_length > 0 else None

            # 다음 PI의 진입 완화곡선까지의 직선 길이
            if entry_spec:
                spiral_TL = cls._spiral_tangent_length(
                    entry_spec.radius, entry_spec.entry_length, entry_spec.spiral_type
                )
                straight_len = seg_len - spiral_TL
            else:
                straight_len = seg_len

            if straight_len < -cls.MIN_TANGENT_LENGTH:
                raise InvalidGeometryError(
                    f"PI[{i}]→PI[{i + 1}] 구간 길이 부족: "
                    f"seg={seg_len:.3f}, spiral_TL={spiral_TL:.3f}"
                )
            straight_len = max(0.0, straight_len)

            # 직선 Entity
            if straight_len > cls.MIN_TANGENT_LENGTH:
                line = LineEntity.create(
                    start_coord=current_coord,
                    end_coord=cls._interpolate(current_coord, seg_az, straight_len),
                    start_station=current_station,
                )
                entities.append(line)
                current_station += line.length
                current_coord = line.end_coord

            # 진입 완화곡선 Entity (다음 PI의 entry)
            if entry_spec:
                # 완화곡선이 속한 PI 지점은 i + 1 입니다. (예: i=0일 때 PI[1]에서의 곡선)
                pi_idx = i + 1
                bp = pts[pi_idx - 1]
                ip = pts[pi_idx]
                ep = pts[pi_idx + 1] if pi_idx + 1 < len(pts) else None

                curve_dir = find_curve_direction(bp, ip, ep) if ep else CurveDirection.NULL

                spiral = SpiralEntity.create(
                    start_coord=current_coord,
                    start_azimuth=seg_az,
                    radius=entry_spec.radius,
                    length=entry_spec.entry_length,
                    spiral_type=entry_spec.spiral_type,
                    direction=curve_dir,
                    start_station=current_station,
                )
                entities.append(spiral)
                current_station += spiral.length
                current_coord = spiral.end_coord

            # 원곡선 Entity (PI[i+1]이 곡선일 때)
            if spec_b.radius is not None:
                arc = cls._build_arc_at_pi(
                    pts=pts,
                    pi_index=i + 1,
                    spec=spec_b,
                    entry_end_coord=current_coord,
                    entry_end_station=current_station,
                )
                if arc is not None:
                    entities.append(arc)
                    current_station += arc.length
                    current_coord = arc.end_coord

                    # 진출 완화곡선
                    if spec_b.has_spiral and spec_b.exit_length > 0:
                        exit_spiral = SpiralEntity.create(
                            start_coord=current_coord,
                            start_azimuth=arc.end_azimuth,
                            radius=spec_b.radius,
                            length=spec_b.exit_length,
                            spiral_type=spec_b.spiral_type,
                            direction=arc.geometry.direction,
                            start_station=current_station,
                        )
                        entities.append(exit_spiral)
                        current_station += exit_spiral.length
                        current_coord = exit_spiral.end_coord

        # 4) 컬렉션 생성 (연속성 검증 포함)
        return AlignmentEntityCollection(entities=tuple(entities))

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

    @staticmethod
    def _spiral_tangent_length(
            radius: float, length: float, spiral_type: SpiralType
    ) -> float:
        """완화곡선의 접선장 TL (근사)."""
        if radius is None or length <= 0:
            return 0.0
        # 표준 근사: TL ≈ L/2 + L³/(240·R²) (클로소이드)
        # 일본식도 유사 근사 사용
        return length / 2 + length ** 3 / (240 * radius ** 2)

    @staticmethod
    def _find_direction(p1: Point2d, p2: Point2d, p3: Point2d) -> CurveDirection:
        """세 점으로 곡선 방향 판정."""
        return find_curve_direction(p1, p2, p3)

    @classmethod
    def _build_arc_at_pi(
            cls,
            pts: Sequence[Point2d],
            pi_index: int,
            spec: PICurveSpec,
            entry_end_coord: Point2d,
            entry_end_station: float,
    ) -> ArcEntity | None:
        """
        PI[pi_index]에서 원곡선 생성.
        entry_end_coord: 진입 완화곡선(또는 직선)이 끝난 점
        """
        bp = pts[pi_index - 1]
        ip = pts[pi_index]
        ep = pts[pi_index + 1] if pi_index + 1 < len(pts) else None

        if ep is None:
            return None

        # 유효성 검사
        is_invalid, msg = is_invalid_arc(bp, ip, ep, spec.radius)
        if is_invalid:
            raise InvalidGeometryError(msg)

        # IA, 방향
        ia = calculator_internal_angle(bp, ip, ep)
        direction = find_curve_direction(bp, ip, ep)
        if direction == CurveDirection.NULL:
            raise InvalidGeometryError(f"PI[{pi_index}] 방향 판정 불가")

        # 접선장 TL
        R = spec.radius
        TL = R * math.tan(ia / 2)

        # 진입/진출 완화곡선에 의한 보정
        if spec.has_spiral:
            TL_entry = cls._spiral_tangent_length(R, spec.entry_length, spec.spiral_type)
            TL_exit = cls._spiral_tangent_length(R, spec.exit_length, spec.spiral_type)
            TL -= TL_entry + TL_exit

        if TL < cls.MIN_TANGENT_LENGTH:
            raise InvalidGeometryError(
                f"PI[{pi_index}] 접선장 부족: TL={TL:.3f}"
            )

        # 원곡선 시작점 (BC) = IP에서 역방향 TL
        bp_az = calculate_bearing(bp, ip)
        bc = cls._interpolate(ip, bp_az + math.pi, TL)

        # 원곡선 시작 접선 방위각
        if direction == CurveDirection.LEFT:
            start_az = bp_az + ia / 2  # 보정 (근사)
        else:
            start_az = bp_az - ia / 2

        # delta = ia (완화곡선이 있으면 감소)
        delta = ia
        if spec.has_spiral:
            # 완화곡선 각도만큼 감소
            theta_entry = cls._spiral_theta(spec.entry_length, R, spec.spiral_type)
            theta_exit = cls._spiral_theta(spec.exit_length, R, spec.spiral_type)
            delta = ia - theta_entry - theta_exit

        if delta <= 0:
            raise InvalidGeometryError(
                f"PI[{pi_index}] 원곡선 교각 부족: delta={delta:.4f}"
            )

        return ArcEntity.create(
            start_coord=entry_end_coord,  # ← 연속성 유지
            start_azimuth=start_az,
            radius=R,
            delta=delta,
            direction=direction,
            start_station=entry_end_station,
        )

    @staticmethod
    def _spiral_theta(length: float, radius: float, spiral_type: SpiralType) -> float:
        """완화곡선 회전각 θ = L / (2R) (근사)."""
        if length <= 0 or radius <= 0:
            return 0.0
        return length / (2 * radius)


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