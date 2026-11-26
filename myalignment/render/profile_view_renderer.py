from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
import math
from typing import TYPE_CHECKING

from myalignment.profile.band_style import GeometryBandStyle, VerticalGeometryBandStyle
from myalignment.profile.cant_band_style import CantBandStyle
from myalignment.profile.earthwork_band_generator import EarthworkBandGenerator
from myalignment.profile.earthwork_band_style import EarthworkBandStyle
from myalignment.profile.grade_break_style import GradeBreakLabelStyle
from myalignment.profile.hatch_generator import ProfileHatchGenerator
from myalignment.profile.hatch_style import ProfileHatchStyle
from myalignment.profile.profiletype import ProfileType
from myalignment.profile.label_type import ProfileLabelType
from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.rail.rail_alignment import RailAlignment
from myalignment.render.cant_band_renderer import CantBandRenderer
from myalignment.render.depth_label_renderer import DepthLabelRenderer
from myalignment.render.earthwork_band_renderer import EarthworkBandRenderer
from myalignment.render.grade_break_label_renderer import GradeBreakLabelRenderer
from myalignment.render.geometry_band_renderer import HorizontalGeometryBandRenderer
from myalignment.render.primitives import Primitive, Style
from myalignment.render.profile_hatch_renderer import ProfileHatchRenderer
from myalignment.render.profile_label_renderer import ProfileLabelRenderer
from myalignment.render.profile_renderer import ProfileRenderer, _entity_ranges
from myalignment.render.projection_renderer import ProjectionRenderer
from myalignment.render.scene import Layer, Scene
from myalignment.render.stagger_config import StaggerConfig
from myalignment.render.stagger_presets import StaggerConfigPresets
from myalignment.render.staggered_renderer import StaggeredRenderer
from myalignment.render.station_label_renderer import StationLabelRenderer
from myalignment.render.vertical_geometry_band_renderer import VerticalGeometryBandRenderer
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.profile.depth_label import DepthLabel
    from myalignment.profile.hatch_region import HatchCollection
    from myalignment.profile.profile import Profile
    from myalignment.profile.station_label import StationElevationLabel
    from myalignment.profile.view_projection import ProfileViewProjection


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


def _elevations(profile: Profile, station_range: tuple[float, float]):
    for entity, start, end in _entity_ranges(profile, station_range):
        yield entity.elevation_at(start)
        yield entity.elevation_at(end)
        extremum = getattr(entity, "extremum_station", None)
        if callable(extremum):
            station = extremum()
            if station is not None and start < station < end:
                yield entity.elevation_at(station)


def _profile_by_name_or_type(profiles, name, code, profile_type):
    if name is not None:
        return next((profile for profile in profiles if profile.name == name), None)
    named = next((profile for profile in profiles if profile.name == code), None)
    return named if named is not None else next((p for p in profiles if p.profile_type is profile_type), None)


