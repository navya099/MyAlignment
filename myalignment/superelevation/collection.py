# superelevation/collection.py
from __future__ import annotations
from dataclasses import dataclass, field, replace

from myalignment.superelevation.critical_station import CrossSegmentType, TransitionRegionType
from myalignment.superelevation.curve import PivotMethod, SuperelevationCurve


@dataclass(frozen=True, slots=True)
class SuperelevationCollection:
    """
    편구배 곡선 컬렉션 (불변).

    C3D의 Alignment.SuperelevationCurves와 호환.
    """
    curves: tuple[SuperelevationCurve, ...] = field(default_factory=tuple)

    def __len__(self) -> int:
        return len(self.curves)

    def __iter__(self):
        return iter(self.curves)

    def curve_at_station(self, station: float) -> SuperelevationCurve | None:
        """측점이 속한 편구배 곡선."""
        for c in self.curves:
            if c.start_station <= station <= c.end_station:
                return c
        return None

    def add(self, curve: SuperelevationCurve) -> "SuperelevationCollection":
        """새 곡선 추가한 새 컬렉션."""
        new_list = list(self.curves) + [curve]
        new_list.sort(key=lambda c: c.start_station)
        return SuperelevationCollection(curves=tuple(new_list))

    def _reversed_about(self, station_sum: float) -> "SuperelevationCollection":
        transitions = {
            TransitionRegionType.TRANSITION_IN: TransitionRegionType.TRANSITION_OUT,
            TransitionRegionType.TRANSITION_OUT: TransitionRegionType.TRANSITION_IN,
        }
        pivots = {PivotMethod.LEFT_SIDE: PivotMethod.RIGHT_SIDE, PivotMethod.RIGHT_SIDE: PivotMethod.LEFT_SIDE}
        sides = {}
        for segment in CrossSegmentType:
            side, kind = segment.name.split("_", maxsplit=1)
            other = "RIGHT" if side == "LEFT" else "LEFT"
            sides[segment] = CrossSegmentType[f"{other}_{kind}"]

        curves = (
            replace(
                curve, start_station=station_sum - curve.end_station,
                end_station=station_sum - curve.start_station,
                pivot_method=pivots.get(curve.pivot_method, curve.pivot_method),
                critical_stations=tuple(
                    replace(
                        station, station=station_sum - station.station,
                        region_type=transitions.get(station.region_type, station.region_type),
                        slopes={sides[segment]: slope for segment, slope in station.slopes.items()},
                    )
                    for station in reversed(curve.critical_stations)
                ),
            )
            for curve in self.curves
        )
        return SuperelevationCollection(tuple(sorted(curves, key=lambda curve: curve.start_station)))
