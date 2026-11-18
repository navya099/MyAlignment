# quantity/takeoff.py
from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict
import math

from myalignment.quantity.material import Material, UnitType
from myalignment.quantity.pay_item import PayItem
from myalignment.quantity.shape import Shape
from myalignment.corridor.corridor import Corridor
from myalignment.corridor.region import CorridorRegion
from myalignment.target.mapping import TargetMapping


@dataclass(frozen=True, slots=True)
class MaterialQuantity:
    """재료별 집계 수량."""
    material_name: str
    unit_type: UnitType
    total_quantity: float
    total_cost: float

    def __repr__(self) -> str:
        return (
            f"MaterialQuantity('{self.material_name}', "
            f"{self.total_quantity:,.2f} {self.unit_type.value}, "
            f"{self.total_cost:,.0f}원)"
        )


@dataclass(frozen=True, slots=True)
class TakeoffResult:
    """
    수량 산출 결과 (불변).

    C3D QTO Report와 호환.
    """
    material_quantities: tuple[MaterialQuantity, ...] = field(default_factory=tuple)

    @property
    def total_cost(self) -> float:
        return sum(mq.total_cost for mq in self.material_quantities)

    def __repr__(self) -> str:
        lines = [f"TakeoffResult(총 {self.total_cost:,.0f}원):"]
        for mq in self.material_quantities:
            lines.append(f"  {mq}")
        return "\n".join(lines)


class QuantityTakeoff:
    """
    수량 산출 엔진.

    C3D의 Compute Materials + Generate QTO 워크플로우.
    """

    def __init__(self, materials: list[Material] | None = None):
        self._materials = materials or []

    def add_material(self, material: Material) -> "QuantityTakeoff":
        self._materials.append(material)
        return self

    def _material_by_shape_code(self, shape_code: str) -> Material | None:
        for m in self._materials:
            if m.shape_code == shape_code:
                return m
        return None

    def compute(
            self,
            corridor: Corridor,
            corridor_regions: list[CorridorRegion],
            target_mappings: dict[str, TargetMapping] | None = None,
    ) -> TakeoffResult:
        """
        코리더 전체 수량 산출.

        Args:
            corridor: 코리더.
            corridor_regions: 영역 리스트.
            target_mappings: Region별 Target 매핑 (선택).

        Returns:
            TakeoffResult
        """
        if target_mappings is None:
            target_mappings = {}

        # 재료별 누적
        material_volumes = defaultdict(float)  # material_name → volume
        material_areas = defaultdict(float)  # material_name → max area (or avg)
        material_lengths = defaultdict(float)  # material_name → length

        # Region별 산출
        for region in corridor_regions:
            if region.assembly is None:
                continue

            targets = target_mappings.get(region.name, region.target_mapping)
            stations = region.sample_stations()

            if len(stations) < 2:
                # 단일 측점: 면적만 산출
                _, _, shapes = self._cross_section_with_shapes(region, stations[0], targets)
                for shape in shapes:
                    material = self._material_by_shape_code(shape.code.name)
                    if material:
                        material_areas[material.name] += shape.area
                continue

            # 인접 측점 쌍별 체적 산출 (평균단면법)
            prev_station = stations[0]
            prev_shapes = self._cross_section_with_shapes(
                region, prev_station, targets
            )[2]

            for sta in stations[1:]:
                cur_shapes = self._cross_section_with_shapes(region, sta, targets)[2]

                # 측점 간 거리
                length = sta - prev_station

                # Shape 코드별 매칭
                for prev_shape in prev_shapes:
                    material = self._material_by_shape_code(prev_shape.code.name)
                    if material is None:
                        continue

                    # 같은 코드의 현재 Shape 찾기
                    cur_shape = self._find_shape_by_code(cur_shapes, prev_shape.code)
                    if cur_shape is None:
                        continue

                    # 평균단면법
                    avg_area = (prev_shape.area + cur_shape.area) / 2.0
                    volume = avg_area * length

                    material_volumes[material.name] += volume
                    # 길이 (포장 둘레 누적도 가능)
                    material_lengths[material.name] += length

                prev_station = sta
                prev_shapes = cur_shapes

        # 결과 조립
        quantities = []
        for material in self._materials:
            name = material.name
            if material.unit_type == UnitType.VOLUME:
                qty = material_volumes[name]
            elif material.unit_type == UnitType.AREA:
                qty = material_areas[name]
            elif material.unit_type == UnitType.LENGTH:
                qty = material_lengths[name]
            else:
                qty = 0.0

            quantities.append(
                MaterialQuantity(
                    material_name=name,
                    unit_type=material.unit_type,
                    total_quantity=qty,
                    total_cost=qty * material.unit_price,
                )
            )

        return TakeoffResult(material_quantities=tuple(quantities))

    def _cross_section_with_shapes(
            self,
            region: CorridorRegion,
            station: float,
            targets: TargetMapping,
    ) -> tuple[tuple, tuple, tuple[Shape, ...]]:
        """
        측점의 횡단면 + Shape 추출.

        실제로는 Assembly가 Shape을 반환해야 함.
        현재는 링크로부터 Shape 생성 (연속 링크 그룹화).
        """
        points, links = region.cross_section_at(station)
        # 링크 → Shape 변환 (shape_code 있는 링크만)
        shapes = self._build_shapes(links)
        return points, links, shapes

    @staticmethod
    def _build_shapes(links) -> tuple[Shape, ...]:
        """
        링크 → Shape 변환 (간단화).

        C3D에서는 Shape이 명시적이지만, 여기선 링크 그룹화.
        - 같은 shape_code를 가진 연속 링크를 하나의 Shape으로 묶음.
        """
        shape_links = {}  # shape_code → [links]
        for link in links:
            if link.shape_code is None:
                continue
            code = link.shape_code
            if code not in shape_links:
                shape_links[code] = []
            shape_links[code].append(link)

        shapes = []
        for code, grouped in shape_links.items():
            if len(grouped) < 3:
                # 최소 3점 필요
                pts = []
                seen = set()
                for link in grouped:
                    for p in (link.start, link.end):
                        key = (round(p.x, 6), round(p.z, 6))
                        if key not in seen:
                            seen.add(key)
                            pts.append(p)
                if len(pts) >= 3:
                    shapes.append(Shape(code=code, points=tuple(pts)))
            else:
                pts = []
                seen = set()
                for link in grouped:
                    for p in (link.start, link.end):
                        key = (round(p.x, 6), round(p.z, 6))
                        if key not in seen:
                            seen.add(key)
                            pts.append(p)
                if len(pts) >= 3:
                    shapes.append(Shape(code=code, points=tuple(pts)))

        return tuple(shapes)

    @staticmethod
    def _find_shape_by_code(shapes: tuple[Shape, ...], code) -> Shape | None:
        for s in shapes:
            if s.code == code:
                return s
        return None