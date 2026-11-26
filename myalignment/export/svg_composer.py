from collections.abc import Mapping
from pathlib import Path
import re

from myalignment.export.svg_exporter import SvgExporter
from myalignment.export.svg_style import SvgStyle
from myalignment.render.scene import Scene


class SvgExportComposer:
    """이름이 지정된 여러 2D 장면을 SVG 파일로 저장한다."""

    @staticmethod
    def export_all(
        scenes: Mapping[str, Scene], output_dir: str | Path = ".", styles: Mapping[str, SvgStyle] | None = None,
    ) -> dict[str, str]:
        """장면 이름별 출력 경로를 반환한다."""
        directory = Path(output_dir)
        style_by_name = styles or {}
        outputs = {}
        used = set()
        for name in scenes:
            if not name.strip() or name in (".", "..") or any(char in name for char in '/\\\x00'):
                raise ValueError(f"Invalid SVG filename stem: {name!r}")
            style = style_by_name.get(name)
            filename = name
            if style is not None:
                background = re.sub(r"[^\w-]+", "-", style.background_color.lstrip("#")).strip("-")
                filename += "_" + (background or "style")
            path = directory / f"{filename}.svg"
            if path.name.casefold() in used:
                raise ValueError(f"Duplicate SVG output filename: {path.name}")
            used.add(path.name.casefold())
            outputs[name] = str(path)

        directory.mkdir(parents=True, exist_ok=True)
        for name, scene in scenes.items():
            SvgExporter.export(scene, outputs[name], style_by_name.get(name))
        return outputs
