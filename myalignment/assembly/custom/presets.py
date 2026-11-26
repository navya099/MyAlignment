from dataclasses import dataclass, replace

from myalignment.assembly.assembly import Assembly, AssemblyBuilder
from myalignment.assembly.codes import LinkCode, PointCode, ShapeCode
from myalignment.assembly.custom.builder import CustomSubassemblyBuilder
from myalignment.assembly.custom.custom_subassembly import CustomSubassembly
from myalignment.assembly.parameter.parameter import Parameter
from myalignment.assembly.parameter.parameter_set import ParameterSet
from myalignment.assembly.parameter.parameter_type import ParameterType
from myalignment.assembly.parameterized.parametric_slope import _daylight
from myalignment.assembly.subassemblies.sidewalk import SidewalkSubassembly
from myalignment.target.target_type import TargetType


def custom_lane(width: float = 3.5, slope: float = -0.02, side: int = 1) -> CustomSubassembly:
    """폭과 구배로 정의한 두께 0.1m의 포장 차로."""
    return (
        CustomSubassemblyBuilder("CustomLane").with_side(side)
        .with_parameter("width", width, "m", 0.5, 10.0)
        .with_parameter("slope", slope, "m/m", -0.2, 0.2)
        .with_parameter("thickness", 0.1, "m", min_value=1e-6)
        .with_output("lane_area", "width", "m²", "차로 1m 길이당 평면적")
        .add_point(PointCode.CROWN)
        .add_point(PointCode.LANE_EDGE, "width", "slope * width")
        .add_point(PointCode.PAVEMENT_BOTTOM, "width", "slope * width - thickness")
        .add_point(PointCode.PAVEMENT_BOTTOM, "0", "-thickness")
        .add_link(0, 1, LinkCode.PAVEMENT)
        .add_link(1, 2, LinkCode.PAVEMENT_SIDE)
        .add_link(2, 3, LinkCode.PAVEMENT_BOTTOM)
        .add_link(3, 0, LinkCode.PAVEMENT_SIDE)
        .add_shape("pavement", (0, 1, 2, 3), ShapeCode.PAVEMENT)
        .build()
    )


def custom_shoulder_with_curb(
    shoulder_width: float = 2.0, curb_height: float = 0.15, side: int = 1,
) -> CustomSubassembly:
    """갓길 끝에 닫힌 연석 단면을 추가하는 빌더 예제."""
    return (
        CustomSubassemblyBuilder("ShoulderCurb").with_side(side)
        .with_parameter("shoulder_width", shoulder_width, "m", min_value=1e-6)
        .with_parameter("curb_height", curb_height, "m", min_value=1e-6)
        .with_parameter("curb_width", 0.15, "m", min_value=1e-6)
        .with_parameter("shoulder_slope", -0.04, "m/m")
        .with_computed("shoulder_z", "shoulder_width * shoulder_slope", "m")
        .add_point(PointCode.SHOULDER_INNER)
        .add_point(PointCode.SHOULDER_OUTER, "shoulder_width", "shoulder_z")
        .add_point(PointCode.CURB_FACE, "shoulder_width", "shoulder_z + curb_height")
        .add_point(PointCode.CURB_BACK, "shoulder_width + curb_width", "shoulder_z")
        .add_point(PointCode.CURB_TOP, "shoulder_width + curb_width", "shoulder_z + curb_height")
        .add_link(0, 1, LinkCode.SHOULDER, ShapeCode.SHOULDER)
        .add_link(1, 2, LinkCode.CURB)
        .add_link(2, 4, LinkCode.CURB)
        .add_link(4, 3, LinkCode.CURB)
        .add_link(3, 1, LinkCode.DATUM)
        .add_shape("curb", (1, 2, 3, 4), ShapeCode.CURB)
        .build()
    )


def custom_v_ditch(top_width: float = 1.5, depth: float = 0.5, side: int = 1) -> CustomSubassembly:
    """대칭 V형 배수로와 한쪽 사면 길이."""
    return (
        CustomSubassemblyBuilder("VDitch").with_side(side)
        .with_parameter("top_width", top_width, "m", min_value=1e-6)
        .with_parameter("depth", depth, "m", min_value=1e-6)
        .with_computed("slope_length", "((top_width / 2)**2 + depth**2)**0.5", "m")
        .add_point(PointCode.DITCH_INNER)
        .add_point(PointCode.DITCH_BOTTOM, "top_width / 2", "-depth")
        .add_point(PointCode.DITCH_OUTER, "top_width", "0")
        .add_link(0, 1, LinkCode.DITCH)
        .add_link(1, 2, LinkCode.DITCH)
        .build()
    )


@dataclass(frozen=True, slots=True)
class _CustomSlope(CustomSubassembly):
    def _geometry_at(self, params, mapping, context, origin_x, origin_z, sign):
        points, links = super(_CustomSlope, self)._geometry_at(params, mapping, context, origin_x, origin_z, sign)
        key = params.get_value("target_surface")
        reference = mapping.get(key) if mapping is not None and key is not None else None
        if context is None or reference is None or reference.target_type is not TargetType.SURFACE:
            return points, links
        hit = _daylight(
            context, reference.object_name, origin_x, (context.base_elevation or 0.0) + origin_z,
            sign, params.get_value("slope_ratio"),
        )
        if hit is None:
            return points, links
        end = replace(points[1], x=hit[0], z=hit[1], is_parametric=True, apply_aor=False)
        return (points[0], end), (replace(links[0], end=end),)


def custom_slope(
    slope_ratio: float = 1.5, height: float = 5.0, side: int = 1, *, target_surface: str = "TargetDTM",
) -> CustomSubassembly:
    """지표면 타깃과의 교점을 찾고 교점이 없으면 지정 높이를 적용한다."""
    part = (
        CustomSubassemblyBuilder("CustomSlope").with_side(side)
        .with_parameter("slope_ratio", slope_ratio, "1:n", min_value=1e-6)
        .with_parameter("height", height, "m", min_value=1e-6)
        .with_computed("horizontal_length", "slope_ratio * height", "m")
        .add_point(PointCode.HINGE_POINT)
        .add_point(PointCode.CATCH_POINT, "horizontal_length", "-height")
        .add_link(0, 1, LinkCode.SLOPE)
        .build()
    )
    target = Parameter("target_surface", ParameterType.TARGET, default=target_surface)
    return _CustomSlope(
        name=part.name, side=side, geometry_def=part.geometry_def,
        param_set=ParameterSet((*part.param_set, target)),
    )


def custom_urban_road(
    lane_width: float = 3.5, lane_count: int = 2, sidewalk_width: float = 2.0,
    curb_height: float = 0.15, slope_ratio: float = 1.5,
) -> Assembly:
    """좌우에 차로, 갓길·연석, 보도와 사면을 배치한다."""
    if type(lane_count) is not int or lane_count < 1:
        raise ValueError("lane_count must be a positive integer")
    builder = AssemblyBuilder("CustomUrbanRoad")
    for _ in range(lane_count):
        builder.add_both(lambda side: custom_lane(width=lane_width, side=side))
    return (
        builder
        .add_both(lambda side: custom_shoulder_with_curb(0.5, curb_height, side))
        .add_both(lambda side: SidewalkSubassembly.create(width=sidewalk_width, side=side))
        .add_both(lambda side: custom_slope(slope_ratio, 3.0, side))
        .build()
    )