def _profile_pair(profiles, fg_name, eg_name):
    design = _profile_by_name_or_type(profiles, fg_name, "FG", ProfileType.FG)
    candidates = tuple(profile for profile in profiles if profile is not design)
    existing = _profile_by_name_or_type(candidates, eg_name, "EG", ProfileType.EG)
    return design, existing


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
        earthwork_band_style: EarthworkBandStyle | None = None,
        road_width: float = 10.0,
        labels: Sequence[StationElevationLabel] | None = None,
        depth_labels: Sequence[DepthLabel] | None = None,
        render_labels: bool = True,
        grade_break_style: GradeBreakLabelStyle | None = None,
        render_grade_breaks: bool = True,
        stagger_config: StaggerConfig | None = None,
        station_range: tuple[float, float] | None = None,
        projections: Sequence[ProfileViewProjection] | None = None,
        hatch_style: ProfileHatchStyle | None = None,
        fg_profile_name: str | None = None,
        eg_profile_name: str | None = None,
        hatches: HatchCollection | None = None,
    ) -> Scene:
        """종단 뷰를 렌더링하고 지정한 레이블을 배치한다.

        수평 기하 및 캔트 밴드의 원본 선형은 alignment로 전달한다.
        depth_labels에는 두 원시 측점 사이를 측정하는 레이블을 전달한다.
        station_range를 지정하면 해당 원시 측점 구간만 그린다.
        projections에는 원시 측점과 표고로 변환한 객체를 전달한다.
        EARTHWORK 밴드의 profile_names는 계획·현황 종단의 이름을 순서대로 지정한다.
        """
        scene = Scene() if scene is None else scene
        valid_profiles = tuple(profile for profile in profiles if profile.is_valid)
        if not valid_profiles:
            return scene

        window_elevations = []
        if station_range is None:
            start = min(profile.start_station for profile in valid_profiles)
            end = max(profile.end_station for profile in valid_profiles)
        else:
            start, end = station_range
            if not math.isfinite(start) or not math.isfinite(end) or start >= end:
                raise ValueError("station_range must be finite and increasing")
            window_elevations = [z for profile in valid_profiles for z in _elevations(profile, station_range)]
        if not window_elevations:
            window_elevations = [value for profile in valid_profiles
                                 for value in (profile.min_elevation, profile.max_elevation)]
        window_elevations.extend(
            point.elevation for projection in projections or ()
            if projection.style.show_range or projection.style.show_marker or projection.style.show_label
            for path in projection.clipped_paths((start, end)) for point in path
        )
        if hatches is not None:
            for region in hatches:
                clipped = region.clipped((start, end))
                if clipped is not None:
                    window_elevations.extend(point.y for point in clipped.polygon)
        low, high = min(window_elevations) - 5, max(window_elevations) + 5
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
        if station_range is not None:
            frame = Style(color=8, layer=cls.GRID_LAYER)
            grid.append(Primitive.polyline(
                (viewport.project(x, y) for x, y in ((start, low), (end, low), (end, high), (start, high))),
                closed=True, style=frame,
            ))
        scene = scene.add_layer(Layer(cls.GRID_LAYER, color=8)).add_all(grid)

        if hatches is None and hatch_style is not None:
            design, existing = _profile_pair(valid_profiles, fg_profile_name, eg_profile_name)
            if design is not None and existing is not None:
                hatches = ProfileHatchGenerator.generate(design, existing, hatch_style, station_range=(start, end))
        if hatches is not None:
            scene = ProfileHatchRenderer.render(scene, hatches, style, style=hatch_style, station_range=(start, end))

        custom_grade_breaks = render_grade_breaks and grade_break_style is not None
        for profile in valid_profiles:
            scene = ProfileRenderer.render(
                profile, scene, vertical_exaggeration=style.vertical_exaggeration, station_range=station_range,
            )
            if render_labels:
                generic = profile
                if custom_grade_breaks:
                    generic = profile.with_label_set(
                        profile.label_set.without_style(ProfileLabelType.GRADIENT_BREAK)
                        .without_style(ProfileLabelType.PVI)
                    )
                scene = ProfileLabelRenderer.render(
                    scene, generic, style.vertical_exaggeration, station_range=station_range,
                )
            if custom_grade_breaks:
                scene = GradeBreakLabelRenderer.render(
                    scene, profile, grade_break_style, style.vertical_exaggeration, station_range=station_range,
                )

        fixed_text_layers = set()
        if bands:
            geometry_style = geometry_band_style or GeometryBandStyle()
            vertical_style = vertical_geometry_band_style or VerticalGeometryBandStyle()
            cant_style = cant_band_style or CantBandStyle()
            earthwork_style = earthwork_band_style or EarthworkBandStyle.standard()
            stations = _ticks(start, end, style.grid_major_interval_station)
            edges = {"bottom": low, "top": high}
            for band in bands:
                location = band.location or style.band_location
                direction = 1 if location == "top" else -1
                base = edges[location] + direction * band.gap
                if band.band_type is BandType.EARTHWORK:
                    if not earthwork_style.total_height:
                        continue
                    names = band.profile_names
                    fg_name = names[0] if names else fg_profile_name
                    eg_name = names[1] if len(names) > 1 else eg_profile_name
                    design, existing = _profile_pair(valid_profiles, fg_name, eg_name)
                    if design is None or existing is None:
                        continue
                    data = EarthworkBandGenerator.generate(
                        design, existing, earthwork_style, road_width, station_range=(start, end),
                    )
                    outer_edge = base + direction * earthwork_style.total_height
                    rendered = EarthworkBandRenderer.render(
                        scene, data, style, max(base, outer_edge), earthwork_style, alignment=alignment,
                    )
                    if rendered is not scene:
                        edges[location] = outer_edge + direction * earthwork_style.band_gap
                        fixed_text_layers.add(earthwork_style.layer)
                        scene = rendered
                    continue
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
                        station_range=station_range,
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
            if station_range is None or start <= label.station <= end:
                scene = StationLabelRenderer.render(scene, label, valid_profiles, style.vertical_exaggeration)
        if depth_labels:
            selected_depth = tuple(
                label for label in depth_labels
                if station_range is None or start <= label.start_station < label.end_station <= end
            )
            scene = DepthLabelRenderer.render_multiple(scene, selected_depth, profiles, style.vertical_exaggeration)
        if projections:
            scene = ProjectionRenderer.render(scene, projections, style, min_sta=start, max_sta=end)

        scene = replace(scene, metadata={
            **scene.metadata,
            "alignment_name": alignment_name,
            "vertical_exaggeration": style.vertical_exaggeration,
            "start_station": start,
            "end_station": end,
            **({"elevation_range": (low, high)} if station_range is not None else {}),
        })
        if stagger_config is None and custom_grade_breaks:
            stagger_config = StaggerConfigPresets.up_increment(base=3.0, increment=2.0)
        if stagger_config is not None:
            return StaggeredRenderer.apply_stagger(scene, stagger_config, fixed_text_layers=fixed_text_layers)
        return scene

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
