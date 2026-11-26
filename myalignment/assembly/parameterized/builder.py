from collections.abc import Iterable
from typing import Self

from myalignment.assembly.assembly import Assembly, AssemblyBuilder
from myalignment.assembly.parameter.cant_binding import CantBinding
from myalignment.assembly.parameter.superelevation_binding import SuperelevationBinding
from myalignment.assembly.parameterized.parametric_rail import ParametricRailTrack
from myalignment.cant.curve import CantCurve, CantPivotMethod
from myalignment.superelevation.collection import SuperelevationCollection
from myalignment.superelevation.critical_station import CrossSegmentType
from myalignment.assembly.parameterized.parametric_lane import ParametricLane
from myalignment.assembly.parameterized.parametric_shoulder import ParametricShoulder
from myalignment.assembly.parameterized.parametric_slope import ParametricSlope


class ParametricAssemblyBuilder:
    """양쪽 차로, 갓길과 사면을 조립한다."""

    def __init__(self, name: str = "ParametricAssembly"):
        self._name = name
        self._lane = (3.5, -0.02)
        self._shoulder = (2.0, -0.04)
        self._slope = (1.5, 5.0)
        self._superelevation: SuperelevationCollection | None = None
        self._segment: CrossSegmentType | None = None
        self._cant: CantBinding | None = None

    def with_lane(self, width: float, slope: float = -0.02) -> Self:
        self._lane = width, slope
        return self

    def with_shoulder(self, width: float, slope: float = -0.04) -> Self:
        self._shoulder = width, slope
        return self

    def with_slope(self, ratio: float, height: float = 5.0) -> Self:
        self._slope = ratio, height
        return self

    def with_superelevation(
        self, collection: SuperelevationCollection, segment_type: CrossSegmentType | None = None,
    ) -> Self:
        """좌우 차로의 대응 편구배 세그먼트를 연결한다."""
        if segment_type is not None and not isinstance(segment_type, CrossSegmentType):
            raise ValueError("segment_type must be a CrossSegmentType")
        self._superelevation = collection
        self._segment = segment_type
        return self

    def with_cant(
        self, cant_curves: Iterable[CantCurve], pivot_method: CantPivotMethod | None = None, *,
        gauge: float = 1.435, default_cant: float = 0.0,
    ) -> Self:
        """캔트가 바인딩된 철도 중심 궤도 단면을 설정한다."""
        pivot = CantPivotMethod.CENTERLINE if pivot_method is None else pivot_method
        self._cant = CantBinding(tuple(cant_curves), pivot, gauge, default_cant)
        return self

    def _build_lane(self, side: int) -> ParametricLane:
        lane = ParametricLane.create(*self._lane, side=side)
        if self._superelevation is None:
            return lane
        kind = self._segment.name.split("_", 1)[1] if self._segment is not None else "OUT_LANE"
        lateral = "LEFT" if side < 0 else "RIGHT"
        binding = SuperelevationBinding(self._superelevation, CrossSegmentType[f"{lateral}_{kind}"], self._lane[1])
        return lane.with_params(apply_aor=True).with_superelevation(binding)

    def build(self) -> Assembly:
        if self._cant is not None:
            if self._superelevation is not None:
                raise ValueError("Choose either road superelevation or rail cant")
            return AssemblyBuilder(self._name).add_center(ParametricRailTrack.create(cant=self._cant)).build()
        return (
            AssemblyBuilder(self._name)
            .add_both(self._build_lane)
            .add_both(lambda side: ParametricShoulder.create(*self._shoulder, side=side))
            .add_both(lambda side: ParametricSlope.create(*self._slope, side=side))
            .build()
        )
