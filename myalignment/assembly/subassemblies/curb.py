from __future__ import annotations

from dataclasses import dataclass, field

from myalignment.assembly.codes import LinkCode, PointCode, ShapeCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassembly import Subassembly
from myalignment.assembly.subassemblies.curb_params import CurbParams
from myalignment.assembly.subassemblies.curb_type import CurbType


@dataclass(frozen=True, slots=True)
class CurbSubassembly(Subassembly):
    """차로 끝에서 시작하는 연석. 다음 단면은 후면 하단에 연결한다."""

    name: str = "Curb"
    params: CurbParams = field(default_factory=CurbParams)

    @classmethod
    def create(
        cls, curb_type: CurbType = CurbType.VERTICAL, height: float = 0.15, width: float = 0.15,
        side: int = 1, *, top_slope: float = 0.0, face_slope: float | None = None,
    ) -> CurbSubassembly:
        return cls(side=side, params=CurbParams(curb_type, height, width, top_slope, face_slope))

    def generate_geometry(self, target_mapping=None):
        p = self.params
        toe = AssemblyPoint(PointCode.EDGE, 0.0, 0.0)
        face = AssemblyPoint(PointCode.CURB_FACE, p.face_offset, p.height)
        top = AssemblyPoint(PointCode.CURB_TOP, p.width, p.back_height)
        back = AssemblyPoint(PointCode.CURB_BACK, p.width, 0.0)
        links = (
            AssemblyLink(LinkCode.CURB, toe, face, ShapeCode.CURB),
            AssemblyLink(LinkCode.CURB, face, top, ShapeCode.CURB),
            AssemblyLink(LinkCode.CURB, top, back, ShapeCode.CURB),
            AssemblyLink(LinkCode.DATUM, back, toe, ShapeCode.CURB),
        )
        # Assembly는 가장 먼 X의 첫 점에 후속 부품을 연결한다.
        return (toe, face, back, top), links
