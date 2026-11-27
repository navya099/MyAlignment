from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
import math
from typing import TYPE_CHECKING, Literal

from cadgeom import Point2d

from myalignment.profile.earthwork_band_style import EarthworkBandStyle
from myalignment.profile.profiletype import ProfileType
from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.render.contour_renderer import ContourRenderer
from myalignment.render.feature_line_2d_renderer import FeatureLine2DRenderer
from myalignment.render.legend_renderer import LegendItem, LegendRenderer
from myalignment.render.primitives import Primitive, Style
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.scene import Layer, Scene
from myalignment.render.surface_renderer import TinSurfaceRenderer
from myalignment.render.title_block_renderer import TitleBlockRenderer
from myalignment.sheet.clipping import place_scene
from myalignment.sheet.layout import SheetLayout
from myalignment.sheet.profile_view import _station_capacity, render_profile_panel
from myalignment.sheet.viewport import PlanViewportTransform
from myalignment.surface.contour_style import ContourStyle

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.profile.hatch_style import ProfileHatchStyle
    from myalignment.profile.profile import Profile
    from myalignment.profile.view_band import ProfileViewBand
    from myalignment.profile.view_projection import ProfileViewProjection
    from myalignment.profile.view_style import ProfileViewStyle
    from myalignment.surface.tin_surface import TinSurface


def _frame(scene, bounds, layer, weight=0.35):
    x0, y0, x1, y1 = bounds
    style = Style(color=7, layer=layer, lineweight=weight)
    vertices = (Point2d(x0, y0), Point2d(x1, y0), Point2d(x1, y1), Point2d(x0, y1))
    return scene.add_layer(Layer(layer)).add(Primitive.polyline(vertices, closed=True, style=style))


def _capacity(layout):
    limits = []
    if layout.plan_viewport is not None:
        a = layout.plan_viewport
        limits.append((a.width_mm - 8) / a.mm_per_m)
    if layout.profile_viewport is not None:
        limits.append(_station_capacity(layout.profile_viewport))
    length = min(limits, default=math.inf)
    if length <= 0:
        raise ValueError("Viewport width is too small for a station window")
    return length


def _station_range(alignment, start, end):
    if not alignment.is_valid:
        raise ValueError("A valid alignment is required")
    start = alignment.start_station if start is None else start
    end = alignment.end_station if end is None else end
    if not alignment.start_station <= start < end <= alignment.end_station:
        raise ValueError("Station range must be increasing and inside the alignment's raw station range")
    return start, end


def _plan_transform(viewport, alignment, station_range, center, rotation, step, plan_tangent):
    start, end = station_range
    if rotation is None:
        if plan_tangent == "start":
            # Use the outgoing element when the sheet starts at a geometry boundary.
            entity = next(entity for entity in alignment.entities if entity.end_station > start)
            rotation = entity.tangent_at(max(start, entity.start_station))
        else:
            rotation = alignment.tangent_at(start + (end - start) / 2)
    if center is not None:
        return PlanViewportTransform(viewport, center, rotation)
    frame = PlanViewportTransform(viewport, alignment.point_at(start), rotation)
    projected = []
    for entity in alignment.entities:
        left, right = max(start, entity.start_station), min(end, entity.end_station)
        if left >= right:
            continue
        count = max(1, math.ceil((right - left) / step))
        projected.extend(frame.to_paper(entity.point_at(left + (right - left) * i / count)) for i in range(count))
        projected.append(frame.to_paper(entity.point_at(right)))
    x, y = zip(*((point.x, point.y) for point in projected))
    midpoint = Point2d((min(x) + max(x)) / 2, (min(y) + max(y)) / 2)
    return replace(frame, world_center=frame.to_world(midpoint))


def _north_arrow(scene, transform):
    viewport = transform.viewport
    if min(viewport.width_mm, viewport.height_mm) < 26:
        return scene
    right, top = viewport.bounds[2:]
    layer = "A-NORTH"
    style = Style(color=7, layer=layer, lineweight=0.45)
    angle = transform.rotation
    dx, dy = math.sin(angle), math.cos(angle)
    x, y = right - 14, top - 14

    def point(along, across=0):
        return Point2d(x + dx * along - dy * across, y + dy * along + dx * across)

    label = point(8)
    return scene.add_layer(Layer(layer)).add_all((
        Primitive.line(point(-6), point(6), style),
        Primitive.polyline((point(3, 1.5), point(6), point(3, -1.5)), style=style),
        Primitive.text(Point2d(label.x - 0.75, label.y - 0.75), "N", 2.5, style=style),
    ))


