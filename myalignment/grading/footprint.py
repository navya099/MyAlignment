# grading/footprint.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from cadgeom import Point2d


@dataclass(frozen=True, slots=True)
class FootprintVertex:
    """발자국 정점 (3D)."""
    x: float = 0.0
    y: float = 0.0
    elevation: float = 0.0

    @property
    def point_2d(self) -> Point2d:
        return Point2d(self.x, self.y)


@dataclass(frozen=True, slots=True)
class Footprint:
    """
    발자국 (불변).

    C3D의 FeatureLine/부지 경계선과 호환.
    - 열린 선 또는 닫힌 선.
    """
    name: str = ""
    vertices: tuple[FootprintVertex, ...] = field(default_factory=tuple)
    is_closed: bool = False

    def __post_init__(self):
        if len(self.vertices) < 2:
            raise ValueError(f"발자국 ≥ 2점 필요: {len(self.vertices)}")

    @property
    def length(self) -> float:
        total = 0.0
        n = len(self.vertices)
        limit = n if self.is_closed else n - 1
        for i in range(limit):
            a = self.vertices[i]
            b = self.vertices[(i + 1) % n]
            total += math.hypot(b.x - a.x, b.y - a.y)
        return total

    def segments(self) -> list[tuple[FootprintVertex, FootprintVertex]]:
        """발자국 세그먼트 리스트."""
        result = []
        n = len(self.vertices)
        limit = n if self.is_closed else n - 1
        for i in range(limit):
            result.append((self.vertices[i], self.vertices[(i + 1) % n]))
        return result

    def outward_normals(self) -> list[float]:
        """
        각 세그먼트의 외향 법선 방위각.

        - 닫힌 선: 반시계 방향이면 좌측이 안쪽 → 우측(외향)
        - 열린 선: 좌측 법선
        """
        result = []
        for a, b in self.segments():
            seg_az = math.atan2(b.y - a.y, b.x - a.x)
            if self.is_closed:
                # 반시계 폴리곤 가정 → 외향은 우측(seg_az - π/2)
                result.append(seg_az - math.pi / 2)
            else:
                # 열린 선: 좌측
                result.append(seg_az + math.pi / 2)
        return result

    # footprint.py
    def vertex_outward_normals(self) -> list[float]:
        """각 정점의 외향 법선 방위각 (인접 세그먼트 평균)."""
        seg_normals = self.outward_normals()
        n = len(self.vertices)
        result = []
        if self.is_closed:
            for i in range(n):
                prev_seg = seg_normals[i - 1]
                next_seg = seg_normals[i]
                result.append(self._angle_average(prev_seg, next_seg))
        else:
            for i in range(n):
                if i == 0:
                    result.append(seg_normals[0])
                elif i == n - 1:
                    result.append(seg_normals[-1])
                else:
                    result.append(self._angle_average(seg_normals[i - 1], seg_normals[i]))
        return result

    @staticmethod
    def _angle_average(a: float, b: float) -> float:
        x = math.cos(a) + math.cos(b)
        y = math.sin(a) + math.sin(b)
        return math.atan2(y, x)