from enum import Enum


class StationEquationType(Enum):
    INCREASING = "Increasing"
    DECREASING = "Decreasing"

    @property
    def sign(self) -> int:
        return 1 if self is StationEquationType.INCREASING else -1
