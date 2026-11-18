# surface/delaunay.py
from __future__ import annotations

from myalignment.surface.tin_point import TinPoint
from myalignment.surface.triangle import Triangle


class DelaunayTriangulator:
    """
    들로네 삼각분할 (Bowyer-Watson).

    주의: O(N²) ~ O(N³). 대량 점에는 scipy.spatial.Delaunay 권장.
    규칙 격자는 TinSurfaceBuilder.add_grid (O(N)) 사용.
    """

    @staticmethod
    def triangulate(points: list[TinPoint]) -> list[Triangle]:
        if len(points) < 3:
            return []

        min_x = min(p.x for p in points)
        max_x = max(p.x for p in points)
        min_y = min(p.y for p in points)
        max_y = max(p.y for p in points)

        dx = max_x - min_x
        dy = max_y - min_y
        dmax = max(dx, dy) if max(dx, dy) > 0 else 1.0
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2

        st = [
            TinPoint(mid_x - 20 * dmax, mid_y - dmax, 0),
            TinPoint(mid_x, mid_y + 20 * dmax, 0),
            TinPoint(mid_x + 20 * dmax, mid_y - dmax, 0),
        ]
        all_points = list(points) + st
        st_offset = len(points)

        triangles: list[Triangle] = [Triangle(st_offset, st_offset + 1, st_offset + 2)]

        for i in range(len(points)):
            triangles = DelaunayTriangulator._insert_point(all_points, triangles, i)

        result: list[Triangle] = []
        for tri in triangles:
            if tri.a >= st_offset or tri.b >= st_offset or tri.c >= st_offset:
                continue
            a, b, c = sorted((tri.a, tri.b, tri.c))
            result.append(Triangle(a, b, c))
        return result

    @staticmethod
    def _insert_point(
        points: list[TinPoint],
        triangles: list[Triangle],
        point_idx: int,
    ) -> list[Triangle]:
        p = points[point_idx]
        px, py = p.x, p.y

        # 1) Bad 삼각형 수집 (인라인 외접원 판정)
        bad: list[Triangle] = []
        for tri in triangles:
            p1 = points[tri.a]
            p2 = points[tri.b]
            p3 = points[tri.c]
            if DelaunayTriangulator._in_circumcircle(p1, p2, p3, px, py):
                bad.append(tri)

        if not bad:
            return triangles

        # 2) 경계 엣지 수집 (카운트)
        edge_count: dict[tuple[int, int], int] = {}
        for tri in bad:
            for a, b in ((tri.a, tri.b), (tri.b, tri.c), (tri.c, tri.a)):
                key = (a, b) if a < b else (b, a)
                edge_count[key] = edge_count.get(key, 0) + 1

        boundary_edges = [e for e, c in edge_count.items() if c == 1]

        # 3) Bad 제거 (id set)
        bad_ids = set(id(t) for t in bad)
        triangles = [t for t in triangles if id(t) not in bad_ids]

        # 4) 새 삼각형
        for a, b in boundary_edges:
            triangles.append(Triangle(*sorted((a, b, point_idx))))

        return triangles

    @staticmethod
    def _in_circumcircle(
        p1: TinPoint, p2: TinPoint, p3: TinPoint,
        px: float, py: float,
    ) -> bool:
        """점 (px, py)가 삼각형 (p1,p2,p3)의 외접원 내부인지."""
        ax = p1.x - px
        ay = p1.y - py
        bx = p2.x - px
        by = p2.y - py
        cx = p3.x - px
        cy = p3.y - py

        d = (
            ax * (by * (cx * cx + cy * cy) - (bx * bx + by * by) * cy)
            - ay * (bx * (cx * cx + cy * cy) - (bx * bx + by * by) * cx)
            + (ax * ax + ay * ay) * (bx * cy - by * cx)
        )

        # 반시계 보정
        area2 = (p2.x - p1.x) * (p3.y - p1.y) - (p3.x - p1.x) * (p2.y - p1.y)
        if area2 < 0:
            d = -d
        return d > 1e-9