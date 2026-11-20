from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from myalignment.corridor.surface_builder import CorridorSurfaceSpec
from myalignment.corridor.surface_code import CorridorSurfaceCode
from myalignment.render.scene_3d import Scene3D
from myalignment.render.tin_surface_3d_renderer import TinSurface3DRenderer

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.profile.profile import Profile


class CorridorSurface3DRenderer:
    @classmethod
    def render(
        cls, corridor: Corridor, surface_code: CorridorSurfaceCode = CorridorSurfaceCode.TOP,
        show_mesh: bool = True, show_wireframe: bool = False, *,
        alignments: Mapping[str, Alignment] | None = None,
        profiles: Mapping[str, Profile] | None = None,
    ) -> Scene3D:
        """저장된 기본 이름의 표면을 쓰거나 제공된 기준선으로 추출한다."""
        surface = corridor.surfaces.get(f"{corridor.name}_{surface_code.value}")
        if surface is None:
            if alignments is None:
                raise ValueError("alignments are required to extract a missing corridor surface")
            surface = corridor.build_surface(
                CorridorSurfaceSpec(code=surface_code), alignments=alignments, profiles=profiles,
            )
        return TinSurface3DRenderer.render(surface, show_wireframe=show_wireframe, show_mesh=show_mesh)
