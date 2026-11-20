from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from myalignment.corridor.corridor_3d_renderer import Corridor3DRenderer
from myalignment.corridor.surface_code import CorridorSurfaceCode
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.render.corridor_surface_3d import CorridorSurface3DRenderer

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.profile.profile import Profile


class Corridor3DPreview:
    """코리더 렌더링부터 브라우저 미리보기 파일 저장까지 수행한다."""

    @staticmethod
    def wireframe(
        corridor: Corridor, alignment: Alignment, html_path: str | Path, sample_frequency: float = 20.0,
        *, profile: Profile | None = None, three_module_base: str | None = None,
    ) -> None:
        scene = Corridor3DRenderer.render_wireframe(corridor, alignment, sample_frequency, profile=profile)
        _save(scene, html_path, f"3D Wireframe — {corridor.name}", three_module_base)

    @staticmethod
    def mesh(
        corridor: Corridor, alignment: Alignment, html_path: str | Path, sample_frequency: float = 20.0,
        *, profile: Profile | None = None, three_module_base: str | None = None,
    ) -> None:
        scene = Corridor3DRenderer.render_mesh(corridor, alignment, sample_frequency, profile=profile)
        _save(scene, html_path, f"3D Mesh — {corridor.name}", three_module_base)

    @staticmethod
    def surface(
        corridor: Corridor, html_path: str | Path, surface_code: CorridorSurfaceCode | None = None, *,
        alignments: Mapping[str, Alignment] | None = None, profiles: Mapping[str, Profile] | None = None,
        three_module_base: str | None = None,
    ) -> None:
        code = surface_code or CorridorSurfaceCode.TOP
        scene = CorridorSurface3DRenderer.render(corridor, code, alignments=alignments, profiles=profiles)
        _save(scene, html_path, f"3D Surface — {corridor.name} ({code.value})", three_module_base)

    @staticmethod
    def combined(
        corridor: Corridor, alignment: Alignment, html_path: str | Path, sample_frequency: float = 20.0,
        *, profile: Profile | None = None, three_module_base: str | None = None,
    ) -> None:
        wireframe = Corridor3DRenderer.render_wireframe(corridor, alignment, sample_frequency, profile=profile)
        profiles = {candidate.name: candidate for candidate in alignment.profiles}
        if profile is not None:
            profiles.update((baseline.profile_name, profile) for baseline in corridor.baselines
                            if baseline.alignment_name == alignment.name and baseline.profile_name)
        surface = CorridorSurface3DRenderer.render(
            corridor, alignments={alignment.name: alignment}, profiles=profiles,
        )
        _save(
            wireframe.add_all(surface.primitives), html_path, f"3D Combined — {corridor.name}", three_module_base,
        )


def _save(scene, path, title, three_module_base):
    options = {} if three_module_base is None else {"three_module_base": three_module_base}
    Json3DExporter.export_to_html(scene, path, title, **options)
