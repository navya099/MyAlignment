from dataclasses import dataclass, field
import math

from myalignment.pressure.part import PressurePipePart
from myalignment.render.primitives_3d import Point3D


@dataclass(frozen=True, slots=True)
class PressurePipe:
    """직선 관 중심선과 양 끝의 피팅 또는 부속품 참조."""

    id: str = ""
    name: str = ""
    part: PressurePipePart = field(default_factory=PressurePipePart)
    start_point: Point3D | None = None
    end_point: Point3D | None = None
    start_fitting_id: str = ""
    end_fitting_id: str = ""
    alignment_name: str = ""
    surface_name: str = ""
    start_appurtenance_id: str = ""
    end_appurtenance_id: str = ""
    cover: float | None = None

    def __post_init__(self):
        if ((self.start_fitting_id and self.start_appurtenance_id)
                or (self.end_fitting_id and self.end_appurtenance_id)):
            raise ValueError("Each pipe endpoint can connect to one fitting or appurtenance")
        if self.cover is not None and not math.isfinite(self.cover):
            raise ValueError("cover must be finite")

    @property
    def centerline(self) -> tuple[Point3D, ...]:
        if self.start_point is None or self.end_point is None:
            return ()
        return self.start_point, self.end_point

    @property
    def length(self) -> float:
        return self.start_point.distance_to(self.end_point) if self.centerline else 0.0

    @property
    def slope(self) -> float:
        """시점에서 종점으로의 축 구배. 수직 관은 방향에 따라 ±inf이다."""
        if not self.centerline:
            return 0.0
        a, b = self.centerline
        rise = b.z - a.z
        run = math.hypot(b.x - a.x, b.y - a.y)
        return rise / run if run else math.copysign(math.inf, rise) if rise else 0.0
