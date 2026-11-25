from __future__ import annotations

from dataclasses import dataclass, field
import math

from myalignment.section.projection_object_type import SectionProjectionObjectType
from myalignment.section.projection_style import SectionProjectionStyle
from myalignment.section.section_view_data import SectionPoint as SectionProjectedPoint


@dataclass(frozen=True, slots=True)
class SectionProjection:
    """한 횡단면에서 원본 객체가 차지하는 횡거와 표고 범위.

    projected_points는 교차점과 선분 끝점을 담는다.
    projected_links는 횡단면에 놓인 선분만 인덱스로 연결한다.
    """

    original_object: object = None
    name: str = ""
    object_type: SectionProjectionObjectType = SectionProjectionObjectType.STRUCTURE
    left_offset: float = 0.0
    right_offset: float = 0.0
    bottom_elevation: float = 0.0
    top_elevation: float = 0.0
    projected_points: tuple[SectionProjectedPoint, ...] = ()
    style: SectionProjectionStyle = field(default_factory=SectionProjectionStyle.structure_style)
    diameter: float = 0.0
    projected_links: tuple[tuple[int, int], ...] = ()
    pier_bottom_elevation: float | None = None

    def __post_init__(self):
        if self.object_type is not self.style.object_type:
            raise ValueError("section projection and style object types must match")
        if not all(map(math.isfinite, (self.left_offset, self.right_offset,
                                       self.bottom_elevation, self.top_elevation, self.diameter))):
            raise ValueError("section projection bounds and diameter must be finite")
        if self.left_offset > self.right_offset or self.bottom_elevation > self.top_elevation:
            raise ValueError("section projection bounds must be ordered")
        if self.diameter < 0 or (self.object_type is SectionProjectionObjectType.PIPE and self.diameter == 0):
            raise ValueError("pipe diameter must be positive")
        if any(a == b or not (0 <= a < len(self.projected_points) and 0 <= b < len(self.projected_points))
               for a, b in self.projected_links):
            raise ValueError("invalid section projection link indices")
        base = self.pier_bottom_elevation
        if base is not None and (not math.isfinite(base) or base >= self.bottom_elevation):
            raise ValueError("pier bottom elevation must be finite and below the deck")

    @property
    def offset_center(self) -> float:
        return (self.left_offset + self.right_offset) / 2

    @property
    def offset_width(self) -> float:
        return self.right_offset - self.left_offset

    @property
    def elevation_height(self) -> float:
        return self.top_elevation - self.bottom_elevation

    def contains_offset(self, offset: float) -> bool:
        """횡거가 객체의 표시 범위에 포함되는지 확인한다."""
        return self.left_offset <= offset <= self.right_offset
