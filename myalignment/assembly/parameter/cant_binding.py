from dataclasses import dataclass
import math

from myalignment.cant.curve import CantCurve, CantPivotMethod


@dataclass(frozen=True, slots=True)
class CantBinding:
    """철도 캔트 곡선과 레일 회전축. 기본 캔트의 단위는 mm다."""

    cant_curves: tuple[CantCurve, ...] = ()
    pivot_method: CantPivotMethod = CantPivotMethod.CENTERLINE
    gauge: float = 1.435
    default_cant: float = 0.0

    def __post_init__(self):
        object.__setattr__(self, "cant_curves", tuple(self.cant_curves))
        if not isinstance(self.pivot_method, CantPivotMethod):
            raise ValueError("pivot_method must be a CantPivotMethod")
        if not math.isfinite(self.gauge) or self.gauge <= 0:
            raise ValueError("gauge must be finite and positive")
        if not math.isfinite(self.default_cant):
            raise ValueError("default_cant must be finite")

    def _cant_metres_at(self, station: float) -> float:
        if not math.isfinite(station):
            raise ValueError("station must be finite")
        for curve in self.cant_curves:
            if curve.start_station <= station <= curve.end_station:
                sample = curve.cant_at(station)
                if sample is not None:
                    return sample.cant_value
        return self.default_cant / 1000

    def cant_at(self, station: float) -> float:
        """우측 레일과 좌측 레일의 표고차를 mm로 반환한다."""
        return self._cant_metres_at(station) * 1000

    def rail_offsets_at(self, station: float) -> tuple[float, float]:
        """피벗에 따른 좌·우 레일의 기준 표고 대비 변위를 m로 반환한다."""
        cant = self._cant_metres_at(station)
        if self.pivot_method is CantPivotMethod.LEFT_RAIL:
            return 0.0, cant
        if self.pivot_method is CantPivotMethod.RIGHT_RAIL:
            return -cant, 0.0
        return -cant / 2, cant / 2
