from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.render.alignment_label_renderer import _component_primitives
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.alignment.station_offset_label import StationOffsetLabel


def _primitives(label, alignment, reference_alignment, reference_point):
    location = label._location(alignment)
    anchor, _, _, azimuth = location
    style = label.resolved_style(alignment)
    if style.show_marker:
        marker = Style(color=style.marker_color, layer=style.marker_layer, lineweight=0.5)
        size = style.marker_size
        for direction in (-1, 1):
            yield Primitive.line(
                Point2d(anchor.x - size, anchor.y - direction * size),
                Point2d(anchor.x + size, anchor.y + direction * size), marker,
            )
    fields = label._fields(alignment, location, reference_alignment, reference_point)
    hidden = set()
    if not style.show_station:
        hidden.update(("Station Value", "Raw Station"))
    if not style.show_offset:
        hidden.add("Offset Value")
    for component in style.components:
        if component.visible:
            yield from _component_primitives(component, anchor, azimuth, fields, hidden)


def _add(scene, primitives):
    layers = {}
    for primitive in primitives:
        style = primitive.style
        layers.setdefault(style.layer, Layer(style.layer, color=style.color))
    for layer in layers.values():
        scene = scene.add_layer(layer)
    return scene.add_all(primitives) if primitives else scene


class StationOffsetLabelRenderer:
    """평면 뷰에 측점·횡거 표식기와 텍스트를 추가한다."""

    @staticmethod
    def render(
        scene: Scene, label: StationOffsetLabel, alignment: Alignment, reference_alignment: Alignment | None = None, *,
        reference_point: Point2d | None = None,
    ) -> Scene:
        """지정한 점의 단일 레이블을 그린다."""
        return _add(scene, tuple(_primitives(label, alignment, reference_alignment, reference_point)))

    @staticmethod
    def render_multiple(
        scene: Scene, labels: Iterable[StationOffsetLabel], alignment: Alignment,
        reference_alignment: Alignment | None = None, *,
        reference_alignments: Mapping[str, Alignment] | None = None,
        reference_points: Mapping[str, Point2d] | None = None,
    ) -> Scene:
        """현재 선형 범위에 있는 레이블과 이름으로 지정한 참조를 그린다."""
        if not alignment.is_valid:
            return scene
        references = reference_alignments or {}
        points = reference_points or {}
        primitives = []
        for label in labels:
            if label.fixed_point is None and not alignment.start_station <= label.relative_station <= alignment.end_station:
                continue
            selected = references.get(label.reference_alignment_name, reference_alignment)
            if label.reference_alignment_name == alignment.name:
                selected = alignment
            primitives.extend(_primitives(label, alignment, selected, points.get(label.reference_point_name)))
        return _add(scene, primitives)