def _scale_bar(scene, layout):
    viewport = layout.plan_viewport or layout.profile_viewport
    if viewport is None:
        return scene
    scale = viewport.mm_per_m
    available = 45 / scale
    unit = 10 ** math.floor(math.log10(available))
    length_m = max(step * unit for step in (1, 2, 5) if step * unit <= available)
    length = length_m * scale
    layer = "A-SCALE-BAR"
    style = Style(color=7, layer=layer, lineweight=0.45)
    x = layout.margin_mm + 3
    y = layout.margin_mm + (layout.legend_height_mm if layout.show_legend else 0.0) + 3
    coordinates = (x, x + length / 2, x + length)
    ticks = [Primitive.line(Point2d(a, y - 1), Point2d(a, y + 1), style) for a in coordinates]
    labels = [
        Primitive.text(Point2d(coordinates[0], y + 2), "0", 1.8, style=style),
        Primitive.text(Point2d(coordinates[-1], y + 2), f"{length_m:g} m", 1.8, style=style),
        Primitive.text(Point2d(coordinates[-1] + 15, y - 0.5), f"1:{viewport.scale:g}", 2.0, style=style),
    ]
    return scene.add_layer(Layer(layer)).add_all((
        Primitive.line(Point2d(x, y), Point2d(x + length, y), style), *ticks, *labels,
    ))


