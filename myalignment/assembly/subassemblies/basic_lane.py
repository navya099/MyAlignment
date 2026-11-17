# assembly/subassemblies/basic_lane.py
from __future__ import annotations
from dataclasses import dataclass

from myalignment.assembly.codes import PointCode, LinkCode, ShapeCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassembly import Subassembly


@dataclass(frozen=True, slots=True)
class BasicLane(Subassembly):
    """
    기본 차로 (C3D BasicLane 호환).

    폭과 기울기로 정의.
    """
    name: str = "BasicLane"
    width: float = 3.5  # 차로 폭 (m)
    slope: float = -0.02  # 기울기 (2% 우측 하향)
    side: int = 1  # +1: 우측, -1: 좌측

    def __post_init__(self):
        if self.width <= 0:
            raise ValueError(f"width > 0 필요: {self.width}")
        if self.side not in (-1, 0, 1):
            raise ValueError(f"side는 -1/0/1: {self.side}")

    def generate_geometry(self):
        # 우측 기준 (side=+1)
        start = AssemblyPoint(code=PointCode.CROWN, x=0.0, z=0.0)
        end = AssemblyPoint(
            code=PointCode.LANE_EDGE,
            x=self.width,
            z=self.slope * self.width,
        )
        link = AssemblyLink(
            code=LinkCode.PAVEMENT,
            start=start,
            end=end,
            shape_code=ShapeCode.PAVEMENT,
        )
        return (start, end), (link,)