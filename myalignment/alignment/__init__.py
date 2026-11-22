"""Public horizontal alignment API."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .alignment import Alignment
    from .alignment_builder import AlignmentBuilder

__all__ = ["Alignment", "AlignmentBuilder"]


def __getattr__(name: str):
    # RailAlignment imports Alignment and AlignmentBuilder imports RailAlignment.
    if name == "Alignment":
        from .alignment import Alignment

        return Alignment
    if name == "AlignmentBuilder":
        from .alignment_builder import AlignmentBuilder

        return AlignmentBuilder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
