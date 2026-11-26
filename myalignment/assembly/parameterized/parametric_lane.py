from dataclasses import dataclass, field

from myalignment.assembly.codes import LinkCode, PointCode, ShapeCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.parameter.parameterized import ParameterizedSubassembly
from myalignment.assembly.parameter.parameter_set import ParameterSet
from myalignment.assembly.parameter.superelevation_binding import SuperelevationBinding
from myalignment.assembly.point import AssemblyPoint


@dataclass(frozen=True, slots=True)
class ParametricLane(ParameterizedSubassembly):
    """폭과 횡단 구배를 파라미터로 지정하는 차로."""

    name: str = "ParametricLane"
    param_set: ParameterSet = field(default_factory=ParameterizedSubassembly.create_lane_params)

    def __post_init__(self):
        if self.param_set.get("apply_aor") is not None:
            object.__setattr__(self, "apply_aor", self.get_param("apply_aor") in (True, "True"))

    @classmethod
    def default_parameters(cls):
        return list(cls.create_lane_params())

    @classmethod
    def create(
        cls, width: float = 3.5, slope: float = -0.02, side: int = 1,
        superelevation: SuperelevationBinding | None = None,
    ) -> "ParametricLane":
        return cls(side=side, param_set=cls.create_lane_params(width, slope), superelevation_binding=superelevation)

    def generate_geometry(self, target_mapping=None):
        return self._lane_geometry(self.evaluated_parameters())

    def _geometry_at(self, params, mapping, context, origin_x, origin_z, sign):
        return self._lane_geometry(params)

    def _lane_geometry(self, params):
        width, slope = params.get_value("width", 3.5), params.get_value("slope", -0.02)
        # The road binding already sets the cross slope at the attachment.
        apply_cant = self.apply_aor and self.superelevation_binding is None
        start = AssemblyPoint(PointCode.CROWN, 0.0, 0.0, apply_aor=apply_cant)
        end = AssemblyPoint(PointCode.LANE_EDGE, width, width * slope, apply_aor=apply_cant)
        return (start, end), (AssemblyLink(LinkCode.PAVEMENT, start, end, ShapeCode.PAVEMENT),)
