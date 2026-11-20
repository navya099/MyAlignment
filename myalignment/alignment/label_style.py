from __future__ import annotations

from dataclasses import dataclass

from myalignment.alignment.label_component import (
    AlignmentLabelComponent, AlignmentLabelComponentType, ReferenceObjectType,
)
from myalignment.alignment.label_type import AlignmentLabelType


@dataclass(frozen=True, slots=True)
class AlignmentLabelStyle:
    """평면선형 유형별 레이블 스타일."""

    name: str = "Standard"
    label_type: AlignmentLabelType = AlignmentLabelType.GEOMETRY_POINT
    description: str = ""
    components: tuple[AlignmentLabelComponent, ...] = ()

    def __post_init__(self):
        if not self.components:
            raise ValueError("최소 1개 컴포넌트 필요")

    def text_components(self) -> tuple[AlignmentLabelComponent, ...]:
        return tuple(c for c in self.components if c.component_type is AlignmentLabelComponentType.TEXT)

    @classmethod
    def major_station_style(cls) -> AlignmentLabelStyle:
        return cls("Major Station", AlignmentLabelType.MAJOR_STATION, components=(
            AlignmentLabelComponent(AlignmentLabelComponentType.TICK, size=1.5, offset_y=0.0),
            AlignmentLabelComponent(contents="STA <[Station Value]>", offset_y=2.5),
            AlignmentLabelComponent(contents="N: <[Northing]>", text_height=1.5, offset_y=1.0),
        ))

    @classmethod
    def minor_station_style(cls) -> AlignmentLabelStyle:
        return cls("Minor Station", AlignmentLabelType.MINOR_STATION, components=(
            AlignmentLabelComponent(AlignmentLabelComponentType.TICK, size=0.5, text_color=8, offset_y=0.0),
        ))

    @classmethod
    def minor_station_with_text_style(cls) -> AlignmentLabelStyle:
        return cls("Minor Station + Text", AlignmentLabelType.MINOR_STATION, components=(
            AlignmentLabelComponent(AlignmentLabelComponentType.TICK, size=0.3, text_color=8, offset_y=0.0),
            AlignmentLabelComponent(contents="<[Station Value]>", text_height=1.0, text_color=8, offset_y=1.5),
        ))

    @classmethod
    def geometry_point_style(cls) -> AlignmentLabelStyle:
        return cls("Geometry Point", AlignmentLabelType.GEOMETRY_POINT, components=(
            AlignmentLabelComponent(contents="<[Geometry Point Text]>", offset_y=2.5),
            AlignmentLabelComponent(contents="STA <[Station Value]>", text_height=1.5, offset_y=1.0),
        ))

    @classmethod
    def geometry_point_with_surface_style(cls) -> AlignmentLabelStyle:
        return cls("Geometry Point + Surface", AlignmentLabelType.GEOMETRY_POINT, components=(
            AlignmentLabelComponent(contents="<[Geometry Point Text]>", offset_y=3.5),
            AlignmentLabelComponent(contents="STA <[Station Value]>", text_height=1.5, offset_y=2.0),
            AlignmentLabelComponent(
                contents="EL <[Surface Elevation]>", text_height=1.5, offset_y=0.5,
                reference_type=ReferenceObjectType.SURFACE, reference_field="Surface Elevation",
            ),
        ))

    @classmethod
    def line_style(cls) -> AlignmentLabelStyle:
        return cls("Line", AlignmentLabelType.LINE, components=(
            AlignmentLabelComponent(contents="B: <[Bearing]>", text_height=1.5, offset_y=2.0),
            AlignmentLabelComponent(contents="D: <[Distance]>", text_height=1.5, offset_y=0.5),
        ))

    @classmethod
    def curve_style(cls) -> AlignmentLabelStyle:
        return cls("Curve", AlignmentLabelType.CURVE, components=(
            AlignmentLabelComponent(contents="R: <[Radius]>", text_height=1.5),
            AlignmentLabelComponent(contents="Δ: <[Delta]>", text_height=1.5, offset_y=0.5),
        ))

    @classmethod
    def spiral_style(cls) -> AlignmentLabelStyle:
        return cls("Spiral", AlignmentLabelType.SPIRAL, components=(
            AlignmentLabelComponent(contents="L: <[Distance]>", text_height=1.5),
            AlignmentLabelComponent(contents="R: <[Radius]>", text_height=1.5, offset_y=0.5),
        ))
