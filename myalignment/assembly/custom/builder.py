from __future__ import annotations

from dataclasses import replace
from enum import Enum
from typing import Self

from myalignment.assembly.codes import LinkCode, ShapeCode
from myalignment.assembly.custom.custom_subassembly import CustomSubassembly
from myalignment.assembly.custom.geometry_definition import (
    GeometryDefinition, LinkDefinition, PointDefinition, ShapeDefinition,
)
from myalignment.assembly.parameter.parameter import Parameter, ParameterValue
from myalignment.assembly.parameter.parameter_set import ParameterSet
from myalignment.assembly.parameter.parameter_type import ParameterType
from myalignment.assembly.section_context import SectionContext


class CustomSubassemblyBuilder:
    """입력 파라미터와 로컬 단면을 선언하는 빌더."""

    def __init__(self, name: str = "Custom"):
        self._name = name
        self._side = 1
        self._parameters: list[Parameter] = []
        self._points: list[PointDefinition] = []
        self._links: list[LinkDefinition] = []
        self._shapes: list[ShapeDefinition] = []

    def with_side(self, side: int) -> Self:
        self._side = side
        return self

    def with_parameter(
        self, name: str, default: ParameterValue = 0.0, unit: str = "",
        min_value: float | None = None, max_value: float | None = None, description: str = "",
    ) -> Self:
        self._parameters.append(Parameter(
            name, default=default, unit=unit, min_value=min_value, max_value=max_value, description=description,
        ))
        return self

    def with_computed(self, name: str, expression: str, unit: str = "", description: str = "") -> Self:
        self._parameters.append(Parameter(
            name, ParameterType.COMPUTED, expression=expression, unit=unit, description=description,
        ))
        return self

    def with_output(self, name: str, expression: str, unit: str = "", description: str = "") -> Self:
        """다른 수식에서도 사용할 수 있는 읽기 전용 결과값을 추가한다."""
        self._parameters.append(Parameter(
            name, ParameterType.OUTPUT, expression=expression, unit=unit, description=description,
        ))
        return self

    def add_point(self, code: Enum, x: str = "0.0", z: str = "0.0") -> Self:
        self._points.append(PointDefinition(code, x, z))
        return self

    def add_link(
        self, start_index: int, end_index: int, code: Enum = LinkCode.PAVEMENT,
        shape_code: ShapeCode | None = None,
    ) -> Self:
        self._links.append(LinkDefinition(start_index, end_index, code, shape_code))
        return self

    def add_shape(self, name: str, link_indices: tuple[int, ...], shape_code: ShapeCode) -> Self:
        self._shapes.append(ShapeDefinition(name, link_indices, shape_code))
        return self

    def build(self, *, context: SectionContext | None = None) -> CustomSubassembly:
        """기본값과 선택한 측점 컨텍스트에서 수식과 단면 정의를 검증한다."""
        subassembly = CustomSubassembly(
            name=self._name, side=self._side, param_set=ParameterSet(tuple(self._parameters)),
            geometry_def=GeometryDefinition(self._points, self._links, self._shapes),
            current_station=0.0 if context is None else context.station,
        )
        params = subassembly.evaluated_parameters(context)
        subassembly._geometry_at(params, None, context, 0.0, 0.0, self._side or 1)
        return replace(subassembly, param_set=params)
