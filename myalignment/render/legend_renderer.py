from dataclasses import dataclass

from cadgeom import Point2d

from myalignment.render.label_box import LabelBox
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.title_block_renderer import _footer_width
from myalignment.sheet.layout import SheetLayout


@dataclass(frozen=True, slots=True)
class LegendItem:
    """범례 항목의 선과 색상."""

    label: str
    color: int = 7
    line_type: str = "solid"
    layer: str = "A-LEGEND"


class LegendRenderer:
    """시트 좌하단에 표시된 데이터의 범례를 그린다."""

    @staticmethod
    def render(scene: Scene, layout: SheetLayout, items) -> Scene:
        items = tuple(items)
        if not items or layout.legend_height_mm <= 0:
            return scene
        left = layout.margin_mm + 3
        width = layout.plot_area[2] - (_footer_width(layout) if layout.show_title_block else 0)
        row = layout.legend_height_mm / len(items)
        primitives = []
        for index, item in enumerate(items):
            y = layout.margin_mm + (len(items) - index - 0.5) * row
            linetype = {"solid": "CONTINUOUS", "dashed": "DASHED", "dotted": "DOT"}.get(
                item.line_type, item.line_type,
            )
            line_style = Style(color=item.color, layer=item.layer, linetype=linetype, lineweight=0.35)
            text_style = Style(color=7, layer=item.layer)
            height = min(2.2, row * 0.72)
            label = item.label.replace("\n", " ").replace("\r", " ")
            rendered_width = LabelBox.from_text(0, 0, label, height).width
            if width <= 20:
                continue
            if rendered_width > width - 20:
                height *= (width - 20) / rendered_width
            primitives.extend((
                Primitive.line(Point2d(left, y), Point2d(left + 8, y), line_style),
                Primitive.text(Point2d(left + 11, y - height / 2), label, height, style=text_style),
            ))
            scene = scene.add_layer(Layer(item.layer))
        return scene.add_all(primitives)
