from dataclasses import dataclass
import math

from myalignment.cant.curve import CantPivotMethod
from myalignment.superelevation.critical_station import TransitionRegionType


@dataclass(frozen=True, slots=True)
class CantBandSegment:
    """캔트 밴드 구간. 캔트 크기는 mm 단위로 저장한다."""

    start_station: float = 0.0
    end_station: float = 0.0
    start_cant: float = 0.0
    end_cant: float = 0.0
    region_type: TransitionRegionType = TransitionRegionType.NORMAL
    pivot_method: CantPivotMethod | None = None

    def __post_init__(self):
        if not all(math.isfinite(value) for value in (
            self.start_station, self.end_station, self.start_cant, self.end_cant,
        )):
            raise ValueError("Cant segment stations and values must be finite")
        if self.end_station < self.start_station:
            raise ValueError("Cant segment end_station precedes start_station")

    @property
    def length(self) -> float:
        return self.end_station - self.start_station

    @property
    def cant_change(self) -> float:
        return self.end_cant - self.start_cant

    def cant_at(self, station: float) -> float:
        if not self.length:
            return self.start_cant
        fraction = max(0.0, min(1.0, (station - self.start_station) / self.length))
        return self.start_cant + fraction * self.cant_change
