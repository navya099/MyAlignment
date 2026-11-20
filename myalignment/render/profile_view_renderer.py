from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
import math
from typing import TYPE_CHECKING

from myalignment.profile.band_style import GeometryBandStyle, VerticalGeometryBandStyle
from myalignment.profile.cant_band_style import CantBandStyle
from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.rail.rail_alignment import RailAlignment
from myalignment.render.cant_band_renderer import CantBandRenderer
from myalignment.render.geometry_band_renderer import HorizontalGeometryBandRenderer
from myalignment.render.primitives import Primitive, Style
from myalignment.render.profile_label_renderer import ProfileLabelRenderer
from myalignment.render.profile_renderer import ProfileRenderer
from myalignment.render.scene import Layer, Scene
from myalignment.render.stagger_config import StaggerConfig
from myalignment.render.staggered_renderer import StaggeredRenderer
from myalignment.render.station_label_renderer import StationLabelRenderer
from myalignment.render.vertical_geometry_band_renderer import VerticalGeometryBandRenderer
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.profile.profile import Profile
    from myalignment.profile.station_label import StationElevationLabel


def _ticks(start: float, end: float, interval: float) -> list[float]:
    # 정수 배수에서 직접 계산하여 소수 간격의 누적 오차를 피한다.
    first = math.ceil(math.nextafter(start / interval, -math.inf))
    last = math.floor(math.nextafter(end / interval, math.inf))
    return [min(end, max(start, index * interval)) for index in range(first, last + 1)]


def _grid_ticks(start: float, end: float, major: float, minor: float):
    for value in _ticks(start, end, minor):
        if not math.isclose(value, round(value / major) * major, rel_tol=0.0, abs_tol=minor * 1e-9):
            yield value, 9
    for value in _ticks(start, end, major):
        yield value, 8


