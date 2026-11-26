from __future__ import annotations

import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.profile.projection_builder import ProjectionBuilder
from myalignment.render.primitives import Primitive, Style
from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D
from myalignment.render.scene import Layer, Scene
from myalignment.render.scene_3d import Scene3D

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.pressure.network import PressureNetwork
    from myalignment.profile.view_projection import ProfileViewProjection


class PressureNetworkRenderer:
    """관 중심선, 피팅과 부속품의 평면도와 종단 투영을 생성한다."""

    PIPE_LAYER = "C-PRESSURE-PIPE"
    FITTING_LAYER = "C-PRESSURE-FITTING"
    APP_LAYER = "C-PRESSURE-APP"

    @classmethod
    def render_plan(cls, scene: Scene, network: PressureNetwork) -> Scene:
        pipe_style = Style(color=5, layer=cls.PIPE_LAYER, lineweight=0.5)
        fitting_style = Style(color=1, layer=cls.FITTING_LAYER, lineweight=0.3)
        app_style = Style(color=3, layer=cls.APP_LAYER, lineweight=0.4)

        primitives = []
        for pipe in network.pipes:
            if pipe.centerline:
                start, end = (Point2d(point.x, point.y) for point in pipe.centerline)
                if start != end:
                    primitives.append(Primitive.line(start, end, pipe_style))
        for fitting in network.fittings:
            if fitting.location is not None:
                center = Point2d(fitting.location.x, fitting.location.y)
                primitives.append(Primitive.circle(center, fitting.part.diameter_mm / 2000, fitting_style))
        for app in network.appurtenances:
            if app.location is not None:
                x, y = app.location.x, app.location.y
                width = math.sqrt(3) / 2
                primitives.append(Primitive.polyline(
                    (Point2d(x, y + 1), Point2d(x - width, y - 0.5), Point2d(x + width, y - 0.5)),
                    closed=True, style=app_style,
                ))
        for style in (pipe_style, fitting_style, app_style):
            scene = scene.add_layer(Layer(style.layer, color=style.color))
        return scene.add_all(primitives)

    @staticmethod
    def profile_projections(network: PressureNetwork, alignment: Alignment) -> tuple[ProfileViewProjection, ...]:
        """종단 뷰에 표시할 관 중심선 투영을 만든다."""
        return tuple(
            ProjectionBuilder.project_pipe(alignment, pipe.centerline, pipe.name)
            for pipe in network.pipes if pipe.centerline
        )


class PressureNetwork3DRenderer:
    """관 중심선과 연결 노드의 3D 도형을 생성한다."""

    PIPE_LAYER = "C-PRESSURE-3D"
    FITTING_LAYER = "C-PRESSURE-FITTING-3D"
    APP_LAYER = "C-PRESSURE-APP-3D"

    @classmethod
    def render(cls, network: PressureNetwork, z_scale: float = 1.0, *, scene: Scene3D | None = None) -> Scene3D:
        if not math.isfinite(z_scale) or z_scale <= 0:
            raise ValueError("z_scale must be finite and positive")
        scene = Scene3D() if scene is None else scene
        pipe_style = Style3D(color=5, layer=cls.PIPE_LAYER, lineweight=0.5)
        fitting_style = Style3D(color=1, layer=cls.FITTING_LAYER)
        app_style = Style3D(color=3, layer=cls.APP_LAYER)

        def scaled(point):
            return Point3D(point.x, point.y, point.z * z_scale)

        primitives = [
            Primitive3D.line(*(scaled(point) for point in pipe.centerline), style=pipe_style)
            for pipe in network.pipes if pipe.centerline
        ]
        for nodes, style in ((network.fittings, fitting_style), (network.appurtenances, app_style)):
            primitives.extend(
                Primitive3D.point(scaled(node.location), style)
                for node in nodes if node.location is not None
            )
        return scene.add_all(primitives)
