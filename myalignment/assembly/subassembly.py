# assembly/subassembly.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from typing import ClassVar

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
    uses_section_context: ClassVar[bool] = False

    name: str = ""
    side: int = 1  # +1: 우측, -1: 좌측, 0: 중심
    apply_aor: bool = False  # 캔트 적용 여부
    # Target 파라미터 정의 (서브어셈블리별)
    _target_parameters: tuple[str, ...] = field(default_factory=tuple, repr=False)

    @property
    def has_station_binding(self) -> bool:
        """측점 이동에 따라 바인딩 원본 측점을 보존해야 하는지 반환한다."""
        return False

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

    def _place_with_context(self, origin_x, origin_z, side_sign, target_mapping, context):
        return self.place_at(origin_x, origin_z, side_sign=side_sign, target_mapping=target_mapping)

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
        sign = side_sign if side_sign is not None else (self.side or 1)
        return self._transform_geometry(*self.generate_geometry(target_mapping), origin_x, origin_z, sign)

    @staticmethod
    def _transform_geometry(points, links, origin_x, origin_z, sign):
        placed = {
            p: replace(p, x=origin_x + sign * p.x, z=origin_z + p.z)
            for p in points
        }
        placed_links = tuple(
            AssemblyLink(
                code=link.code,
                start=placed[link.start],
                end=placed[link.end],
                shape_code=link.shape_code,
            )
            for link in links
            if link.start in placed and link.end in placed
        )
        return tuple(placed[p] for p in points), placed_links
