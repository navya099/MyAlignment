from dataclasses import dataclass, field

from myalignment.turnout.table import TurnoutTable
from myalignment.turnout.type import TurnoutSide, TurnoutType

@dataclass(frozen=True, slots=True)
class Turnout:
    name: str = ''
    turnout_type: TurnoutType | None = None
    # 테이블 참조: 키워드 인자로만 전달
    table_name: str = field(default="", kw_only=True)
    table_entry_name: str = field(default="", kw_only=True)

    source_alignment_name: str = ''
    branch_alignment_name: str = ''
    station_on_source: float = 0.0
    side: TurnoutSide = TurnoutSide.RIGHT

    def __post_init__(self):
        if self.turnout_type is None or not self.source_alignment_name:
            raise ValueError('turnout_type and source_alignment_name are required')

    @classmethod
    def from_table(
            cls,
            name: str,
            table: TurnoutTable,
            entry_name: str,
            source_alignment_name: str,
            branch_alignment_name: str,
            station_on_source: float,
            side: TurnoutSide = None,
    ) -> "Turnout":
        """
        테이블 항목으로 턴아웃 생성.

        - entry_name으로 테이블에서 조회
        - side가 None이면 entry.default_side 사용
        """
        entry = table.get_or_raise(entry_name)
        return cls(
            name=name,
            turnout_type=entry.to_turnout_type(),
            table_name=table.name,
            table_entry_name=entry.name,
            source_alignment_name=source_alignment_name,
            branch_alignment_name=branch_alignment_name,
            station_on_source=station_on_source,
            side=side if side is not None else entry.default_side,
        )

    @property
    def branch_start_station(self) -> float:
        # Legacy property: approximate longitudinal station of branch arc start.
        return self.station_on_source + self.turnout_type.lead_length
