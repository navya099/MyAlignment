from dataclasses import replace

from cadgeom import Point2d

from myalignment.render.label_box import LabelBox
from myalignment.render.primitives import PrimitiveType
from myalignment.render.scene import Scene
from myalignment.render.stagger_config import StaggerConfig
from myalignment.render.staggerer import Staggerer


class StaggeredRenderer:
    """Scene의 텍스트를 배치하고 해결되지 않은 레이블 ID를 기록한다."""

    @classmethod
    def apply_stagger(cls, scene: Scene, config: StaggerConfig) -> Scene:
        if not config.is_active:
            return scene

        boxes = []
        for index, primitive in enumerate(scene.primitives):
            if primitive.type is not PrimitiveType.TEXT or not primitive.points or not primitive.text:
                continue
            point = primitive.points[0]
            boxes.append((index, LabelBox.from_text(
                point.x, point.y, primitive.text, primitive.text_height,
                rotation=primitive.rotation, label_id=f"text_{index}",
            )))
        if not boxes:
            return scene

        result = Staggerer.stagger([box for _, box in boxes], config)
        primitives = list(scene.primitives)
        for index, box in boxes:
            dx, dy = result.offsets[box.label_id]
            if dx or dy:
                primitive = primitives[index]
                point = primitive.points[0]
                primitives[index] = replace(
                    primitive, points=(Point2d(point.x + dx, point.y + dy), *primitive.points[1:]),
                )
        return replace(
            scene, primitives=tuple(primitives),
            metadata={
                **scene.metadata,
                "stagger_levels": result.level_map,
                "stagger_unresolved": list(result.unresolved),
            },
        )
