# ================================================================
# 빌더 — 선언적 Alignment 생성
# ================================================================
from cadgeom import Point2d

from myalignment.corridor.corridor import Corridor
from myalignment.profile.profile import Profile
from myalignment.alignment.alignment import Alignment
from myalignment.alignment.style.alignment_style import AlignmentStyle
from myalignment.enitity.entity_factory import EntityFactory
from myalignment.enum.spiraltype import SpiralType
from myalignment.ipdata.ipdata import PIInput
from myalignment.rail.rail_alignment import RailAlignment
from myalignment.structure.bridge import Bridge
from myalignment.structure.structurecollection import StructureCollection
from myalignment.structure.tunnel import Tunnel
from myalignment.superelevation.collection import SuperelevationCollection


class AlignmentBuilder:
    """
    Alignment 선언적 생성 빌더.

    사용 예:
        alignment = (
            AlignmentBuilder("노선1")
            .with_pi_coords([(0,0), (100,0), (200,100)])
            .with_radii([None, 300, None])
            .with_spiral_lengths(entry=[0, 30, 0], exit=[0, 30, 0])
            .with_design_speed(80)
            .build()
        )
    """

    def __init__(self, name: str = "Alignment1"):
        self._superelevation_curves = SuperelevationCollection()
        self._corridors: list[Corridor] = []
        self._name = name
        self._coords: list[tuple[float, float] | Point2d] = []
        self._radii: list[float | None] = []
        self._entry_lengths: list[float] = []
        self._exit_lengths: list[float] = []
        self._spiral_type = None
        self._start_station = 0.0

        self._profiles: list[Profile] = []
        self._structures = StructureCollection()
        self._design_speed = 0.0
        self._route_type = ""
        self._metadata: dict = {}
        self._style = AlignmentStyle.basic()

        self._is_rail = False
        self._gauge = 1.435
        self._cant_curves: list = []

    def with_pi_coords(self, coords) -> "AlignmentBuilder":
        self._coords = list(coords)
        return self

    def with_radii(self, radii: list[float | None]) -> "AlignmentBuilder":
        self._radii = list(radii)
        return self

    def with_spiral_lengths(
            self,
            entry: list[float],
            exit: list[float] | None = None,
            spiral_type=None,
    ) -> "AlignmentBuilder":

        self._entry_lengths = list(entry)
        self._exit_lengths = list(exit) if exit else list(entry)
        self._spiral_type = spiral_type or SpiralType.Clothoid
        return self

    def with_start_station(self, sta: float) -> "AlignmentBuilder":
        self._start_station = sta
        return self

    def with_profile(self, profile: Profile) -> "AlignmentBuilder":
        self._profiles.append(profile)
        return self

    def with_structure(self, structure) -> "AlignmentBuilder":
        self._structures = self._structures.add(structure)
        return self

    def with_bridge(self, name, start_station, end_station, **metadata):
        return self.with_structure(
            Bridge.create(name, start_station, end_station, **metadata)
        )

    def with_tunnel(self, name, start_station, end_station, **metadata):
        return self.with_structure(
            Tunnel.create(name, start_station, end_station, **metadata)
        )

    def with_design_speed(self, speed: float) -> "AlignmentBuilder":
        self._design_speed = speed
        return self

    def with_route_type(self, route_type: str) -> "AlignmentBuilder":
        self._route_type = route_type
        return self

    def with_style(self, style: AlignmentStyle) -> "AlignmentBuilder":
        self._style = style
        return self

    def with_metadata(self, **kwargs) -> "AlignmentBuilder":
        self._metadata.update(kwargs)
        return self

    def with_superelevation_curve(self, curve) -> "AlignmentBuilder":
        """편구배 곡선 추가 (여러 개 누적 가능)."""
        self._superelevation_curves= self._superelevation_curves.add(curve)
        return self

    def with_corridor(self, corridor) -> "AlignmentBuilder":
        """코리더 추가 (여러 개 누적 가능)."""
        self._corridors.append(corridor)
        return self

    def build(self) -> Alignment | RailAlignment:
        if not self._coords:
            raise ValueError("PI 좌표가 없습니다.")
        if not self._radii:
            self._radii = [None] * len(self._coords)
        if len(self._radii) != len(self._coords):
            raise ValueError("좌표/반경 길이 불일치")

        if not self._entry_lengths:
            self._entry_lengths = [0.0] * len(self._coords)
        if not self._exit_lengths:
            self._exit_lengths = [0.0] * len(self._coords)

        pi_input = PIInput.from_coords_and_radii(
            coords=self._coords,
            radii=self._radii,
            start_station=self._start_station,
            spiral_type=self._spiral_type or SpiralType.Clothoid,
            entry_lengths=self._entry_lengths,
            exit_lengths=self._exit_lengths,
        )
        entities = EntityFactory.build(pi_input)

        # 철도 선형 모드인 경우 RailAlignment 반환
        if self._is_rail:
            return RailAlignment(
                name=self._name,
                entities=entities,
                profiles=tuple(self._profiles),
                structures=self._structures,
                design_speed=self._design_speed,
                route_type=self._route_type,
                metadata=dict(self._metadata),
                corridors=self._corridors,
                superelevation=self._superelevation_curves,
                style=self._style,
                is_rail=True,
                gauge=self._gauge,
                cant_curves=tuple(self._cant_curves),
            )

        # 일반 Alignment 반환
        return Alignment(
            name=self._name,
            entities=entities,
            profiles=tuple(self._profiles),
            structures=self._structures,
            design_speed=self._design_speed,
            route_type=self._route_type,
            metadata=dict(self._metadata),
            corridors=self._corridors,
            superelevation=self._superelevation_curves,
            style=self._style,
        )

    def as_rail_alignment(self, gauge: float = 1.435, cant_curves=None) -> "AlignmentBuilder":
        """철도 선형 빌드 모드로 설정합니다 (체이닝 유지)."""
        self._is_rail = True
        self._gauge = gauge
        if cant_curves:
            self._cant_curves.extend(cant_curves)
        return self

    def with_cant_curve(self, curve) -> "AlignmentBuilder":
        """빌더 단계에서 캔트 커브 추가"""
        self._cant_curves.append(curve)
        return self