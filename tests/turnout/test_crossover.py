import math
import pytest

from cadgeom import Point2d
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.turnout.crossover import Crossover
from myalignment.turnout.crossover_builder import CrossoverBuilder
from myalignment.turnout.crossover_type import CrossoverType
from myalignment.turnout.crossover_validator import CrossoverValidator
from myalignment.turnout.turnout import Turnout
from myalignment.turnout.type import TurnoutType
from myalignment.turnout.type import TurnoutSide


class MockAlignment:
    """테스트용 Alignment 목업."""
    def __init__(self, name: str, coords: list):
        self.name = name
        # 테스트 검증에 필요한 최소한의 실제 Alignment 빌드 결과를 품도록 구성
        self.rail = (
            AlignmentBuilder(name)
            .with_pi_coords(coords)
            .with_radii([None] * len(coords))
            .as_rail_alignment(gauge=1.435)
            .build()
        )
        self.is_rail = self.rail.is_rail
        self.gauge = self.rail.gauge

    # CrossoverValidator 등이 요구하는 실제 Alignment 메서드들을 self.rail로 위임
    def evaluate_at(self, station: float):
        if hasattr(self.rail, "evaluate_at"):
            return self.rail.evaluate_at(station)
        return Point2d(station, 0)

    def tangent_at(self, station: float):
        if hasattr(self.rail, "tangent_at"):
            return self.rail.tangent_at(station)
        return Point2d(1.0, 0.0)  # 기본 수평 방향 벡터 예시

    def point_at(self, station: float):
        if hasattr(self.rail, "point_at"):
            return self.rail.point_at(station)
        return Point2d(1.0, 0.0)  # 기본 수평 방향 벡터 예시
def test_validator_parallel_ok():
    a1 = MockAlignment("A1", [(0, 0), (1000, 0)])
    a2 = MockAlignment("A2", [(0, 70), (1000, 70)])  # 충분한 선간 거리 확보
    is_valid, err = CrossoverValidator.validate(
        a1, a2,
        t1_lead_length=20, t2_lead_length=20,
        station1=100, station2=100,
    )
    assert is_valid
    assert err == ""


def test_validator_not_parallel():
    a1 = MockAlignment("A1", [(0, 0), (1000, 0)])
    a2 = MockAlignment("A2", [(0, 10), (1000, 110)])   # 10% 기울기 (비평행)
    is_valid, err = CrossoverValidator.validate(
        a1, a2, 20, 20, 100, 100
    )
    assert not is_valid
    assert "평행하지 않음" in err


def test_validator_distance_too_small():
    a1 = MockAlignment("A1", [(0, 0), (1000, 0)])
    a2 = MockAlignment("A2", [(0, 5), (1000, 5)])   # 5m 간격 (너무 좁음)
    is_valid, err = CrossoverValidator.validate(
        a1, a2, 20, 20, 100, 100
    )
    assert not is_valid
    assert "선간 거리" in err


def test_crossover_build():
    tt = TurnoutType(name="1/12", lead_length=30, radius=300)
    crossover = (
        CrossoverBuilder("C1")
        .with_alignments("본선1", "본선2")
        .with_turnout_type(tt)
        .at_stations(sta1=100, sta2=120)
        .with_sides(left=TurnoutSide.RIGHT, right=TurnoutSide.LEFT)
        .build()
    )
    assert crossover.name == "C1"
    assert crossover.turnout1 is not None
    assert crossover.turnout2 is not None
    assert crossover.crossover_type == CrossoverType.SINGLE


def test_crossover_compute_geometry():
    a1 = MockAlignment("A1", [(0, 0), (1000, 0)])       # 기준선 (Y=0)
    a2 = MockAlignment("A2", [(0, 70), (1000, 70)])  # 상대선 (Y=70, 우측에 위치)

    tt = TurnoutType(name="1/12", lead_length=30, radius=300)
    crossover = (
        CrossoverBuilder("C1")
        .with_alignments("A1", "A2")
        .with_turnout_type(tt)
        .at_stations(100, 100)
        .with_sides(TurnoutSide.LEFT, TurnoutSide.RIGHT)  # 상대 선형 방향에 맞게 좌/우측 분기기 방향 정렬
        .build()
    )

    geom = crossover.compute_geometry(a1, a2)
    assert geom.is_valid
    assert geom.connecting_length > 0
    assert geom.turnout1_point is not None
    assert geom.turnout2_point is not None


def test_crossover_double():
    tt = TurnoutType(name="1/12", lead_length=30, radius=300)
    crossover = Crossover.double_crossover(
        name="C_Double",
        alignment1_name="A1",
        alignment2_name="A2",
        turnout_type=tt,
        station1=100,
        station2=120,
        connecting_length=80,
    )
    assert crossover.crossover_type == CrossoverType.DOUBLE
    assert crossover.turnout1.side == TurnoutSide.RIGHT
    assert crossover.turnout2.side == TurnoutSide.LEFT