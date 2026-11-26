from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from myalignment.assembly.custom.custom_subassembly import CustomSubassembly


@dataclass(frozen=True, slots=True)
class CustomSubassemblyLibrary:
    """이름별로 사용자 정의 서브어셈블리를 등록하는 불변 라이브러리."""

    subassemblies: Mapping[str, CustomSubassembly] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "subassemblies", MappingProxyType(dict(self.subassemblies)))

    def register(self, sub: CustomSubassembly) -> CustomSubassemblyLibrary:
        return CustomSubassemblyLibrary({**self.subassemblies, sub.name: sub})

    def get(self, name: str) -> CustomSubassembly | None:
        return self.subassemblies.get(name)

    def list_names(self) -> list[str]:
        return list(self.subassemblies)

    def __len__(self) -> int:
        return len(self.subassemblies)

    def __iter__(self) -> Iterator[CustomSubassembly]:
        return iter(self.subassemblies.values())

    @classmethod
    def standard(cls) -> CustomSubassemblyLibrary:
        from myalignment.assembly.custom.presets import (
            custom_lane, custom_shoulder_with_curb, custom_slope, custom_v_ditch,
        )

        parts = (custom_lane(), custom_shoulder_with_curb(), custom_v_ditch(), custom_slope())
        return cls({part.name: part for part in parts})
