from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.crossover_2d_renderer import Crossover2DRenderer
from myalignment.render.scene import Scene
from myalignment.turnout.crossover_calculator import CrossoverGeometryCalculator

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.turnout.crossover import Crossover


class Crossover2DPreview:
    """크로스오버 평면도를 만들고 선택적으로 DXF로 저장한다."""

    @classmethod
    def preview(
        cls,
        alignment1: Alignment,
        alignment2: Alignment,
        crossover: Crossover,
        dxf_path: str | Path | None = None,
        *,
        scene: Scene | None = None,
    ) -> Scene:
        """기존 Scene이 주어지면 평면도를 그 Scene에 추가한다."""
        geometry = CrossoverGeometryCalculator.calculate(crossover, alignment1, alignment2)
        plan = Crossover2DRenderer.render_2d(
            Scene() if scene is None else scene, geometry, crossover_name=crossover.name,
        )
        if dxf_path is not None:
            DxfWriter(plan).write(dxf_path)
        return plan
