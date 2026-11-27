from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
import math
from typing import Iterator, Self

from cadgeom import Point2d

from myalignment.alignment.alignment_query import AlignmentQuery
from myalignment.alignment.alignment_transaction import AlignmentTransaction
from myalignment.alignment.label_set import AlignmentLabelSet
from myalignment.alignment.offset_station_map import OffsetStationMap
from myalignment.alignment.station_map import StationMap
from myalignment.alignment.station_offset_label import StationOffsetLabel
from myalignment.alignment.station_equation import StationEquation
from myalignment.alignment.station_equation_collection import StationEquationCollection
from myalignment.alignment.station_equation_type import StationEquationType
from myalignment.alignment.style.alignment_style import AlignmentStyle
from myalignment.corridor.corridor import Corridor
from myalignment.profile.profile import Profile
from myalignment.core.projection_result import ProjectionResult
from myalignment.core.station_offset import StationOffsetPoint
from myalignment.enitity.alignment_entity import AlignmentEntity
from myalignment.enitity.entity_collection import AlignmentEntityCollection
from myalignment.enitity.entity_factory import build_alignment_entities
from myalignment.enum.spiraltype import SpiralType
from myalignment.profile.profiletype import ProfileType
from myalignment.quantity.takeoff import TakeoffResult, QuantityTakeoff
from myalignment.structure.structurecollection import StructureCollection
from myalignment.structure.struturetype import StructureType
from myalignment.superelevation.collection import SuperelevationCollection


