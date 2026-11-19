from dataclasses import dataclass
from enum import Enum
import math

class TurnoutSide(Enum):
    LEFT = 'left'
    RIGHT = 'right'

    @property
    def sign(self) -> int:
        return 1 if self is TurnoutSide.LEFT else -1

@dataclass(frozen=True, slots=True)
class TurnoutType:
    """Idealized turnout: straight lead before a circular arc to frog angle.

    WARNING: lead_length is defined HERE as straight approach length before
    the branch arc, NOT a certified manufacturer's turnout lead dimension.
    """
    name: str = ''
    frog_number: float = 0.0
    lead_length: float = 0.0
    radius: float = 0.0
    max_speed_main: float = 0.0
    max_speed_branch: float = 0.0

    def __post_init__(self):
        for key in ('frog_number', 'lead_length', 'radius'):
            value = getattr(self, key)
            if not math.isfinite(value):
                raise ValueError(f'{key} must be finite')
        if self.frog_number <= 0 or self.radius <= 0 or self.lead_length < 0:
            raise ValueError('frog_number and radius must be positive; lead_length nonnegative')

    @property
    def frog_angle(self) -> float:
        return math.atan(1.0 / self.frog_number)

    @property
    def arc_length(self) -> float:
        return self.radius * self.frog_angle

    @property
    def run(self) -> float:
        return self.lead_length + self.radius * math.sin(self.frog_angle)

    @property
    def rise(self) -> float:
        return self.radius * (1.0 - math.cos(self.frog_angle))
