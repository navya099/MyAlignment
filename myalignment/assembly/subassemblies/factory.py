from __future__ import annotations

import math

from myalignment.assembly.assembly import Assembly, AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.curb_and_sidewalk import CurbAndSidewalkSubassembly
from myalignment.assembly.subassemblies.ditch import VShapeDitch
from myalignment.assembly.subassemblies.shoulder import Shoulder
from myalignment.assembly.subassemblies.side_slope import SideSlope


class CurbSidewalkFactory:
    """연석과 보도가 포함된 대칭 도시 도로 단면을 만든다."""

    @classmethod
    def urban_road(
        cls, lane_width: float = 3.5, lane_count: int = 2, shoulder_width: float = 0.5,
        curb_height: float = 0.15, sidewalk_width: float = 2.0, sidewalk_slope: float = -0.02,
        slope_ratio: float = 1.5, slope_height: float = 3.0,
    ) -> Assembly:
        """각 측에 차로, 갓길, 연석과 보도, 사면을 순서대로 배치한다."""
        for name, value in (
            ("shoulder_width", shoulder_width), ("slope_ratio", slope_ratio), ("slope_height", slope_height),
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        builder = cls._add_lanes(AssemblyBuilder("도시도로단면"), lane_width, lane_count)
        return (
            builder
            .add_both(lambda side: Shoulder(side=side, width=shoulder_width))
            .add_both(lambda side: CurbAndSidewalkSubassembly.create(
                side=side, curb_height=curb_height, sidewalk_width=sidewalk_width, sidewalk_slope=sidewalk_slope,
            ))
            .add_both(lambda side: SideSlope(side=side, slope_ratio=slope_ratio, height=slope_height))
            .build()
        )

    @classmethod
    def urban_road_with_drainage(
        cls, lane_width: float = 3.5, curb_height: float = 0.15, sidewalk_width: float = 2.0,
    ) -> Assembly:
        """각 측에 차로 두 개, V형 배수로, 연석과 보도를 배치한다."""
        builder = cls._add_lanes(AssemblyBuilder("배수도시도로"), lane_width, 2)
        return (
            builder
            .add_both(lambda side: VShapeDitch(side=side, width=0.5, depth=0.3))
            .add_both(lambda side: CurbAndSidewalkSubassembly.create(
                side=side, curb_height=curb_height, sidewalk_width=sidewalk_width,
            ))
            .build()
        )

    @staticmethod
    def _add_lanes(builder: AssemblyBuilder, width: float, count: int) -> AssemblyBuilder:
        if type(count) is not int or count < 1:
            raise ValueError("lane_count must be a positive integer")
        if not math.isfinite(width) or width <= 0:
            raise ValueError("lane_width must be finite and positive")
        for _ in range(count):
            builder.add_both(lambda side: BasicLane(side=side, width=width))
        return builder
