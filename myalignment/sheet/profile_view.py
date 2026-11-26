from dataclasses import replace
import math

from cadgeom import Point2d

from myalignment.profile.band_style import GeometryBandStyle, VerticalGeometryBandStyle
from myalignment.profile.cant_band_style import CantBandStyle
from myalignment.profile.earthwork_band_style import EarthworkBandStyle
from myalignment.profile.profiletype import ProfileType
from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.rail.rail_alignment import RailAlignment
from myalignment.render.label_box import LabelBox
from myalignment.render.primitives import Primitive, Style
from myalignment.render.profile_view_renderer import ProfileViewRenderer, _elevations, _ticks
from myalignment.render.scene import Layer, Scene
from myalignment.sheet.clipping import place_scene
from myalignment.sheet.layout import Viewport
from myalignment.sheet.viewport import ProfileViewportTransform


_LEFT_MM = 18.0
_RIGHT_MM = 9.0
_AXIS_LABEL_SPACE_MM = 6.0


def _station_capacity(viewport):
    return (viewport.width_mm - _LEFT_MM - _RIGHT_MM) / viewport.mm_per_m


def _paper_band_options(bands, view_style, earthwork, mm_per_m):
    horizontal, vertical, cant = GeometryBandStyle(), VerticalGeometryBandStyle(), CantBandStyle()
    heights = {
        BandType.PROFILE_DATA: 3.0,
        BandType.HORIZONTAL_GEOMETRY: horizontal.band_height + 2 * horizontal.tick_length + 1,
        BandType.VERTICAL_GEOMETRY: vertical.band_height + 2 * vertical.tick_length + 1,
        BandType.CANT_DATA: cant.band_height + cant.tick_length + 1,
        BandType.EARTHWORK: earthwork.total_height + earthwork.band_gap,
    }
    offsets = {"bottom": _AXIS_LABEL_SPACE_MM, "top": 0.0}
    scaled_bands = []
    for band in bands:
        location = band.location or view_style.band_location
        # 측점 레이블은 종단 그리드의 바로 아래 영역을 사용한다.
        clearance = _AXIS_LABEL_SPACE_MM if location == "bottom" and offsets[location] == _AXIS_LABEL_SPACE_MM else 0
        offsets[location] += band.gap + heights[band.band_type]
        scaled_bands.append(replace(band, location=location, gap=(band.gap + clearance) / mm_per_m))

    def scaled(style, *fields):
        return replace(style, **{field: getattr(style, field) / mm_per_m for field in fields})

    return offsets, scaled_bands, {
        "geometry_band_style": scaled(horizontal, "band_height", "tick_length", "text_height", "text_offset_y"),
        "vertical_geometry_band_style": scaled(vertical, "band_height", "tick_length", "text_height", "text_offset_y"),
        "cant_band_style": scaled(cant, "band_height", "tick_length", "text_height"),
        "earthwork_band_style": scaled(earthwork, "row_height", "band_gap", "text_height", "label_height"),
        "band_spacing_scale": 1 / mm_per_m,
    }


def _axis_labels(scene, transform, alignment, station_range, elevation_range, style):
    viewport = transform.viewport
    start, end = station_range
    low, high = elevation_range
    height = 2.0
    layer = "A-PROFILE-AXES"
    text_style = Style(color=7, layer=layer)
    labels = []
    stations = sorted(set((start, end, *_ticks(start, end, style.grid_major_interval_station))))
    last_right = -math.inf
    right = transform.to_paper(end, low).x
    end_label = f"{alignment.raw_to_display_station(end):.2f}"
    end_width = LabelBox.from_text(0, 0, end_label, height).width
    for station in stations:
        point = transform.to_paper(station, low)
        text = f"{alignment.raw_to_display_station(station):.2f}"
        width = LabelBox.from_text(0, 0, text, height).width
        left = max(viewport.x_mm + 1, min(point.x - width / 2, viewport.bounds[2] - width - 1))
        if left <= last_right + 1 or (station != end and left + width + 1 > right - end_width / 2):
            continue
        labels.append(Primitive.text(Point2d(left, point.y - 3.5), text, height, style=text_style))
        last_right = left + width
    last_y = -math.inf
    for elevation in sorted(set((low, *_ticks(low, high, style.grid_major_interval_elevation)))):
        point = transform.to_paper(start, elevation)
        text = f"{elevation:.2f}"
        width = LabelBox.from_text(0, 0, text, height).width
        if point.y - last_y < height + 1 or point.x - width - 1.5 < viewport.x_mm:
            continue
        labels.append(Primitive.text(Point2d(point.x - width - 1.5, point.y - 0.75), text, height, style=text_style))
        last_y = point.y
    return scene.add_layer(Layer(layer)).add_all(labels)


