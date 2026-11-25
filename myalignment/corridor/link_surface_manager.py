from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from myalignment.corridor.multi_link_surface_builder import LinkSurfaceResult, MultiLinkSurfaceBuilder

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.assembly.codes import LinkCode
    from myalignment.corridor.corridor import Corridor
    from myalignment.corridor.link_surface_spec import LinkSurfaceSpec
    from myalignment.profile.profile import Profile


@dataclass(frozen=True, slots=True)
class LinkSurfaceManager:
    """링크 표면의 불변 집합. 이름과 단일 링크 코드로 결과를 찾는다."""

    surfaces: tuple[LinkSurfaceResult, ...] = ()
    name: str = "LinkSurfaces"

    def __post_init__(self):
        surfaces = tuple(self.surfaces)
        if len({result.surface.name.casefold() for result in surfaces}) != len(surfaces):
            raise ValueError("link surface names must be unique")
        object.__setattr__(self, "surfaces", surfaces)

    def __len__(self) -> int:
        return len(self.surfaces)

    def __iter__(self) -> Iterator[LinkSurfaceResult]:
        return iter(self.surfaces)

    def get(self, name: str) -> LinkSurfaceResult | None:
        return next((item for item in self if item.surface.name == name), None)

    def get_by_link_code(self, code: LinkCode) -> LinkSurfaceResult | None:
        return next((item for item in self if item.link_code == code), None)

    def add(self, result: LinkSurfaceResult) -> LinkSurfaceManager:
        return replace(self, surfaces=(*self.surfaces, result))

    @classmethod
    def from_corridor(
        cls,
        corridor: Corridor,
        name: str = "LinkSurfaces",
        specs: Sequence[LinkSurfaceSpec] | None = None,
        *,
        alignments: Mapping[str, Alignment],
        profiles: Mapping[str, Profile] | None = None,
    ) -> LinkSurfaceManager:
        """명시한 사양을 추출한다. specs를 생략하면 모든 링크 코드를 대상으로 한다."""
        if specs is None:
            extracted = MultiLinkSurfaceBuilder.build_all_links(
                corridor, name, alignments=alignments, profiles=profiles,
            )
        else:
            extracted = []
            for spec in specs:
                result = MultiLinkSurfaceBuilder.build_from_spec(
                    corridor, spec, alignments=alignments, profiles=profiles,
                )
                extracted.extend(result if isinstance(result, list) else (result,))
        return cls(tuple(extracted), name)

    @property
    def total_area(self) -> float:
        """개별 표면의 평면 면적 합. 겹치는 층은 각각 포함한다."""
        return sum(item.surface.area_2d for item in self)

    def surfaces_by_code(self) -> dict[LinkCode, LinkSurfaceResult]:
        """코드별 첫 번째 단일 코드 표면을 반환한다."""
        by_code = {}
        for result in self:
            if result.link_code is not None:
                by_code.setdefault(result.link_code, result)
        return by_code
