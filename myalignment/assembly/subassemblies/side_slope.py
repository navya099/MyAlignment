# assembly/subassemblies/side_slope.py
from __future__ import annotations
from dataclasses import dataclass

from myalignment.assembly.codes import PointCode, LinkCode, ShapeCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassembly import Subassembly
from myalignment.target.mapping import TargetMapping
from myalignment.target.target_type import TargetType


@dataclass(frozen=True, slots=True)
class SideSlope(Subassembly):
    """
    사면 (C3D BasicSideSlopeCutDitch 호환).
    Target 지원:
        - "TargetDTM" (Surface): 사면이 지표면과 만나는 지점까지 연장.

    성토/절토 사면을 근사적으로 표현.
    """
    name: str = "SideSlope"
    slope_ratio: float = 1.5  # 1:n (수평:수직)
    height: float = 5.0  # 사면 높이 (m)
    side: int = 1
    _target_parameters: tuple[str, ...] = ("TargetDTM",)

    def __post_init__(self):
        if self.slope_ratio <= 0:
            raise ValueError(f"slope_ratio > 0 필요: {self.slope_ratio}")
        if self.height <= 0:
            raise ValueError(f"height > 0 필요: {self.height}")

    def generate_geometry(self, target_mapping=None):
        start = AssemblyPoint(code=PointCode.HINGE_POINT, x=0.0, z=0.0)

        # target_mapping에 지표면 target이 있으면 CATCH_POINT는 파라메트릭
        is_parametric = False
        print(f"[SideSlope] target_mapping={target_mapping}")
        if target_mapping is not None:
            print(f"  refs={target_mapping.references}")
            for ref in target_mapping.references:
                print(f"  ref.target_type={ref.target_type} (type={type(ref.target_type)})")
            print(f"  TargetType.SURFACE={TargetType.SURFACE} (type={type(TargetType.SURFACE)})")

            # TargetType.SURFACE 또는 logical_name="TargetDTM" 확인
            surface_refs = [
                ref for ref in target_mapping.references
                if ref.target_type == TargetType.SURFACE
            ]
            is_parametric = len(surface_refs) > 0

        end = AssemblyPoint(
            code=PointCode.CATCH_POINT,
            x=self.slope_ratio * self.height,
            z=-self.height,
            is_parametric=is_parametric,  # ← 추가
        )
        link = AssemblyLink(code=LinkCode.SLOPE, start=start, end=end)
        return (start, end), (link,)