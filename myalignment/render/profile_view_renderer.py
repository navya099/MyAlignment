from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
import math
from typing import TYPE_CHECKING

from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.rail.rail_alignment import RailAlignment
from myalignment.render.primitives import Primitive, Style
from myalignment.render.profile_renderer import ProfileRenderer
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.profile.profile import Profile


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

        if bands:
            scene = scene.add_layer(Layer(cls.BAND_LAYER))
            stations = _ticks(start, end, style.grid_major_interval_station)
            edges = {"bottom": low, "top": high}
            for band in bands:
                location = band.location or style.band_location
                direction = 1 if location == "top" else -1
                base = edges[location] + direction * band.gap
                selected = tuple(
                    p for p in valid_profiles if not band.profile_names or p.name in band.profile_names
                )
                rows = max(1, len(selected)) if band.band_type is BandType.VERTICAL_GEOMETRY else 1
                edges[location] = base + direction * (2.0 * rows + 1.0)
                scene = scene.add_all(cls._band_primitives(
                    band, selected, alignment, stations, start, end, base, direction, viewport
                ))

        return replace(scene, metadata={
            **scene.metadata,
            "alignment_name": alignment_name,
            "vertical_exaggeration": style.vertical_exaggeration,
            "start_station": start,
            "end_station": end,
        })

    @classmethod
    def _band_primitives(
        cls, band, profiles, alignment, stations, start, end, base, direction, viewport,
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
                    labels.append((station, 0, f"{station:g} | " + " | ".join(values)))
        elif band.band_type is BandType.VERTICAL_GEOMETRY:
            for row, profile in enumerate(profiles):
                for entity in profile.entities:
                    station = (entity.start_station + entity.end_station) / 2
                    labels.append((
                        station, row, f"{profile.name}: {entity.entity_type.name} "
                        f"{entity.start_grade:+.2%} to {entity.end_grade:+.2%}",
                    ))
        elif band.band_type is BandType.HORIZONTAL_GEOMETRY and alignment is not None:
            for entity in alignment.entities:
                lo, hi = max(start, entity.start_station), min(end, entity.end_station)
                if lo < hi:
                    labels.append(((lo + hi) / 2, 0, f"{entity.entity_type.name} {entity.length:.2f} m"))
        elif band.band_type is BandType.CANT_DATA and isinstance(alignment, RailAlignment):
            sample_stations = set(stations)
            sample_stations.update(
                critical.station for curve in alignment.cant_curves
                for critical in curve.critical_stations if start <= critical.station <= end
            )
            for station in sorted(sample_stations):
                cant = alignment.cant_at(station)
                if cant is not None:
                    labels.append((station, 0, f"{station:g} | {cant.cant_value * 1000:+.1f} mm"))

        exaggeration = viewport.vertical_exaggeration
        for station, row, text in labels:
            # TEXT의 삽입점이 하단이므로 아래 밴드는 글자 높이만큼 추가로 내린다.
            offset = 2.0 * row + (0.5 if direction > 0 else 2.0)
            point = viewport.project(station, base + direction * offset)
            yield Primitive.text(point, text, 1.5 * exaggeration, style=style)
