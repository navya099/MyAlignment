from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

from myalignment.render.link_surface_3d_renderer import LinkSurface3DRenderer
from myalignment.render.scene_3d import Scene3D

if TYPE_CHECKING:
    from myalignment.assembly.codes import LinkCode
    from myalignment.corridor.link_surface_manager import LinkSurfaceManager


@dataclass(frozen=True, slots=True)
class LinkSurface3DScene:
    """단일 링크 코드별 3D 장면의 불변 모음."""

    scenes_by_code: Mapping[LinkCode, Scene3D] = field(default_factory=dict)
    manager: LinkSurfaceManager | None = None

    def __post_init__(self):
        object.__setattr__(self, "scenes_by_code", MappingProxyType(dict(self.scenes_by_code)))

    @classmethod
    def from_manager(
        cls,
        manager: LinkSurfaceManager,
        show_mesh: bool = True,
        show_wireframe: bool = False,
        z_scale: float = 1.0,
        *,
        opacity: float = 0.8,
    ) -> LinkSurface3DScene:
        """코드별 장면을 만든다."""
        scenes = LinkSurface3DRenderer.render_individual(
            manager, show_mesh, show_wireframe, z_scale=z_scale, opacity=opacity,
        )
        return cls(scenes, manager)

    def get_scene(self, code: LinkCode) -> Scene3D | None:
        return self.scenes_by_code.get(code)

    def merge_all(self) -> Scene3D:
        """모든 단일 코드 장면을 합성한다."""
        return self.merge_selected(self.available_codes())

    def merge_selected(self, codes: Sequence[LinkCode]) -> Scene3D:
        """선택한 코드의 장면과 레이어 범례를 합성한다."""
        primitives = []
        legend = {}
        for code in dict.fromkeys(codes):
            scene = self.get_scene(code)
            if scene is not None:
                primitives.extend(scene.primitives)
                legend.update(scene.metadata.get("link_surfaces", {}))
        return Scene3D(tuple(primitives), {"link_surfaces": legend} if legend else {})

    def available_codes(self) -> list[LinkCode]:
        return list(self.scenes_by_code)

    def __len__(self) -> int:
        return len(self.scenes_by_code)
