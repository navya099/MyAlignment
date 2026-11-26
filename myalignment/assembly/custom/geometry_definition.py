from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from myalignment.assembly.codes import LinkCode, ShapeCode
from myalignment.assembly.parameter.parameter import ParameterValue
from myalignment.assembly.parameter.parameter_set import _evaluate_formula


@dataclass(frozen=True, slots=True)
class PointDefinition:
    """로컬 횡거 X와 표고차 Z를 수식으로 정의한다."""

    code: Enum
    x_expr: str = "0.0"
    z_expr: str = "0.0"


@dataclass(frozen=True, slots=True)
class LinkDefinition:
    """0부터 시작하는 점 인덱스 두 개로 링크를 정의한다."""

    start_index: int
    end_index: int
    code: Enum = LinkCode.PAVEMENT
    shape_code: ShapeCode | None = None


@dataclass(frozen=True, slots=True)
class ShapeDefinition:
    """닫힌 재료 단면을 구성하는 링크 인덱스와 형상 코드."""

    name: str
    link_indices: tuple[int, ...]
    shape_code: ShapeCode

    def __post_init__(self):
        object.__setattr__(self, "link_indices", tuple(self.link_indices))
        if not self.name.strip():
            raise ValueError("shape name is required")
        if not isinstance(self.shape_code, ShapeCode):
            raise ValueError("shape_code must be a ShapeCode")


def _check_index(index, size, description):
    if type(index) is not int or not 0 <= index < size:
        raise ValueError(f"{description} out of range: {index!r}")


def _validate_boundary(shape, links):
    edges = defaultdict(set)
    for index in shape.link_indices:
        link = links[index]
        edges[link.start_index].add(link.end_index)
        edges[link.end_index].add(link.start_index)
    if len(edges) != len(shape.link_indices) or any(len(neighbors) != 2 for neighbors in edges.values()):
        raise ValueError(f"Shape {shape.name!r} must form one closed boundary")
    reached = set()
    pending = [next(iter(edges))]
    while pending:
        vertex = pending.pop()
        reached.add(vertex)
        pending.extend(edges[vertex] - reached)
    if len(reached) != len(edges):
        raise ValueError(f"Shape {shape.name!r} must form one closed boundary")


@dataclass(frozen=True, slots=True)
class GeometryDefinition:
    """점, 링크, 닫힌 형상으로 구성된 불변 로컬 단면 정의."""

    points: tuple[PointDefinition, ...] = ()
    links: tuple[LinkDefinition, ...] = ()
    shapes: tuple[ShapeDefinition, ...] = ()
    _shape_codes: tuple[ShapeCode | None, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        for name in ("points", "links", "shapes"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        if any(not isinstance(point.code, Enum) for point in self.points):
            raise ValueError("point codes must be enum values")
        for link in self.links:
            _check_index(link.start_index, len(self.points), "Link start_index")
            _check_index(link.end_index, len(self.points), "Link end_index")
            if link.start_index == link.end_index:
                raise ValueError("Link endpoints must use different point indices")
            if not isinstance(link.code, Enum):
                raise ValueError("link codes must be enum values")
            if link.shape_code is not None and not isinstance(link.shape_code, ShapeCode):
                raise ValueError("shape_code must be a ShapeCode")
        if len({shape.name for shape in self.shapes}) != len(self.shapes):
            raise ValueError("Duplicate shape name")
        codes = [link.shape_code for link in self.links]
        for shape in self.shapes:
            indices = shape.link_indices
            if len(indices) < 3 or len(set(indices)) != len(indices):
                raise ValueError(f"Shape {shape.name!r} requires at least three distinct links")
            for index in indices:
                _check_index(index, len(self.links), "Shape link index")
                if codes[index] is not None and codes[index] is not shape.shape_code:
                    raise ValueError(f"Conflicting shape codes for link {index}")
                codes[index] = shape.shape_code
            _validate_boundary(shape, self.links)
        object.__setattr__(self, "_shape_codes", tuple(codes))

    def point_count(self) -> int:
        return len(self.points)

    def link_count(self) -> int:
        return len(self.links)

    def validate_expressions(self, context: Mapping[str, ParameterValue]) -> list[str]:
        """모든 좌표 수식을 검사하고 점 인덱스와 축이 포함된 오류를 반환한다."""
        _, errors = self._evaluate_coordinates(context)
        return errors

    def _evaluate_coordinates(self, context):
        def lookup(name):
            if name not in context:
                raise ValueError(f"Unknown formula variable {name!r}")
            return context[name]

        coordinates, errors = [], []
        for index, point in enumerate(self.points):
            values = []
            for axis, expression in (("x", point.x_expr), ("z", point.z_expr)):
                try:
                    values.append(_evaluate_formula(expression, lookup))
                except ValueError as error:
                    errors.append(f"Point[{index}].{axis}: {error}")
            if len(values) == 2:
                coordinates.append(tuple(values))
        return coordinates, errors
