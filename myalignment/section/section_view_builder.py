from __future__ import annotations

from collections.abc import Sequence
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

        elevation = offset_elevation + (profile.elevation_at(station) if profile is not None else 0.0)
        section = CrossSection3D.from_region(alignment, station, region, elevation)
        return SectionViewData.from_cross_section_3d(section, alignment)

    @classmethod
    def single(
        cls, corridor: Corridor, alignment: Alignment, station: float,
        style: SectionViewStyle | None = None, label_set: SectionLabelSet | None = None, *,
        profile: Profile | None = None,
        offset_elevation: float = 0.0,
        baseline_name: str | None = None,
    ) -> Scene:
        data = cls.build_data(
            corridor, alignment, station, profile=profile,
            offset_elevation=offset_elevation, baseline_name=baseline_name,
        )
        return SectionViewRenderer.render(Scene(), data, style, label_set if label_set is not None else SectionLabelSet.standard())

    @classmethod
    def multiple(
        cls, corridor: Corridor, alignment: Alignment, stations: Sequence[float],
        style: SectionViewStyle | None = None, column_gap: float = 20.0, *, label_set: SectionLabelSet | None = None,
        profile: Profile | None = None, offset_elevation: float = 0.0,
        baseline_name: str | None = None,
    ) -> Scene:
        return cls.grid_layout(
            corridor, alignment, stations, style, max(1, len(stations)), column_gap,
            label_set=label_set, profile=profile, offset_elevation=offset_elevation, baseline_name=baseline_name,
        )

    @classmethod
    def grid_layout(
        cls, corridor: Corridor, alignment: Alignment, stations: Sequence[float],
        style: SectionViewStyle | None = None, columns: int = 3,
        column_gap: float = 20.0, row_gap: float = 20.0, *, label_set: SectionLabelSet | None = None,
        profile: Profile | None = None, offset_elevation: float = 0.0,
        baseline_name: str | None = None,
    ) -> Scene:
        if not isinstance(columns, int) or columns <= 0:
            raise ValueError("columns must be a positive integer")
        if any(not math.isfinite(gap) or gap < 0 for gap in (column_gap, row_gap)):
            raise ValueError("layout gaps must be finite and nonnegative")

        style = style or SectionViewStyle()
        scene = Scene()
        rendered = []
        primitives = []
        for station in stations:
            region = corridor.region_at(station, alignment_name=alignment.name, baseline_name=baseline_name)
            if region is None or region.assembly is None:
                continue
            section = cls.single(
                corridor, alignment, station, style, label_set, profile=profile,
                offset_elevation=offset_elevation, baseline_name=baseline_name,
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
