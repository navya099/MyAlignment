from __future__ import annotations

from dataclasses import dataclass, field, replace
import math
from typing import TYPE_CHECKING, Self

from myalignment.assembly.parameter.cant_binding import CantBinding
from myalignment.assembly.parameter.superelevation_binding import SuperelevationBinding
from myalignment.assembly.parameter.parameter import Parameter, ParameterValue
from myalignment.assembly.parameter.parameter_set import ParameterSet
from myalignment.assembly.parameter.parameter_type import ParameterType as Kind
from myalignment.assembly.subassembly import Subassembly

if TYPE_CHECKING:
    from myalignment.assembly.section_context import SectionContext


@dataclass(frozen=True, slots=True)
class ParameterizedSubassembly(Subassembly):
    """조건 컨텍스트와 파라미터를 사용해 횡단 형상을 배치하는 기반 클래스."""

    uses_section_context = True

    name: str = "Parameterized"
    param_set: ParameterSet = ParameterSet()
    superelevation_binding: SuperelevationBinding | None = field(default=None, kw_only=True)
    cant_binding: CantBinding | None = field(default=None, kw_only=True)
    current_station: float = field(default=0.0, kw_only=True)

    @property
    def has_station_binding(self) -> bool:
        return self.superelevation_binding is not None or self.cant_binding is not None

    def with_station(self, station: float) -> Self:
        """측점과 그 측점에서 평가한 파라미터를 저장한 새 객체."""
        updated = replace(self, current_station=station)
        return replace(updated, param_set=updated.evaluated_parameters())

    def with_superelevation(self, binding: SuperelevationBinding) -> Self:
        """편구배 원본을 연결한다."""
        return replace(self, superelevation_binding=binding)

    def with_cant(self, binding: CantBinding) -> Self:
        """캔트 원본을 연결한다."""
        return replace(self, cant_binding=binding)

    @classmethod
    def default_parameters(cls) -> list[Parameter]:
        return []

    def with_params(self, *, context: SectionContext | None = None, **kwargs: ParameterValue) -> Self:
        """입력값과 수식 결과를 갱신한 새 서브어셈블리를 반환한다."""
        updated = replace(self, param_set=self.param_set.update_values(**kwargs))
        return replace(updated, param_set=updated.evaluated_parameters(context))

    def get_param(self, name: str, default: ParameterValue = None) -> ParameterValue:
        return self.param_set.get_value(name, default)

    def evaluated_parameters(self, context: SectionContext | None = None) -> ParameterSet:
        """측점, 기준 표고, 구배와 사용자 변수로 수식을 평가한다."""
        station = self.current_station if context is None else context.station
        if not math.isfinite(station):
            raise ValueError("station must be finite")
        binding_station = station if context is None or context.binding_station is None else context.binding_station
        params = self.param_set
        updates = {}
        if self.superelevation_binding is not None and params.get("slope") is not None:
            binding = self.superelevation_binding
            enabled = params.get_value("apply_aor", self.apply_aor) in (True, "True")
            updates["slope"] = binding.slope_at(binding_station) if enabled else binding.default_slope
        if self.cant_binding is not None:
            offsets = self.cant_binding.rail_offsets_at(binding_station)
            updates.update(
                (name, offset) for name, offset in zip(("cant_left_offset", "cant_right_offset"), offsets)
                if params.get(name) is not None
            )
        values = {} if context is None else {
            **context.values, "base_elevation": context.base_elevation, "grade": context.grade,
        }
        return params.update_values(**updates).evaluate_computed({**values, "station": station})

    def place_at(self, origin_x, origin_z, side_sign=None, target_mapping=None, *, context=None):
        """파라미터를 배치 위치의 컨텍스트에서 평가한다."""
        return self._place_with_context(origin_x, origin_z, side_sign, target_mapping, context)

    def _place_with_context(self, origin_x, origin_z, side_sign, target_mapping, context):
        sign = side_sign if side_sign is not None else self.side or 1
        geometry = self._geometry_at(self.evaluated_parameters(context), target_mapping, context, origin_x, origin_z, sign)
        return self._transform_geometry(*geometry, origin_x, origin_z, sign)

    def _geometry_at(self, params, mapping, context, origin_x, origin_z, sign):
        return replace(self, param_set=params).generate_geometry(mapping)

    @staticmethod
    def create_lane_params(width: float = 3.5, slope: float = -0.02) -> ParameterSet:
        return ParameterSet((
            Parameter("width", default=width, unit="m", min_value=0.5, max_value=10),
            Parameter("slope", default=slope, unit="m/m", min_value=-0.20, max_value=0.20),
            Parameter("apply_aor", Kind.ENUM, default=False, options=(True, False, "True", "False")),
            Parameter("computed_slope_percent", Kind.COMPUTED, expression="slope * 100", unit="%"),
            Parameter("computed_elevation_drop", Kind.COMPUTED, expression="width * slope", unit="m"),
            Parameter("computed_area", Kind.OUTPUT, expression="width", unit="m²",
                      description="차로 1m 길이당 평면적"),
        )).evaluate_computed()

    @staticmethod
    def create_shoulder_params(width: float = 2.0, slope: float = -0.04) -> ParameterSet:
        return ParameterSet((
            Parameter("width", default=width, unit="m", min_value=0.5, max_value=5),
            Parameter("slope", default=slope, unit="m/m", min_value=-0.10, max_value=0.10),
            Parameter("computed_elevation_drop", Kind.COMPUTED, expression="width * slope", unit="m"),
        )).evaluate_computed()

    @staticmethod
    def create_slope_params(slope_ratio: float = 1.5, height: float = 5.0) -> ParameterSet:
        return ParameterSet((
            Parameter("slope_ratio", default=slope_ratio, unit="1:n", min_value=0.5, max_value=10),
            Parameter("height", default=height, unit="m", min_value=0.5, max_value=50),
            Parameter("target_surface", Kind.TARGET, default="TargetDTM"),
            Parameter("computed_horizontal_length", Kind.COMPUTED, expression="slope_ratio * height", unit="m"),
            Parameter("computed_grade_percent", Kind.COMPUTED, expression="100 / slope_ratio", unit="%"),
        )).evaluate_computed()
