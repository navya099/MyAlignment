from dataclasses import dataclass, field

from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.parameter.cant_binding import CantBinding
from myalignment.assembly.parameter.parameter import Parameter
from myalignment.assembly.parameter.parameter_set import ParameterSet
from myalignment.assembly.parameter.parameterized import ParameterizedSubassembly
from myalignment.assembly.point import AssemblyPoint


def _rail_parameters(gauge: float = 1.435) -> ParameterSet:
    return ParameterSet((
        Parameter("gauge", default=gauge, unit="m", min_value=1.0, max_value=1.8),
        Parameter("cant_left_offset", unit="m"),
        Parameter("cant_right_offset", unit="m"),
    ))


@dataclass(frozen=True, slots=True)
class ParametricRailTrack(ParameterizedSubassembly):
    """중심에 배치하는 궤간·캔트 기반 레일 단면."""

    name: str = "ParametricRailTrack"
    side: int = 0
    param_set: ParameterSet = field(default_factory=_rail_parameters)

    @classmethod
    def default_parameters(cls):
        return list(_rail_parameters())

    @classmethod
    def create(cls, gauge: float | None = None, cant: CantBinding | None = None) -> "ParametricRailTrack":
        width = (cant.gauge if cant is not None else 1.435) if gauge is None else gauge
        return cls(param_set=_rail_parameters(width), cant_binding=cant)

    def generate_geometry(self, target_mapping=None):
        return self._rail_geometry(self.evaluated_parameters())

    def _geometry_at(self, params, mapping, context, origin_x, origin_z, sign):
        return self._rail_geometry(params)

    def _rail_geometry(self, params):
        half_gauge = params.get_value("gauge", 1.435) / 2
        left = params.get_value("cant_left_offset", 0)
        right = params.get_value("cant_right_offset", 0)
        apply_cant = None if self.cant_binding is None and not (left or right) else False
        a = AssemblyPoint(PointCode.LEFT_RAIL, -half_gauge, left, apply_aor=apply_cant)
        b = AssemblyPoint(PointCode.RIGHT_RAIL, half_gauge, right, apply_aor=apply_cant)
        return (a, b), (AssemblyLink(LinkCode.PAVEMENT, a, b),)
