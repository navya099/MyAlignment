from cadgeom import Point2d

from myalignment.render.label_box import LabelBox
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.sheet.layout import SheetLayout


def _footer_width(layout):
    return min(155.0, layout.plot_area[2] * 0.52)


class TitleBlockRenderer:
    """시트 우하단에 표제와 도면 정보를 배치한다."""

    LAYER = "A-TITLE-BLOCK"

    @classmethod
    def render(cls, scene: Scene, layout: SheetLayout) -> Scene:
        height = layout.title_height_mm
        width = _footer_width(layout)
        if height <= 0 or width <= 6:
            return scene
        y = layout.margin_mm
        right = layout.size.width_mm - layout.margin_mm
        left = right - width
        style = Style(color=7, layer=cls.LAYER, lineweight=0.4)
        fields = [layout.title, layout.project_name, layout.drawing_number, layout.designer, layout.date]
        fields = [value.replace("\n", " ").replace("\r", " ") for value in fields if value]
        outline = Primitive.polyline(
            (Point2d(left, y), Point2d(right, y), Point2d(right, y + height), Point2d(left, y + height)),
            closed=True, style=style,
        )
        labels = []
        if fields:
            row = height / len(fields)
            for index, value in enumerate(fields):
                size = min(row * 0.62, 3.5 if index == 0 else 2.5)
                text_width = LabelBox.from_text(0, 0, value, size).width
                if text_width > width - 6:
                    size *= (width - 6) / text_width
                labels.append(Primitive.text(
                    Point2d(left + 3, y + height - row * (index + 0.5) - size / 2), value, size, style=style,
                ))
        return scene.add_layer(Layer(cls.LAYER)).add_all((outline, *labels))
