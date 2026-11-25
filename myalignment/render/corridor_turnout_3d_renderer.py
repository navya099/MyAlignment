from __future__ import annotations

from collections.abc import Sequence
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.corridor.corridor_3d_renderer import Corridor3DRenderer
from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.render.crossover_2d_renderer import Crossover2DRenderer
from myalignment.render.crossover_3d_renderer import Crossover3DRenderer
from myalignment.render.scene import Scene
from myalignment.render.scene_3d import Scene3D
from myalignment.render.turnout_3d_renderer import Turnout3DRenderer
from myalignment.render.turnout_renderer import TurnoutRenderer
from myalignment.turnout.crossover_calculator import CrossoverGeometryCalculator
from myalignment.turnout.geometry import TurnoutGeometryCalculator

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.turnout.crossover import Crossover
    from myalignment.turnout.turnout import Turnout


def _source(alignments, name):
    if name not in alignments:
        raise ValueError(f"Missing alignment: {name}")
    return alignments[name]


def _grade(corridor, alignment, station):
    profiles = {
        baseline.profile_name for baseline in corridor.baselines
        if baseline.alignment_name == alignment.name
        and baseline.start_station - 1e-8 <= station <= baseline.end_station + 1e-8
    }
    if not profiles or profiles == {""}:
        return 0.0
    if len(profiles) != 1:
        raise ValueError(f"{alignment.name} STA {station}: ambiguous corridor profiles")
    name = profiles.pop()
    profile = next((item for item in alignment.profiles if item.name == name), None)
    if profile is None:
        raise ValueError(f"Missing profile: {name}")
    # Use the exact endpoint when projection introduced roundoff.
    if profile.start_station - 1e-8 <= station < profile.start_station:
        station = profile.start_station
    elif profile.end_station < station <= profile.end_station + 1e-8:
        station = profile.end_station
    return profile.elevation_at(station)


def _midpoints(rails):
    return tuple(Point2d(a.x / 2 + b.x / 2, a.y / 2 + b.y / 2) for a, b in zip(*rails, strict=True))


def _profile_levels(corridor, alignment, rails, height):
    return tuple(
        _grade(corridor, alignment, alignment.project(point).station) - height
        for point in _midpoints(rails)
    )


def _connector_levels(rails, start_level, end_level, azimuth, height, marker=None):
    centers = _midpoints(rails)
    start, end = centers[0], centers[-1]
    ux, uy = math.cos(azimuth), math.sin(azimuth)
    length = (end.x - start.x) * ux + (end.y - start.y) * uy

    def level(point):
        distance = (point.x - start.x) * ux + (point.y - start.y) * uy
        fraction = max(0.0, min(1.0, distance / length)) if length > 0 else 0.0
        return start_level + (end_level - start_level) * fraction

    return tuple(level(point) - height for point in centers), level(marker) if marker is not None else 0.0


