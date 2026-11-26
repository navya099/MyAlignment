from dataclasses import dataclass, field

from myalignment.pressure.part import AppurtenancePart
from myalignment.render.primitives_3d import Point3D


@dataclass(frozen=True, slots=True)
class PressureAppurtenance:
    """위치와 연결 관을 가진 밸브 등 기능 부속품."""

    id: str = ""
    name: str = ""
    part: AppurtenancePart = field(default_factory=AppurtenancePart)
    location: Point3D | None = None
    connected_pipe_ids: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "connected_pipe_ids", tuple(dict.fromkeys(self.connected_pipe_ids)))
