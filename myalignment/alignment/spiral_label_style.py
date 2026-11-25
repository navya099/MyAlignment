from __future__ import annotations

from dataclasses import dataclass, field

from myalignment.alignment.label_style import AlignmentLabelStyle, _text_rows
from myalignment.alignment.label_type import AlignmentLabelType


@dataclass(frozen=True, slots=True)
class SpiralLabelStyle(AlignmentLabelStyle):
    """완화곡선 제원과 전이 측점 레이블의 표시 항목."""

    name: str = "Spiral Standard"
    label_type: AlignmentLabelType = field(default=AlignmentLabelType.SPIRAL, init=False)
    show_a_value: bool = True
    show_length: bool = True
    show_theta: bool = True
    show_radius: bool = True
    show_ts_station: bool = True
    show_sc_station: bool = False
    show_cs_station: bool = False
    show_st_station: bool = True
    angle_format: str = "dms"

    def __post_init__(self):
        AlignmentLabelStyle.__post_init__(self)
        object.__setattr__(self, "components", tuple(self.components))
        if self.angle_format not in ("dms", "decimal"):
            raise ValueError("angle_format must be dms or decimal")

    @classmethod
    def standard(cls) -> SpiralLabelStyle:
        """A 값, 길이, 접선 변화각과 반경을 표시한다."""
        return cls(components=_text_rows(
            ("SPIRAL", "A = <[A Value]>", "L = <[Length]>", "θ = <[Theta]>", "R = <[Radius]>"),
            "C-ALIGN-SPIRAL-LABEL", 6,
        ))

    @classmethod
    def stations(cls) -> SpiralLabelStyle:
        """진입 또는 진출 완화곡선의 TS·SC·CS·ST 측점을 표시한다."""
        return cls(name="Spiral Stations", components=_text_rows(
            ("TS: <[TS Station]>", "SC: <[SC Station]>", "CS: <[CS Station]>", "ST: <[ST Station]>"),
            "C-ALIGN-SPIRAL-LABEL", 6,
        ), show_sc_station=True, show_cs_station=True)
