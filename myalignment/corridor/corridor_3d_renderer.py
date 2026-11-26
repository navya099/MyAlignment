from __future__ import annotations

from collections import defaultdict
import math
from typing import TYPE_CHECKING

from myalignment.corridor.corridor_mesh import CorridorMesh, check_section_topology
from myalignment.corridor.cross_section_3d import CrossSection3D
from myalignment.render.primitives_3d import Primitive3D, Style3D
from myalignment.render.scene_3d import Scene3D

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.profile.profile import Profile


class Corridor3DRenderer:
    """코리더 영역별 횡단, 종방향 와이어 또는 삼각형 메쉬."""

    LINK_COLORS = {
        "Pavement": 1, "Pavement_Top": 1, "Pavement_Bottom": 1, "Pavement_Side": 1,
        "Shoulder": 3, "Slope": 5, "Ditch": 6, "Top": 7, "Datum": 8,
    }

    @classmethod
    def render_wireframe(
        cls, corridor: Corridor, alignment: Alignment, sample_frequency: float | None = None,
        offset_elevation: float = 0.0, *, profile: Profile | None = None,
    ) -> Scene3D:
        primitives = []
        longitudinal = Style3D(color=8, lineweight=0.15, layer="C-CORRIDOR-LONGITUDINAL")
        for sections in _sections(corridor, alignment, sample_frequency, offset_elevation, profile):
            primitives.extend(cls._cross_links(sections))
            for first, second in zip(sections, sections[1:]):
                check_section_topology(first, second)
                primitives.extend(Primitive3D.line(a, b, longitudinal) for a, b in zip(first.points, second.points))
        return Scene3D(tuple(primitives))

    @classmethod
    def render_sections_only(
        cls, corridor: Corridor, alignment: Alignment, sample_frequency: float | None = None,
        offset_elevation: float = 0.0, *, profile: Profile | None = None,
    ) -> Scene3D:
        return Scene3D(tuple(
            primitive
            for sections in _sections(corridor, alignment, sample_frequency, offset_elevation, profile)
            for primitive in cls._cross_links(sections)
        ))

    @classmethod
    def render_mesh(
        cls, corridor: Corridor, alignment: Alignment, sample_frequency: float | None = None,
        offset_elevation: float = 0.0, *, profile: Profile | None = None,
    ) -> Scene3D:
        primitives = []
        for sections in _sections(corridor, alignment, sample_frequency, offset_elevation, profile):
            mesh = CorridorMesh.from_sections(sections)
            groups = defaultdict(list)
            for triangle, code in zip(mesh.triangles, mesh.face_codes):
                groups[cls.LINK_COLORS.get(getattr(code, "value", ""), 7)].append(triangle)
            for color, faces in groups.items():
                primitives.append(_indexed_mesh(mesh.vertices, faces, Style3D(color=color, layer="C-CORRIDOR-MESH")))
        return Scene3D(tuple(primitives))

    @classmethod
    def _cross_links(cls, sections):
        for section in sections:
            for (a, b), code in zip(section.links, section.link_codes):
                color = cls.LINK_COLORS.get(getattr(code, "value", ""), 7)
                yield Primitive3D.line(
                    section.points[a], section.points[b],
                    Style3D(color=color, lineweight=0.3, layer="C-CORRIDOR-SECTION"),
                )


def _indexed_mesh(vertices, faces, style):
    indices = {index: position for position, index in enumerate(dict.fromkeys(i for face in faces for i in face))}
    return Primitive3D.mesh(
        (vertices[index] for index in indices),
        (tuple(indices[index] for index in face) for face in faces),
        style,
    )


def _sections(corridor, alignment, frequency, offset, profile, *, baseline_name=None):
    if frequency is not None and (not math.isfinite(frequency) or frequency <= 0):
        raise ValueError("sample_frequency must be finite and positive")
    if not math.isfinite(offset):
        raise ValueError("offset_elevation must be finite")
    if baseline_name is not None and not any(
        baseline.name == baseline_name and baseline.alignment_name == alignment.name for baseline in corridor.baselines
    ):
        raise ValueError(f"Missing baseline {baseline_name!r} for alignment {alignment.name!r}")
    profiles = {candidate.name: candidate for candidate in alignment.profiles}
    for region in corridor.regions:
        if region.assembly is None:
            continue
        grade = profile
        baseline = corridor.baseline_for_region(region)
        if baseline_name is not None and (baseline is None or baseline.name != baseline_name):
            continue
        if baseline is not None:
            if baseline.alignment_name != alignment.name:
                continue
            if grade is None and baseline.profile_name:
                grade = profiles.get(baseline.profile_name)
                if grade is None:
                    raise ValueError(f"Missing profile: {baseline.profile_name}")

        stations = region.sample_stations(frequency)
        yield [
            CrossSection3D.from_region(
                alignment, station, region,
                offset + (grade.elevation_at(station) if grade is not None else 0.0),
            )
            for station in stations
        ]