class SheetComposer:
    """모델 좌표를 실제 축척의 평면도·종단도로 배치한다."""

    @classmethod
    def compose(
        cls, layout: SheetLayout, alignment: Alignment, fg_profile: Profile | None = None,
        eg_profile: Profile | None = None, surface: TinSurface | None = None, corridor: Corridor | None = None,
        station_start: float | None = None, station_end: float | None = None, *,
        plan_center: Point2d | None = None, plan_rotation: float | None = None,
        plan_tangent: Literal["midpoint", "start"] = "midpoint", plan_sample_step: float = 1.0,
        plan_scene: Scene | None = None, render_plan_labels: bool = True, render_profile_labels: bool = True,
        contour_style: ContourStyle | None = None, profile_style: ProfileViewStyle | None = None,
        profile_vertical_scale: float | None = None, profile_datum: float | None = None,
        bands: Sequence[ProfileViewBand] | None = None, earthwork_band_style: EarthworkBandStyle | None = None,
        projections: Sequence[ProfileViewProjection] | None = None, hatch_style: ProfileHatchStyle | None = None,
    ) -> Scene:
        """평면 회전각을 생략하면 plan_tangent로 지정한 접선 방향을 사용한다."""
        if not math.isfinite(plan_sample_step) or plan_sample_step <= 0:
            raise ValueError("plan_sample_step must be finite and positive")
        if plan_tangent not in ("midpoint", "start"):
            raise ValueError("plan_tangent must be 'midpoint' or 'start'")
        start, end = _station_range(alignment, station_start, station_end)
        if station_end is None:
            end = min(end, start + _capacity(layout))
        if layout.profile_viewport is not None and end - start > _station_capacity(layout.profile_viewport) + 1e-8:
            raise ValueError("Station range exceeds the profile viewport at its drawing scale")
        station_range = start, end
        fg_profile = fg_profile if fg_profile is not None else alignment.fg_profile
        eg_profile = eg_profile if eg_profile is not None else alignment.eg_profile
        profiles = tuple(
            replace(profile, profile_type=role) for profile, role in (
                (fg_profile, ProfileType.FG), (eg_profile, ProfileType.EG),
            ) if profile is not None and profile.is_valid
        )
        size, margin = layout.size, layout.margin_mm
        scene = _frame(Scene(), (margin, margin, size.width_mm - margin, size.height_mm - margin), "A-FRAME", 0.65)
        metadata = {
            "sheet_width_mm": size.width_mm, "sheet_height_mm": size.height_mm,
            "station_range": station_range, "alignment_name": alignment.name,
        }
        if layout.plan_viewport is not None:
            viewport = layout.plan_viewport
            transform = _plan_transform(
                viewport, alignment, station_range, plan_center, plan_rotation, plan_sample_step, plan_tangent,
            )
            source = plan_scene if plan_scene is not None else Scene()
            if surface is not None:
                style = contour_style or ContourStyle.standard()
                source = ContourRenderer.render(source, surface.generate_contours(style), style)
            if corridor is not None:
                for corridor_surface in corridor.surfaces:
                    source = TinSurfaceRenderer.render(corridor_surface, source, show_triangles=False)
                source = FeatureLine2DRenderer.render(source, corridor.feature_lines)
            source = AlignmentRenderer.render_plan(
                alignment, source, plan_sample_step, render_labels=render_plan_labels,
                surface=surface, fg_profile=fg_profile, station_range=station_range,
            )
            scene = place_scene(scene, source, viewport, transform.to_paper, rotation=-transform.rotation)
            scene = _frame(scene, viewport.bounds, "A-VIEWPORT")
            if layout.show_north_arrow:
                scene = _north_arrow(scene, transform)
            metadata["plan_transform"] = transform
        if layout.profile_viewport is not None:
            viewport = layout.profile_viewport
            scene, transform = render_profile_panel(
                scene, viewport, alignment, profiles, station_range, profile_style=profile_style,
                bands=bands, datum=profile_datum, vertical_scale=profile_vertical_scale,
                earthwork_style=earthwork_band_style, projections=projections, hatch_style=hatch_style,
                render_labels=render_profile_labels,
            )
            scene = _frame(scene, viewport.bounds, "A-VIEWPORT")
            metadata["profile_transform"] = transform
        if layout.show_title_block:
            scene = TitleBlockRenderer.render(scene, layout)
        if layout.show_legend:
            layers = {primitive.style.layer for primitive in scene.primitives}
            items = []
            for profile, layer, color in (
                (fg_profile, ProfileViewRenderer.FG_LAYER, 1), (eg_profile, ProfileViewRenderer.EG_LAYER, 3),
            ):
                if profile is not None and layer in layers:
                    items.append(LegendItem(profile.name or ("FG" if color == 1 else "EG"), color))
            earthwork = earthwork_band_style or EarthworkBandStyle.standard()
            if earthwork.layer in layers:
                if earthwork.show_cut:
                    items.append(LegendItem("Cut", earthwork.cut_color))
                if earthwork.show_fill:
                    items.append(LegendItem("Fill", earthwork.fill_color))
            scene = LegendRenderer.render(scene, layout, items)
        if layout.show_scale_bar:
            scene = _scale_bar(scene, layout)
        return replace(scene, metadata=metadata)

    @classmethod
    def compose_series(
        cls, layout: SheetLayout, alignment: Alignment, fg_profile: Profile | None = None,
        eg_profile: Profile | None = None, *, station_start: float | None = None, station_end: float | None = None,
        station_span: float | None = None,
        plan_tangent: Literal["midpoint", "start"] = "midpoint",
        **options,
    ) -> tuple[Scene, ...]:
        """같은 축척으로 시트를 나눈다. station_span은 장당 원시 측점 길이(m)이다."""
        start, end = _station_range(alignment, station_start, station_end)
        capacity = _capacity(layout)
        span = capacity
        if station_span is not None:
            if not math.isfinite(station_span) or station_span <= 0 or start + station_span == start:
                raise ValueError("station_span must be finite, positive and advance the station")
            span = min(station_span, end - start)
            if span > capacity + 1e-8:
                raise ValueError(
                    f"station_span requires {span:g} m per sheet but the viewport capacity is {capacity:g} m "
                    "at the current drawing scales"
                )
        count = max(1, math.ceil((end - start) / span - 1e-12))
        scenes = []
        for index in range(count):
            left = start + span * index if index else start
            right = end if index == count - 1 else start + span * (index + 1)
            sheet_layout = replace(layout, drawing_number=f"{layout.drawing_number}-{index + 1:02d}") if (
                layout.drawing_number and count > 1
            ) else layout
            scene = cls.compose(sheet_layout, alignment, fg_profile, eg_profile, station_start=left, station_end=right,
                                plan_tangent=plan_tangent, **options)
            scenes.append(replace(scene, metadata={**scene.metadata, "sheet_index": index + 1, "sheet_count": count}))
        return tuple(scenes)
