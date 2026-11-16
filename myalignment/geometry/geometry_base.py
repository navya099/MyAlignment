# geometry/geometry_base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import math

from cadgeom import Point2d

from myalignment.core.projection_result import ProjectionResult


@dataclass(frozen=True, slots=True)
class Geometry(ABC):
    """
    로컬 좌표계 기반 기하 요소의 추상 기반 클래스.

    모든 `Geometry`는 로컬 측점 `s` (0 ~ length)로 파라미터화됩니다.
    월드 좌표 변환은 `AlignmentEntity`가 담당합니다.

    좌표계 규약:
        - x축: 시작점에서의 접선 방향 (진행 방향)
        - y축: 진행 방향 기준 좌측(+), 우측(-)
        - offset: 좌(-) / 우(+)
        - 각도: 라디안(rad), 반시계(+)
    """
    start_azimuth: float = 0.0  # 로컬 좌표계의 x축 방위각 (rad)
    is_reversed: bool = False  # 뒤집힌 기하인지

    # ---- 필수 속성 ----
    @property
    @abstractmethod
    def length(self) -> float:
        """기하 요소의 총 길이 (m)."""
        ...

    @property
    @abstractmethod
    def is_valid(self) -> bool:
        """유효한 기하인지."""
        ...

    # ---- 좌표 계산 ----
    @abstractmethod
    def point_at(self, s: float, offset: float = 0.0) -> Point2d:
        """로컬 측점 s에서의 좌표 (offset 적용)."""
        ...

    @abstractmethod
    def tangent_at(self, s: float) -> float:
        """로컬 측점 s에서의 접선 방위각 (rad)."""
        ...

    # ---- 역변환 ----
    @abstractmethod
    def project_at(self, p: Point2d) -> ProjectionResult:
        """로컬 점 p를 기하에 투영."""
        ...

    # ---- 불변 변환 (새 객체 반환) ----
    @abstractmethod
    def reversed(self) -> "Geometry":
        """뒤집힌 새 기하 반환."""
        ...

    @abstractmethod
    def offset_by(self, distance: float) -> "Geometry":
        """평행 이동한 새 기하 반환 (offset: 좌-, 우+)."""
        ...

    # ---- 검증 헬퍼 ----
    def _check_s(self, s: float) -> float:
        """s 범위 검증 및 클램프."""
        if not math.isfinite(s):
            raise ValueError(f"s가 유한하지 않음: {s}")
        return max(0.0, min(self.length, s))