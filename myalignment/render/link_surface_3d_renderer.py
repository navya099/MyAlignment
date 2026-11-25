from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
import math
from pathlib import Path
import re
from typing import TYPE_CHECKING

from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.render.link_surface_renderer import LinkSurfaceRenderer
from myalignment.render.primitives_3d import Style3D
from myalignment.render.scene_3d import Scene3D
from myalignment.render.tin_surface_3d_renderer import TinSurface3DRenderer

if TYPE_CHECKING:
    from myalignment.assembly.codes import LinkCode
    from myalignment.corridor.link_surface_manager import LinkSurfaceManager


class LinkSurface3DRenderer:
    """코리더 링크별 TIN을 3D 메쉬와 와이어프레임으로 배치한다."""

    LINK_COLORS = LinkSurfaceRenderer.LINK_COLORS

    @classmethod
    def render_3d(
        cls,
        scene: Scene3D,
        manager: LinkSurfaceManager,
        show_mesh: bool = True,
        show_wireframe: bool = False,
        z_scale: float = 1.0,
        opacity: float = 0.8,
        *,
        z_offset_per_link: float = 0.0,
    ) -> Scene3D:
        """표면을 장면에 추가한다. 정점 표고는 z_scale과 순서별 Z 간격을 적용한다."""
        if not math.isfinite(z_scale) or z_scale <= 0 or not math.isfinite(z_offset_per_link):
            raise ValueError("z_scale must be positive and both Z settings must be finite")
        if not math.isfinite(opacity) or not 0 <= opacity <= 1:
            raise ValueError("opacity must be between 0 and 1")

        used_layers = {item.style.layer.casefold() for item in scene.primitives}
        legend = dict(scene.metadata.get("link_surfaces", {}))
        primitives = []
        for index, result in enumerate(manager):
            surface = result.surface
            code = result.link_code
            token = re.sub(r"[^\w-]+", "-", code.value if code is not None else surface.name).strip("-")
            base = f"C-CORRIDOR-{token.upper() or 'CUSTOM'}"
            layer, suffix = base, 2
            while {layer.casefold(), f"{layer}-WIRE".casefold()} & used_layers:
                layer = f"{base}-{suffix}"
                suffix += 1
            wire_layer = f"{layer}-WIRE"
            used_layers.update((layer.casefold(), wire_layer.casefold()))
            color = cls.LINK_COLORS.get(code, 7) if result.color is None else result.color
            rendered = TinSurface3DRenderer.render(
                surface, show_mesh=show_mesh, show_wireframe=show_wireframe,
                mesh_style=Style3D(color=color, layer=layer, lineweight=0.3, opacity=opacity),
                wire_style=Style3D(color=color, layer=wire_layer, lineweight=0.15),
                z_scale=z_scale, z_offset=index * z_offset_per_link,
            )
            primitives.extend(rendered.primitives)
            if rendered.primitives:
                entry = {"name": surface.name, "area_2d": surface.area_2d, "code": code.value if code else None}
                if show_mesh:
                    legend[layer] = entry
                if show_wireframe:
                    legend[wire_layer] = {**entry, "name": f"{surface.name} (Wire)"}
        if not primitives:
            return scene
        return replace(
            scene.add_all(primitives),
            metadata={**scene.metadata, "link_surfaces": legend},
        )

    @classmethod
    def render_individual(
        cls,
        manager: LinkSurfaceManager,
        show_mesh: bool = True,
        show_wireframe: bool = False,
        *,
        z_scale: float = 1.0,
        opacity: float = 0.8,
    ) -> dict[LinkCode, Scene3D]:
        """단일 코드 결과를 코드별 장면에 모은다. 같은 코드의 여러 표면도 포함한다."""
        grouped = defaultdict(list)
        for result in manager:
            if result.link_code is not None:
                grouped[result.link_code].append(result)
        return {
            code: cls.render_3d(
                Scene3D(), replace(manager, surfaces=tuple(results)), show_mesh, show_wireframe, z_scale, opacity,
            )
            for code, results in grouped.items()
        }

    @classmethod
    def render_combined_flat(
        cls,
        manager: LinkSurfaceManager,
        z_offset_per_link: float = 0.0,
        show_mesh: bool = True,
        show_wireframe: bool = False,
        z_scale: float = 1.0,
        *,
        opacity: float = 0.8,
    ) -> Scene3D:
        """표면 순서에 따라 Z 간격을 주어 각 층을 분리해서 표시한다."""
        return cls.render_3d(
            Scene3D(), manager, show_mesh, show_wireframe, z_scale, opacity,
            z_offset_per_link=z_offset_per_link,
        )


class LinkSurface3DPreview:
    """통합 또는 Z 간격을 둔 링크 표면의 미리보기와 도면을 저장한다."""

    @classmethod
    def preview_combined(
        cls,
        manager: LinkSurfaceManager,
        html_path: str | Path | None,
        dxf_path: str | Path | None = None,
        show_mesh: bool = True,
        show_wireframe: bool = True,
        *,
        z_scale: float = 1.0,
        opacity: float = 0.8,
        three_module_base: str | None = None,
    ) -> Scene3D:
        """메쉬와 와이어프레임을 합성하고 선택한 파일 형식으로 저장한다."""
        scene = LinkSurface3DRenderer.render_3d(Scene3D(), manager, show_mesh, show_wireframe, z_scale, opacity)
        if dxf_path is not None:
            Dxf3DWriter(scene).write(dxf_path)
        if html_path is not None:
            cls._export_html(scene, html_path, "Link Surfaces 3D", three_module_base)
        return scene

    @classmethod
    def preview_flat(
        cls,
        manager: LinkSurfaceManager,
        html_path: str | Path,
        z_offset_per_link: float = 5.0,
        *,
        z_scale: float = 1.0,
        opacity: float = 0.8,
        three_module_base: str | None = None,
    ) -> Scene3D:
        """표면에 Z 간격을 적용하고 HTML에 저장한다."""
        scene = LinkSurface3DRenderer.render_combined_flat(
            manager, z_offset_per_link, z_scale=z_scale, opacity=opacity,
        )
        cls._export_html(scene, html_path, "Link Surfaces 3D — Z Offset", three_module_base)
        return scene

    @staticmethod
    def _export_html(scene, path, title, three_module_base):
        options = {} if three_module_base is None else {"three_module_base": three_module_base}
        Json3DExporter.export_to_html(scene, path, title, **options)
