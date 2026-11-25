from __future__ import annotations

from collections.abc import Iterable
import math
from pathlib import Path
from typing import TYPE_CHECKING

from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D
from myalignment.render.scene_3d import Scene3D

if TYPE_CHECKING:
    from myalignment.corridor.slope_pattern import SlopePattern, SlopePatternCollection


class SlopePattern3DRenderer:
    """사면 패턴의 월드 3D 형상을 장면에 추가한다."""

    @staticmethod
    def render(scene: Scene3D, collection: Iterable[SlopePattern], z_scale: float = 1.0) -> Scene3D:
        """Z축에만 표시 배율을 적용한다."""
        if not math.isfinite(z_scale) or z_scale <= 0:
            raise ValueError("z_scale must be finite and positive")
        primitives = []
        for pattern in collection:
            style = pattern.style
            appearance = Style3D(color=style.color, layer=style.layer, lineweight=style.lineweight)
            for element in pattern.elements:
                points = tuple(Point3D(p.x, p.y, p.z * z_scale) for p in element.points)
                if len(points) == 1:
                    primitives.append(Primitive3D.point(points[0], appearance))
                elif len(points) == 2:
                    primitives.append(Primitive3D.line(*points, style=appearance))
                else:
                    primitives.append(Primitive3D.polyline(points, style=appearance))
        return scene.add_all(primitives) if primitives else scene


class SlopePattern3DPreview:
    """사면 패턴을 HTML과 3D DXF로 내보낸다."""

    @staticmethod
    def preview(
        collection: SlopePatternCollection, html_path: str | Path | None,
        dxf_path: str | Path | None = None, *, z_scale: float = 1.0,
        three_module_base: str | None = None,
    ) -> Scene3D:
        """출력한 월드 3D 장면을 반환한다."""
        scene = SlopePattern3DRenderer.render(Scene3D(), collection, z_scale)
        if dxf_path is not None:
            Dxf3DWriter(scene).write(dxf_path)
        if html_path is not None:
            options = {} if three_module_base is None else {"three_module_base": three_module_base}
            Json3DExporter.export_to_html(scene, html_path, f"Slope Patterns ({len(collection)})", **options)
        return scene
