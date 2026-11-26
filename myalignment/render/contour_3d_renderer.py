from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D
from myalignment.render.scene_3d import Scene3D
from myalignment.surface.contour_style import ContourStyle

if TYPE_CHECKING:
    from myalignment.surface.contour_line import ContourSet


class Contour3DRenderer:
    """등고선 표고에 3D 폴리라인을 배치한다."""

    @staticmethod
    def render(
        scene: Scene3D, contours: ContourSet, style: ContourStyle | None = None, z_scale: float = 1.0,
    ) -> Scene3D:
        if not math.isfinite(z_scale) or z_scale <= 0:
            raise ValueError("z_scale must be finite and positive")
        style = style or ContourStyle.standard()
        primitives = []
        for contour in contours:
            if contour.point_count < 2 or not style.is_visible(contour.contour_type):
                continue
            layer, color, weight = style.appearance(contour.contour_type, contour.elevation)
            elevation = contour.elevation * z_scale
            primitives.append(Primitive3D.polyline(
                (Point3D(p.x, p.y, elevation) for p in contour.points),
                closed=contour.closed, style=Style3D(color=color, layer=layer, lineweight=weight),
            ))
        return scene.add_all(primitives) if primitives else scene


class Contour3DPreview:
    """3D 등고선 장면을 HTML 미리보기나 DXF로 저장한다."""

    @staticmethod
    def preview(
        contours: ContourSet, html_path: str | Path | None, dxf_path: str | Path | None = None,
        style: ContourStyle | None = None, *, z_scale: float = 1.0, three_module_base: str | None = None,
    ) -> Scene3D:
        scene = Contour3DRenderer.render(Scene3D(), contours, style, z_scale)
        if dxf_path is not None:
            Dxf3DWriter(scene).write(dxf_path)
        if html_path is not None:
            options = {} if three_module_base is None else {"three_module_base": three_module_base}
            Json3DExporter.export_to_html(scene, html_path, f"Surface Contours ({len(scene)})", **options)
        return scene
