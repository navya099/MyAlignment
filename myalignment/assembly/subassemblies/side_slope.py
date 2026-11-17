# assembly/subassemblies/side_slope.py
from __future__ import annotations
from dataclasses import dataclass

from myalignment.assembly.codes import PointCode, LinkCode, ShapeCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassembly import Subassembly


@dataclass(frozen=True, slots=True)
class SideSlope(Subassembly):
    """
    사면 (C3D BasicSideSlopeCutDitch 호환).

    성토/절토 사면을 근사적으로 표현.
    """
    name: str = "SideSlope"
    slope_ratio: float = 1.5  # 1:n (수평:수직)
    height: float = 5.0  # 사면 높이 (m)
    side: int = 1

    def __post_init__(self):
        if self.slope_ratio <= 0:
            raise ValueError(f"slope_ratio > 0 필요: {self.slope_ratio}")
        if self.height <= 0:
            raise ValueError(f"height > 0 필요: {self.height}")

    def generate_geometry(self):
        start = AssemblyPoint(code=PointCode.HINGE_POINT, x=0.0, z=0.0)
        end = AssemblyPoint(
            code=PointCode.CATCH_POINT,
            x=self.slope_ratio * self.height,
            z=-self.height,
        )
        link = AssemblyLink(code=LinkCode.SLOPE, start=start, end=end)
        return (start, end), (link,)