from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.corridor.cross_section_3d import CrossSection3D
from myalignment.render.scene import Scene
from myalignment.render.section_view_renderer import SectionViewRenderer
from myalignment.section.label_set import SectionLabelSet
from myalignment.section.section_view_data import SectionViewData
from myalignment.section.section_view_style import SectionViewStyle

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.profile.profile import Profile
    from myalignment.section.section_projection import SectionProjection


class SectionViewBuilder:
    """코리더에서 단일 및 다중 횡단 뷰를 생성한다."""

    @classmethod
    def build_data(
        cls, corridor: Corridor, alignment: Alignment, station: float, *,
        profile: Profile | None = None, offset_elevation: float = 0.0,
        baseline_name: str | None = None,
    ) -> SectionViewData:
        region = corridor.region_at(station, alignment_name=alignment.name, baseline_name=baseline_name)
        if region is None or region.assembly is None:
            raise ValueError(f"STA {station}에 해당하는 Region/Assembly 없음")
        baseline = corridor.baseline_for_region(region)
        if baseline is not None and profile is None and baseline.profile_name:
            profile = next((p for p in alignment.profiles if p.name == baseline.profile_name), None)
            if profile is None:
                raise ValueError(f"Missing profile: {baseline.profile_name}")

        design_elevation = profile.elevation_at(station) if profile is not None else None
        elevation = offset_elevation + (design_elevation if design_elevation is not None else 0.0)
        grade = profile.grade_at(station) if profile is not None and region.assembly.has_conditional else None
        section = CrossSection3D.from_region(
            alignment, station, region, elevation, design_elevation=design_elevation, grade=grade,
        )
        return SectionViewData.from_cross_section_3d(section, alignment)

    @classmethod
    def single(
        cls, corridor: Corridor, alignment: Alignment, station: float,
        style: SectionViewStyle | None = None, label_set: SectionLabelSet | None = None, *,
        profile: Profile | None = None,
        offset_elevation: float = 0.0,
        baseline_name: str | None = None,
        projections: Sequence[SectionProjection] = (),
    ) -> Scene:
        data = cls.build_data(
            corridor, alignment, station, profile=profile,
            offset_elevation=offset_elevation, baseline_name=baseline_name,
        )
        return SectionViewRenderer.render(
            Scene(), data, style, label_set if label_set is not None else SectionLabelSet.standard(),
            projections=projections,
        )

    @classmethod
    def single_with_projections(
        cls, corridor: Corridor, alignment: Alignment, station: float,
        projections: Sequence[SectionProjection], style: SectionViewStyle | None = None,
        label_set: SectionLabelSet | None = None, *, profile: Profile | None = None,
        offset_elevation: float = 0.0, baseline_name: str | None = None,
    ) -> Scene:
        """선택한 측점의 코리더 단면과 미리 계산한 투영 객체를 그린다."""
        return cls.single(
            corridor, alignment, station, style, label_set, profile=profile,
            offset_elevation=offset_elevation, baseline_name=baseline_name, projections=projections,
        )

    @classmethod
    def multiple(
        cls, corridor: Corridor, alignment: Alignment, stations: Sequence[float],
        style: SectionViewStyle | None = None, column_gap: float = 20.0, *, label_set: SectionLabelSet | None = None,
        profile: Profile | None = None, offset_elevation: float = 0.0,
        baseline_name: str | None = None,
        projections_by_station: Mapping[float, Sequence[SectionProjection]] | None = None,
    ) -> Scene:
        return cls.grid_layout(
            corridor, alignment, stations, style, max(1, len(stations)), column_gap,
            label_set=label_set, profile=profile, offset_elevation=offset_elevation, baseline_name=baseline_name,
            projections_by_station=projections_by_station,
        )

    @classmethod
    def grid_layout(
        cls, corridor: Corridor, alignment: Alignment, stations: Sequence[float],
        style: SectionViewStyle | None = None, columns: int = 3,
        column_gap: float = 20.0, row_gap: float = 20.0, *, label_set: SectionLabelSet | None = None,
        profile: Profile | None = None, offset_elevation: float = 0.0,
        baseline_name: str | None = None,
        projections_by_station: Mapping[float, Sequence[SectionProjection]] | None = None,
    ) -> Scene:
        if not isinstance(columns, int) or columns <= 0:
            raise ValueError("columns must be a positive integer")
        if any(not math.isfinite(gap) or gap < 0 for gap in (column_gap, row_gap)):
            raise ValueError("layout gaps must be finite and nonnegative")

        style = style or SectionViewStyle()
        scene = Scene()
        station_projections = projections_by_station or {}
        rendered = []
        primitives = []
        for station in stations:
            region = corridor.region_at(station, alignment_name=alignment.name, baseline_name=baseline_name)
            if region is None or region.assembly is None:
                continue
            section = cls.single(
                corridor, alignment, station, style, label_set, profile=profile,
                offset_elevation=offset_elevation, baseline_name=baseline_name,
                projections=station_projections.get(station, ()),
            )
            row, col = divmod(len(rendered), columns)
            x, y = col * (style.width + column_gap), -row * (style.height + row_gap)
            for layer in section.layers:
                scene = scene.add_layer(layer)
            primitives.extend(
                replace(p, points=tuple(Point2d(pt.x + x, pt.y + y) for pt in p.points))
                for p in section.primitives
            )
            rendered.append(station)
        return replace(scene.add_all(primitives), metadata={"section_stations": tuple(rendered)})
