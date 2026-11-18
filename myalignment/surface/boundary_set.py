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
    # 분류 캐시
    _outer: Boundary | None = field(
        init=False, repr=False, compare=False, default=None
    )
    _hides: tuple[Boundary, ...] = field(
        init=False, repr=False, compare=False, default=()
    )
    _shows: tuple[Boundary, ...] = field(
        init=False, repr=False, compare=False, default=()
    )
    _data_clips: tuple[Boundary, ...] = field(
        init=False, repr=False, compare=False, default=()
    )

    def __post_init__(self):
        outer = None
        hides: list[Boundary] = []
        shows: list[Boundary] = []
        data_clips: list[Boundary] = []
        for b in self.boundaries:
            bt = b.boundary_type
            if bt == BoundaryType.OUTER:
                if outer is not None:
                    raise ValueError("Outer Boundary는 1개만 허용")
                outer = b
            elif bt == BoundaryType.HIDE:
                hides.append(b)
            elif bt == BoundaryType.SHOW:
                shows.append(b)
            elif bt == BoundaryType.DATA_CLIP:
                data_clips.append(b)
        object.__setattr__(self, "_outer", outer)
        object.__setattr__(self, "_hides", tuple(hides))
        object.__setattr__(self, "_shows", tuple(shows))
        object.__setattr__(self, "_data_clips", tuple(data_clips))

    # ---- 분류 (캐시) ----
    @property
    def outer(self) -> Boundary | None:
        return self._outer

    @property
    def hide_boundaries(self) -> tuple[Boundary, ...]:
        return self._hides

    @property
    def show_boundaries(self) -> tuple[Boundary, ...]:
        return self._shows

    @property
    def data_clip_boundaries(self) -> tuple[Boundary, ...]:
        return self._data_clips

    # ---- 포함 판정 (bbox 사전 필터) ----
    def contains_point(self, x: float, y: float) -> bool:
        """
        점 (x, y)가 유효 영역 내부인지.

        규칙:
            1. Outer가 있으면: Outer 내부
            2. Hide 내부면: False (구멍)
            3. Show가 있으면: Show 내부만 True
            4. 그 외: True
        """
        # 1) Outer: bbox → 내부
        outer = self._outer
        if outer is not None:
            if not outer.bbox_contains(x, y):
                return False
            if not outer.contains_point(x, y):
                return False

        # 2) Hide: bbox → 내부
        for hide in self._hides:
            if hide.bbox_contains(x, y) and hide.contains_point(x, y):
                return False

        # 3) Show: bbox → 내부
        if self._shows:
            for show in self._shows:
                if show.bbox_contains(x, y) and show.contains_point(x, y):
                    return True
            return False

        return True

    # ---- 면적 ----
    @property
    def effective_area(self) -> float:
        outer_area = self._outer.area if self._outer else 0.0
        hide_area = sum(b.area for b in self._hides)
        show_area = sum(b.area for b in self._shows)
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
            f"outer={'Y' if self._outer else 'N'}, "
            f"hide={len(self._hides)}, "
            f"area={self.effective_area:.2f}m²)"
        )