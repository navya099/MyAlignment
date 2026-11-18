# surface/boundary_set.py
from __future__ import annotations
from dataclasses import dataclass, field

from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_type import BoundaryType


@dataclass(frozen=True, slots=True)
class BoundarySet:
    """
    Surface 경계 집합 (불변).

    C3D의 Surface.Boundaries와 호환.
    - Outer는 1개만 허용.
    - Show/Hide/DataClip은 여러 개.
    """
    boundaries: tuple[Boundary, ...] = field(default_factory=tuple)

    def __post_init__(self):
        # Outer 개수 검증
        outer_count = sum(1 for b in self.boundaries if b.boundary_type == BoundaryType.OUTER)
        if outer_count > 1:
            raise ValueError(f"Outer Boundary는 1개만: {outer_count}개")

    # ---- 조회 ----
    @property
    def outer(self) -> Boundary | None:
        """외곽 경계."""
        for b in self.boundaries:
            if b.boundary_type == BoundaryType.OUTER:
                return b
        return None

    @property
    def show_boundaries(self) -> tuple[Boundary, ...]:
        return tuple(b for b in self.boundaries if b.boundary_type == BoundaryType.SHOW)

    @property
    def hide_boundaries(self) -> tuple[Boundary, ...]:
        return tuple(b for b in self.boundaries if b.boundary_type == BoundaryType.HIDE)

    @property
    def data_clip_boundaries(self) -> tuple[Boundary, ...]:
        return tuple(b for b in self.boundaries if b.boundary_type == BoundaryType.DATA_CLIP)

    # ---- 포함 판정 ----
    def contains_point(self, x: float, y: float) -> bool:
        """
        점 (x, y)가 유효 영역 내부인지.

        규칙:
            1. Outer가 있으면: Outer 내부
            2. Hide Boundary 내부면: False (구멍)
            3. Show Boundary가 있으면: Show 내부만 True
            4. 그 외: True
        """
        # 1) Outer 체크
        outer = self.outer
        if outer is not None and not outer.contains_point(x, y):
            return False

        # 2) Hide Boundary 체크
        for hide in self.hide_boundaries:
            if hide.contains_point(x, y):
                return False

        # 3) Show Boundary 체크
        shows = self.show_boundaries
        if shows:
            return any(s.contains_point(x, y) for s in shows)

        return True

    # ---- 면적 ----
    @property
    def effective_area(self) -> float:
        """
        유효 면적 (Outer - Hide + Show).
        """
        outer_area = self.outer.area if self.outer else 0.0
        hide_area = sum(b.area for b in self.hide_boundaries)
        show_area = sum(b.area for b in self.show_boundaries)
        return outer_area - hide_area + show_area

    # ---- 추가/제거 ----
    def add(self, boundary: Boundary) -> "BoundarySet":
        return BoundarySet(boundaries=self.boundaries + (boundary,))

    def remove(self, name: str) -> "BoundarySet":
        return BoundarySet(
            boundaries=tuple(b for b in self.boundaries if b.name != name)
        )

    def __len__(self) -> int:
        return len(self.boundaries)

    def __iter__(self):
        return iter(self.boundaries)

    def __repr__(self) -> str:
        return (
            f"BoundarySet(n={len(self.boundaries)}, "
            f"outer={'Y' if self.outer else 'N'}, "
            f"hide={len(self.hide_boundaries)}, "
            f"area={self.effective_area:.2f}m²)"
        )