from dataclasses import dataclass
from myalignment.turnout.type import TurnoutSide, TurnoutType

@dataclass(frozen=True, slots=True)
class Turnout:
    name: str = ''
    turnout_type: TurnoutType | None = None
    source_alignment_name: str = ''
    branch_alignment_name: str = ''
    station_on_source: float = 0.0
    side: TurnoutSide = TurnoutSide.RIGHT

    def __post_init__(self):
        if self.turnout_type is None or not self.source_alignment_name:
            raise ValueError('turnout_type and source_alignment_name are required')

    @property
    def branch_start_station(self) -> float:
        # Legacy property: approximate longitudinal station of branch arc start.
        return self.station_on_source + self.turnout_type.lead_length
