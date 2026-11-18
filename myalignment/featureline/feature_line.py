# featureline/feature_line.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
import math

from myalignment.featureline.vertex import FeatureLineVertex, FeatureLinePointType
from myalignment.surface.breakline import Breakline
from myalignment.surface.breakline_type import BreaklineType


@dataclass(frozen=True, slots=True)
class FeatureLine:
    """
    FeatureLine (불변).

    C3D의 FeatureLine과 호환.
    - 3D 폴리라인 (표고 포함).
    - Grading 기반, Surface Breakline 역할.
    - Corridor Baseline으로도 사용 가능 (권장되진 않음).

    Attributes:
        name: FeatureLine 이름.
        vertices: 3D 정점 튜플.
        is_closed: 닫힌 선 여부.
        site_id: 소속 Site ID (Grading과 연계).
        relative_surface: 상대 표고 기준 Surface 이름 (선택).
    """
    name: str = ""
    vertices: tuple[FeatureLineVertex, ...] = field(default_factory=tuple)
    is_closed: bool = False
    site_id: str = ""
    relative_surface: str = ""

    def __post_init__(self):
        if len(self.vertices) < 2:
            raise ValueError(f"FeatureLine은 ≥ 2점 필요: {len(self.vertices)}")

    # ================================================================
    # 기본 속성 (C3D 호환)
    # ================================================================
    @property
    def length_2d(self) -> float:
        """2D 길이 (m)."""
        total = 0.0
        n = len(self.vertices)
        limit = n if self.is_closed else n - 1
        for i in range(limit):
            a = self.vertices[i]
            b = self.vertices[(i + 1) % n]
            total += math.hypot(b.x - a.x, b.y - a.y)
        return total

    @property
    def length_3d(self) -> float:
        """3D 길이 (m)."""
        total = 0.0
        n = len(self.vertices)
        limit = n if self.is_closed else n - 1
        for i in range(limit):
            a = self.vertices[i]
            b = self.vertices[(i + 1) % n]
            total += math.sqrt(
                (b.x - a.x) ** 2 + (b.y - a.y) ** 2 + (b.z - a.z) ** 2
            )
        return total

    @property
    def max_elevation(self) -> float:
        return max((v.z for v in self.vertices), default=0.0)

    @property
    def min_elevation(self) -> float:
        return min((v.z for v in self.vertices), default=0.0)

    @property
    def max_grade(self) -> float:
        """최대 구배 (오르막, 양수)."""
        grades = self._segment_grades()
        return max(grades) if grades else 0.0

    @property
    def min_grade(self) -> float:
        """최소 구배 (내리막, 음수)."""
        grades = self._segment_grades()
        return min(grades) if grades else 0.0

    @property
    def points_count(self) -> int:
        """전체 점 개수 (PI + Elevation)."""
        return len(self.vertices)

    @property
    def pi_points_count(self) -> int:
        """PI 점 개수."""
        return sum(1 for v in self.vertices if v.point_type == FeatureLinePointType.PI)

    @property
    def elevation_points_count(self) -> int:
        """Elevation 점 개수."""
        return sum(1 for v in self.vertices if v.point_type == FeatureLinePointType.ELEVATION)

    def _segment_grades(self) -> list[float]:
        """각 세그먼트의 구배 리스트."""
        grades = []
        n = len(self.vertices)
        limit = n if self.is_closed else n - 1
        for i in range(limit):
            a = self.vertices[i]
            b = self.vertices[(i + 1) % n]
            dx = math.hypot(b.x - a.x, b.y - a.y)
            if dx > 1e-9:
                grades.append((b.z - a.z) / dx)
        return grades

    # ================================================================
    # 점 조회 (C3D GetPoints 호환)
    # ================================================================
    def get_points(
            self,
            point_type: FeatureLinePointType = FeatureLinePointType.ALL,
    ) -> tuple[FeatureLineVertex, ...]:
        """유형별 점 반환."""
        if point_type == FeatureLinePointType.ALL:
            return self.vertices
        return tuple(v for v in self.vertices if v.point_type == point_type)

    # ================================================================
    # 구배/거리 조회 (C3D 호환)
    # ================================================================
    def grade_in_at_point(self, vertex_index: int) -> float:
        """주어진 점으로 들어오는 구배 (이전 세그먼트)."""
        if vertex_index <= 0 or vertex_index >= len(self.vertices):
            return 0.0
        a = self.vertices[vertex_index - 1]
        b = self.vertices[vertex_index]
        dx = math.hypot(b.x - a.x, b.y - a.y)
        if dx < 1e-9:
            return 0.0
        return (b.z - a.z) / dx

    def grade_out_at_point(self, vertex_index: int) -> float:
        """주어진 점에서 나가는 구배 (다음 세그먼트)."""
        if vertex_index < 0 or vertex_index >= len(self.vertices) - 1:
            return 0.0
        a = self.vertices[vertex_index]
        b = self.vertices[vertex_index + 1]
        dx = math.hypot(b.x - a.x, b.y - a.y)
        if dx < 1e-9:
            return 0.0
        return (b.z - a.z) / dx

    def get_3d_distance_at_point(self, vertex_index: int) -> float:
        """시작점에서 주어진 점까지의 3D 누적 거리."""
        if vertex_index <= 0:
            return 0.0
        total = 0.0
        for i in range(min(vertex_index, len(self.vertices) - 1)):
            a = self.vertices[i]
            b = self.vertices[i + 1]
            total += math.sqrt(
                (b.x - a.x) ** 2 + (b.y - a.y) ** 2 + (b.z - a.z) ** 2
            )
        return total

    def elevation_at_xy(self, x: float, y: float, tol: float = 1e-6) -> float | None:
        """점 (x, y)가 FeatureLine 위에 있으면 표고 반환."""
        for i in range(len(self.vertices) - 1):
            a, b = self.vertices[i], self.vertices[i + 1]
            t = self._project_param(a, b, x, y, tol)
            if t is not None:
                return a.z + t * (b.z - a.z)
        return None

    @staticmethod
    def _project_param(a, b, x, y, tol=1e-6) -> float | None:
        dx = b.x - a.x
        dy = b.y - a.y
        length_sq = dx * dx + dy * dy
        if length_sq < tol * tol:
            return None
        t = ((x - a.x) * dx + (y - a.y) * dy) / length_sq
        if t < -tol or t > 1 + tol:
            return None
        px = a.x + t * dx
        py = a.y + t * dy
        if math.hypot(x - px, y - py) > tol:
            return None
        return max(0.0, min(1.0, t))

    # ================================================================
    # Breakline 변환 (Surface 제어용)
    # ================================================================
    def to_breakline(
            self,
            breakline_type: BreaklineType = BreaklineType.STANDARD,
    ) -> Breakline:
        """FeatureLine → Breakline 변환 (Surface 삼각분할 제어)."""
        from myalignment.surface.breakline_vertex import BreaklineVertex
        return Breakline(
            name=self.name,
            breakline_type=breakline_type,
            vertices=tuple(
                BreaklineVertex(v.x, v.y, v.z) for v in self.vertices
            ),
        )

    # ================================================================
    # 불변 변환
    # ================================================================
    def reversed(self) -> "FeatureLine":
        """뒤집힌 FeatureLine."""
        return replace(self, vertices=tuple(reversed(self.vertices)))

    def add_vertex(self, vertex: FeatureLineVertex, index: int = -1) -> "FeatureLine":
        """정점 추가한 새 FeatureLine."""
        new_verts = list(self.vertices)
        if index < 0 or index >= len(new_verts):
            new_verts.append(vertex)
        else:
            new_verts.insert(index, vertex)
        return replace(self, vertices=tuple(new_verts))

    def set_elevation(self, vertex_index: int, z: float) -> "FeatureLine":
        """정점 표고 변경한 새 FeatureLine."""
        if vertex_index < 0 or vertex_index >= len(self.vertices):
            raise IndexError(f"정점 인덱스 범위 초과: {vertex_index}")
        new_verts = list(self.vertices)
        old = new_verts[vertex_index]
        new_verts[vertex_index] = FeatureLineVertex(
            old.x, old.y, z, old.point_type
        )
        return replace(self, vertices=tuple(new_verts))

    # ================================================================
    # Surface 표고 할당 (C3D AssignElevationsFromSurface)
    # ================================================================
    def assign_elevations_from_surface(self, surface) -> "FeatureLine":
        """
        Surface에서 표고를 가져와 FeatureLine 갱신.

        Args:
            surface: elevation_at(x, y) 메서드를 가진 Surface.
        """
        new_verts = []
        for v in self.vertices:
            z = surface.elevation_at(v.x, v.y)
            new_verts.append(FeatureLineVertex(v.x, v.y, z, v.point_type))
        return replace(self, vertices=tuple(new_verts))

    # ================================================================
    # Corridor Baseline 지원
    # ================================================================
    def to_baseline_data(self) -> dict:
        """
        Corridor Baseline용 데이터.

        FeatureLine은 Alignment+Profile 대체 가능 (제한적).
        """
        return {
            'name': self.name,
            'start_station': 0.0,
            'end_station': self.length_2d,
            'length': self.length_2d,
            'vertices': [(v.x, v.y, v.z) for v in self.vertices],
        }

    def __repr__(self) -> str:
        return (
            f"FeatureLine('{self.name}', "
            f"n={len(self.vertices)}, "
            f"L2D={self.length_2d:.2f}m, "
            f"L3D={self.length_3d:.2f}m)"
        )