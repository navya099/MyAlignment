from pathlib import Path
import shutil
import subprocess

from myalignment.export.dxf_writer import DxfWriter
from myalignment.export.svg_style import SvgStyle
from myalignment.export.svg_writer import SvgWriter
from myalignment.render.scene import Scene


class SheetExporter:
    """도면 좌표와 용지 크기를 유지하여 SVG, PDF 또는 DXF로 출력한다."""

    @staticmethod
    def _svg(scene: Scene, width_mm: float | None, height_mm: float | None) -> SvgWriter:
        width = scene.metadata.get("sheet_width_mm", 841) if width_mm is None else width_mm
        height = scene.metadata.get("sheet_height_mm", 594) if height_mm is None else height_mm
        return SvgWriter(scene, SvgStyle(
            page_width_mm=width, page_height_mm=height, margin_mm=0, auto_fit_viewport=False,
        ))

    @classmethod
    def export_svg(
        cls, scene: Scene, path: str | Path, width_mm: float | None = None, height_mm: float | None = None,
    ) -> None:
        cls._svg(scene, width_mm, height_mm).write(path)

    @classmethod
    def export_pdf(
        cls, scene: Scene, path: str | Path, width_mm: float | None = None, height_mm: float | None = None,
    ) -> None:
        """CairoSVG 또는 Inkscape를 사용해 시트 실측 크기의 PDF를 출력한다."""
        data = cls._svg(scene, width_mm, height_mm).to_string().encode("utf-8")
        try:
            from cairosvg import svg2pdf
        except ImportError:
            inkscape = shutil.which("inkscape")
            if inkscape is None:
                raise RuntimeError("PDF export requires CairoSVG or Inkscape") from None
            result = subprocess.run(
                [inkscape, "--pipe", "--export-type=pdf", f"--export-filename={Path(path).resolve()}"],
                input=data, capture_output=True, check=False,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
        else:
            svg2pdf(bytestring=data, write_to=str(path))

    @staticmethod
    def export_dxf(scene: Scene, path: str | Path) -> None:
        """종이 mm 좌표로 평탄화한 2D DXF R12 모델 공간 도면을 쓴다."""
        DxfWriter(scene).write(path)
