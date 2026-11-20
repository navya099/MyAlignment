from __future__ import annotations

import math
from typing import TYPE_CHECKING

from myalignment.turnout.crossover_validator import CrossoverValidator
from myalignment.turnout.scissors_crossover import ScissorsCrossover
from myalignment.turnout.scissors_type import ScissorsCrossoverType
from myalignment.turnout.turnout import Turnout
from myalignment.turnout.type import TurnoutSide, TurnoutType

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment


class ScissorsCrossoverBuilder:
    """Scissors Crossover의 수동 및 자동 배치 빌더."""

    def __init__(self, name: str = "Scissors1"):
        self._name = name
        self._alignment1 = ""
        self._alignment2 = ""
        self._turnout_type: TurnoutType | None = None
        self._crossover_type = ScissorsCrossoverType.STANDARD
        self._stations = (0.0, 0.0, 0.0, 0.0)
        self._sides = (TurnoutSide.RIGHT, TurnoutSide.RIGHT)
        self._auto_placement: tuple[Alignment, Alignment, float] | None = None

    def with_alignments(self, a1: str, a2: str) -> ScissorsCrossoverBuilder:
        self._alignment1, self._alignment2 = a1, a2
        return self

    def with_turnout_type(self, tt: TurnoutType) -> ScissorsCrossoverBuilder:
        self._turnout_type = tt
        return self

    def with_stations(
        self, sta1: float, sta2: float, sta3: float, sta4: float
    ) -> ScissorsCrossoverBuilder:
        self._stations = (sta1, sta2, sta3, sta4)
        self._auto_placement = None
        return self

    def symmetric_at(self, center: float, spacing: float) -> ScissorsCrossoverBuilder:
        """각 본선의 동일한 수치 측점을 기준으로 수동 대칭 배치."""
        start, end = center - spacing, center + spacing
        return self.with_stations(start, end, start, end).as_symmetric()

    def symmetric_auto_at(
        self, alignment1: Alignment, alignment2: Alignment, center: float
    ) -> ScissorsCrossoverBuilder:
        """본선1의 center 측점에서 두 평행 직선 본선에 대칭 배치.

        본선2 중심 측점, 턴아웃 간격, 분기 방향은 build()에서 계산한다.
        """
        if not math.isfinite(center):
            raise ValueError("중심 측점은 유한해야 합니다")
        self.with_alignments(alignment1.name, alignment2.name)
        self._auto_placement = (alignment1, alignment2, center)
        return self.as_symmetric()

    def with_sides(
        self, side1: TurnoutSide, side2: TurnoutSide
    ) -> ScissorsCrossoverBuilder:
        self._sides = (side1, side2)
        return self

    def as_symmetric(self) -> ScissorsCrossoverBuilder:
        self._crossover_type = ScissorsCrossoverType.SYMMETRIC
        return self

    def build(self) -> ScissorsCrossover:
        tt = self._turnout_type
        if tt is None:
            raise ValueError("turnout_type이 설정되지 않음")
        if not self._alignment1 or not self._alignment2 or self._alignment1 == self._alignment2:
            raise ValueError("서로 다른 두 본선 이름이 필요합니다")

        sta1, sta2, sta3, sta4 = self._stations
        side1, side2 = self._sides
        if self._auto_placement is not None:
            alignment1, alignment2, center = self._auto_placement
            signed_distance, center2 = alignment1.distance_to_alignment(center, alignment2)
            azimuth_delta = CrossoverValidator._normalize_angle(
                alignment2.tangent_at(center2) - alignment1.tangent_at(center)
            )
            if abs(azimuth_delta) > CrossoverValidator.ANGLE_TOL:
                raise ValueError("두 본선은 같은 방향으로 평행해야 합니다")

            diagonal_rise = abs(signed_distance) - 2 * tt.rise
            if diagonal_rise <= 0:
                raise ValueError("대각 연결선에 필요한 선간 거리가 부족합니다")

            # 양 끝 턴아웃의 run과 frog 각도를 만족하는 대각 연결선의 종방향 길이.
            spacing = tt.run + diagonal_rise / (2 * math.tan(tt.frog_angle))
            sta1, sta2 = center - spacing, center + spacing
            sta3, sta4 = center2 - spacing, center2 + spacing
            if signed_distance > 0:
                side1, side2 = TurnoutSide.LEFT, TurnoutSide.RIGHT
            else:
                side1, side2 = TurnoutSide.RIGHT, TurnoutSide.LEFT

        c14, c32, c12, c34 = (f"{self._name}_C{pair}" for pair in (14, 32, 12, 34))

        def turnout(number, source, branch, station, side):
            return Turnout(
                name=f"{self._name}_T{number}",
                turnout_type=tt,
                source_alignment_name=source,
                branch_alignment_name=branch,
                station_on_source=station,
                side=side,
            )

        scissors = ScissorsCrossover(
            name=self._name,
            crossover_type=self._crossover_type,
            turnout1=turnout(1, self._alignment1, c14, sta1, side1),
            turnout2=turnout(2, self._alignment1, c12, sta2, side1),
            turnout3=turnout(3, self._alignment2, c32, sta3, side2),
            turnout4=turnout(4, self._alignment2, c34, sta4, side2),
            source_alignment1_name=self._alignment1,
            source_alignment2_name=self._alignment2,
            connecting_alignment_names=(c14, c32, c12, c34),
        )
        if self._auto_placement is None:
            return scissors

        geometry = scissors.compute_geometry(alignment1, alignment2)
        if not geometry.is_valid:
            raise ValueError(geometry.error_message)
        return scissors.with_geometry(geometry)
