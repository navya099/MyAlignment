from __future__ import annotations

from dataclasses import dataclass

from myalignment.assembly.custom.geometry_definition import GeometryDefinition
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.parameter.parameter_type import ParameterType
from myalignment.assembly.parameter.parameterized import ParameterizedSubassembly
from myalignment.assembly.point import AssemblyPoint


@dataclass(frozen=True, slots=True)
class CustomSubassembly(ParameterizedSubassembly):
    """입력·계산·출력 파라미터로 구성된 선언적 단면."""

    name: str = "Custom"
    geometry_def: GeometryDefinition | None = None

    def __post_init__(self):
        if type(self.side) is not int or self.side not in (-1, 0, 1):
            raise ValueError("side must be -1, 0 or 1")

    @property
    def target_parameters(self) -> tuple[str, ...]:
        targets = (
            p.current for p in self.param_set
            if p.param_type is ParameterType.TARGET and p.current is not None
        )
        return tuple(dict.fromkeys((*self._target_parameters, *targets)))

    def generate_geometry(self, target_mapping=None, *, context=None):
        """원점에서 평가한 로컬 점과 링크를 반환한다."""
        return self._geometry_at(
            self.evaluated_parameters(context), target_mapping, context, 0.0, 0.0, self.side or 1,
        )

    def _geometry_at(self, params, mapping, context, origin_x, origin_z, sign):
        definition = self.geometry_def
        if definition is None or not definition.points:
            raise ValueError(f"{self.name!r}: geometry requires at least one point")
        values = {"station": self.current_station, "base_elevation": None, "grade": None}
        if context is not None:
            values.update(context.values)
            values.update(station=context.station, base_elevation=context.base_elevation, grade=context.grade)
        values.update((p.name, p.current) for p in params)
        coordinates, errors = definition._evaluate_coordinates(values)
        if errors:
            raise ValueError(f"{self.name!r}: " + " | ".join(errors))
        points = tuple(
            AssemblyPoint(point.code, *location)
            for point, location in zip(definition.points, coordinates, strict=True)
        )
        links = tuple(
            AssemblyLink(link.code, points[link.start_index], points[link.end_index], shape_code)
            for link, shape_code in zip(definition.links, definition._shape_codes, strict=True)
        )
        return points, links
