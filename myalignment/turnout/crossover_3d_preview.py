from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.render.crossover_3d_renderer import Crossover3DRenderer
from myalignment.render.scene_3d import Scene3D
from myalignment.turnout.crossover_calculator import CrossoverGeometryCalculator

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.turnout.crossover import Crossover


class Crossover3DPreview:
    """크로스오버를 Scene3D에 배치하고 선택적으로 DXF와 HTML을 저장한다."""

    @classmethod
    def preview(
        cls,
        alignment1: Alignment,
        alignment2: Alignment,
        crossover: Crossover,
        elevation: float = 0.0,
        dxf_path: str | Path | None = None,
        html_path: str | Path | None = None,
        *,
        scene: Scene3D | None = None,
    ) -> Scene3D:
        """기존 Scene3D를 전달하면 크로스오버를 그 장면에 합성한다."""
        geometry = CrossoverGeometryCalculator.calculate(crossover, alignment1, alignment2)
        rendered = Crossover3DRenderer.render_3d(Scene3D() if scene is None else scene, geometry, elevation)
        if dxf_path is not None:
            Dxf3DWriter(rendered).write(dxf_path)
        if html_path is not None:
            Json3DExporter.export_to_html(rendered, html_path, title=f"Crossover 3D — {crossover.name}")
        return rendered

    @classmethod
    def preview_full(
        cls,
        alignment1: Alignment,
        alignment2: Alignment,
        crossover: Crossover,
        base_dxf: str | Path = "crossover_3d.dxf",
        base_html: str | Path = "crossover_3d.html",
        *,
        elevation: float = 0.0,
    ) -> Scene3D:
        """같은 Scene3D를 DXF와 HTML로 저장한다."""
        return cls.preview(alignment1, alignment2, crossover, elevation, dxf_path=base_dxf, html_path=base_html)
