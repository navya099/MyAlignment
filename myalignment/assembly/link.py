# assembly/link.py
from __future__ import annotations
from dataclasses import dataclass
import math

from myalignment.assembly.codes import LinkCode, ShapeCode
from myalignment.assembly.point import AssemblyPoint


@dataclass(frozen=True, slots=True)
class AssemblyLink:
    """
    두 접점 사이의 연결 (불변).

    포장면/사면/배수로 등의 선분.
    """
    code: LinkCode = LinkCode.TOP
    start: AssemblyPoint = None
    end: AssemblyPoint = None
    shape_code: ShapeCode | None = None  # 형상(면적) 코드 (재료 물량)

    def __post_init__(self):
        if self.start is None or self.end is None:
            raise ValueError("start/end가 None입니다.")

    @property
    def length(self) -> float:
        return math.hypot(
            self.end.x - self.start.x,
            self.end.z - self.start.z,
        )

    @property
    def slope(self) -> float:
        """기울기 (z/x). x=0이면 inf."""
        dx = self.end.x - self.start.x
        if abs(dx) < 1e-9:
            return math.inf if self.end.z > self.start.z else -math.inf
        return (self.end.z - self.start.z) / dx

    def __repr__(self) -> str:
        return f"Link({self.code.name}, {self.start.code.name}→{self.end.code.name}, L={self.length:.3f})"