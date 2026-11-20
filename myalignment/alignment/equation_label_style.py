from __future__ import annotations

from dataclasses import dataclass

from myalignment.alignment.label_component import AlignmentLabelComponent, AlignmentLabelComponentType


_LAYER = "C-ALIGN-EQUATION"


@dataclass(frozen=True, slots=True)
class StationEquationLabelStyle:
    """측점 방정식 위치에 표시할 텍스트, 틱과 방향별 접미사."""

    name: str = "Station Equation"
    components: tuple[AlignmentLabelComponent, ...] = ()
    show_raw_station: bool = True
    show_delta: bool = True
    increasing_suffix: str = "(Eq)"
    decreasing_suffix: str = "(Eq-)"

    def __post_init__(self):
        if not self.components:
            raise ValueError("최소 1개 컴포넌트 필요")

    @classmethod
    def standard(cls) -> StationEquationLabelStyle:
        return cls("Standard", (
            AlignmentLabelComponent(
                contents="STA <[Station Ahead]> <[Equation Suffix]>",
                text_color=1, offset_y=3.5, layer=_LAYER,
            ),
            AlignmentLabelComponent(
                contents="Raw: <[Raw Station]>", text_height=1.5, text_color=1, offset_y=2.0, layer=_LAYER,
            ),
            AlignmentLabelComponent(
                contents="Δ: <[Delta]>", text_height=1.5, text_color=1, offset_y=0.5, layer=_LAYER,
            ),
            AlignmentLabelComponent(
                AlignmentLabelComponentType.TICK, size=0.8, text_color=1, offset_y=0.0, layer=_LAYER,
            ),
        ))

    @classmethod
    def minimal(cls) -> StationEquationLabelStyle:
        return cls("Minimal", (
            AlignmentLabelComponent(
                contents="STA <[Station Ahead]> <[Equation Suffix]>",
                text_color=1, offset_y=2.5, layer=_LAYER,
            ),
            AlignmentLabelComponent(
                AlignmentLabelComponentType.TICK, size=0.6, text_color=1, offset_y=0.0, layer=_LAYER,
            ),
        ), show_raw_station=False, show_delta=False)

    @classmethod
    def with_arrow(cls) -> StationEquationLabelStyle:
        return cls("With Arrow", (
            AlignmentLabelComponent(
                contents="STA <[Station Ahead]> <[Equation Suffix]>",
                text_color=1, offset_y=3.5, layer=_LAYER,
            ),
            AlignmentLabelComponent(
                contents="<[Raw Station]> → <[Station Ahead]>",
                text_height=1.5, text_color=1, offset_y=2.0, layer=_LAYER,
            ),
        ))
