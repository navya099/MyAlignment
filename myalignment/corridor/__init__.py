"""Public corridor API."""

from typing import TYPE_CHECKING

from .corridor import Corridor
from .corridor_builder import CorridorBuilder
from .surface_builder import CorridorSurfaceSpec

if TYPE_CHECKING:
    from .rail_corridor_builder import RailCorridorBuilder

__all__ = ["Corridor", "CorridorBuilder", "CorridorSurfaceSpec", "RailCorridorBuilder"]


def __getattr__(name: str):
    if name == "RailCorridorBuilder":
        from .rail_corridor_builder import RailCorridorBuilder

        return RailCorridorBuilder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
