from dataclasses import dataclass, field

from myalignment.assembly.codes import LinkCode, PointCode, ShapeCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.parameter.parameterized import ParameterizedSubassembly
from myalignment.assembly.parameter.parameter_set import ParameterSet
from myalignment.assembly.point import AssemblyPoint


@dataclass(frozen=True, slots=True)
class ParametricShoulder(ParameterizedSubassembly):
    """폭과 횡단 구배를 파라미터로 지정하는 갓길."""

    name: str = "ParametricShoulder"
    param_set: ParameterSet = field(default_factory=ParameterizedSubassembly.create_shoulder_params)

    @classmethod
    def default_parameters(cls):
        return list(cls.create_shoulder_params())

    @classmethod
    def create(cls, width: float = 2.0, slope: float = -0.04, side: int = 1) -> "ParametricShoulder":
        return cls(side=side, param_set=cls.create_shoulder_params(width, slope))

    def generate_geometry(self, target_mapping=None):
        width, slope = self.get_param("width", 2.0), self.get_param("slope", -0.04)
        start = AssemblyPoint(PointCode.SHOULDER_INNER, 0.0, 0.0)
        end = AssemblyPoint(PointCode.SHOULDER_OUTER, width, width * slope)
        return (start, end), (AssemblyLink(LinkCode.SHOULDER, start, end, ShapeCode.SHOULDER),)
