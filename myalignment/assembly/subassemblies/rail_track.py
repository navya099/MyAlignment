from dataclasses import dataclass, field
import math

from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassembly import Subassembly


@dataclass(frozen=True, slots=True)
class SingleTrack(Subassembly):
    """중심선 좌우의 레일과 도상 어깨를 생성하는 단선 궤도."""

    name: str = field(default="SingleTrack", init=False)
    side: int = field(default=0, init=False)
    apply_aor: bool = field(default=True, init=False)
    _target_parameters: tuple[str, ...] = field(default=(), init=False, repr=False)
    gauge: float = 1.435
    ballast_depth: float = 0.3

    def __post_init__(self):
        if not math.isfinite(self.gauge) or self.gauge <= 0:
            raise ValueError("gauge must be finite and positive")
        if not math.isfinite(self.ballast_depth) or self.ballast_depth <= 0:
            raise ValueError("ballast_depth must be finite and positive")

    def generate_geometry(self, target_mapping=None):
        half_gauge = self.gauge / 2
        left = AssemblyPoint(PointCode.LEFT_RAIL, -half_gauge, 0.0)
        right = AssemblyPoint(PointCode.RIGHT_RAIL, half_gauge, 0.0)
        ballast_left = AssemblyPoint(PointCode.EDGE, -half_gauge - 0.5, -self.ballast_depth)
        ballast_right = AssemblyPoint(PointCode.EDGE, half_gauge + 0.5, -self.ballast_depth)
        return (left, right, ballast_left, ballast_right), (
            AssemblyLink(LinkCode.PAVEMENT, left, right),
            AssemblyLink(LinkCode.SLOPE, ballast_left, left),
            AssemblyLink(LinkCode.SLOPE, right, ballast_right),
            AssemblyLink(LinkCode.BALLAST, ballast_left, ballast_right),
        )