class CorridorTurnout3DRenderer:
    """본선과 분기선 코리더, 턴아웃 및 크로스오버를 한 장면에 합성한다."""

    @classmethod
    def render(
        cls,
        main_alignment: Alignment,
        branch_alignment: Alignment,
        corridor: Corridor,
        turnouts: Sequence[Turnout] | None = None,
        crossovers: Sequence[Crossover] | None = None,
        elevation: float = 0.0,
        rail_elevation: float = 0.15,
        sample_frequency: float | None = 5.0,
    ) -> Scene3D:
        """코리더 종단에 레일 상단을 맞추고 elevation만큼 장면을 이동한다.

        연결 레일은 접속하는 종단 표고 사이를 평면 종방향 거리로 보간한다.
        침목 단면 및 분기 경로의 캔트는 이 보간에 포함하지 않는다.
        """
        if main_alignment.name == branch_alignment.name:
            raise ValueError("main and branch alignment names must differ")
        alignments = {main_alignment.name: main_alignment, branch_alignment.name: branch_alignment}
        for region in corridor.regions:
            baseline = corridor.baseline_for_region(region)
            if baseline is not None:
                _source(alignments, baseline.alignment_name)

        scene = Corridor3DRenderer.render_wireframe(corridor, main_alignment, sample_frequency, elevation)
        if corridor.baselines:
            branch = Corridor3DRenderer.render_wireframe(corridor, branch_alignment, sample_frequency, elevation)
            scene = scene.add_all(branch.primitives)

        for turnout in turnouts or ():
            source = _source(alignments, turnout.source_alignment_name)
            geometry = TurnoutGeometryCalculator.calculate(source, turnout, extension=0)
            if not geometry.is_valid:
                raise ValueError(f"{turnout.name}: {geometry.error_message}")
            ps = _grade(corridor, source, geometry.ps_station)
            pf = _grade(corridor, source, geometry.pf_station)
            pc = pf
            target = alignments.get(turnout.branch_alignment_name)
            if target is not None and target.is_valid:
                projected = target.project(geometry.pc_point)
                if projected.distance <= 1e-6:
                    pc = _grade(corridor, target, projected.station)

            main_levels = _profile_levels(
                corridor, source, (geometry.main_left_rail, geometry.main_right_rail), rail_elevation,
            )
            branch_levels, _ = _connector_levels(
                (geometry.branch_left_rail, geometry.branch_right_rail), ps, pc, geometry.ps_azimuth, rail_elevation,
            )
            scene = Turnout3DRenderer.render_3d(
                scene, geometry, elevation, rail_elevation,
                track_levels=(main_levels, branch_levels), marker_levels=(ps, pf, pc),
            )

        for crossover in crossovers or ():
            first = _source(alignments, crossover.source_alignment1_name)
            second = _source(alignments, crossover.source_alignment2_name)
            geometry = CrossoverGeometryCalculator.calculate(crossover, first, second, extension=0)
            if not geometry.is_valid:
                raise ValueError(f"{crossover.name}: {geometry.error_message}")

            levels = [
                _profile_levels(corridor, first, (geometry.main1_left_rail, geometry.main1_right_rail), rail_elevation),
                _profile_levels(corridor, second, (geometry.main2_left_rail, geometry.main2_right_rail), rail_elevation),
            ]
            # Turnout and path order is (first, second), then (second, first) for DOUBLE.
            sources = (first, second, second, first)
            marker_levels = tuple(
                _grade(corridor, sources[index // 3], station) if station is not None else 0.0
                for index, (_, _, station) in enumerate(geometry.turnout_markers)
            )
            diamond_levels = []
            for index, (rails, path) in enumerate(zip(geometry.connecting_rails, geometry.paths, strict=True)):
                path_levels, at_diamond = _connector_levels(
                    rails, marker_levels[index * 6], marker_levels[index * 6 + 3],
                    path.first.azimuth, rail_elevation, geometry.diamond_center,
                )
                levels.append(path_levels)
                diamond_levels.append(at_diamond)
            scene = Crossover3DRenderer.render_3d(
                scene, geometry, elevation, rail_elevation=rail_elevation,
                track_levels=levels, marker_levels=marker_levels,
                diamond_level=sum(diamond_levels) / len(diamond_levels),
            )
        return scene

    @classmethod
    def render_2d(
        cls,
        main_alignment: Alignment,
        corridor: Corridor,
        turnouts: Sequence[Turnout] | None = None,
        crossovers: Sequence[Crossover] | None = None,
        sample_frequency: float = 5.0,
        *,
        branch_alignment: Alignment | None = None,
    ) -> Scene:
        """코리더 기준선과 턴아웃, 크로스오버를 평면도에 합성한다."""
        alignments = {main_alignment.name: main_alignment}
        if branch_alignment is not None:
            if branch_alignment.name == main_alignment.name:
                raise ValueError("main and branch alignment names must differ")
            alignments[branch_alignment.name] = branch_alignment
        names = tuple(dict.fromkeys(baseline.alignment_name for baseline in corridor.baselines))
        scene = Scene()
        for name in names or (main_alignment.name,):
            scene = AlignmentRenderer.render_plan(_source(alignments, name), scene, sample_frequency)
        for turnout in turnouts or ():
            alignment = _source(alignments, turnout.source_alignment_name)
            geometry = TurnoutGeometryCalculator.calculate(alignment, turnout)
            scene = TurnoutRenderer.render_2d(scene, geometry, turnout.name)
        for crossover in crossovers or ():
            first = _source(alignments, crossover.source_alignment1_name)
            second = _source(alignments, crossover.source_alignment2_name)
            geometry = CrossoverGeometryCalculator.calculate(crossover, first, second)
            scene = Crossover2DRenderer.render_2d(scene, geometry, crossover.name)
        return scene
