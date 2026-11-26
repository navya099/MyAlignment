from dataclasses import dataclass, field
import math

from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.parameter.parameterized import ParameterizedSubassembly
from myalignment.assembly.parameter.parameter_set import ParameterSet
from myalignment.assembly.point import AssemblyPoint
from myalignment.target.target_type import TargetType


_TOLERANCE = 1e-8


def _intersect(segment, offset, elevation, sign, slope):
    (ax, az), (bx, bz) = sorted((sign * (x - offset), z) for x, z in segment)
    if bx < 0:
        return None
    if bx - ax <= _TOLERANCE:
        design = elevation + max(0, bx) * slope
        return max(0, bx) if min(az, bz) - _TOLERANCE <= design <= max(az, bz) + _TOLERANCE else None
    start = max(0.0, ax)
    za = az + (bz - az) * (start - ax) / (bx - ax)
    fa, fb = za - (elevation + start * slope), bz - (elevation + bx * slope)
    if abs(fa) <= _TOLERANCE:
        return start
    if abs(fb) <= _TOLERANCE:
        return bx
    if (fa > 0) == (fb > 0):
        return None
    return start + (bx - start) * fa / (fa - fb)


def _daylight(context, target, offset, elevation, sign, ratio):
    if context is None or target is None or context.surface_section_at is None:
        return None
    segments = tuple(context.surface_section_at(target))
    ground = context.surface_elevation_at(target, offset) if context.surface_elevation_at is not None else None
    directions = (1, -1) if ground is None else (1,) if ground > elevation else (-1,)
    candidates = []
    for direction in directions:
        slope = direction / ratio
        for segment in segments:
            distance = _intersect(segment, offset, elevation, sign, slope)
            if distance is not None:
                candidates.append((distance, distance * slope))
    return min(candidates, default=None)


@dataclass(frozen=True, slots=True)
class ParametricSlope(ParameterizedSubassembly):
    """타깃 TIN에서 접점을 찾고 미교차 시 지정 높이를 사용하는 사면."""

    name: str = "ParametricSlope"
    param_set: ParameterSet = field(default_factory=ParameterizedSubassembly.create_slope_params)

    @property
    def target_parameters(self):
        target = self.get_param("target_surface")
        return (target,) if target else ()

    @classmethod
    def default_parameters(cls):
        return list(cls.create_slope_params())

    @classmethod
    def create(cls, slope_ratio: float = 1.5, height: float = 5.0, side: int = 1) -> "ParametricSlope":
        return cls(side=side, param_set=cls.create_slope_params(slope_ratio, height))

    def generate_geometry(self, target_mapping=None, *, context=None):
        return self._geometry_at(self.evaluated_parameters(context), target_mapping, context, 0, 0, self.side or 1)

    def _geometry_at(self, params, mapping, context, origin_x, origin_z, sign):
        ratio, height = params.get_value("slope_ratio", 1.5), params.get_value("height", 5.0)
        if not all(math.isfinite(value) and value > 0 for value in (ratio, height)):
            raise ValueError("slope_ratio and height must be finite and positive")
        key = params.get_value("target_surface", "TargetDTM")
        reference = mapping.get(key) if mapping is not None and key is not None else None
        target = reference.object_name if reference is not None and reference.target_type is TargetType.SURFACE else None
        base = context.base_elevation if context is not None else None
        hit = _daylight(context, target, origin_x, (base or 0.0) + origin_z, sign, ratio)
        width, change = hit if hit is not None else (ratio * height, -height)
        start = AssemblyPoint(PointCode.HINGE_POINT, 0.0, 0.0)
        end = AssemblyPoint(
            PointCode.CATCH_POINT, width, change, is_parametric=hit is not None,
            apply_aor=False if hit is not None else None,
        )
        return (start, end), (AssemblyLink(LinkCode.SLOPE, start, end),)
