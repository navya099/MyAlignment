from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.export.dxf_writer import DxfWriter
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.render.scene import Scene
from myalignment.render.scene_3d import Scene3D
from myalignment.render.turnout_3d_renderer import Turnout3DRenderer
from myalignment.render.turnout_renderer import TurnoutRenderer
from myalignment.turnout.geometry import TurnoutGeometryCalculator

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.turnout.turnout import Turnout


class TurnoutPreview:
    """턴아웃 Scene을 만들고 선택적으로 DXF와 3D HTML을 저장한다."""

    @classmethod
    def preview_2d(
        cls, alignment: Alignment, turnout: Turnout, dxf_path: str | Path | None = None,
    ) -> Scene:
        """단일 턴아웃의 2D 평면도와 선택적인 DXF를 생성한다."""
        geometry = TurnoutGeometryCalculator.calculate(alignment, turnout)
        scene = TurnoutRenderer.render_2d(Scene(), geometry, turnout_name=turnout.name)
        if dxf_path is not None:
            DxfWriter(scene).write(dxf_path)
        return scene

    @classmethod
    def preview_3d(
        cls,
        alignment: Alignment,
        turnouts: Sequence[Turnout],
        elevation: float = 0.0,
        dxf_path: str | Path | None = None,
        html_path: str | Path | None = None,
    ) -> Scene3D:
        """여러 턴아웃을 기준 표고에 배치하고 선택한 형식으로 저장한다."""
        scene = Turnout3DRenderer.render_turnout_set_3d(Scene3D(), turnouts, alignment, elevation)
        if dxf_path is not None:
            Dxf3DWriter(scene).write(dxf_path)
        if html_path is not None:
            Json3DExporter.export_to_html(scene, html_path, title=f"Turnout 3D ({len(turnouts)})")
        return scene

    @classmethod
    def preview_full(
        cls,
        alignment: Alignment,
        turnout: Turnout,
        base_dxf: str | Path = "turnout_2d.dxf",
        base_html_3d: str | Path = "turnout_3d.html",
    ) -> tuple[Scene, Scene3D]:
        """같은 기하를 2D DXF와 3D HTML로 동시에 저장한다."""
        geometry = TurnoutGeometryCalculator.calculate(alignment, turnout)
        plan = TurnoutRenderer.render_2d(Scene(), geometry, turnout_name=turnout.name)
        spatial = Turnout3DRenderer.render_3d(Scene3D(), geometry)
        DxfWriter(plan).write(base_dxf)
        Json3DExporter.export_to_html(spatial, base_html_3d, title="Turnout 3D (1)")
        return plan, spatial
