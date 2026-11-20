from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from myalignment.render.primitives import Primitive


@dataclass(frozen=True, slots=True)
class Layer:
    name: str
    color: int = 7
    linetype: str = "CONTINUOUS"
    lineweight: float = 0.0
    visible: bool = True


@dataclass(frozen=True, slots=True)
class Scene:
    primitives: tuple[Primitive, ...] = ()
    layers: tuple[Layer, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def add(self, prim: Primitive) -> Scene:
        return self.add_all((prim,))

    def add_all(self, prims: Iterable[Primitive]) -> Scene:
        return replace(self, primitives=self.primitives + tuple(prims))

    def add_layer(self, layer: Layer) -> Scene:
        if any(existing.name.casefold() == layer.name.casefold() for existing in self.layers):
            return self
        return replace(self, layers=self.layers + (layer,))

    def __len__(self) -> int:
        return len(self.primitives)

    def __repr__(self) -> str:
        return f"Scene(primitives={len(self.primitives)}, layers={len(self.layers)})"
