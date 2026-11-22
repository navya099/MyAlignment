# ================================================================
# Transaction — 불변 Alignment 수정
# ================================================================
from __future__ import annotations
from dataclasses import replace
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.profile.profile import Profile

from myalignment.enitity.entity_factory import EntityFactory
from myalignment.ipdata.ipdata import PIInput, PICurveSpec
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.line_entity import LineEntity
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.exception.alignment_error import InvalidGeometryError
from myalignment.structure.structure import Structure

from myalignment.alignment.station_map import EditStationMap

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
        self._active = False
        self._result: Alignment | None = None

    def __enter__(self) -> "AlignmentTransaction":
        if self._active:
            raise RuntimeError("Transaction이 이미 진행 중입니다.")
        self._active = True
        self._result = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self._result = self._build_result()
        finally:
            self._pending.clear()
            self._active = False
        return False

    def _build_result(self) -> Alignment:
        original = self._original
        result = original
        entities = self._pending.get("entities")
        if entities is not None and (
            original.entities._pi_input is None or original.entities._pi_input != entities._pi_input
        ):
            result = original._with_restationed_geometry(
                entities, EditStationMap.between(original.entities, entities),
            )

        # 명시적으로 새로 제공한 종단과 구조물은 편집 후 측점으로 해석한다.
        if "profiles" in self._pending:
            by_identity = {id(a): b for a, b in zip(original.profiles, result.profiles)}
            result = replace(result, profiles=tuple(
                by_identity.get(id(profile), profile) for profile in self._pending["profiles"]
            ))
        if "structures" in self._pending:
            structures = result.structures
            for item in self._pending["structures"]:
                structures = structures.add(item)
            result = replace(result, structures=structures)
        return result._with_renamed_references(self._pending.get("name", original.name))

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

        new_pi_input = replace(
            pi_input,
            pi_coords=tuple(new_coords),
            curve_specs=tuple(new_specs),
        )
        self._pending['entities'] = EntityFactory.build(new_pi_input)
        return self

    def update_profile(self, profile: Profile) -> "AlignmentTransaction":
        """프로파일 교체/추가."""
        profiles = list(self._pending.get("profiles", self._original.profiles))
        for i, p in enumerate(profiles):
            if p.profile_type == profile.profile_type:
                profiles[i] = profile
                break
        else:
            profiles.append(profile)
        self._pending['profiles'] = tuple(profiles)
        return self

    def add_structure(self, structure: Structure) -> "AlignmentTransaction":
        """구조물 추가."""
        self._pending.setdefault("structures", []).append(structure)
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
        """현재 PI 사양을 읽고, 직접 조립한 Entity는 접선 교점에서 역산한다."""
        entities = self._pending.get("entities", self._original.entities)
        if entities._pi_input is not None:
            return entities._pi_input

        points = [entities.start_coord]
        specs = [PICurveSpec()]
        i = 0
        while i < len(entities):
            first = entities[i]
            if isinstance(first, LineEntity):
                i += 1
                if i == len(entities) or isinstance(entities[i], LineEntity):
                    points.append(first.end_coord)
                    specs.append(PICurveSpec())
                continue

            arc_index = i + int(isinstance(first, SpiralEntity) and not first.geometry.is_reversed)
            if arc_index >= len(entities) or not isinstance(entities[arc_index], ArcEntity):
                raise InvalidGeometryError("Entity에서 PI 곡선 사양을 복원할 수 없습니다.")
            arc = entities[arc_index]
            entry = first if arc_index != i else None
            i = arc_index + 1
            exit_ = entities[i] if (
                i < len(entities) and isinstance(entities[i], SpiralEntity)
                and entities[i].geometry.is_reversed
            ) else None
            i += int(exit_ is not None)
            last = exit_ or arc
            incoming, outgoing = first.start_azimuth, last.end_azimuth
            determinant = math.sin(outgoing - incoming)
            if abs(determinant) < 1e-10:
                raise InvalidGeometryError("평행 접선에서 PI를 복원할 수 없습니다.")
            dx = last.end_coord.x - first.start_coord.x
            dy = last.end_coord.y - first.start_coord.y
            before = (dx * math.sin(outgoing) - dy * math.cos(outgoing)) / determinant
            points.append(Point2d(
                first.start_coord.x + before * math.cos(incoming),
                first.start_coord.y + before * math.sin(incoming),
            ))
            entry_length = entry.length if entry else 0.0
            exit_length = exit_.length if exit_ else 0.0
            spiral = entry or exit_
            spec = PICurveSpec(
                radius=arc.geometry.radius, entry_length=entry_length,
                exit_length=exit_length, is_symmetric=entry_length == exit_length,
            )
            specs.append(replace(spec, spiral_type=spiral.geometry.spiral_type) if spiral else spec)
            if i == len(entities):
                points.append(last.end_coord)
                specs.append(PICurveSpec())

        pi_input = PIInput(tuple(points), tuple(specs), entities.start_station)
        rebuilt = EntityFactory.build(pi_input)
        if len(rebuilt) != len(entities) or any(
            type(a) is not type(b)
            or a.start_coord.distance_to(b.start_coord) > 1e-6
            or a.end_coord.distance_to(b.end_coord) > 1e-6
            or abs(a.length - b.length) > 1e-6
            or abs(math.remainder(a.start_azimuth - b.start_azimuth, math.tau)) > 1e-8
            or (isinstance(a, SpiralEntity) and a.geometry.spiral_type != b.geometry.spiral_type)
            for a, b in zip(entities, rebuilt)
        ):
            raise InvalidGeometryError("원래 형상을 유지하는 PI 곡선 사양을 복원할 수 없습니다.")
        return pi_input
