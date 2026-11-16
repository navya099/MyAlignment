# ================================================================
# Transaction — 불변 Alignment 수정
# ================================================================
from __future__ import annotations
from dataclasses import dataclass, field, replace
import math
from typing import Iterator, TYPE_CHECKING

from cadgeom import Point2d

from myalignment.profile.profile import Profile

from myalignment.enitity.entity_factory import EntityFactory
from myalignment.ipdata.ipdata import PIInput, PICurveSpec
from myalignment.structure.structurecollection import StructureCollection

# 타입 힌트 전용으로만 안전하게 임포트
if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment

class AlignmentTransaction:
    """
    Alignment 수정 트랜잭션 (C3D Modify 패턴).

    사용 예:
        with alignment.modify() as tx:
            tx.update_pi_and_radius(index=1, point=Point2d(...), radius=300)
        new_alignment = tx.result
    """

    def __init__(self, alignment: Alignment):
        self._original = alignment
        self._pending: dict = {}
        self._result: Alignment | None = None

    def __enter__(self) -> "AlignmentTransaction":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._result = replace(self._original, **self._pending)
        return False

    # ---- 빌더 메서드 ----
    def update_pi_and_radius(
            self,
            index: int,
            point: Point2d | None = None,
            radius: float | None = None,
    ) -> "AlignmentTransaction":
        """PI/반경 업데이트 (내부적으로 Entity 재생성)."""
        # 현재 PI 좌표/반경 추출
        pi_input = self._extract_pi_input()
        if index <= 0 or index >= len(pi_input.pi_coords) - 1:
            raise IndexError(f"PI 인덱스 {index}는 수정 불가 (BP/EP는 별도)")

        new_coords = list(pi_input.pi_coords)
        new_specs = list(pi_input.curve_specs)
        if point is not None:
            new_coords[index] = point
        if radius is not None:
            new_specs[index] = replace(new_specs[index], radius=radius)

        new_pi_input = PIInput(
            pi_coords=tuple(new_coords),
            curve_specs=tuple(new_specs),
            start_station=pi_input.start_station,
        )
        self._pending['entities'] = EntityFactory.build(new_pi_input)
        return self

    def update_profile(self, profile: Profile) -> "AlignmentTransaction":
        """프로파일 교체/추가."""
        profiles = list(self._original.profiles)
        for i, p in enumerate(profiles):
            if p.profile_type == profile.profile_type:
                profiles[i] = profile
                break
        else:
            profiles.append(profile)
        self._pending['profiles'] = tuple(profiles)
        return self

    def add_structure(self, structure) -> "AlignmentTransaction":
        """구조물 추가."""
        structures = list(self._original.structures)
        structures.append(structure)
        new_col = StructureCollection()
        for s in structures:
            new_col.append(s)
        self._pending['structures'] = new_col
        return self

    def rename(self, new_name: str) -> "AlignmentTransaction":
        self._pending['name'] = new_name
        return self

    @property
    def result(self) -> Alignment:
        if self._result is None:
            raise RuntimeError("Transaction이 아직 완료되지 않았습니다.")
        return self._result

    # ---- 내부 ----
    def _extract_pi_input(self) -> PIInput:
        """현재 Alignment에서 PIInput 역산."""
        pts = [e.start_coord for e in self._original.entities]
        if self._original.entities:
            pts.append(self._original.entities[-1].end_coord)

        specs = []
        for i, pt in enumerate(pts):
            if i == 0 or i == len(pts) - 1:
                specs.append(PICurveSpec())  # 첫/끝은 직선
            else:
                # PI 위치에서 가장 가까운 Entity 찾기
                e = self._original.entities.entity_at_station(
                    self._original.start_station + i
                ) if len(self._original.entities) > i else None
                radius = getattr(e, 'geometry', None) and getattr(e.geometry, 'radius', None)
                specs.append(PICurveSpec(radius=radius))
        return PIInput(
            pi_coords=tuple(pts),
            curve_specs=tuple(specs),
            start_station=self._original.start_station,
        )