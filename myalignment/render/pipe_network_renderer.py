from __future__ import annotations

import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.pipe.pipe_type import StructureType
from myalignment.profile.projection_builder import ProjectionBuilder
from myalignment.render.primitives import Primitive, Style
from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D
from myalignment.render.scene import Layer, Scene
from myalignment.render.scene_3d import Scene3D

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.pipe.network import PipeNetwork
    from myalignment.profile.view_projection import ProfileViewProjection


class PipeNetworkRenderer:
    """관망 평면도와 종단 투영을 생성한다."""

    PIPE_LAYER = "C-PIPE-NETWORK-PIPE"
    STRUCT_LAYER = "C-PIPE-NETWORK-STRUCT"

    @classmethod
    def render_plan(cls, scene: Scene, network: PipeNetwork) -> Scene:
        """관 경로와 보이는 구조물의 위치 및 이름을 추가한다."""
        pipe_style = Style(color=5, layer=cls.PIPE_LAYER, lineweight=0.5)
        structure_style = Style(color=1, layer=cls.STRUCT_LAYER, lineweight=0.5)
        pipes = (
            Primitive.line(pipe.start_point, pipe.end_point, pipe_style)
            for pipe in network.pipes if pipe.start_point is not None and pipe.end_point is not None
        )
        structures = []
        for structure in network.structures:
            point = structure.point
            if point is None or structure.part.structure_type is StructureType.NULL:
                continue
            radius = structure.part.diameter_m / 2
            structures.extend((
                Primitive.circle(point, radius, structure_style),
                Primitive.text(Point2d(point.x + radius + 1, point.y), structure.name, 1.5, style=structure_style),
            ))
        return (
            scene.add_layer(Layer(cls.PIPE_LAYER, color=5))
            .add_layer(Layer(cls.STRUCT_LAYER, color=1))
            .add_all(pipes)
            .add_all(structures)
        )

    @staticmethod
    def profile_projections(network: PipeNetwork, alignment: Alignment) -> tuple[ProfileViewProjection, ...]:
        """종단 뷰에서 사용할 관 중심선 투영을 반환한다."""
        return tuple(
            ProjectionBuilder.project_pipe(alignment, points, pipe.name)
            for pipe in network.pipes if (points := pipe.centerline)
        )


class PipeNetwork3DRenderer:
    """관저고 경로와 구조물의 높이 및 림을 3D 와이어프레임으로 그린다."""

    PIPE_LAYER = "C-PIPE-3D"
    STRUCT_LAYER = "C-STRUCT-3D"

    @classmethod
    def render(cls, network: PipeNetwork, z_scale: float = 1.0, *, scene: Scene3D | None = None) -> Scene3D:
        if not math.isfinite(z_scale) or z_scale <= 0:
            raise ValueError("z_scale must be finite and positive")
        scene = Scene3D() if scene is None else scene
        pipe_style = Style3D(color=5, layer=cls.PIPE_LAYER, lineweight=0.5)
        structure_style = Style3D(color=1, layer=cls.STRUCT_LAYER, lineweight=0.5)
        primitives = []
        for pipe in network.pipes:
            if pipe.start_point is not None and pipe.end_point is not None:
                primitives.append(Primitive3D.line(
                    Point3D(pipe.start_point.x, pipe.start_point.y, pipe.start_invert * z_scale),
                    Point3D(pipe.end_point.x, pipe.end_point.y, pipe.end_invert * z_scale),
                    pipe_style,
                ))
        for structure in network.structures:
            point = structure.point
            if point is None or structure.part.structure_type is StructureType.NULL:
                continue
            top = structure.rim_elevation * z_scale
            bottom = structure.bottom_elevation * z_scale
            if top != bottom:
                primitives.append(Primitive3D.line(
                    Point3D(point.x, point.y, top), Point3D(point.x, point.y, bottom), structure_style,
                ))
            radius = structure.part.diameter_m / 2
            angles = (math.tau * index / 16 for index in range(16))
            rim = (
                Point3D(point.x + radius * math.cos(angle), point.y + radius * math.sin(angle), top)
                for angle in angles
            )
            primitives.append(Primitive3D.polyline(rim, closed=True, style=structure_style))
        return scene.add_all(primitives)
