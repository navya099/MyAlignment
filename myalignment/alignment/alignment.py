from dataclasses import dataclass, field, replace
from typing import Iterator

from cadgeom import Point2d

from myalignment.alignment.alignment_transaction import AlignmentTransaction
from myalignment.profile.profile import Profile
from myalignment.core.projection_result import ProjectionResult
from myalignment.core.station_offset import StationOffsetPoint
from myalignment.enitity.alignment_entity import AlignmentEntity
from myalignment.enitity.entity_collection import AlignmentEntityCollection
from myalignment.profile.profiletype import ProfileType
from myalignment.structure.structurecollection import StructureCollection


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
        """측점/횡거의 월드 좌표."""
        return self.entities.point_at(station, offset)

    def tangent_at(self, station: float) -> float:
        """측점의 접선 방위각 (rad)."""
        return self.entities.tangent_at(station)

    def station_offset_of(self, point: Point2d) -> StationOffsetPoint:
        """월드 점 → 측점/횡거."""
        pr = self.project(point)
        return pr.to_station_offset()

    def project(self, point: Point2d) -> ProjectionResult:
        """월드 점을 가장 가까운 Entity에 투영."""
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
        from alignment.alignment_query import AlignmentQuery
        return AlignmentQuery.distance_to_alignment(self, station, other, side)

    def intersection_with(self, other: "Alignment") -> list[StationOffsetPoint]:
        """두 선형의 교차점들 (station-offset)."""
        from alignment.alignment_query import AlignmentQuery
        return AlignmentQuery.intersection(self, other)

    def offset_alignment(self, offset: float) -> "Alignment":
        """평행 이동한 새 선형."""
        return replace(self, entities=self.entities.offset_by(offset))

    def reversed_alignment(self) -> "Alignment":
        """뒤집힌 새 선형 (측점도 재배치)."""
        return replace(self, entities=self.entities.reversed())

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
        """FG 프로파일의 PVI 개수."""
        fg = self.fg_profile
        return len(fg.pvis) if fg else 0

    @property
    def max_grade(self) -> float:
        """FG 프로파일의 최대 기울기."""
        fg = self.fg_profile
        return fg.max_slope if fg else 0.0

    # ================================================================
    # Structure 조회
    # ================================================================
    @property
    def bridge_count(self) -> int:
        return len(self.structures.get_by_type('교량'))

    @property
    def tunnel_count(self) -> int:
        return len(self.structures.get_by_type('터널'))

    @property
    def cost(self) -> float:
        """공사비 (구조물 + 토공, 미구현)."""
        # TODO: 구조물별 단가 적용
        return 0.0

    # ================================================================
    # Transaction 기반 수정
    # ================================================================
    def modify(self) -> "AlignmentTransaction":
        """트랜잭션 시작."""
        return AlignmentTransaction(self)