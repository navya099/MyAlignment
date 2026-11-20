from __future__ import annotations

from dataclasses import dataclass

from myalignment.profile.grade_break_component import GradeBreakComponentType, GradeBreakLabelComponent


@dataclass(frozen=True, slots=True)
class GradeBreakLabelStyle:
    """구배 레이블에서 표시할 데이터와 구성요소."""

    name: str = "Grade Break"
    components: tuple[GradeBreakLabelComponent, ...] = ()
    show_station: bool = True
    show_elevation: bool = True
    show_grade_in: bool = True
    show_grade_out: bool = True
    show_grade_change: bool = True
    show_k_value: bool = False
    use_sign: bool = True
    show_arrows: bool = True

    def __post_init__(self):
        if not self.components:
            raise ValueError("최소 1개 컴포넌트 필요")

    @classmethod
    def standard(cls) -> GradeBreakLabelStyle:
        return cls("Standard", (
            GradeBreakLabelComponent(contents="<[Point Type]>", text_height=2, text_color=1, offset_y=7),
            GradeBreakLabelComponent(contents="STA <[Station Value]>", text_height=1.5, text_color=1, offset_y=5.5),
            GradeBreakLabelComponent(contents="EL <[Elevation Value]>", text_height=1.5, text_color=1, offset_y=4),
            GradeBreakLabelComponent(contents="G1: <[Grade In]>", text_height=1.4, text_color=3, offset_y=2.5),
            GradeBreakLabelComponent(contents="G2: <[Grade Out]>", text_height=1.4, text_color=5, offset_y=1),
            GradeBreakLabelComponent(contents="ΔG: <[Grade Change]>", text_height=1.4, text_color=6, offset_y=-.5),
            GradeBreakLabelComponent(GradeBreakComponentType.TICK, text_color=1, offset_y=0),
        ))

    @classmethod
    def minimal(cls) -> GradeBreakLabelStyle:
        return cls("Minimal", (
            GradeBreakLabelComponent(
                contents="<[Grade In]> → <[Grade Out]>", text_height=1.5, text_color=1,
            ),
            GradeBreakLabelComponent(GradeBreakComponentType.TICK, size=.8, text_color=1, offset_y=0),
        ), show_station=False, show_elevation=False, show_grade_change=False)

    @classmethod
    def with_k_value(cls) -> GradeBreakLabelStyle:
        return cls("With K", (
            GradeBreakLabelComponent(contents="STA <[Station Value]>", text_height=1.5, offset_y=6),
            GradeBreakLabelComponent(contents="EL <[Elevation Value]>", text_height=1.5, offset_y=4.5),
            GradeBreakLabelComponent(contents="G1: <[Grade In]>", text_height=1.3, offset_y=3),
            GradeBreakLabelComponent(contents="G2: <[Grade Out]>", text_height=1.3, offset_y=1.5),
            GradeBreakLabelComponent(contents="K: <[K Value]>", text_height=1.3, offset_y=0),
            GradeBreakLabelComponent(GradeBreakComponentType.TICK, offset_y=0),
        ), show_k_value=True)

    @classmethod
    def with_arrows(cls) -> GradeBreakLabelStyle:
        return cls("With Arrows", (
            GradeBreakLabelComponent(contents="G1: <[Grade In]>  G2: <[Grade Out]>", text_height=1.5, offset_y=2.5),
            GradeBreakLabelComponent(GradeBreakComponentType.ARROW, size=2, offset_y=0),
        ))
