from dataclasses import dataclass
from enum import Enum
import math

from cadgeom import Point2d


class ViewportType(Enum):
    PLAN = "Plan"
    PROFILE = "Profile"
    SECTION = "Section"


@dataclass(frozen=True, slots=True)
class Viewport:
    """평면 XY 또는 종·횡단의 수평 좌표와 표고를 도면에 배치한다."""

    type: ViewportType = ViewportType.PLAN
    vertical_exaggeration: float = 1.0
    origin_x: float = 0.0
    origin_y: float = 0.0

    def __post_init__(self):
        if not math.isfinite(self.vertical_exaggeration) or self.vertical_exaggeration <= 0:
            raise ValueError("vertical_exaggeration must be finite and positive")

    def project(self, x: float, y: float) -> Point2d:
        scale = 1.0 if self.type is ViewportType.PLAN else self.vertical_exaggeration
        return Point2d(self.origin_x + x, self.origin_y + y * scale)
