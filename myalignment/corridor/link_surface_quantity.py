from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from myalignment.assembly.codes import LinkCode
    from myalignment.corridor.link_surface_manager import LinkSurfaceManager


@dataclass(frozen=True, slots=True)
class LinkQuantity:
    """단일 링크 코드 표면의 평면 면적과 실제 면적."""

    link_code: LinkCode
    surface_name: str
    area_2d: float
    area_3d: float
    volume: float = 0.0


@dataclass(frozen=True, slots=True)
class LinkSurfaceQuantity:
    """단일 코드 표면별 면적 집계."""

    quantities: tuple[LinkQuantity, ...] = ()

    @classmethod
    def from_manager(cls, manager: LinkSurfaceManager) -> LinkSurfaceQuantity:
        """단일 코드 결과의 TIN 삼각면을 바탕으로 2D·3D 면적을 집계한다."""
        return cls(tuple(
            LinkQuantity(item.link_code, item.surface.name, item.surface.area_2d, item.surface.area_3d)
            for item in manager if item.link_code is not None
        ))

    def get_by_code(self, code: LinkCode) -> LinkQuantity | None:
        return next((quantity for quantity in self.quantities if quantity.link_code == code), None)

    @property
    def total_area_2d(self) -> float:
        return sum(item.area_2d for item in self.quantities)

    def to_dict(self) -> dict:
        """첫 결과의 표면 이름과 면적을 링크 코드별로 반환한다."""
        result = {}
        for item in self.quantities:
            result.setdefault(item.link_code.value, {
                "surface": item.surface_name, "area_2d": item.area_2d, "area_3d": item.area_3d,
            })
        return result
