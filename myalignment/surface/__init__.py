"""Public TIN surface API."""

from typing import TYPE_CHECKING

from .tin_surface import TinSurface

if TYPE_CHECKING:
    from .tin_surface_builder import TinSurfaceBuilder

__all__ = ["TinSurface", "TinSurfaceBuilder"]


def __getattr__(name: str):
    if name == "TinSurfaceBuilder":
        from .tin_surface_builder import TinSurfaceBuilder

        return TinSurfaceBuilder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
