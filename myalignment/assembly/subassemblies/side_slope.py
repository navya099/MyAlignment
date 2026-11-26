# assembly/subassemblies/side_slope.py
from __future__ import annotations
from dataclasses import dataclass, field

from myalignment.assembly.codes import PointCode, LinkCode, ShapeCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassembly import Subassembly
from myalignment.target.mapping import TargetMapping
from myalignment.target.target_type import TargetType


@dataclass(frozen=True, slots=True)
class SideSlope(Subassembly):
    """
    지정한 사면비와 높이로 사면을 근사한다.

    표면 타깃을 전달하면 끝점에 `is_parametric` 표시를 남긴다.
    끝점 좌표는 고정 사면 제원으로 계산한다.
    """
    name: str = "SideSlope"
    slope_ratio: float = 1.5  # 1:n (수평:수직)
    height: float = 5.0  # 사면 높이 (m)
    side: int = 1
    _target_parameters: tuple[str, ...] = ("TargetDTM",)
    is_cut: bool = field(default=False, kw_only=True)

    def __post_init__(self):
        if self.slope_ratio <= 0:
            raise ValueError(f"slope_ratio > 0 필요: {self.slope_ratio}")
        if self.height <= 0:
            raise ValueError(f"height > 0 필요: {self.height}")

    def generate_geometry(self, target_mapping: TargetMapping | None = None):
        start = AssemblyPoint(code=PointCode.HINGE_POINT, x=0.0, z=0.0)

        is_parametric = target_mapping is not None and any(
            ref.target_type is TargetType.SURFACE for ref in target_mapping.references
        )

        end = AssemblyPoint(
            code=PointCode.CATCH_POINT,
            x=self.slope_ratio * self.height,
            z=self.height if self.is_cut else -self.height,
            is_parametric=is_parametric,
        )
        link = AssemblyLink(code=LinkCode.SLOPE, start=start, end=end)
        return (start, end), (link,)