@dataclass(frozen=True, slots=True)
class Alignment:
    """
    선형(Alignment) — C3D 호환 최상위 컨테이너.

    Attributes:
        name: 선형 이름.
        entities: Entity 시퀀스 (불변).
        profiles: 종단 프로파일 리스트.
        structures: 구조물 컬렉션.
        design_speed: 설계 속도 (km/h).
        route_type: 노선 종류.
        metadata: 추가 메타데이터.
    """
    name: str = "Alignment1"
    entities: AlignmentEntityCollection = field(
        default_factory=AlignmentEntityCollection
    )
    profiles: tuple[Profile, ...] = field(default_factory=tuple)
    structures: StructureCollection = field(default_factory=StructureCollection)
    design_speed: float = 0.0
    route_type: str = ""
    metadata: dict = field(default_factory=dict)

    superelevation: SuperelevationCollection = field(
        default_factory=SuperelevationCollection
    )

    corridors: tuple[Corridor, ...] = field(default_factory=tuple)
    style: AlignmentStyle = field(default_factory=AlignmentStyle.basic, kw_only=True)

    label_set: AlignmentLabelSet = field(default_factory=AlignmentLabelSet.standard, kw_only=True)

    station_offset_labels: tuple[StationOffsetLabel, ...] = field(default=(), kw_only=True)

    station_equations: StationEquationCollection = field(
        default_factory=StationEquationCollection, kw_only=True,
    )

    def __post_init__(self):
        object.__setattr__(self, "corridors", tuple(self.corridors))
        object.__setattr__(self, "station_offset_labels", tuple(self.station_offset_labels))

    @classmethod
    def from_pi_coords(
        cls, coords: Iterable[tuple[float | str, float | str] | Point2d], *, name: str = "Alignment1",
        radii: Iterable[float | None] | None = None, start_station: float = 0.0,
        entry_lengths: Iterable[float] | None = None, exit_lengths: Iterable[float] | None = None,
        spiral_type: SpiralType = SpiralType.Clothoid, profiles: Iterable[Profile] = (),
    ) -> Self:
        """PI 좌표와 선택한 곡선 제원으로 선형을 한 번에 만든다.

        반경을 생략하면 모든 PI를 직선으로 연결한다. 좌표와 곡선 제원은 PI 순서로 입력한다.
        진입 완화곡선장만 입력하면 같은 값을 진출에 적용한다.
        """
        if not math.isfinite(start_station):
            raise ValueError("start_station must be finite")
        points = []
        for index, row in enumerate(coords, start=1):
            if isinstance(row, (str, bytes)):
                raise ValueError(f"PI row {index}: expected two numeric coordinates")
            try:
                x, y = (row.x, row.y) if isinstance(row, Point2d) else row
                x, y = float(x), float(y)
            except (TypeError, ValueError, OverflowError) as error:
                raise ValueError(f"PI row {index}: expected two numeric coordinates") from error
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError(f"PI row {index}: coordinates must be finite")
            points.append(Point2d(x, y))
        entry = None if entry_lengths is None else list(entry_lengths)
        exit_ = entry if exit_lengths is None else list(exit_lengths)
        entities = build_alignment_entities(
            points, [None] * len(points) if radii is None else list(radii),
            start_station=start_station, spiral_type=spiral_type, entry_lengths=entry, exit_lengths=exit_,
        )
        return cls(name=name, entities=entities, profiles=tuple(profiles))

    def raw_to_display_station(self, raw_station: float) -> float:
        return self.station_equations.raw_to_display(raw_station)

    def display_to_raw_stations(self, display_station: float) -> tuple[float, ...]:
        """점프 구간이면 빈 튜플, 중복 구간이면 복수 원시 측점을 반환한다."""
        if self.station_equations and self.is_valid:
            return self.station_equations.display_to_raw(display_station, self.start_station, self.end_station)
        return self.station_equations.display_to_raw(display_station)

    def display_to_raw_station(self, display_station: float) -> float:
        """표시 측점이 단일 원시 측점에 대응할 때 역변환한다."""
        candidates = self.display_to_raw_stations(display_station)
        if not candidates:
            raise ValueError(f"No raw station matches display station {display_station}")
        if len(candidates) > 1:
            raise ValueError(f"Ambiguous display station {display_station}: {candidates}")
        return candidates[0]

    def add_station_equation(
        self, raw_station_back: float, station_ahead: float,
        equation_type: StationEquationType = StationEquationType.INCREASING, comment: str = "",
    ) -> "Alignment":
        equation = StationEquation(raw_station_back, station_ahead, equation_type, comment)
        return replace(self, station_equations=self.station_equations.add(equation))

    def remove_station_equation(self, raw_station_back: float) -> "Alignment":
        return replace(self, station_equations=self.station_equations.remove_at_raw(raw_station_back))

    def with_label_set(self, label_set: AlignmentLabelSet) -> "Alignment":
        return replace(self, label_set=label_set)

    def with_station_offset_labels(self, labels: Iterable[StationOffsetLabel]) -> Self:
        """측점·횡거 레이블을 교체한 선형을 반환한다."""
        return replace(self, station_offset_labels=tuple(labels))

    def add_station_offset_label(self, label: StationOffsetLabel) -> Self:
        """측점·횡거 레이블을 추가한 선형을 반환한다."""
        return self.with_station_offset_labels((*self.station_offset_labels, label))

    def with_style(self, style: AlignmentStyle) -> "Alignment":
        """표시 스타일을 교체한 새 선형을 반환한다."""
        return replace(self, style=style)

    # ================================================================
    # 기본 속성
    # ================================================================
    @property
    def start_station(self) -> float:
        return self.entities.start_station

    @property
    def end_station(self) -> float:
        return self.entities.end_station

    @property
    def length(self) -> float:
        """선형 총 연장 (m)."""
        return self.entities.length

    @property
    def is_valid(self) -> bool:
        return len(self.entities) > 0

    def __len__(self) -> int:
        return len(self.entities)

    def __iter__(self) -> Iterator[AlignmentEntity]:
        return iter(self.entities)

    # ================================================================
    # 좌표 조회 (C3D 호환)
    # ================================================================
    def point_at(self, station: float, offset: float = 0.0) -> Point2d:
        """측점과 횡거에 해당하는 월드 평면 좌표를 반환한다.

        Args:
            station: 측점 방정식으로 변환하기 전의 기하 측점.
            offset: 진행 방향 기준 우측은 양수, 좌측은 음수인 횡거.
        """
        return self.entities.point_at(station, offset)

    def tangent_at(self, station: float) -> float:
        """측점의 접선 방위각 (rad)."""
        return self.entities.tangent_at(station)

    def station_offset_of(self, point: Point2d) -> StationOffsetPoint:
        """월드 점 → 측점/횡거."""
        pr = self.project(point)
        return pr.to_station_offset()

    def project(self, point: Point2d) -> ProjectionResult:
        """월드 좌표를 가장 가까운 선형 요소에 투영한다.

        Returns:
            투영점과 기하 측점, 부호 있는 횡거를 담은 결과.
        """
        return self.entities.project(point)

    def entity_at_station(self, station: float) -> AlignmentEntity:
        """측점이 속한 Entity."""
        return self.entities.entity_at_station(station)

    # ================================================================
    # 고급 조회 (C3D 호환)
    # ================================================================
    def distance_to_alignment(
            self,
            station: float,
            other: "Alignment",
            side: "AlignmentSide" = None,
    ) -> tuple[float, float]:
        """
        C3D DistanceToAlignment 호환.

        Args:
            station: 이 선형의 기준 측점.
            other: 대상 선형.
            side: 탐색 방향 (LEFT/RIGHT/BOTH). None이면 BOTH.

        Returns:
            (signed_distance, station_on_other)
            - signed_distance: 좌(+)/우(-) 부호 거리.
            - station_on_other: 대상 선형의 측점.
        """

        return AlignmentQuery.distance_to_alignment(self, station, other, side)

    def intersection_with(self, other: "Alignment") -> list[StationOffsetPoint]:
        """두 선형의 교차점들 (station-offset)."""
        return AlignmentQuery.intersection(self, other)

    def offset_alignment(self, offset: float) -> Self:
        """평행 이동한 기하와 연결 객체에 새 측점을 적용한다."""
        entities = self.entities.offset_by(offset)
        if entities is self.entities:
            return self
        return self._with_restationed_geometry(entities, OffsetStationMap(self.entities, entities))

    def _with_restationed_geometry(self, entities: AlignmentEntityCollection, stations: StationMap) -> Self:
        result = replace(
            self, entities=entities,
            profiles=tuple(profile._map_stations(stations) for profile in self.profiles),
            superelevation=self.superelevation._offset_stations(stations.forward),
            station_equations=StationEquationCollection(tuple(
                replace(equation, raw_station_back=stations.forward(equation.raw_station_back))
                for equation in self.station_equations
            )),
        )
        return self._with_mapped_dependencies(
            result, stations.forward, reverse=False, inverse=stations.backward,
            grade_scale=lambda station: stations.inverse_rate(station, outgoing=station < result.end_station),
        )

    def reversed_alignment(self) -> Self:
        """평면 기하 및 연결 객체의 측점과 횡단 방향을 반전한다."""
        station_sum = self.start_station + self.end_station

        def reflect(station: float) -> float:
            return station_sum - station

        result = replace(
            self, entities=self.entities.reversed(),
            profiles=tuple(profile._reversed_about(station_sum) for profile in self.profiles),
            superelevation=self.superelevation._reversed_about(station_sum),
            station_equations=self.station_equations.reversed(self.start_station, self.end_station),
        )
        return self._with_mapped_dependencies(
            result, reflect, reverse=True, inverse=reflect, grade_scale=lambda _: -1.0,
        )

    def _with_mapped_dependencies(
        self, result: Self, transform: Callable[[float], float], *, reverse: bool,
        inverse: Callable[[float], float], grade_scale: Callable[[float], float],
    ) -> Self:
        structures = []
        for item in self.structures:
            start, end = transform(item.start_station), transform(item.end_station)
            structures.append(item.with_station_range(min(start, end), max(start, end)))
        result = replace(
            result, structures=StructureCollection(tuple(sorted(structures, key=lambda item: item.start_station))),
            corridors=tuple(
                corridor._map_alignment_stations(
                    self.name, transform, reverse=reverse, inverse=inverse, grade_scale=grade_scale,
                )
                for corridor in self.corridors
            ),
        )
        return result._map_additional_stations(transform, reverse=reverse)

    def _with_renamed_references(self, name: str) -> Self:
        if self.name == name:
            return self
        return replace(
            self, name=name,
            corridors=tuple(corridor._rename_alignment(self.name, name) for corridor in self.corridors),
            station_offset_labels=tuple(
                replace(label, reference_alignment_name=name) if label.reference_alignment_name == self.name else label
                for label in self.station_offset_labels
            ),
        )

    def _map_additional_stations(self, transform: Callable[[float], float], *, reverse: bool) -> Self:
        return self

    # ================================================================
    # Profile 조회
    # ================================================================
    def profile_by_type(self, profile_type: ProfileType) -> Profile | None:
        """타입별 프로파일 조회."""
        for p in self.profiles:
            if p.profile_type == profile_type:
                return p
        return None

    @property
    def fg_profile(self) -> Profile | None:
        """설계선(FG)."""
        return self.profile_by_type(ProfileType.FG)

    @property
    def eg_profile(self) -> Profile | None:
        """현황선(EG)."""
        return self.profile_by_type(ProfileType.EG)

    @property
    def grades_count(self) -> int:
        """FG 프로파일의 PVI 개수 (기존 API 호환)."""
        fg = self.fg_profile
        return fg.pvi_count if fg else 0

    @property
    def max_grade(self) -> float:
        """FG 프로파일의 최대 오르막 (양수)."""
        fg = self.fg_profile
        return fg.max_slope if fg else 0.0

    @property
    def max_abs_grade(self) -> float:
        """FG 프로파일의 최대 절댓값 구배."""
        fg = self.fg_profile
        return fg.max_abs_slope if fg else 0.0

    # ---- Structure 조회 ----
    @property
    def bridge_count(self) -> int:
        return self.structures.bridge_count

    @property
    def tunnel_count(self) -> int:
        return self.structures.tunnel_count

    @property
    def total_bridge_length(self) -> float:
        return self.structures.total_bridge_length

    @property
    def total_tunnel_length(self) -> float:
        return self.structures.total_tunnel_length

    def structure_type_at(self, station: float) -> StructureType | None:
        """주어진 측점의 구조물 타입 (None = 토공)."""
        return self.structures.structure_type_at(station)

    def structure_at(self, station: float):
        """주어진 측점의 구조물."""
        return self.structures.find_at_station(station)

    # ---- 공사비 (확장) ----
    @property
    def cost(self) -> float:
        """
        공사비 (구조물 + 토공).

        현재는 구조물만 계산. 토공/포장은 별도 모듈.
        """
        bridge_cost = self.total_bridge_length * self._bridge_unit_cost()
        tunnel_cost = self.total_tunnel_length * self._tunnel_unit_cost()
        return bridge_cost + tunnel_cost

    def _bridge_unit_cost(self) -> float:
        """교량 단가 (원/m) — metadata 또는 기본값."""
        return float(self.metadata.get('bridge_unit_cost', 5_000_000))

    def _tunnel_unit_cost(self) -> float:
        """터널 단가 (원/m)."""
        return float(self.metadata.get('tunnel_unit_cost', 10_000_000))

    @property
    def has_superelevation(self) -> bool:
        return len(self.superelevation) > 0

    def superelevation_at(self, station: float):
        """측점의 편구배 임계 측점."""
        curve = self.superelevation.curve_at_station(station)
        return curve.critical_station_at(station) if curve else None

    @property
    def primary_corridor(self) -> Corridor | None:
        """첫 번째 코리더."""
        return self.corridors[0] if self.corridors else None

    def corridor_by_name(self, name: str) -> Corridor | None:
        for c in self.corridors:
            if c.name == name:
                return c
        return None

    def add_corridor(self, corridor: Corridor) -> "Alignment":
        """새 코리더 추가한 새 선형."""
        return replace(self, corridors=self.corridors + (corridor,))

    # ================================================================
    # Transaction 기반 수정
    # ================================================================
    def modify(self) -> "AlignmentTransaction":
        """트랜잭션 시작."""
        return AlignmentTransaction(self)

    @property
    def quantity_takeoff(self) -> TakeoffResult | None:
        """
        첫 코리더에서 이 선형을 기준선으로 사용하는 영역의 수량 산출.

        재료 정보는 metadata에 저장:
            metadata['materials'] = [...]
        """
        if not self.corridors:
            return None
        corridor = self.primary_corridor
        regions = [
            region for region, _ in corridor._regions_with_baselines(None, self.name, None)
        ]
        materials = self.metadata.get('materials', [])

        qto = QuantityTakeoff(materials=materials)
        return qto.compute(corridor, regions)
