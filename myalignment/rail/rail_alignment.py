from dataclasses import dataclass, field
from myalignment.alignment.alignment import Alignment
from myalignment.cant.curve import CantCurve, CantCriticalStation
from myalignment.turnout.crossover_set import CrossoverSet
from myalignment.turnout.table_set import TurnoutTableSet


@dataclass(frozen=True, slots=True)  # 부모와 동일하게 frozen=True 설정
class RailAlignment(Alignment):
    """
    C3D 호환 철도 선형(Rail Alignment) 컨테이너.
    """
    is_rail: bool = True
    gauge: float = 1.435  # 표준궤 (m)
    cant_curves: tuple[CantCurve, ...] = field(default_factory=tuple)
    crossovers: CrossoverSet = field(default_factory=CrossoverSet)

    # 테이블 참조
    turnout_tables: TurnoutTableSet = field(default_factory=TurnoutTableSet)

    def turnout_entry(self, table_name: str, entry_name: str):
        """테이블에서 항목 조회."""
        table = self.turnout_tables.get(table_name)
        if table is None:
            return None
        return table.get(entry_name)

    def cant_at(self, station: float) -> CantCriticalStation | None:
        """특정 측점의 캔트(Cant) 정보를 조회합니다."""
        for c in self.cant_curves:
            if c.start_station <= station <= c.end_station:
                return c.cant_at(station)
        return None

    def crossovers_with(self, other_name: str) -> tuple:
        """특정 선형과의 Crossover."""
        return tuple(
            c for c in self.crossovers
            if (c.source_alignment1_name == self.name and c.source_alignment2_name == other_name)
            or (c.source_alignment1_name == other_name and c.source_alignment2_name == self.name)
        )