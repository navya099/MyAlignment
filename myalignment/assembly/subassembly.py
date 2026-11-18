# assembly/subassembly.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import math

from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint


@dataclass(frozen=True, slots=True)
class Subassembly(ABC):
    """
    서브어셈블리 (불변, 추상).

    C3D의 Subassembly와 호환.
    - 입력 매개변수로 로컬 형상 생성.
    - 기준점(origin) + 방향(azimuth)으로 배치.
    """
    name: str = ""
    side: int = 1  # +1: 우측, -1: 좌측, 0: 중심
    apply_aor: bool = False  # 캔트 적용 여부
    # Target 파라미터 정의 (서브어셈블리별)
    _target_parameters: tuple[str, ...] = field(default_factory=tuple, repr=False)

    @property
    def target_parameters(self) -> tuple[str, ...]:
        """이 서브어셈블리가 사용하는 Target logical_name 목록."""
        return self._target_parameters

    @abstractmethod
    def generate_geometry(self, target_mapping: "TargetMapping | None" = None) -> tuple[tuple[AssemblyPoint, ...], tuple[AssemblyLink, ...]]:
        """
        서브어셈블리의 로컬 기하 생성.
        Args:
            target_mapping: Target 매핑 (없으면 기본값 사용).
        Returns:
            (points, links) — 로컬 좌표계의 접점들 + 연결들.
        """
        ...

    def place_at(
            self,
            origin_x: float,
            origin_z: float,
            side_sign: int = None,
            target_mapping: "TargetMapping | None" = None,
    ) -> tuple[tuple[AssemblyPoint, ...], tuple[AssemblyLink, ...]]:
        """
        서브어셈블리를 지정 위치에 배치.

        Args:
            origin_x: 배치 x 좌표
            origin_z: 배치 z 좌표
            side_sign: 방향 (+1: 우측, -1: 좌측). None이면 self.side 사용.
        """
        sign = side_sign if side_sign is not None else self.side
        points, links = self.generate_geometry(target_mapping)

        placed_points = []
        for p in points:
            placed_points.append(
                AssemblyPoint(
                    code=p.code,
                    x=origin_x + sign * p.x,
                    z=origin_z + p.z,
                    is_parametric=p.is_parametric,
                )
            )

        # 링크는 접점 참조 → 재매핑
        placed_links = []
        for link in links:
            new_start = self._find_point(placed_points, link.start.code)
            new_end = self._find_point(placed_points, link.end.code)
            if new_start and new_end:
                placed_links.append(
                    AssemblyLink(
                        code=link.code,
                        start=new_start,
                        end=new_end,
                        shape_code=link.shape_code,
                    )
                )

        return tuple(placed_points), tuple(placed_links)

    @staticmethod
    def _find_point(points, code):
        for p in points:
            if p.code == code:
                return p
        return None