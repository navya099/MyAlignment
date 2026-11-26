from __future__ import annotations

from dataclasses import dataclass, field

from myalignment.assembly.codes import LinkCode, PointCode, ShapeCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassembly import Subassembly
from myalignment.assembly.subassemblies.curb_params import SidewalkParams


@dataclass(frozen=True, slots=True)
class SidewalkSubassembly(Subassembly):
    """일정 두께의 보도. 다음 단면은 외측 포장 상단에 연결한다."""

    name: str = "Sidewalk"
    params: SidewalkParams = field(default_factory=SidewalkParams)

    @classmethod
    def create(
        cls, width: float = 2.0, slope: float = -0.02, thickness: float = 0.1, side: int = 1,
    ) -> SidewalkSubassembly:
        return cls(side=side, params=SidewalkParams(width, slope, thickness))

    def generate_geometry(self, target_mapping=None):
        p = self.params
        top_z = p.slope * p.width
        inner = AssemblyPoint(PointCode.SIDEWALK_IN, 0.0, 0.0)
        outer = AssemblyPoint(PointCode.SIDEWALK_OUT, p.width, top_z)
        outer_base = AssemblyPoint(PointCode.EDGE, p.width, top_z - p.thickness)
        inner_base = AssemblyPoint(PointCode.EDGE, 0.0, -p.thickness)
        links = (
            AssemblyLink(LinkCode.PAVEMENT, inner, outer, ShapeCode.SIDEWALK),
            AssemblyLink(LinkCode.PAVEMENT_SIDE, outer, outer_base, ShapeCode.SIDEWALK),
            AssemblyLink(LinkCode.SUBBASE, outer_base, inner_base, ShapeCode.SIDEWALK),
            AssemblyLink(LinkCode.PAVEMENT_SIDE, inner_base, inner, ShapeCode.SIDEWALK),
        )
        return (inner, outer, outer_base, inner_base), links
