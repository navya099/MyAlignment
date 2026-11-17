# assembly/subassemblies/shoulder.py
from __future__ import annotations
from dataclasses import dataclass

from myalignment.assembly.codes import PointCode, LinkCode, ShapeCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassembly import Subassembly


@dataclass(frozen=True, slots=True)
class Shoulder(Subassembly):
    """갓길 (C3D ShoulderExtendAll 호환)."""
    name: str = "Shoulder"
    width: float = 2.0
    slope: float = -0.04       # 갓길 기울기 (4%)
    side: int = 1

    def __post_init__(self):
        if self.width <= 0:
            raise ValueError(f"width > 0 필요: {self.width}")

    def generate_geometry(self, target_mapping: "TargetMapping | None" = None):
        start = AssemblyPoint(code=PointCode.SHOULDER_INNER, x=0.0, z=0.0)
        end = AssemblyPoint(
            code=PointCode.SHOULDER_OUTER,
            x=self.width,
            z=self.slope * self.width,
        )
        link = AssemblyLink(
            code=LinkCode.SHOULDER,
            start=start,
            end=end,
            shape_code=ShapeCode.SHOULDER,
        )
        return (start, end), (link,)