from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True, slots=True)
class ConnectionGeometry:
    name: str
    start_point: Any
    end_point: Any
    start_azimuth: float
    end_azimuth: float
    length: float
    start_station: float
    end_station: float

@dataclass(frozen=True, slots=True)
class CrossoverGeometry:
    turnout1_station: float = 0.0
    turnout1_point: Any = None
    turnout1_azimuth: float = 0.0
    turnout2_station: float = 0.0
    turnout2_point: Any = None
    turnout2_azimuth: float = 0.0
    connecting_length: float = 0.0
    connecting_azimuth: float = 0.0
    connections: tuple[ConnectionGeometry, ...] = field(default_factory=tuple)
    required_station_delta: float = 0.0
    is_valid: bool = False
    error_message: str = ''

    def __post_init__(self):
        if not self.is_valid and not self.error_message:
            raise ValueError('invalid geometry requires error_message')