def render_profile_panel(
    scene, viewport, alignment, profiles, station_range, *, profile_style, bands, datum, vertical_scale,
    earthwork_style, projections, hatch_style, render_labels,
):
    start, end = station_range
    view_style = profile_style or ProfileViewStyle(grid_major_interval_elevation=5, grid_minor_interval_elevation=1)
    if vertical_scale is None:
        vertical_scale = viewport.scale / view_style.vertical_exaggeration
    if not math.isfinite(vertical_scale) or vertical_scale <= 0:
        raise ValueError("profile_vertical_scale must be finite and positive")
    view_style = replace(view_style, vertical_exaggeration=viewport.scale / vertical_scale)
    vertical_mm_per_m = 1000 / vertical_scale
    overlapping = tuple(profile for profile in profiles if profile.start_station < end and profile.end_station > start)
    fg = next((p for p in overlapping if p.profile_type is ProfileType.FG), None)
    eg = next((p for p in overlapping if p.profile_type is ProfileType.EG), None)
    bands = (ProfileViewBand(BandType.EARTHWORK, location="bottom"),) if bands is None else bands
    bands = tuple(band for band in bands if (
        overlapping
        and (band.band_type is not BandType.EARTHWORK or fg is not None and eg is not None
             and max(fg.start_station, eg.start_station, start) < min(fg.end_station, eg.end_station, end))
        and (band.band_type is not BandType.CANT_DATA or isinstance(alignment, RailAlignment))
    ))
    offsets, scaled_bands, renderer_options = _paper_band_options(
        bands, view_style, earthwork_style or EarthworkBandStyle.standard(), vertical_mm_per_m,
    )
    height = viewport.height_mm - offsets["bottom"] - offsets["top"] - 6
    if height <= 0 or _station_capacity(viewport) <= 0:
        raise ValueError("Profile viewport is too small for the plot and its bands")

    if datum is None:
        elevations = [z for profile in overlapping for z in _elevations(profile, station_range)]
        elevations.extend(point.elevation for projection in projections or ()
                          for path in projection.clipped_paths(station_range) for point in path)
        step = view_style.grid_minor_interval_elevation
        datum = math.floor((min(elevations) - 4 / vertical_mm_per_m) / step) * step if elevations else 0.0
    station_width = (end - start) * viewport.mm_per_m
    centered_x = viewport.x_mm + (viewport.width_mm - station_width) / 2
    plot_left = max(viewport.x_mm + _LEFT_MM, min(centered_x, viewport.bounds[2] - _RIGHT_MM - station_width))
    paper_origin = Point2d(plot_left, viewport.y_mm + 3 + offsets["bottom"])
    transform = ProfileViewportTransform(viewport, paper_origin, start, datum, vertical_scale)
    elevation_range = (datum, datum + height / vertical_mm_per_m)
    source = ProfileViewRenderer.render(
        overlapping, alignment.name, view_style, scaled_bands, alignment=alignment, station_range=station_range,
        elevation_range=elevation_range, projections=projections, hatch_style=hatch_style,
        fg_profile_name=fg.name if fg is not None else None, eg_profile_name=eg.name if eg is not None else None,
        render_labels=render_labels, **renderer_options,
    )
    band_layers = {ProfileViewRenderer.BAND_LAYER} | {
        style.layer for key, style in renderer_options.items() if key.endswith("_style")
    }
    band_items = tuple(p for p in source.primitives if p.style.layer in band_layers)
    plot_items = tuple(p for p in source.primitives if p.style.layer not in band_layers)
    plot_clip = Viewport(viewport.name, viewport.x_mm, paper_origin.y, viewport.width_mm, height, viewport.scale)
    scene = place_scene(scene, replace(source, primitives=plot_items), plot_clip, transform.project_rendered)
    scene = place_scene(scene, replace(source, primitives=band_items), viewport, transform.project_rendered)
    if overlapping:
        axes = _axis_labels(Scene(), transform, alignment, station_range, elevation_range, view_style)
        scale_text = f"H 1:{viewport.scale:g}  V 1:{vertical_scale:g}"
        axes = axes.add(Primitive.text(
            Point2d(viewport.x_mm + 3, viewport.bounds[3] - 2.5), scale_text, 1.8,
            style=Style(color=7, layer="A-PROFILE-AXES"),
        ))
        scene = place_scene(scene, axes, viewport, lambda point: point, scale=1.0)
    return scene, transform
