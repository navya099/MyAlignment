# corridor/region.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
from collections.abc import Callable
import math

from myalignment.assembly.assembly import Assembly
from myalignment.assembly.codes import PointCode
from myalignment.assembly.section_context import SectionContext
from myalignment.cant.curve import CantCurve, CantPivotMethod
from myalignment.target.mapping import TargetMapping


@dataclass(frozen=True, slots=True)
class CorridorRegion:
    """
    코리더 영역 (불변).

    어셈블리가 적용되는 측점 범위.
    """
    name: str = ""
    start_station: float = 0.0
    end_station: float = 0.0
    assembly: Assembly | None = None
    frequency: float = 10.0  # 측점 간격 (m)
    target_mapping: TargetMapping = field(default_factory=TargetMapping.empty)
    # Region에 CantCurve 참조 (선택)
    cant_curve: CantCurve | None = None
    baseline_name: str | None = field(default=None, kw_only=True)
    context_provider: Callable[[float], SectionContext] | None = field(default=None, kw_only=True, repr=False)
    _binding_station_map: Callable[[float], float] | None = field(default=None, kw_only=True, repr=False)
    _mirrored: bool = field(default=False, repr=False, kw_only=True)

    def __post_init__(self):
        if not (math.isfinite(self.start_station) and math.isfinite(self.end_station)):
            raise ValueError("측점은 유한해야 합니다.")
        if self.end_station < self.start_station:
            raise ValueError(f"end < start: {self.end_station} < {self.start_station}")
        if not math.isfinite(self.frequency) or self.frequency <= 0:
            raise ValueError(f"frequency > 0 필요: {self.frequency}")

    @property
    def length(self) -> float:
        return self.end_station - self.start_station

    @property
    def station_count(self) -> int:
        """영역 내 샘플 측점 수."""
        return math.ceil(self.length / self.frequency) + 1

    def sample_stations(self, frequency: float | None = None) -> list[float]:
        """시작, 지정 간격, 끝 측점을 중복 없이 반환한다."""
        step = self.frequency if frequency is None else frequency
        if not math.isfinite(step) or step <= 0:
            raise ValueError("frequency는 유한한 양수여야 합니다.")
        stations = [self.start_station + i * step for i in range(math.ceil(self.length / step))]
        if stations and stations[-1] >= self.end_station:
            stations.pop()
        stations.append(self.end_station)
        return stations

    def cross_section_at(self, station: float, *, context: SectionContext | None = None):
        if self.assembly is None:
            return (), ()
        if self.assembly.uses_section_context:
            if context is None and self.context_provider is not None:
                context = self.context_provider(station)
            context = context or SectionContext(station=station)
            binding_station = self._binding_station_map(station) if self._binding_station_map else context.binding_station
            context = replace(context, station=station, binding_station=binding_station)
            points, links = self.assembly.generate_cross_section(self.target_mapping, context=context)
        else:
            points, links = self.assembly.generate_cross_section(self.target_mapping)
        if self._mirrored:
            rail_codes = {
                PointCode.LEFT_RAIL: PointCode.RIGHT_RAIL,
                PointCode.RIGHT_RAIL: PointCode.LEFT_RAIL,
                PointCode.BRANCH_LEFT_RAIL: PointCode.BRANCH_RIGHT_RAIL,
                PointCode.BRANCH_RIGHT_RAIL: PointCode.BRANCH_LEFT_RAIL,
            }
            reflected = {
                point: replace(point, x=-point.x, code=rail_codes.get(point.code, point.code))
                for point in (*points, *(p for link in links for p in (link.start, link.end)))
            }
            points = tuple(reflected[point] for point in points)
            links = tuple(replace(link, start=reflected[link.start], end=reflected[link.end]) for link in links)
        if self.cant_curve is None:
            return points, links
        cant = self.cant_curve.cant_at(station)
        if cant is None or (not cant.left_rail_delta and not cant.right_rail_delta):
            return points, links

        left_x, right_x = -1.435 / 2, 1.435 / 2
        rail_offsets = {p.code: p.x for p in points}
        if PointCode.LEFT_RAIL in rail_offsets and PointCode.RIGHT_RAIL in rail_offsets:
            track_left = rail_offsets[PointCode.LEFT_RAIL]
            track_right = rail_offsets[PointCode.RIGHT_RAIL]
            if track_left < 0 < track_right:
                left_x, right_x = track_left, track_right

        left_delta, right_delta = cant.left_rail_delta, cant.right_rail_delta
        slope = (right_delta - left_delta) / (right_x - left_x)

        section_points = dict.fromkeys(points)
        for link in links:
            section_points[link.start] = None
            section_points[link.end] = None
        fixed = {(round(p.x, 9), round(p.z, 9)) for p in section_points if p.apply_aor is False}

        def apply_cant(point):
            if fixed and (round(point.x, 9), round(point.z, 9)) in fixed:
                return point
            if self.cant_curve.pivot_method is CantPivotMethod.CENTERLINE:
                if point.x < 0:
                    delta = point.x * left_delta / left_x
                else:
                    delta = point.x * right_delta / right_x
            else:
                delta = left_delta + (point.x - left_x) * slope
            return replace(point, z=point.z + delta)

        updated = {point: apply_cant(point) for point in section_points}
        return (
            tuple(updated[p] for p in points),
            tuple(replace(link, start=updated[link.start], end=updated[link.end]) for link in links),
        )

    def with_targets(self, mapping: TargetMapping) -> "CorridorRegion":
        """Target 매핑 갱신한 새 Region."""
        return replace(self, target_mapping=mapping)
