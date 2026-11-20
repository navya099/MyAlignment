from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

from cadgeom import Point2d


class PrimitiveType(Enum):
    LINE = "LINE"
    ARC = "ARC"
    POLYLINE = "POLYLINE"
    TEXT = "TEXT"
    CIRCLE = "CIRCLE"


@dataclass(frozen=True, slots=True)
class Style:
    """ACI 색상, 선종류, 선가중치(mm), 레이어."""

    color: int = 256
    linetype: str = "CONTINUOUS"
    lineweight: float = 0.0
    layer: str = "0"


class _Text:
    """클래스에서는 팩토리, 인스턴스에서는 레이블 문자열을 제공한다."""

    def __get__(self, instance, owner):
        return owner.text_label if instance is None else instance.contents


@dataclass(frozen=True, slots=True)
class Primitive:
    """2D 렌더링 도형. 원호 각도는 도, 텍스트 회전각은 라디안."""

    type: PrimitiveType
    points: tuple[Point2d, ...] = ()
    style: Style = field(default_factory=Style)
    contents: str = ""
    text_height: float = 0.0
    rotation: float = 0.0
    closed: bool = False
    radius: float = 0.0
    start_angle: float = 0.0
    end_angle: float = 0.0

    text = _Text()

    @classmethod
    def line(cls, p1: Point2d, p2: Point2d, style: Style | None = None) -> Primitive:
        return cls(PrimitiveType.LINE, (p1, p2), style or Style())

    @classmethod
    def polyline(
        cls, points: Iterable[Point2d], closed: bool = False, style: Style | None = None
    ) -> Primitive:
        vertices = tuple(points)
        if closed and len(vertices) > 1 and vertices[-1] != vertices[0]:
            vertices += (vertices[0],)
        return cls(PrimitiveType.POLYLINE, vertices, style or Style(), closed=closed)

    @classmethod
    def arc(
        cls, center: Point2d, radius: float, start_angle: float,
        end_angle: float, style: Style | None = None,
    ) -> Primitive:
        return cls(
            PrimitiveType.ARC, (center,), style or Style(), radius=radius,
            start_angle=start_angle, end_angle=end_angle,
        )

    @classmethod
    def circle(cls, center: Point2d, radius: float, style: Style | None = None) -> Primitive:
        return cls(PrimitiveType.CIRCLE, (center,), style or Style(), radius=radius)

    @classmethod
    def text_label(
        cls, p: Point2d, text: str, height: float,
        rotation: float = 0.0, style: Style | None = None,
    ) -> Primitive:
        return cls(PrimitiveType.TEXT, (p,), style or Style(), text, height, rotation)
