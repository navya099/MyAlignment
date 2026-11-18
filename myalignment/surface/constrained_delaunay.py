# surface/constrained_delaunay.py
from __future__ import annotations
import math

from myalignment.surface.tin_point import TinPoint

from myalignment.surface.triangle import Triangle
from myalignment.surface.breakline import Breakline
from myalignment.surface.breakline_type import BreaklineType
from myalignment.surface.delaunay import DelaunayTriangulator


class ConstrainedDelaunayTriangulator:
    """
    제약 들로네 삼각분할 (CDT).

    Breakline을 따라 삼각형 변을 강제.

    알고리즘:
        1. 표준 Delaunay 삼각분할
        2. Breakline을 따라 삼각형 분할 (edge flipping)
    """

    @staticmethod
    def triangulate(
            points: list[TinPoint],
            breaklines: list[Breakline] | None = None,
    ) -> tuple[list[Triangle], list[TinPoint]]:
        """
        Breakline을 강제한 TIN 생성.

        Returns:
            (triangles, all_points) — Breakline 정점이 추가된 points 포함.
        """
        if breaklines is None:
            breaklines = []

        # 1) Breakline 정점을 points에 추가
        all_points = list(points)
        breakline_indices: list[list[int]] = []

        for bl in breaklines:
            if bl.breakline_type == BreaklineType.NON_DESTRUCTIVE:
                # 비파괴: 삼각분할에 영향 없음
                breakline_indices.append([])
                continue

            indices = []
            for v in bl.vertices:
                idx = ConstrainedDelaunayTriangulator._add_or_find_point(
                    all_points, TinPoint(v.x, v.y, v.z)
                )
                indices.append(idx)
            breakline_indices.append(indices)

        # 2) 표준 Delaunay 삼각분할
        from myalignment.surface.tin_surface import _triangulate
        triangles = _triangulate(tuple(points))   # ← delaunay.triangulate 대신

        # 3) Breakline을 따라 edge flipping (삼각형 변 강제)
        for bl, indices in zip(breaklines, breakline_indices):
            if bl.breakline_type == BreaklineType.NON_DESTRUCTIVE:
                continue
            for i in range(len(indices) - 1):
                a, b = indices[i], indices[i + 1]
                triangles = ConstrainedDelaunayTriangulator._force_edge(
                    all_points, triangles, a, b
                )

        return triangles, all_points

    @staticmethod
    def _add_or_find_point(points: list[TinPoint], p: TinPoint, tol: float = 1e-6) -> int:
        """점이 이미 있으면 인덱스, 없으면 추가 후 인덱스."""
        for i, existing in enumerate(points):
            if existing.distance_2d(p) < tol:
                return i
        points.append(p)
        return len(points) - 1

    @staticmethod
    def _force_edge(
            points: list[TinPoint],
            triangles: list[Triangle],
            a: int, b: int,
            max_iter: int = 100,
    ) -> list[Triangle]:
        """
        변 (a, b)를 삼각형 변으로 강제 (edge flipping).

        이미 변이 있으면 그대로 반환.
        """
        # 이미 (a, b) 변이 있는지 확인
        if ConstrainedDelaunayTriangulator._has_edge(triangles, a, b):
            return triangles

        for _ in range(max_iter):
            # (a, b)와 교차하는 변 찾기
            crossing = ConstrainedDelaunayTriangulator._find_crossing_edge(
                points, triangles, a, b
            )
            if crossing is None:
                # 더 이상 교차 없음 → 실패 (수치 문제)
                break

            # 교차하는 변 (c, d)를 공유하는 두 삼각형 찾기
            t1, t2 = ConstrainedDelaunayTriangulator._find_triangles_with_edge(
                triangles, crossing[0], crossing[1]
            )
            if t1 is None or t2 is None:
                break

            # Edge flip: (c, d) → (a, b) 또는 다른 변
            new_t1, new_t2 = ConstrainedDelaunayTriangulator._flip_edge(
                t1, t2, crossing[0], crossing[1]
            )
            if new_t1 is None or new_t2 is None:
                break

            # 삼각형 갱신
            triangles = [t for t in triangles if t != t1 and t != t2]
            triangles.extend([new_t1, new_t2])

            if ConstrainedDelaunayTriangulator._has_edge(triangles, a, b):
                return triangles

        return triangles

    @staticmethod
    def _has_edge(triangles: list[Triangle], a: int, b: int) -> bool:
        """삼각형 집합에 변 (a, b)가 있는지."""
        for t in triangles:
            verts = {t.a, t.b, t.c}
            if a in verts and b in verts:
                return True
        return False

    @staticmethod
    def _find_crossing_edge(
            points: list[TinPoint],
            triangles: list[Triangle],
            a: int, b: int,
    ) -> tuple[int, int] | None:
        """(a, b) 선분과 교차하는 변 찾기."""
        pa = points[a]
        pb = points[b]

        for t in triangles:
            verts = [t.a, t.b, t.c]
            edges = [(verts[0], verts[1]), (verts[1], verts[2]), (verts[2], verts[0])]
            for c, d in edges:
                if a in (c, d) or b in (c, d):
                    continue
                if ConstrainedDelaunayTriangulator._segments_intersect(
                        pa, pb, points[c], points[d]
                ):
                    return c, d
        return None

    @staticmethod
    def _segments_intersect(p1: TinPoint, p2: TinPoint, p3: TinPoint, p4: TinPoint) -> bool:
        """두 선분이 교차하는지 (양 끝점 제외)."""

        def cross(o, a, b):
            return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)

        d1 = cross(p3, p4, p1)
        d2 = cross(p3, p4, p2)
        d3 = cross(p1, p2, p3)
        d4 = cross(p1, p2, p4)

        return ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
            ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))

    @staticmethod
    def _find_triangles_with_edge(
            triangles: list[Triangle], a: int, b: int,
    ) -> tuple[Triangle | None, Triangle | None]:
        """변 (a, b)를 공유하는 두 삼각형."""
        result = []
        for t in triangles:
            verts = {t.a, t.b, t.c}
            if a in verts and b in verts:
                result.append(t)
                if len(result) == 2:
                    break
        t1 = result[0] if len(result) >= 1 else None
        t2 = result[1] if len(result) >= 2 else None
        return t1, t2

    @staticmethod
    def _flip_edge(
            t1: Triangle, t2: Triangle, a: int, b: int,
    ) -> tuple[Triangle | None, Triangle | None]:
        """변 (a, b)를 공유하는 두 삼각형을 반대 대각선으로 flip."""
        # t1, t2의 공통 변 (a, b) 아닌 정점
        c = None
        d = None
        for v in (t1.a, t1.b, t1.c):
            if v not in (a, b):
                c = v
                break
        for v in (t2.a, t2.b, t2.c):
            if v not in (a, b):
                d = v
                break

        if c is None or d is None:
            return None, None

        # 새 삼각형: (c, d, a), (c, d, b)
        return (
            Triangle(*sorted((c, d, a))),
            Triangle(*sorted((c, d, b))),
        )