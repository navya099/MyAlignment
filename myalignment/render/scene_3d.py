from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from myalignment.render.primitives_3d import Primitive3D


@dataclass(frozen=True, slots=True)
class Scene3D:
    """3D 도형과 메타데이터를 가진 렌더링 결과."""

    primitives: tuple[Primitive3D, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def add(self, prim: Primitive3D) -> Scene3D:
        return self.add_all((prim,))

    def add_all(self, prims: Iterable[Primitive3D]) -> Scene3D:
        return replace(self, primitives=self.primitives + tuple(prims))

    def __len__(self) -> int:
        return len(self.primitives)

    def __repr__(self) -> str:
        return f"Scene3D(primitives={len(self.primitives)})"
