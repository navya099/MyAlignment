# assembly/subassemblies/ditch.py
from __future__ import annotations
from dataclasses import dataclass

from myalignment.assembly.codes import PointCode, LinkCode, ShapeCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassembly import Subassembly


@dataclass(frozen=True, slots=True)
class VShapeDitch(Subassembly):
    """V형 배수로."""
    name: str = "VDitch"
    width: float = 1.5
    depth: float = 0.5
    side: int = 1

    def generate_geometry(self):
        p1 = AssemblyPoint(code=PointCode.DITCH_INNER, x=0.0, z=0.0)
        p2 = AssemblyPoint(code=PointCode.DITCH_BOTTOM, x=self.width / 2, z=-self.depth)
        p3 = AssemblyPoint(code=PointCode.DITCH_OUTER, x=self.width, z=0.0)

        links = (
            AssemblyLink(code=LinkCode.DITCH, start=p1, end=p2),
            AssemblyLink(code=LinkCode.DITCH, start=p2, end=p3),
        )
        return (p1, p2, p3), links