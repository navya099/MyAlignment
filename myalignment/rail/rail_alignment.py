from dataclasses import dataclass, field
from myalignment.alignment.alignment import Alignment
from myalignment.cant.curve import CantCurve, CantCriticalStation

@dataclass(frozen=True, slots=True)  # 부모와 동일하게 frozen=True 설정
class RailAlignment(Alignment):
    """
    C3D 호환 철도 선형(Rail Alignment) 컨테이너.
    """
    is_rail: bool = True
    gauge: float = 1.435  # 표준궤 (m)
    cant_curves: tuple[CantCurve, ...] = field(default_factory=tuple)

    def cant_at(self, station: float) -> CantCriticalStation | None:
        """특정 측점의 캔트(Cant) 정보를 조회합니다."""
        for c in self.cant_curves:
            if c.start_station <= station <= c.end_station:
                return c.cant_at(station)
        return None