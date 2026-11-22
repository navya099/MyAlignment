# quantity/takeoff.py
from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict
import math

from myalignment.quantity.material import Material, UnitType
from myalignment.quantity.shape import Shape
from myalignment.corridor.corridor import Corridor
from myalignment.corridor.region import CorridorRegion
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.volume import cut_fill_between
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

    cut_volume: float = 0.0
    fill_volume: float = 0.0

    @property
    def net_volume(self) -> float:
        return self.cut_volume - self.fill_volume

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

            if region.name in target_mappings:
                region = region.with_targets(target_mappings[region.name])
            stations = region.sample_stations()
            previous = self._shape_areas(region, stations[0])
            if len(stations) == 1:
                for code, area in previous.items():
                    material = self._material_by_shape_code(code.name)
                    if material:
                        material_areas[material.name] += area

            for start, end in zip(stations, stations[1:]):
                current = self._shape_areas(region, end)
                length = end - start
                for code in previous.keys() | current.keys():
                    material = self._material_by_shape_code(code.name)
                    if material is None:
                        continue
                    area = (previous.get(code, 0.0) + current.get(code, 0.0)) / 2
                    material_volumes[material.name] += area * length
                    material_lengths[material.name] += length
                previous = current

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

    def compute_with_surfaces(
        self,
        corridor: Corridor,
        design_surface: TinSurface,
        existing_surface: TinSurface,
    ) -> TakeoffResult:
        """설계면과 원지형의 겹치는 영역에서 절·성토량을 산출한다."""
        cut, fill = cut_fill_between(existing_surface, design_surface)
        return TakeoffResult(cut_volume=cut, fill_volume=fill)

    def _shape_areas(self, region: CorridorRegion, station: float) -> dict:
        _, links = region.cross_section_at(station)
        areas = defaultdict(float)
        for shape in self._build_shapes(links):
            areas[shape.code] += shape.area
        return areas

    @staticmethod
    def _build_shapes(links) -> tuple[Shape, ...]:
        """같은 코드의 링크 그래프에서 유한한 면의 경계를 순회한다."""
        graphs = defaultdict(lambda: defaultdict(set))
        points = {}
        for link in links:
            if link.shape_code is None:
                continue
            a = (round(link.start.x, 9), round(link.start.z, 9))
            b = (round(link.end.x, 9), round(link.end.z, 9))
            if a == b:
                continue
            points.setdefault(a, link.start)
            points.setdefault(b, link.end)
            graph = graphs[link.shape_code]
            graph[a].add(b)
            graph[b].add(a)

        shapes = []
        for code, graph in graphs.items():
            next_edge = {}
            for vertex, neighbors in graph.items():
                ordered = sorted(neighbors, key=lambda p: math.atan2(p[1] - vertex[1], p[0] - vertex[0]))
                for i, neighbor in enumerate(ordered):
                    next_edge[neighbor, vertex] = (vertex, ordered[i - 1])
            visited = set()
            for edge in next_edge:
                if edge in visited:
                    continue
                cycle = []
                current = edge
                while current not in visited:
                    visited.add(current)
                    cycle.append(current[0])
                    current = next_edge[current]
                if len(cycle) < 3:
                    continue
                # 반시계 경계는 유한 면, 시계 경계는 바깥 면이다.
                area2 = sum(
                    a[0] * b[1] - a[1] * b[0]
                    for a, b in zip(cycle, cycle[1:] + cycle[:1])
                )
                if area2 > 1e-12:
                    shapes.append(Shape(code=code, points=tuple(points[key] for key in cycle)))
        return tuple(shapes)
