from __future__ import annotations

from dataclasses import dataclass, field

from myalignment.profile.label_component import ProfileLabelComponent


@dataclass(frozen=True, slots=True)
class DepthLabelStyle:
    """두 측점 사이의 표고차, 평균 구배, 수평거리를 표시하는 스타일.

    표시 옵션은 해당 필드가 포함된 텍스트 행을 제어한다.
    show_arrow는 두 점의 연결선과 끝점 마커를 제어한다.
    """

    name: str = "Depth"
    components: tuple[ProfileLabelComponent, ...] = field(default_factory=tuple)
    show_stations: bool = True
    show_elevation_diff: bool = True
    show_grade: bool = True
    show_distance: bool = True
    show_arrow: bool = True

    def __post_init__(self):
        object.__setattr__(self, "components", tuple(self.components))
        if not self.components:
            raise ValueError("최소 1개 컴포넌트 필요")

    @classmethod
    def standard(cls) -> DepthLabelStyle:
        """두 측점과 표고차, 구배, 수평거리를 표시한다."""
        return cls(name="Standard", components=(
            ProfileLabelComponent(contents="STA <[Start Station]> → <[End Station]>", text_height=1.8, offset_y=4.5),
            ProfileLabelComponent(contents="ΔE: <[Elevation Difference]> m", text_height=1.5, offset_y=3.0),
            ProfileLabelComponent(contents="Grade: <[Grade]>", text_height=1.5, offset_y=1.5),
            ProfileLabelComponent(contents="Dist: <[Distance]> m", text_height=1.5, offset_y=0.0),
        ))

    @classmethod
    def minimal(cls) -> DepthLabelStyle:
        """표고차만 표시한다."""
        return cls(
            name="Minimal",
            components=(ProfileLabelComponent(
                contents="ΔE: <[Elevation Difference]> m", text_height=1.5, offset_y=1.5,
            ),),
            show_stations=False, show_grade=False, show_distance=False,
        )

    @classmethod
    def slope_only(cls) -> DepthLabelStyle:
        """두 점 사이의 평균 구배만 표시한다."""
        return cls(
            name="Slope Only",
            components=(ProfileLabelComponent(contents="Grade: <[Grade]>", text_height=1.8, offset_y=1.5),),
            show_stations=False, show_elevation_diff=False, show_distance=False,
        )
