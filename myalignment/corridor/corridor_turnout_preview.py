from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.render.corridor_turnout_3d_renderer import CorridorTurnout3DRenderer
from myalignment.render.scene_3d import Scene3D

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.turnout.crossover import Crossover
    from myalignment.turnout.turnout import Turnout


class CorridorTurnoutPreview:
    """통합 3D 장면을 만들고 선택적으로 DXF와 HTML에 저장한다."""

    @classmethod
    def preview_3d(
        cls,
        main_alignment: Alignment,
        branch_alignment: Alignment,
        corridor: Corridor,
        turnouts: Sequence[Turnout] | None = None,
        crossovers: Sequence[Crossover] | None = None,
        elevation: float = 0.0,
        dxf_path: str | Path | None = None,
        html_path: str | Path | None = None,
        *,
        rail_elevation: float = 0.15,
        sample_frequency: float | None = 5.0,
    ) -> Scene3D:
        """양쪽 코리더와 분기 장치를 합성하고 지정한 형식으로 저장한다."""
        scene = CorridorTurnout3DRenderer.render(
            main_alignment, branch_alignment, corridor, turnouts, crossovers,
            elevation, rail_elevation, sample_frequency,
        )
        if dxf_path is not None:
            Dxf3DWriter(scene).write(dxf_path)
        if html_path is not None:
            Json3DExporter.export_to_html(scene, html_path, title=f"Corridor + Turnout 3D — {corridor.name}")
        return scene

    @classmethod
    def preview_full(
        cls,
        main_alignment: Alignment,
        branch_alignment: Alignment,
        corridor: Corridor,
        turnouts: Sequence[Turnout] | None = None,
        base_dxf: str | Path = "corridor_turnout_3d.dxf",
        base_html: str | Path = "corridor_turnout_3d.html",
        *,
        crossovers: Sequence[Crossover] | None = None,
        elevation: float = 0.0,
    ) -> Scene3D:
        """같은 통합 장면을 DXF와 HTML로 저장한다."""
        return cls.preview_3d(
            main_alignment, branch_alignment, corridor, turnouts, crossovers, elevation,
            dxf_path=base_dxf, html_path=base_html,
        )