class ProfileViewRenderer:
    """종단선, 그리드, 데이터 밴드를 하나의 Scene에 렌더링한다."""

    GRID_LAYER = "C-PROF-GRID"
    FG_LAYER = ProfileRenderer.FG_LAYER
    EG_LAYER = ProfileRenderer.EG_LAYER
    BAND_LAYER = "C-PROF-BAND"

    @classmethod
    def render(
        cls,
        profiles: Sequence[Profile],
        alignment_name: str,
        style: ProfileViewStyle,
        bands: Sequence[ProfileViewBand] | None = None,
        scene: Scene | None = None,
        *,
        alignment: Alignment | None = None,
        geometry_band_style: GeometryBandStyle | None = None,
        vertical_geometry_band_style: VerticalGeometryBandStyle | None = None,
        cant_band_style: CantBandStyle | None = None,
        labels: Sequence[StationElevationLabel] | None = None,
        render_labels: bool = True,
        stagger_config: StaggerConfig | None = None,
    ) -> Scene:
        """수평 기하 및 캔트 밴드의 원본 선형은 alignment로 전달한다."""
        scene = Scene() if scene is None else scene
        valid_profiles = tuple(profile for profile in profiles if profile.is_valid)
        if not valid_profiles:
            return scene

        start = min(profile.start_station for profile in valid_profiles)
        end = max(profile.end_station for profile in valid_profiles)
        low = min(profile.min_elevation for profile in valid_profiles) - 5.0
        high = max(profile.max_elevation for profile in valid_profiles) + 5.0
        viewport = Viewport(ViewportType.PROFILE, style.vertical_exaggeration)

        grid = []
        for station, color in _grid_ticks(
            start, end, style.grid_major_interval_station, style.grid_minor_interval_station
        ):
            grid.append(Primitive.line(
                viewport.project(station, low), viewport.project(station, high),
                Style(color=color, layer=cls.GRID_LAYER),
            ))
        for elevation, color in _grid_ticks(
            low, high, style.grid_major_interval_elevation, style.grid_minor_interval_elevation
        ):
            grid.append(Primitive.line(
                viewport.project(start, elevation), viewport.project(end, elevation),
                Style(color=color, layer=cls.GRID_LAYER),
            ))
        scene = scene.add_layer(Layer(cls.GRID_LAYER, color=8)).add_all(grid)

        for profile in valid_profiles:
            scene = ProfileRenderer.render(profile, scene, vertical_exaggeration=style.vertical_exaggeration)
            if render_labels:
                scene = ProfileLabelRenderer.render(scene, profile, style.vertical_exaggeration)

        if bands:
            geometry_style = geometry_band_style or GeometryBandStyle()
            vertical_style = vertical_geometry_band_style or VerticalGeometryBandStyle()
            cant_style = cant_band_style or CantBandStyle()
            stations = _ticks(start, end, style.grid_major_interval_station)
            edges = {"bottom": low, "top": high}
            for band in bands:
                location = band.location or style.band_location
                direction = 1 if location == "top" else -1
                base = edges[location] + direction * band.gap
                if band.band_type is BandType.HORIZONTAL_GEOMETRY and alignment is not None:
                    outer_edge = base + direction * geometry_style.band_height
                    scene = HorizontalGeometryBandRenderer.render(
                        scene, alignment, max(base, outer_edge), geometry_style,
                        style.vertical_exaggeration, station_range=(start, end),
                    )
                    edges[location] = outer_edge + direction * (2 * geometry_style.tick_length + 1.0)
                    continue
                if band.band_type is BandType.VERTICAL_GEOMETRY:
                    profile = valid_profiles[0]
                    if band.profile_names:
                        profile = next(
                            (p for p in valid_profiles if p.name == band.profile_names[0]), profile,
                        )
                    outer_edge = base + direction * vertical_style.band_height
                    scene = VerticalGeometryBandRenderer.render(
                        scene, profile, max(base, outer_edge), vertical_style, style.vertical_exaggeration,
                    )
                    edges[location] = outer_edge + direction * (2 * vertical_style.tick_length + 1.0)
                    continue
                if band.band_type is BandType.CANT_DATA:
                    if isinstance(alignment, RailAlignment):
                        outer_edge = base + direction * cant_style.band_height
                        rendered = CantBandRenderer.render(
                            scene, alignment, max(base, outer_edge), cant_style,
                            style.vertical_exaggeration, start_station=start, end_station=end,
                        )
                        if rendered is not scene:
                            edges[location] = outer_edge + direction * (cant_style.tick_length + 1.0)
                            scene = rendered
                    continue
                scene = scene.add_layer(Layer(cls.BAND_LAYER))
                selected = tuple(
                    p for p in valid_profiles if not band.profile_names or p.name in band.profile_names
                )
                edges[location] = base + direction * 3.0
                scene = scene.add_all(cls._band_primitives(
                    band, selected, stations, start, end, base, direction, viewport
                ))

        for label in labels or ():
            scene = StationLabelRenderer.render(scene, label, valid_profiles, style.vertical_exaggeration)

        scene = replace(scene, metadata={
            **scene.metadata,
            "alignment_name": alignment_name,
            "vertical_exaggeration": style.vertical_exaggeration,
            "start_station": start,
            "end_station": end,
        })
        return StaggeredRenderer.apply_stagger(scene, stagger_config) if stagger_config is not None else scene

    @classmethod
    def _band_primitives(
        cls, band, profiles, stations, start, end, base, direction, viewport,
    ):
        style = Style(color=7, layer=cls.BAND_LAYER)
        yield Primitive.line(viewport.project(start, base), viewport.project(end, base), style)

        labels = []
        if band.band_type is BandType.PROFILE_DATA:
            for station in stations:
                values = [
                    f"{p.name}: {p.elevation_at(station):.2f}"
                    for p in profiles if p.start_station <= station <= p.end_station
                ]
                if values:
                    labels.append((station, f"{station:g} | " + " | ".join(values)))
        exaggeration = viewport.vertical_exaggeration
        for station, text in labels:
            # TEXT의 삽입점이 하단이므로 아래 밴드는 글자 높이만큼 추가로 내린다.
            offset = 0.5 if direction > 0 else 2.0
            point = viewport.project(station, base + direction * offset)
            yield Primitive.text(point, text, 1.5 * exaggeration, style=style)
