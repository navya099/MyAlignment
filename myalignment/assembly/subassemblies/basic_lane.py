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

    def generate_geometry(self, target_mapping=None):
        # 차로 상단
        top_start = AssemblyPoint(code=PointCode.LANE_EDGE, x=0.0, z=0.0)
        top_end = AssemblyPoint(
            code=PointCode.LANE_EDGE,
            x=self.width,
            z=self.width * self.slope,
        )
        # 포장층 (두께 0.1m 가정)
        thickness = 0.1
        bot_end = AssemblyPoint(
            code=PointCode.PAVEMENT_BOTTOM,
            x=self.width,
            z=top_end.z - thickness,
        )
        bot_start = AssemblyPoint(
            code=PointCode.PAVEMENT_BOTTOM,
            x=0.0,
            z=-thickness,
        )
        # 링크
        lane_link = AssemblyLink(code=LinkCode.LANE, start=top_start, end=top_end)
        pave_top = AssemblyLink(
            code=LinkCode.PAVEMENT_TOP, start=top_start, end=top_end,
            shape_code=ShapeCode.PAVEMENT,
        )
        pave_side_r = AssemblyLink(
            code=LinkCode.PAVEMENT_SIDE, start=top_end, end=bot_end,
            shape_code=ShapeCode.PAVEMENT,
        )
        pave_bot = AssemblyLink(
            code=LinkCode.PAVEMENT_BOTTOM, start=bot_end, end=bot_start,
            shape_code=ShapeCode.PAVEMENT,
        )
        pave_side_l = AssemblyLink(
            code=LinkCode.PAVEMENT_SIDE, start=bot_start, end=top_start,
            shape_code=ShapeCode.PAVEMENT,
        )
        return (top_start, top_end, bot_end, bot_start), (
            lane_link, pave_top, pave_side_r, pave_bot, pave_side_l,
        )
