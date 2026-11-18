# surface/delaunay.py
from __future__ import annotations
import math

from myalignment.surface.tin_point import TinPoint
from myalignment.surface.triangle import Triangle


class DelaunayTriangulator:
    """
    들로네 삼각분할 (Bowyer-Watson 알고리즘).

    점 집합 → Triangle 집합.
    O(N²) ~ O(N log N) (점 개수에 따라).
    """

    @staticmethod
    def triangulate(points: list[TinPoint]) -> list[Triangle]:
        """들로네 삼각분할."""
        if len(points) < 3:
            return []

        # 1) Super-triangle 생성 (모든 점을 포함하는 큰 삼각형)
        min_x = min(p.x for p in points)
        max_x = max(p.x for p in points)
        min_y = min(p.y for p in points)
        max_y = max(p.y for p in points)

        dx = max_x - min_x
        dy = max_y - min_y
        dmax = max(dx, dy)
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2

        # 충분히 큰 super-triangle
        st_points = [
            TinPoint(mid_x - 20 * dmax, mid_y - dmax, 0),
            TinPoint(mid_x, mid_y + 20 * dmax, 0),
            TinPoint(mid_x + 20 * dmax, mid_y - dmax, 0),
        ]
        all_points = list(points) + st_points
        st_offset = len(points)

        # 초기 삼각형 (super-triangle)
        triangles = [Triangle(st_offset, st_offset + 1, st_offset + 2)]

        # 2) 각 점 삽입
        for i, p in enumerate(points):
            triangles = DelaunayTriangulator._insert_point(all_points, triangles, i)

        # 3) Super-triangle의 정점을 포함한 삼각형 제거
        result = []
        for tri in triangles:
            if any(v >= st_offset for v in (tri.a, tri.b, tri.c)):
                continue
            # 정점 순서 정규화
            a, b, c = sorted((tri.a, tri.b, tri.c))
            result.append(Triangle(a, b, c))

        return result

    @staticmethod
    def _insert_point(
            points: list[TinPoint],
            triangles: list[Triangle],
            point_idx: int,
    ) -> list[Triangle]:
        """Bowyer-Watson 점 삽입."""
        p = points[point_idx]

        # 1) p를 외접원에 포함하는 삼각형들 찾기
        bad_triangles = []
        for tri in triangles:
            if DelaunayTriangulator._circumcircle_contains(points, tri, p):
                bad_triangles.append(tri)

        # 2) Bad 삼각형들의 경계(변) 수집
        edges = []
        for tri in bad_triangles:
            for edge in [(tri.a, tri.b), (tri.b, tri.c), (tri.c, tri.a)]:
                # 반대 방향 변이 이미 있으면 제거 (내부 변)
                reverse = (edge[1], edge[0])
                if reverse in edges:
                    edges.remove(reverse)
                elif edge in edges:
                    edges.remove(edge)
                else:
                    edges.append(edge)

        # 3) Bad 삼각형 제거
        triangles = [t for t in triangles if t not in bad_triangles]

        # 4) 새로운 삼각형 생성 (경계 변 + p)
        for e in edges:
            a, b = e
            if a == point_idx or b == point_idx:
                continue
            triangles.append(Triangle(*sorted((a, b, point_idx))))

        return triangles

    @staticmethod
    def _circumcircle_contains(
            points: list[TinPoint],
            tri: Triangle,
            p: TinPoint,
    ) -> bool:
        """점 p가 삼각형의 외접원 내부에 있는지."""
        p1, p2, p3 = tri.vertices(points)

        ax, ay = p1.x, p1.y
        bx, by = p2.x, p2.y
        cx, cy = p3.x, p3.y
        px, py = p.x, p.y

        # 3×3 행렬식 (외접원 판정)
        # | ax-px  ay-py  (ax-px)²+(ay-py)² |
        # | bx-px  by-py  (bx-px)²+(by-py)² |
        # | cx-px  cy-py  (cx-px)²+(cy-py)² |
        d = (
                (ax - px) * ((by - py) * ((cx - px) ** 2 + (cy - py) ** 2)
                             - ((bx - px) ** 2 + (by - py) ** 2) * (cy - py))
                - (ay - py) * ((bx - px) * ((cx - px) ** 2 + (cy - py) ** 2)
                               - ((bx - px) ** 2 + (by - py) ** 2) * (cx - px))
                + ((ax - px) ** 2 + (ay - py) ** 2) * ((bx - px) * (cy - py) - (by - py) * (cx - px))
        )

        # 반시계 방향 삼각형이면 d > 0
        # 시계 방향이면 부호 반전
        area2 = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
        if area2 < 0:
            d = -d

        return d > 1e-9