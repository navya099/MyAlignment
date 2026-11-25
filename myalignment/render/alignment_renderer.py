from __future__ import annotations

from dataclasses import replace
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.alignment.style.display_rule import AlignmentComponent, ViewType
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.line_entity import LineEntity
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.render.alignment_label_renderer import AlignmentLabelRenderer
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.stagger_config import StaggerConfig
from myalignment.render.staggered_renderer import StaggeredRenderer

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.profile.profile import Profile
    from myalignment.surface.tin_surface import TinSurface


class AlignmentRenderer:
    """선형의 평면 기하를 구성요소별 표시 규칙으로 그린다."""

    LAYER_MAP = {component: f"C-ALIGN-{component.name}" for component in AlignmentComponent}
    _COMPONENTS = {
        LineEntity: AlignmentComponent.LINE,
        ArcEntity: AlignmentComponent.CURVE,
        SpiralEntity: AlignmentComponent.SPIRAL,
    }

    @classmethod
    def render_plan(
        cls, alignment: Alignment, scene: Scene | None = None, sample_step: float = 1.0,
        *, render_labels: bool = False, surface: TinSurface | None = None,
        profile: Profile | None = None, reference_alignment: Alignment | None = None,
        render_equations: bool = True,
        stagger_config: StaggerConfig | None = None,
        render_curves: bool = True,
        render_spirals: bool = True,
    ) -> Scene:
        if not math.isfinite(sample_step) or sample_step <= 0:
            raise ValueError("sample_step must be finite and positive")
        scene = Scene() if scene is None else scene
        styles = {}
        for component, name in cls.LAYER_MAP.items():
            rule = alignment.style.get_rule(component, ViewType.PLAN)
            if rule is None or not rule.visible:
                continue
            scene = scene.add_layer(Layer(name, lineweight=rule.lineweight))
            styles[component] = Style(rule.color, rule.linetype, rule.lineweight, name)

        primitives = []
        for entity in alignment.entities:
            component = next(
                (component for entity_type, component in cls._COMPONENTS.items()
                 if isinstance(entity, entity_type)),
                None,
            )
            style = styles.get(component)
            if style is None:
                continue
            if component is AlignmentComponent.LINE:
                primitives.append(Primitive.line(entity.start_coord, entity.end_coord, style))
            else:
                count = max(8, math.ceil(entity.length / sample_step))
                points = [
                    entity.point_at(entity.start_station + entity.length * i / count)
                    for i in range(count)
                ]
                points.append(entity.end_coord)
                primitives.append(Primitive.polyline(points, style=style))

        if alignment.is_valid:
            if AlignmentComponent.ARROW in styles:
                primitives.append(cls._render_arrow(alignment, styles[AlignmentComponent.ARROW]))
            if AlignmentComponent.MARKER in styles:
                markers = [entity.start_coord for entity in alignment.entities]
                markers.append(alignment.point_at(alignment.end_station))
                primitives.extend(
                    Primitive.circle(point, 0.5, styles[AlignmentComponent.MARKER])
                    for point in markers
                )

        scene = scene.add_all(primitives)
        if render_labels:
            scene = AlignmentLabelRenderer.render(
                scene, alignment, surface, profile=profile, reference_alignment=reference_alignment,
                render_equations=render_equations,
                render_curves=render_curves, render_spirals=render_spirals,
            )
        scene = replace(scene, metadata={
            **scene.metadata,
            "alignment_name": alignment.name,
            "start_station": alignment.start_station,
            "end_station": alignment.end_station,
        })
        return StaggeredRenderer.apply_stagger(scene, stagger_config) if stagger_config is not None else scene

    @staticmethod
    def _render_arrow(alignment: Alignment, style: Style) -> Primitive:
        tip = alignment.point_at(alignment.start_station)
        azimuth = alignment.tangent_at(alignment.start_station)
        dx, dy = math.cos(azimuth), math.sin(azimuth)
        tail_x, tail_y = tip.x - 5 * dx, tip.y - 5 * dy
        left = Point2d(tail_x - 2 * dy, tail_y + 2 * dx)
        right = Point2d(tail_x + 2 * dy, tail_y - 2 * dx)
        return Primitive.polyline((tip, left, right), closed=True, style=style)
