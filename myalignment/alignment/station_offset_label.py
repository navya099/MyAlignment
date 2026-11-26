from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.alignment.station_offset_label_style import StationOffsetLabelStyle
from myalignment.core.station_offset import StationOffsetPoint

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment


def _point_fields(point: Point2d, prefix: str = "") -> dict[str, str]:
    return {f"{prefix}Easting": f"{point.x:.3f}", f"{prefix}Northing": f"{point.y:.3f}"}


def _offset(value: float) -> str:
    return f"{0.0 if abs(value) < 0.0005 else value:+.3f}"


@dataclass(frozen=True, slots=True)
class StationOffsetLabel:
    """고정 XY 또는 원시 측점과 횡거에 배치하는 동적 레이블."""

    label_style: StationOffsetLabelStyle | None = None
    fixed_point: Point2d | None = None
    relative_station: float = 0.0
    relative_offset: float = 0.0
    reference_alignment_name: str = ""
    reference_point_name: str = ""

    def __post_init__(self):
        StationOffsetPoint(self.relative_station, self.relative_offset)
        if self.fixed_point is not None and not all(map(math.isfinite, (self.fixed_point.x, self.fixed_point.y))):
            raise ValueError("fixed_point coordinates must be finite")
        if self.label_style is not None and self.label_style.is_fixed_point and self.fixed_point is None:
            raise ValueError("fixed_point is required by the label style")

    def resolved_style(self, alignment: Alignment) -> StationOffsetLabelStyle:
        """레이블, 선형 레이블 세트, 표준 스타일 순으로 스타일을 조회한다."""
        return self.label_style or alignment.label_set.station_offset_style or StationOffsetLabelStyle.standard()

    def _location(self, alignment: Alignment):
        if self.fixed_point is not None:
            projection = alignment.project(self.fixed_point)
            return self.fixed_point, projection.point, projection.to_station_offset(), projection.tangent
        if self.resolved_style(alignment).is_fixed_point:
            raise ValueError("fixed_point is required by the label style")
        so = StationOffsetPoint(self.relative_station, self.relative_offset)
        return (
            so.to_point(alignment), alignment.point_at(so.station), so, alignment.tangent_at(so.station),
        )

    def evaluate(
        self, alignment: Alignment, reference_alignment: Alignment | None = None, *,
        reference_point: Point2d | None = None,
    ) -> dict[str, str]:
        """측점 방정식을 적용한 표시 측점과 원시 측점, 횡거 및 참조 필드를 반환한다."""
        return self._fields(alignment, self._location(alignment), reference_alignment, reference_point)

    def _fields(self, alignment, location, reference_alignment, reference_point):
        anchor, foot, so, _ = location
        fields = {
            "Station Value": f"{alignment.raw_to_display_station(so.station):.2f}",
            "Raw Station": f"{so.station:.2f}",
            "Offset Value": _offset(so.offset),
            **_point_fields(anchor),
            **_point_fields(foot, "Alignment "),
        }
        if reference_alignment is not None and (
            not self.reference_alignment_name or reference_alignment.name == self.reference_alignment_name
        ):
            fields["Ref Alignment Name"] = reference_alignment.name
            if reference_alignment.is_valid:
                ref = reference_alignment.project(anchor)
                station = f"{reference_alignment.raw_to_display_station(ref.station):.2f}"
                fields.update({
                    "Ref Station": station, "Ref Raw Station": f"{ref.station:.2f}",
                    "Ref Offset": _offset(ref.offset), "Alignment Name": reference_alignment.name,
                    "Alignment Station": station, "Alignment Offset": f"{ref.offset:.3f}",
                })
        if reference_point is not None:
            ref = alignment.project(reference_point)
            fields.update({
                "Ref Point Name": self.reference_point_name,
                "Ref Point Station": f"{alignment.raw_to_display_station(ref.station):.2f}",
                "Ref Point Offset": _offset(ref.offset),
                **_point_fields(reference_point, "Ref Point "),
            })
        return fields
