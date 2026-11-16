# ================================================================
# 빌더 — 선언적 Alignment 생성
# ================================================================
from cadgeom import Point2d
from myalignment.profile.profile import Profile
from myalignment.alignment.alignment import Alignment
from myalignment.enitity.entity_factory import EntityFactory
from myalignment.enum.spiraltype import SpiralType
from myalignment.ipdata.ipdata import PIInput
from myalignment.structure.structurecollection import StructureCollection



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
        self._structures.append(structure)
        return self

    def with_design_speed(self, speed: float) -> "AlignmentBuilder":
        self._design_speed = speed
        return self

    def with_route_type(self, route_type: str) -> "AlignmentBuilder":
        self._route_type = route_type
        return self

    def with_metadata(self, **kwargs) -> "AlignmentBuilder":
        self._metadata.update(kwargs)
        return self

    def build(self) -> Alignment:
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

        return Alignment(
            name=self._name,
            entities=entities,
            profiles=tuple(self._profiles),
            structures=self._structures,
            design_speed=self._design_speed,
            route_type=self._route_type,
            metadata=dict(self._metadata),
        )