# turnout/crossover.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
import math

from myalignment.turnout.crossover_geometry import CrossoverGeometry
from myalignment.turnout.crossover_type import CrossoverType
from myalignment.turnout.crossover_validator import CrossoverValidator
from myalignment.turnout.turnout import Turnout
from myalignment.turnout.type import TurnoutSide


@dataclass(frozen=True, slots=True)
class Crossover:
    """
    크로스오버 (C3D Crossover 호환, 불변).

    C3D에서 Crossover는 단일 객체가 아니라
    "2개 턴아웃 + 연결 선형"의 조합.

    속성:
        name: 크로스오버 이름.
        crossover_type: SINGLE/DOUBLE/SCISSORS.
        turnout1: 첫 번째 턴아웃 (Source → Connecting).
        turnout2: 두 번째 턴아웃 (Connecting → Source).
        source_alignment1_name: 본선1 이름.
        source_alignment2_name: 본선2 이름.
        connecting_alignment_name: 연결 선형 이름.
        geometry: 기하 계산 결과 (검증 포함).
    """
    name: str = ""
    crossover_type: CrossoverType = CrossoverType.SINGLE
    turnout1: Turnout = None
    turnout2: Turnout = None
    source_alignment1_name: str = ""
    source_alignment2_name: str = ""
    connecting_alignment_name: str = ""
    geometry: CrossoverGeometry | None = None

    def __post_init__(self):
        if self.turnout1 is None or self.turnout2 is None:
            raise ValueError("두 턴아웃이 필요합니다.")
        if not self.source_alignment1_name or not self.source_alignment2_name:
            raise ValueError("두 본선 이름이 필요합니다.")

        # Turnout의 source가 본선1/본선2와 일치하는지
        if self.turnout1.source_alignment_name != self.source_alignment1_name:
            raise ValueError(
                f"turnout1.source({self.turnout1.source_alignment_name}) ≠ "
                f"source1({self.source_alignment1_name})"
            )
        if self.turnout2.source_alignment_name != self.source_alignment2_name:
            raise ValueError(
                f"turnout2.source({self.turnout2.source_alignment_name}) ≠ "
                f"source2({self.source_alignment2_name})"
            )

    # ================================================================
    # 기하 계산
    # ================================================================
    def compute_geometry(self, alignment1, alignment2) -> CrossoverGeometry:
        """
        Crossover 기하 계산.

        Args:
            alignment1: 본선1.
            alignment2: 본선2.

        Returns:
            CrossoverGeometry (검증 결과 포함).
        """
        sta1 = self.turnout1.station_on_source
        sta2 = self.turnout2.station_on_source

        # 1) 유효성 검사 (평행/거리)
        is_valid, err = CrossoverValidator.validate(
            alignment1=alignment1,
            alignment2=alignment2,
            t1_lead_length=self.turnout1.turnout_type.lead_length,
            t2_lead_length=self.turnout2.turnout_type.lead_length,
            station1=sta1,
            station2=sta2,
        )
        if not is_valid:
            return CrossoverGeometry(
                turnout1_station=sta1,
                turnout2_station=sta2,
                is_valid=False,
                error_message=err,
            )

        # 2) 방향 검증
        is_valid_dir, err_dir = CrossoverValidator.validate_direction(
            alignment1=alignment1,
            alignment2=alignment2,
            station1=sta1,
            station2=sta2,
            t1_side=self.turnout1.side,
            t2_side=self.turnout2.side,
        )
        if not is_valid_dir:
            return CrossoverGeometry(
                turnout1_station=sta1,
                turnout2_station=sta2,
                is_valid=False,
                error_message=err_dir,
            )

        # 3) 좌표/방위각 계산
        p1 = alignment1.point_at(sta1)
        p2 = alignment2.point_at(sta2)
        az1 = alignment1.tangent_at(sta1)
        az2 = alignment2.tangent_at(sta2)

        # 턴아웃1의 분기 시작점 (lead_length만큼 본선1 위 이동)
        t1_branch_start = alignment1.point_at(
            sta1 + self.turnout1.turnout_type.lead_length
        )
        # 턴아웃2의 분기 시작점 (lead_length만큼 본선2 위 이동)
        t2_branch_start = alignment2.point_at(
            sta2 - self.turnout2.turnout_type.lead_length
        )

        # 연결 선형: t1_branch_start → t2_branch_start
        dx = t2_branch_start.x - t1_branch_start.x
        dy = t2_branch_start.y - t1_branch_start.y
        connecting_length = math.hypot(dx, dy)
        connecting_az = math.atan2(dy, dx)

        return CrossoverGeometry(
            turnout1_station=sta1,
            turnout1_point=t1_branch_start,
            turnout1_azimuth=connecting_az,
            turnout2_station=sta2,
            turnout2_point=t2_branch_start,
            turnout2_azimuth=connecting_az + math.pi,
            connecting_length=connecting_length,
            connecting_azimuth=connecting_az,
            is_valid=True,
        )

    # ================================================================
    # 이중 크로스오버 생성
    # ================================================================
    @classmethod
    def double_crossover(
            cls,
            name: str,
            alignment1_name: str,
            alignment2_name: str,
            turnout_type,
            station1: float,
            station2: float,
            connecting_length: float,
            side1: TurnoutSide = TurnoutSide.RIGHT,
            side2: TurnoutSide = TurnoutSide.LEFT,
    ) -> "Crossover":
        """
        복식 크로스오버 (X자, 양방향) 생성.

        두 턴아웃이 서로 마주보고, 연결 선형이 X자로 교차.
        """

        # 턴아웃1: 본선1 → 본선2 (연결1)
        t1 = Turnout(
            name=f"{name}_T1",
            turnout_type=turnout_type,
            source_alignment_name=alignment1_name,
            branch_alignment_name=f"{name}_Conn1",
            station_on_source=station1,
            side=side1,
        )

        # 턴아웃2: 본선2 → 본선1 (연결2)
        t2 = Turnout(
            name=f"{name}_T2",
            turnout_type=turnout_type,
            source_alignment_name=alignment2_name,
            branch_alignment_name=f"{name}_Conn2",
            station_on_source=station2,
            side=side2,
        )

        return cls(
            name=name,
            crossover_type=CrossoverType.DOUBLE,
            turnout1=t1,
            turnout2=t2,
            source_alignment1_name=alignment1_name,
            source_alignment2_name=alignment2_name,
            connecting_alignment_name=f"{name}_Conn1",
        )

    # ================================================================
    # 불변 변환
    # ================================================================
    def with_geometry(self, geometry: CrossoverGeometry) -> "Crossover":
        """기하 계산 결과를 설정한 새 Crossover."""
        return replace(self, geometry=geometry)

    # ================================================================
    # 조회
    # ================================================================
    @property
    def is_valid(self) -> bool:
        return self.geometry is not None and self.geometry.is_valid

    @property
    def connecting_length(self) -> float:
        return self.geometry.connecting_length if self.geometry else 0.0

    def __repr__(self) -> str:
        status = "OK" if self.is_valid else "INVALID"
        return (
            f"Crossover('{self.name}', {self.crossover_type.name}, "
            f"{status}, L={self.connecting_length:.2f}m)"
        )