from __future__ import annotations

from collections import defaultdict, deque

from myalignment.surface.breakline import Breakline
from myalignment.surface.breakline_type import BreaklineType
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.triangle import Triangle


class ConstrainedDelaunayTriangulator:
    """Breakline을 삼각망의 변으로 삽입한다."""

    @staticmethod
    def triangulate(
        points: list[TinPoint],
        breaklines: list[Breakline] | None = None,
    ) -> tuple[list[Triangle], list[TinPoint]]:
        from myalignment.surface.tin_surface import _triangulate

        active = [
            line for line in breaklines or ()
            if line.breakline_type != BreaklineType.NON_DESTRUCTIVE
        ]
        if not active:
            return _triangulate(tuple(points)), list(points)

        by_xy = {}
        for point in points:
            by_xy.setdefault((point.x, point.y), point)
        base_points = tuple(by_xy.values())
        all_points = list(base_points)
        indices = {xy: i for i, xy in enumerate(by_xy)}
        has_proximity = any(line.breakline_type == BreaklineType.PROXIMITY for line in active)
        base_triangles = _triangulate(base_points) if has_proximity else []

        segments = []
        for line in active:
            vertices = []
            for vertex in line.vertices:
                key = (vertex.x, vertex.y)
                if key not in indices:
                    z = vertex.z
                    if line.breakline_type == BreaklineType.PROXIMITY:
                        z = ConstrainedDelaunayTriangulator._base_elevation(
                            base_points, base_triangles, vertex.x, vertex.y
                        )
                    indices[key] = len(all_points)
                    all_points.append(TinPoint(vertex.x, vertex.y, z))
                vertices.append(indices[key])
            segments.extend(
                (line, a, b, va.z, vb.z)
                for a, b, va, vb in zip(vertices, vertices[1:], line.vertices, line.vertices[1:])
                if a != b
            )

        constraints = set()
        elevations = {}
        for line, a, b, start_z, end_z in segments:
            start, end = all_points[a], all_points[b]
            interior = []
            min_x, max_x = sorted((start.x, end.x))
            min_y, max_y = sorted((start.y, end.y))
            for i, point in enumerate(all_points):
                if (
                    i in (a, b)
                    or not min_x - 1e-6 <= point.x <= max_x + 1e-6
                    or not min_y - 1e-6 <= point.y <= max_y + 1e-6
                ):
                    continue
                param = Breakline._project_param(start, end, point.x, point.y)
                if param is not None and 0 < param < 1:
                    interior.append((param, i))
            chain = [(0.0, a), *sorted(interior), (1.0, b)]
            for (_, u), (_, v) in zip(chain, chain[1:]):
                constraints.add(_edge(u, v))
            if line.breakline_type != BreaklineType.PROXIMITY:
                for param, index in chain:
                    z = start_z + param * (end_z - start_z)
                    if abs(elevations.setdefault(index, z) - z) > 1e-6:
                        raise ValueError("공유 Breakline 정점의 표고가 일치하지 않습니다.")

        for index, z in elevations.items():
            point = all_points[index]
            all_points[index] = TinPoint(point.x, point.y, z)

        triangles = _triangulate(tuple(all_points))
        if not triangles:
            return triangles, all_points
        mesh = _ConstraintMesh(all_points, triangles)
        for edge in sorted(constraints):
            mesh.force_edge(edge, constraints)
        return mesh.triangles, all_points

    @staticmethod
    def _base_elevation(
        points: tuple[TinPoint, ...], triangles: list[Triangle], x: float, y: float,
    ) -> float:
        for triangle in triangles:
            if triangle.contains_point(x, y, points):
                return triangle.elevation_at(x, y, points)
        return min(points, key=lambda p: (p.x - x) ** 2 + (p.y - y) ** 2).z


def _edge(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _triangle_edges(triangle: Triangle):
    return _edge(triangle.a, triangle.b), _edge(triangle.b, triangle.c), _edge(triangle.c, triangle.a)


class _ConstraintMesh:
    def __init__(self, points: list[TinPoint], triangles: list[Triangle]):
        self.points = points
        self.triangles = triangles
        self.faces_by_edge: dict[tuple[int, int], set[int]] = defaultdict(set)
        for face, triangle in enumerate(triangles):
            for edge in _triangle_edges(triangle):
                self.faces_by_edge[edge].add(face)

    def _crosses(self, first: tuple[int, int], second: tuple[int, int]) -> bool:
        if first[0] in second or first[1] in second:
            return False
        a, b = (self.points[i] for i in first)
        c, d = (self.points[i] for i in second)

        def orient(p, q, r):
            return (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x)

        return orient(a, b, c) * orient(a, b, d) < 0 and orient(c, d, a) * orient(c, d, b) < 0

    def force_edge(self, target: tuple[int, int], constraints: set[tuple[int, int]]) -> None:
        if target in self.faces_by_edge:
            return

        crossing = deque(edge for edge in self.faces_by_edge if self._crosses(edge, target))
        # 새 대각선이 제약선과 교차하면 큐 끝에서 다시 처리한다.
        max_passes = len(crossing) + 1
        for _ in range(max_passes):
            flipped = False
            for _ in range(len(crossing)):
                edge = crossing.popleft()
                if edge in constraints:
                    raise ValueError("교차 Breakline에는 공유 정점이 필요합니다.")
                opposite = self._flip(edge)
                if opposite is None:
                    crossing.append(edge)
                    continue
                flipped = True
                if opposite == target:
                    return
                if self._crosses(opposite, target):
                    crossing.append(opposite)
            if not flipped:
                break
        raise ValueError("Breakline을 삼각망 변으로 삽입할 수 없습니다.")

    def _flip(self, edge: tuple[int, int]) -> tuple[int, int] | None:
        adjacent = self.faces_by_edge[edge]
        if len(adjacent) != 2:
            return None
        faces = sorted(adjacent)
        opposite = _edge(*(
            next(i for i in (tri.a, tri.b, tri.c) if i not in edge)
            for tri in (self.triangles[face] for face in faces)
        ))
        if opposite in self.faces_by_edge or not self._crosses(edge, opposite):
            return None

        for face, endpoint in zip(faces, edge):
            for old_edge in _triangle_edges(self.triangles[face]):
                incident = self.faces_by_edge[old_edge]
                incident.remove(face)
                if not incident:
                    del self.faces_by_edge[old_edge]
            new_triangle = Triangle(*sorted((*opposite, endpoint)))
            self.triangles[face] = new_triangle
            for new_edge in _triangle_edges(new_triangle):
                self.faces_by_edge[new_edge].add(face)
        return opposite
