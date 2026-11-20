from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, replace

from myalignment.section.section_view_data import SectionViewData


@dataclass(frozen=True, slots=True)
class SectionViewSet:
    views: tuple[SectionViewData, ...] = ()
    name: str = "SectionViewSet"

    def __len__(self) -> int:
        return len(self.views)

    def __iter__(self) -> Iterator[SectionViewData]:
        return iter(self.views)

    def get_by_station(self, station: float, tol: float = 1e-3) -> SectionViewData | None:
        return next((view for view in self.views if abs(view.station - station) < tol), None)

    def add(self, view: SectionViewData) -> SectionViewSet:
        return replace(self, views=self.views + (view,))

    def stations(self) -> list[float]:
        return [view.station for view in self.views]
