from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from itertools import accumulate
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.profile.view_splitter import ProfileViewSplitter
from myalignment.render.label_box import LabelBox
from myalignment.render.primitives import Primitive, PrimitiveType, Style
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.scene import Layer, Scene

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.profile.depth_label import DepthLabel
    from myalignment.profile.profile import Profile
    from myalignment.profile.station_label import StationElevationLabel
    from myalignment.profile.view_band import ProfileViewBand
    from myalignment.profile.view_split_config import ProfileViewSplitConfig
    from myalignment.profile.view_style import ProfileViewStyle
    from myalignment.render.stagger_config import StaggerConfig


def _drawing_bounds(primitives):
    boxes = []
    for primitive in primitives:
        if primitive.type is PrimitiveType.TEXT:
            anchor = primitive.points[0]
            boxes.append(LabelBox.from_text(
                anchor.x, anchor.y, primitive.text, primitive.text_height, rotation=primitive.rotation,
            ))
        elif primitive.points:
            xs, ys = zip(*((point.x, point.y) for point in primitive.points))
            boxes.append(LabelBox(min(xs), min(ys), max(xs), max(ys)))
    return LabelBox(
        min(box.x_min for box in boxes), min(box.y_min for box in boxes),
        max(box.x_max for box in boxes), max(box.y_max for box in boxes),
    )


class ProfileViewSplitRenderer:
    """측점 구간별 종단 뷰를 그리고 밴드와 레이블을 포함해 그리드에 맞춘다."""

    INDEX_LAYER = "C-PROF-VIEW-INDEX"
    OVERLAP_LAYER = "C-PROF-OVERLAP"

    @classmethod
    def render(
        cls,
        profiles: Sequence[Profile],
        alignment_name: str,
        view_style: ProfileViewStyle,
        split_config: ProfileViewSplitConfig,
        alignment: Alignment | None = None,
        bands: Sequence[ProfileViewBand] | None = None,
        labels: Sequence[StationElevationLabel] | None = None,
        depth_labels: Sequence[DepthLabel] | None = None,
        *,
        stagger_config: StaggerConfig | None = None,
        **view_options,
    ) -> Scene:
        """여러 종단의 전체 범위를 분할하고 입력 순서의 첫 유효 종단에서 PVI를 읽는다.

        view_options에는 ProfileViewRenderer의 밴드 및 레이블 스타일 옵션을
        전달할 수 있다. 겹침 방지는 각 패널 안에서 적용된다.
        """
        valid = tuple(profile for profile in profiles if profile.is_valid)
        if not valid:
            raise ValueError("분할할 유효한 종단이 없습니다.")
        station_range = (min(p.start_station for p in valid), max(p.end_station for p in valid))
        segments = ProfileViewSplitter.split(valid[0], split_config, station_range=station_range)
        panels = []
        for index, segment in enumerate(segments):
            panel = ProfileViewRenderer.render(
                profiles, alignment_name, view_style, bands, alignment=alignment,
                labels=labels, depth_labels=depth_labels, stagger_config=stagger_config,
                station_range=(segment.start_station, segment.end_station), **view_options,
            )
            overlaps = []
            if split_config.overlap_station > 0:
                for neighbor in segments[max(0, index - 1):index] + segments[index + 1:index + 2]:
                    start = max(segment.start_station, neighbor.start_station)
                    end = min(segment.end_station, neighbor.end_station)
                    if start < end:
                        overlaps.append(start + (end - start) / 2)
            panel = cls._annotate(panel, segment, view_style, split_config.include_start_label, overlaps)
            panels.append((panel, _drawing_bounds(panel.primitives)))
        return cls._layout(panels, segments, alignment_name, split_config)

    @classmethod
    def _annotate(cls, panel, segment, view_style, include_start_label, overlaps):
        if overlaps:
            low, high = (z * view_style.vertical_exaggeration for z in panel.metadata["elevation_range"])
            style = Style(color=6, layer=cls.OVERLAP_LAYER, linetype="DASHED")
            panel = panel.add_layer(Layer(cls.OVERLAP_LAYER, color=6)).add_all(
                Primitive.line(Point2d(station, low), Point2d(station, high), style)
                for station in overlaps
            )
        bounds = _drawing_bounds(panel.primitives)
        height = max(2.0, view_style.vertical_exaggeration)
        style = Style(color=7, layer=cls.INDEX_LAYER)
        x, y = segment.start_station, bounds.y_max + height
        heading = f"VIEW {segment.view_index + 1}/{segment.total_views}"
        items = [Primitive.text(Point2d(x, y), heading, height, style=style)]
        if include_start_label:
            items.append(Primitive.text(
                Point2d(x, y + height * 1.2),
                f"STA {segment.start_station:.2f} - {segment.end_station:.2f}", height, style=style,
            ))
        return panel.add_layer(Layer(cls.INDEX_LAYER, color=7)).add_all(items)

    @staticmethod
    def _layout(panels, segments, alignment_name, config):
        columns = min(config.columns, len(panels))
        rows = math.ceil(len(panels) / columns)
        widths, heights = [0.0] * columns, [0.0] * rows
        for index, (_, bounds) in enumerate(panels):
            row, column = divmod(index, columns)
            widths[column] = max(widths[column], bounds.width)
            heights[row] = max(heights[row], bounds.height)

        xs = tuple(accumulate((width + config.column_gap for width in widths), initial=0.0))
        ys = tuple(accumulate((-height - config.row_gap for height in heights), initial=0.0))
        layers = {}
        primitives = []
        panel_metadata = []
        for index, ((panel, bounds), segment) in enumerate(zip(panels, segments, strict=True)):
            row, column = divmod(index, columns)
            dx, dy = xs[column] - bounds.x_min, ys[row] - bounds.y_max
            shifted = bounds.shifted(dx, dy)
            panel_metadata.append({
                "start_station": segment.start_station, "end_station": segment.end_station,
                "translation": (dx, dy),
                "bounds": (shifted.x_min, shifted.y_min, shifted.x_max, shifted.y_max),
            })
            for layer in panel.layers:
                layers.setdefault(layer.name.casefold(), layer)
            primitives.extend(
                replace(primitive, points=tuple(Point2d(p.x + dx, p.y + dy) for p in primitive.points))
                for primitive in panel.primitives
            )

        return Scene(tuple(primitives), tuple(layers.values()), {
            "alignment_name": alignment_name,
            "view_count": len(segments),
            "split_method": config.method.value,
            "panels": tuple(panel_metadata),
        })
