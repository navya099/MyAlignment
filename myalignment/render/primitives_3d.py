from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
import math


class PrimitiveType3D(Enum):
    POINT = "POINT"
    LINE = "LINE"
    POLYLINE = "POLYLINE"
    TRIANGLE = "TRIANGLE"
    MESH = "MESH"


@dataclass(frozen=True, slots=True)
class Point3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __post_init__(self):
        if not all(math.isfinite(value) for value in (self.x, self.y, self.z)):
            raise ValueError("3D coordinates must be finite")

    def distance_to(self, other: Point3D) -> float:
        return math.hypot(self.x - other.x, self.y - other.y, self.z - other.z)


@dataclass(frozen=True, slots=True)
class Style3D:
    color: int = 256
    lineweight: float = 0.0
    layer: str = "0"
    visible: bool = True
    linetype: str = "CONTINUOUS"


@dataclass(frozen=True, slots=True)
class Primitive3D:
    type: PrimitiveType3D
    points: tuple[Point3D, ...] = ()
    style: Style3D = field(default_factory=Style3D)
    indices: tuple[tuple[int, int, int], ...] = ()
    closed: bool = False

    def __post_init__(self):
        count = len(self.points)
        required = {PrimitiveType3D.POINT: 1, PrimitiveType3D.LINE: 2, PrimitiveType3D.TRIANGLE: 3}
        if self.type in required and count != required[self.type]:
            raise ValueError(f"{self.type.value} requires {required[self.type]} points")
        if self.type is PrimitiveType3D.POLYLINE and count < 2:
            raise ValueError("POLYLINE requires at least two points")
        for face in self.indices:
            if len(face) != 3 or len(set(face)) != 3 or any(not 0 <= index < count for index in face):
                raise ValueError(f"Invalid mesh triangle: {face}")

    @classmethod
    def point(cls, point: Point3D, style: Style3D | None = None) -> Primitive3D:
        return cls(PrimitiveType3D.POINT, (point,), style or Style3D())

    @classmethod
    def line(cls, p1: Point3D, p2: Point3D, style: Style3D | None = None) -> Primitive3D:
        return cls(PrimitiveType3D.LINE, (p1, p2), style or Style3D())

    @classmethod
    def polyline(
        cls, points: Iterable[Point3D], closed: bool = False, style: Style3D | None = None,
    ) -> Primitive3D:
        vertices = tuple(points)
        if closed and len(vertices) > 1 and vertices[0] != vertices[-1]:
            vertices += (vertices[0],)
        return cls(PrimitiveType3D.POLYLINE, vertices, style or Style3D(), closed=closed)

    @classmethod
    def triangle(cls, a: Point3D, b: Point3D, c: Point3D, style: Style3D | None = None) -> Primitive3D:
        return cls(PrimitiveType3D.TRIANGLE, (a, b, c), style or Style3D())

    @classmethod
    def mesh(
        cls, vertices: Iterable[Point3D], triangles: Iterable[tuple[int, int, int]],
        style: Style3D | None = None,
    ) -> Primitive3D:
        return cls(PrimitiveType3D.MESH, tuple(vertices), style or Style3D(), tuple(triangles))
