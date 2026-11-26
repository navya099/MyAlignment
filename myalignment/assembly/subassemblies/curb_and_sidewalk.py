from __future__ import annotations

from dataclasses import dataclass, field

from myalignment.assembly.subassembly import Subassembly
from myalignment.assembly.subassemblies.curb import CurbSubassembly
from myalignment.assembly.subassemblies.curb_params import CurbParams, SidewalkParams
from myalignment.assembly.subassemblies.sidewalk import SidewalkSubassembly


@dataclass(frozen=True, slots=True)
class CurbAndSidewalkSubassembly(Subassembly):
    """연석 후면 하단에 보도를 연결한 단면."""

    name: str = "CurbAndSidewalk"
    curb_params: CurbParams = field(default_factory=CurbParams)
    sidewalk_params: SidewalkParams = field(default_factory=SidewalkParams)

    @classmethod
    def create(
        cls, curb_height: float = 0.15, curb_width: float = 0.15, sidewalk_width: float = 2.0,
        sidewalk_slope: float = -0.02, sidewalk_thickness: float = 0.1, side: int = 1,
        *, include_curb: bool = True,
    ) -> CurbAndSidewalkSubassembly:
        return cls(
            side=side, curb_params=CurbParams(height=curb_height, width=curb_width),
            sidewalk_params=SidewalkParams(sidewalk_width, sidewalk_slope, sidewalk_thickness, include_curb),
        )

    def generate_geometry(self, target_mapping=None):
        sidewalk = SidewalkSubassembly(params=self.sidewalk_params)
        if not self.sidewalk_params.include_curb:
            return sidewalk.generate_geometry(target_mapping)
        points, links = CurbSubassembly(params=self.curb_params).generate_geometry(target_mapping)
        walk_points, walk_links = sidewalk.place_at(self.curb_params.width, 0.0, target_mapping=target_mapping)
        return points + walk_points, links + walk_links
