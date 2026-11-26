from __future__ import annotations

from dataclasses import dataclass, field
import math

from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassembly import Subassembly
from myalignment.assembly.subassemblies.curb import CurbSubassembly
from myalignment.assembly.subassemblies.curb_params import CurbParams


@dataclass(frozen=True, slots=True)
class CurbAndGutterSubassembly(Subassembly):
    """차로 끝에서 연석 전면까지 낮아지는 측구와 연석."""

    name: str = "CurbAndGutter"
    curb_params: CurbParams = field(default_factory=CurbParams)
    gutter_width: float = 0.5
    gutter_depth: float = 0.05

    def __post_init__(self):
        if not math.isfinite(self.gutter_width) or self.gutter_width <= 0:
            raise ValueError("gutter_width must be finite and positive")
        if not math.isfinite(self.gutter_depth) or self.gutter_depth < 0:
            raise ValueError("gutter_depth must be finite and nonnegative")

    @classmethod
    def create(
        cls, gutter_width: float = 0.5, gutter_depth: float = 0.05, curb_height: float = 0.15,
        curb_width: float = 0.15, side: int = 1,
    ) -> CurbAndGutterSubassembly:
        return cls(
            side=side, gutter_width=gutter_width, gutter_depth=gutter_depth,
            curb_params=CurbParams(height=curb_height, width=curb_width),
        )

    def generate_geometry(self, target_mapping=None):
        curb = CurbSubassembly(params=self.curb_params)
        points, links = curb.place_at(self.gutter_width, -self.gutter_depth, target_mapping=target_mapping)
        inner = AssemblyPoint(PointCode.DITCH_INNER, 0.0, 0.0)
        invert = AssemblyPoint(PointCode.DITCH_BOTTOM, self.gutter_width, -self.gutter_depth)
        gutter = AssemblyLink(LinkCode.DITCH, inner, invert)
        return (inner, invert, *points), (gutter, *links)
