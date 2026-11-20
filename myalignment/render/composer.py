from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.render.profile_renderer import ProfileRenderer
from myalignment.render.scene import Scene
from myalignment.render.surface_renderer import TinSurfaceRenderer

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment


@dataclass(frozen=True, slots=True)
class RenderOptions:
    render_alignment: bool = True
    render_profiles: bool = True
    render_surfaces: bool = True
    alignment_sample_step: float = 1.0
    profile_sample_step: float = 5.0
    vertical_exaggeration: float = 10.0


class SceneComposer:
    """평면 선형, 종단과 코리더 표면을 레이어별로 합성한다."""

    @classmethod
    def compose_alignment(
        cls, alignment: Alignment, options: RenderOptions | None = None, *,
        scene: Scene | None = None,
    ) -> Scene:
        options = options or RenderOptions()
        scene = Scene() if scene is None else scene
        if options.render_alignment:
            scene = AlignmentRenderer.render_plan(alignment, scene, options.alignment_sample_step)
        if options.render_profiles:
            for profile in alignment.profiles:
                scene = ProfileRenderer.render(
                    profile, scene, options.profile_sample_step, options.vertical_exaggeration,
                )
        if options.render_surfaces:
            for corridor in alignment.corridors:
                for surface in corridor.surfaces:
                    scene = TinSurfaceRenderer.render(surface, scene)
        return scene

    @classmethod
    def compose_multiple(
        cls, alignments: Iterable[Alignment], options: RenderOptions | None = None,
    ) -> Scene:
        scene = Scene()
        names = []
        for alignment in alignments:
            scene = cls.compose_alignment(alignment, options, scene=scene)
            names.append(alignment.name)
        return replace(scene, metadata={**scene.metadata, "alignment_names": tuple(names)})
