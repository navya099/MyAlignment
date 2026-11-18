# turnout/crossover_builder.py
from __future__ import annotations
from myalignment.turnout.crossover import Crossover
from myalignment.turnout.crossover_type import CrossoverType
from myalignment.turnout.turnout import Turnout
from myalignment.turnout.type import TurnoutType, TurnoutSide


class CrossoverBuilder:
    """
    Crossover 선언적 빌더.

    사용 예:
        crossover = (
            CrossoverBuilder("C1")
            .with_alignments("본선1", "본선2")
            .with_turnout_type(TurnoutType(...))
            .at_stations(sta1=100, sta2=120)
            .with_sides(left=TurnoutSide.RIGHT, right=TurnoutSide.LEFT)
            .build()
        )
    """

    def __init__(self, name: str = "Crossover1"):
        self._name = name
        self._crossover_type = CrossoverType.SINGLE
        self._alignment1 = ""
        self._alignment2 = ""
        self._turnout_type: TurnoutType | None = None
        self._station1 = 0.0
        self._station2 = 0.0
        self._side1 = TurnoutSide.RIGHT
        self._side2 = TurnoutSide.LEFT

    def with_alignments(self, align1: str, align2: str) -> "CrossoverBuilder":
        self._alignment1 = align1
        self._alignment2 = align2
        return self

    def with_turnout_type(self, tt: TurnoutType) -> "CrossoverBuilder":
        self._turnout_type = tt
        return self

    def at_stations(self, sta1: float, sta2: float) -> "CrossoverBuilder":
        self._station1 = sta1
        self._station2 = sta2
        return self

    def with_sides(self, left: TurnoutSide, right: TurnoutSide) -> "CrossoverBuilder":
        self._side1 = left
        self._side2 = right
        return self

    def as_double(self) -> "CrossoverBuilder":
        self._crossover_type = CrossoverType.DOUBLE
        return self

    def as_scissors(self) -> "CrossoverBuilder":
        self._crossover_type = CrossoverType.SCISSORS
        return self

    def build(self) -> Crossover:
        if self._turnout_type is None:
            raise ValueError("turnout_type이 설정되지 않음")
        if not self._alignment1 or not self._alignment2:
            raise ValueError("두 본선 이름이 필요")

        # 턴아웃 2개 생성
        t1 = Turnout(
            name=f"{self._name}_T1",
            turnout_type=self._turnout_type,
            source_alignment_name=self._alignment1,
            branch_alignment_name=f"{self._name}_Conn",
            station_on_source=self._station1,
            side=self._side1,
        )
        t2 = Turnout(
            name=f"{self._name}_T2",
            turnout_type=self._turnout_type,
            source_alignment_name=self._alignment2,
            branch_alignment_name=f"{self._name}_Conn",
            station_on_source=self._station2,
            side=self._side2,
        )

        return Crossover(
            name=self._name,
            crossover_type=self._crossover_type,
            turnout1=t1,
            turnout2=t2,
            source_alignment1_name=self._alignment1,
            source_alignment2_name=self._alignment2,
            connecting_alignment_name=f"{self._name}_Conn",
        )