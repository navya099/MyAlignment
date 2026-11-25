from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.render.link_surface_3d_renderer import LinkSurface3DPreview, LinkSurface3DRenderer

if TYPE_CHECKING:
    from myalignment.corridor.link_surface_manager import LinkSurfaceManager


class LinkSurface3DExport:
    """통합 DXF·HTML과 단일 코드별 DXF를 일괄 저장한다."""

    @classmethod
    def export_all(
        cls, manager: LinkSurfaceManager, output_dir: str | Path = ".", prefix: str = "link_surfaces",
    ) -> dict[str, str]:
        """출력한 파일의 경로를 형식과 링크 코드로 조회할 수 있게 반환한다."""
        if not prefix or prefix in {".", ".."} or "/" in prefix or "\\" in prefix:
            raise ValueError("prefix must be a filename prefix")
        folder = Path(output_dir)
        folder.mkdir(parents=True, exist_ok=True)
        dxf = folder / f"{prefix}_all.dxf"
        html = folder / f"{prefix}_all.html"
        LinkSurface3DPreview.preview_combined(manager, html, dxf)
        outputs = {"dxf_combined": str(dxf), "html_combined": str(html)}
        for code, scene in LinkSurface3DRenderer.render_individual(manager).items():
            token = code.value.lower()
            path = folder / f"{prefix}_{token}.dxf"
            Dxf3DWriter(scene).write(path)
            outputs[f"dxf_{token}"] = str(path)
        return outputs
