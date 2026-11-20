from dataclasses import dataclass
import math

from myalignment.render.stagger_direction import StaggerDirection, StaggerMethod


_DIRECTIONS = {
    StaggerDirection.UP: (0, 1),
    StaggerDirection.DOWN: (0, -1),
    StaggerDirection.LEFT: (-1, 0),
    StaggerDirection.RIGHT: (1, 0),
}


@dataclass(frozen=True, slots=True)
class StaggerConfig:
    """도면 좌표에서 텍스트의 겹침을 피할 방향, 거리와 최소 간격."""

    method: StaggerMethod = StaggerMethod.NONE
    direction: StaggerDirection = StaggerDirection.UP
    max_stagger_count: int = 3
    base_offset: float = 2.0
    increment: float = 1.5
    min_spacing: float = 2.0

    def __post_init__(self):
        if not isinstance(self.max_stagger_count, int) or self.max_stagger_count < 0:
            raise ValueError("max_stagger_count must be a nonnegative integer")
        for name in ("base_offset", "increment", "min_spacing"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")

    @property
    def is_active(self) -> bool:
        return self.method is not StaggerMethod.NONE

    def offset_at_level(self, level: int) -> tuple[float, float]:
        """0단계는 원위치이며 첫 이동은 base_offset을 사용한다."""
        if not 0 <= level <= self.max_stagger_count:
            raise ValueError("level is outside the configured range")
        if level == 0 or not self.is_active:
            return 0.0, 0.0
        if self.method is StaggerMethod.DISTANCE:
            distance = self.base_offset * level
        else:
            distance = self.base_offset + (level - 1) * self.increment
        x, y = _DIRECTIONS[self.direction]
        return x * distance, y * distance
