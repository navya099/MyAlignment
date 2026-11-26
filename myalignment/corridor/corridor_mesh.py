from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from myalignment.corridor.cross_section_3d import CrossSection3D
from myalignment.render.primitives_3d import Point3D


def same_section_topology(first: CrossSection3D, second: CrossSection3D) -> bool:
    return (len(first.points), first.links, first.point_codes, first.link_codes) == (
        len(second.points), second.links, second.point_codes, second.link_codes,
    )


def check_section_topology(first: CrossSection3D, second: CrossSection3D) -> None:
    if not same_section_topology(first, second):
        raise ValueError(f"Cross-section topology changes between stations {first.station} and {second.station}")


@dataclass(frozen=True, slots=True)
class CorridorMesh:
    """인접 횡단면의 링크를 연결한 인덱스 삼각형 메쉬."""

    vertices: tuple[Point3D, ...] = ()
    triangles: tuple[tuple[int, int, int], ...] = ()
    face_codes: tuple[Enum | None, ...] = ()

    @classmethod
    def from_sections(cls, sections: Sequence[CrossSection3D]) -> CorridorMesh:
        if not sections:
            return cls()
        vertices = tuple(point for section in sections for point in section.points)
        triangles = []
        codes = []
        count = len(sections[0].points)
        for index, (first, second) in enumerate(zip(sections, sections[1:])):
            check_section_topology(first, second)
            if first.station >= second.station:
                raise ValueError("Cross-section stations must be strictly increasing")
            start = index * count
            for link_index, (a, b) in enumerate(first.links):
                front_a, front_b = start + a, start + b
                back_a, back_b = front_a + count, front_b + count
                triangles.extend(((front_a, front_b, back_b), (front_a, back_b, back_a)))
                code = first.link_codes[link_index] if first.link_codes else None
                codes.extend((code, code))
        return cls(vertices, tuple(triangles), tuple(codes))
