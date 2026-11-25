from __future__ import annotations

from dataclasses import dataclass, field

from myalignment.alignment.label_style import AlignmentLabelStyle, _text_rows
from myalignment.alignment.label_type import AlignmentLabelType


@dataclass(frozen=True, slots=True)
class CurveLabelStyle(AlignmentLabelStyle):
    """원곡선 제원 레이블의 표시 항목과 각도 형식."""

    name: str = "Curve Standard"
    label_type: AlignmentLabelType = field(default=AlignmentLabelType.CURVE, init=False)
    show_radius: bool = True
    show_delta: bool = True
    show_length: bool = True
    show_tangent: bool = True
    show_external: bool = False
    show_mid_ordinate: bool = False
    show_chord: bool = False
    show_bc_station: bool = True
    show_ec_station: bool = True
    angle_format: str = "dms"

    def __post_init__(self):
        AlignmentLabelStyle.__post_init__(self)
        object.__setattr__(self, "components", tuple(self.components))
        if self.angle_format not in ("dms", "decimal"):
            raise ValueError("angle_format must be dms or decimal")

    @classmethod
    def standard(cls) -> CurveLabelStyle:
        """반경, 교각, 곡선장과 접선장을 표시한다."""
        return cls(components=_text_rows(
            ("CURVE", "R = <[Radius]>", "Δ = <[Delta]>", "L = <[Length]>", "T = <[Tangent]>"),
            "C-ALIGN-CURVE-LABEL", 5,
        ))

    @classmethod
    def detailed(cls) -> CurveLabelStyle:
        """외선장, 중앙종거, 현장과 양 끝 측점을 함께 표시한다."""
        return cls(name="Curve Detailed", components=_text_rows((
            "CURVE", "R = <[Radius]>", "Δ = <[Delta]>", "L = <[Length]>", "T = <[Tangent]>",
            "E = <[External]>", "M = <[Mid-ordinate]>", "C = <[Chord]>",
            "BC = <[BC Station]>", "EC = <[EC Station]>",
        ), "C-ALIGN-CURVE-LABEL", 5), show_external=True, show_mid_ordinate=True, show_chord=True)
