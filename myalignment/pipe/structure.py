from dataclasses import dataclass, field
import math

from cadgeom import Point2d

from myalignment.pipe.pipe_part import StructurePart


@dataclass(frozen=True, slots=True)
class Structure:
    """관망의 접속 구조물과 현재 연결된 관 ID."""

    id: str = ""
    name: str = ""
    part: StructurePart = field(default_factory=StructurePart)
    point: Point2d | None = None
    station: float | None = None
    offset: float = 0.0
    rim_elevation: float = 0.0
    invert_elevation: float = 0.0
    sump_elevation: float | None = None
    connected_pipe_ids: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "connected_pipe_ids", tuple(self.connected_pipe_ids))
        required = (self.offset, self.rim_elevation, self.invert_elevation)
        optional = (self.station, self.sump_elevation)
        if not all(map(math.isfinite, required)) or any(
            value is not None and not math.isfinite(value) for value in optional
        ):
            raise ValueError("structure station, offset and elevations must be finite")
        if self.point is not None and not (math.isfinite(self.point.x) and math.isfinite(self.point.y)):
            raise ValueError("structure coordinates must be finite")

    @property
    def depth(self) -> float:
        """림 표고에서 관저고를 뺀 깊이."""
        return self.rim_elevation - self.invert_elevation

    @property
    def bottom_elevation(self) -> float:
        return self.invert_elevation if self.sump_elevation is None else self.sump_elevation
