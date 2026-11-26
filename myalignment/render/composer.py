from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.render.profile_renderer import ProfileRenderer
from myalignment.render.scene import Scene
from myalignment.render.stagger_config import StaggerConfig
from myalignment.render.staggered_renderer import StaggeredRenderer
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
    render_alignment_labels: bool = False
    stagger_config: StaggerConfig | None = None


class SceneComposer:
    """평면 선형, 종단과 코리더 표면을 레이어별로 합성한다."""

    @classmethod
    def compose_alignment(
        cls, alignment: Alignment, options: RenderOptions | None = None, *,
        scene: Scene | None = None,
        reference_alignments: Mapping[str, Alignment] | None = None,
        reference_points: Mapping[str, Point2d] | None = None,
    ) -> Scene:
        options = options or RenderOptions()
        scene = Scene() if scene is None else scene
        if options.render_alignment:
            scene = AlignmentRenderer.render_plan(
                alignment, scene, options.alignment_sample_step,
                render_labels=options.render_alignment_labels,
                reference_alignments=reference_alignments, reference_points=reference_points,
            )
        if options.render_profiles:
            for profile in alignment.profiles:
                scene = ProfileRenderer.render(
                    profile, scene, options.profile_sample_step, options.vertical_exaggeration,
                )
        if options.render_surfaces:
            for corridor in alignment.corridors:
                for surface in corridor.surfaces:
                    scene = TinSurfaceRenderer.render(surface, scene)
        config = options.stagger_config
        return StaggeredRenderer.apply_stagger(scene, config) if config is not None else scene

    @classmethod
    def compose_multiple(
        cls, alignments: Iterable[Alignment], options: RenderOptions | None = None, *,
        reference_points: Mapping[str, Point2d] | None = None,
    ) -> Scene:
        scene = Scene()
        alignments = tuple(alignments)
        names = tuple(alignment.name for alignment in alignments)
        counts = Counter(names)
        references = {alignment.name: alignment for alignment in alignments if counts[alignment.name] == 1}
        options = options or RenderOptions()
        per_alignment_options = replace(options, stagger_config=None)
        for alignment in alignments:
            scene = cls.compose_alignment(
                alignment, per_alignment_options, scene=scene,
                reference_alignments=references, reference_points=reference_points,
            )
        scene = replace(scene, metadata={**scene.metadata, "alignment_names": names})
        config = options.stagger_config
        return StaggeredRenderer.apply_stagger(scene, config) if config is not None else scene
