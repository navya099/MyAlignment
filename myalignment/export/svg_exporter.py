from pathlib import Path

from myalignment.export.svg_style import SvgStyle
from myalignment.export.svg_writer import SvgWriter
from myalignment.render.scene import Scene


class SvgExporter:
    """Scene을 선택한 스타일의 SVG 파일로 내보낸다."""

    @staticmethod
    def export(scene: Scene, path: str | Path, style: SvgStyle | None = None) -> None:
        SvgWriter(scene, style).write(path)

    @classmethod
    def export_web(cls, scene: Scene, path: str | Path) -> None:
        cls.export(scene, path, SvgStyle.web())

    @classmethod
    def export_print(cls, scene: Scene, path: str | Path) -> None:
        cls.export(scene, path, SvgStyle.print())

    @classmethod
    def export_dark(cls, scene: Scene, path: str | Path) -> None:
        cls.export(scene, path, SvgStyle.dark())
