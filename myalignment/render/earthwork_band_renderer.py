from __future__ import annotations

from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.profile.earthwork_band_data import DEPTH_TOLERANCE, EarthworkBandData
from myalignment.profile.earthwork_band_style import EarthworkBandStyle
from myalignment.render.label_box import LabelBox
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.profile.view_style import ProfileViewStyle


class EarthworkBandRenderer:
    """표고와 토공 깊이를 종단 뷰의 원시 측점 좌표에 맞춰 그린다."""

    @staticmethod
    def render(
        scene: Scene, data: EarthworkBandData, view_style: ProfileViewStyle, band_y_base: float,
        style: EarthworkBandStyle | None = None, *, alignment: Alignment | None = None,
    ) -> Scene:
        """밴드의 상단 표고를 기준으로 행과 표식 텍스트를 배치한다."""
        style = style or EarthworkBandStyle.standard()
        if not data.samples or not style.total_height:
            return scene

        viewport = Viewport(ViewportType.PROFILE, view_style.vertical_exaggeration)
        scale = view_style.vertical_exaggeration
        left, right = data.station_range()
        header_style = Style(color=7, layer=style.layer)
        frame_style = Style(color=7, layer=style.layer, lineweight=0.5)
        top = band_y_base
        bottom = top - style.total_height
        primitives = [
            Primitive.line(viewport.project(x, top), viewport.project(x, bottom), frame_style)
            for x in (left, right)
        ]
        primitives.append(Primitive.line(viewport.project(left, top), viewport.project(right, top), frame_style))

        def station_value(sample):
            value = sample.station
            if alignment is not None:
                value = alignment.raw_to_display_station(value)
            return f"{value:.1f}"

        rows = (
            (style.show_station, "STA", style.station_color, station_value),
            (style.show_fg, "FG", style.fg_color, lambda s: f"{s.fg_elevation:.2f}"),
            (style.show_eg, "EG", style.eg_color, lambda s: f"{s.eg_elevation:.2f}"),
            (style.show_cut, "CUT", style.cut_color, lambda s: _depth(s.cut)),
            (style.show_fill, "FILL", style.fill_color, lambda s: _depth(s.fill)),
            (style.show_diff, "Δ", style.diff_color, lambda s: f"{s.diff:+.2f}"),
        )
        header_height = min(style.label_height, style.row_height) * scale
        value_height = min(style.text_height, style.row_height) * scale
        widths = []
        for index, sample in enumerate(data.samples):
            before = data.samples[index - 1].station if index else -float("inf")
            after = data.samples[index + 1].station if index + 1 < len(data) else float("inf")
            widths.append(0.9 * min(sample.station - before, after - sample.station))

        for visible, title, color, value in rows:
            if not visible:
                continue
            middle = (top - style.row_height / 2) * scale
            first_width = 0.0
            value_style = Style(color=color, layer=style.layer)
            for index, (sample, width) in enumerate(zip(data.samples, widths, strict=True)):
                text = value(sample)
                text_width = LabelBox.from_text(0, 0, text, value_height).width
                factor = min(1.0, width / text_width)
                text_width *= factor
                height = value_height * factor
                if index == 0:
                    first_width = text_width
                primitives.append(Primitive.text(
                    Point2d(sample.station - text_width / 2, middle - height / 2),
                    text, height, style=value_style,
                ))
            header_width = LabelBox.from_text(0, 0, title, header_height).width
            header_x = left - first_width / 2 - header_height - header_width
            primitives.append(Primitive.text(
                Point2d(header_x, middle - header_height / 2), title, header_height, style=header_style,
            ))
            top -= style.row_height
            primitives.append(Primitive.line(
                viewport.project(left, top), viewport.project(right, top), frame_style,
            ))
        return scene.add_layer(Layer(style.layer, color=7)).add_all(primitives)


def _depth(value: float) -> str:
    return f"{value:.2f}" if value > DEPTH_TOLERANCE else "—"
