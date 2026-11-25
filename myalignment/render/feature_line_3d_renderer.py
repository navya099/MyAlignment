from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D
from myalignment.render.scene_3d import Scene3D

if TYPE_CHECKING:
    from myalignment.corridor.feature_line_manager import CorridorFeatureLineManager


class FeatureLine3DRenderer:
    """코리더 선의 3D 폴리라인과 점 마커를 추가한다."""

    @staticmethod
    def render(
        scene: Scene3D, manager: CorridorFeatureLineManager, show_points: bool = False, z_scale: float = 1.0,
    ) -> Scene3D:
        """Z 스케일을 적용한 구간별 도형을 기존 장면에 추가한다."""
        if not math.isfinite(z_scale) or z_scale <= 0:
            raise ValueError("z_scale must be finite and positive")
        primitives = []
        for line in manager:
            spec = line.spec
            style = Style3D(color=spec.color, layer=spec.layer, lineweight=spec.lineweight) if spec else Style3D(
                color=7, layer="C-CORRIDOR-FL", lineweight=0.3,
            )
            marker = Style3D(color=style.color, layer=f"{style.layer}-PTS", lineweight=0.15)
            for run in line.segments:
                vertices = tuple(Point3D(p.point.x, p.point.y, p.point.z * z_scale) for p in run)
                if len(vertices) >= 2:
                    primitives.append(Primitive3D.polyline(vertices, style=style))
                elif not show_points:
                    primitives.append(Primitive3D.point(vertices[0], style))
                if show_points:
                    primitives.extend(Primitive3D.point(point, marker) for point in vertices)
        return scene.add_all(primitives) if primitives else scene


class FeatureLine3DPreview:
    """3D 코리더 선을 브라우저 미리보기와 DXF로 내보낸다."""

    @staticmethod
    def preview(
        manager: CorridorFeatureLineManager, html_path: str | Path | None,
        dxf_path: str | Path | None = None, show_points: bool = False, *,
        z_scale: float = 1.0, three_module_base: str | None = None,
    ) -> Scene3D:
        """지정한 경로로 파일을 생성하고 3D 장면을 반환한다."""
        scene = FeatureLine3DRenderer.render(Scene3D(), manager, show_points, z_scale)
        if html_path is not None:
            options = {} if three_module_base is None else {"three_module_base": three_module_base}
            Json3DExporter.export_to_html(scene, html_path, f"Corridor Feature Lines ({len(manager)})", **options)
        if dxf_path is not None:
            Dxf3DWriter(scene).write(dxf_path)
        return scene
