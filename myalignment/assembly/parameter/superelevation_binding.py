from dataclasses import dataclass
import math

from myalignment.superelevation.collection import SuperelevationCollection
from myalignment.superelevation.critical_station import CrossSegmentType


@dataclass(frozen=True, slots=True)
class SuperelevationBinding:
    """한 횡단 세그먼트의 측점별 편구배와 기본 경사."""

    collection: SuperelevationCollection | None = None
    segment_type: CrossSegmentType = CrossSegmentType.RIGHT_OUT_LANE
    default_slope: float = -0.02

    def __post_init__(self):
        if not isinstance(self.segment_type, CrossSegmentType):
            raise ValueError("segment_type must be a CrossSegmentType")
        if not math.isfinite(self.default_slope):
            raise ValueError("default_slope must be finite")

    def slope_at(self, station: float) -> float:
        """인접 임계 측점 사이에서 경사(소수 비율)를 선형 보간한다."""
        if not math.isfinite(station):
            raise ValueError("station must be finite")
        curve = self.collection.curve_at_station(station) if self.collection is not None else None
        critical = curve.critical_stations if curve is not None else ()
        if not critical:
            return self.default_slope

        def slope(point):
            value = point.get_slope(self.segment_type)
            return self.default_slope if value is None else value

        if station <= critical[0].station:
            return slope(critical[0])
        for a, b in zip(critical, critical[1:]):
            if station <= b.station:
                fraction = (station - a.station) / (b.station - a.station)
                return slope(a) + fraction * (slope(b) - slope(a))
        return slope(critical[-1])
