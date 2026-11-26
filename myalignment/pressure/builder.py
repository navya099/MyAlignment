from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from myalignment.pipe.pipe_type import PipeMaterial
from myalignment.pressure.appurtenance import PressureAppurtenance
from myalignment.pressure.fitting import PressureFitting
from myalignment.pressure.network import PressureNetwork
from myalignment.pressure.part import AppurtenancePart, FittingPart, PressurePipePart, _positive
from myalignment.pressure.pipe import PressurePipe
from myalignment.render.primitives_3d import Point3D

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.surface.tin_surface import TinSurface


class PressureNetworkBuilder:
    """관 중심선, 피팅과 부속품을 선언하는 빌더."""

    def __init__(self, name: str = "PressureNetwork1"):
        self._name = name
        self._pipes: list[PressurePipe] = []
        self._fittings: list[PressureFitting] = []
        self._appurtenances: list[PressureAppurtenance] = []
        self._parts_list = ""
        self._alignment_name = ""
        self._surface_name = ""
        self._surface: TinSurface | None = None
        self._pressure_rating = 150.0

    def with_parts_list(self, name: str) -> PressureNetworkBuilder:
        self._parts_list = name
        return self

    def with_alignment(self, name: str | Alignment) -> PressureNetworkBuilder:
        self._alignment_name = name if isinstance(name, str) else name.name
        return self

    def with_surface(self, name: str | TinSurface) -> PressureNetworkBuilder:
        """참조 지표면을 지정한다. TIN 객체를 주면 토피를 계산한다."""
        self._surface = None if isinstance(name, str) else name
        self._surface_name = name if isinstance(name, str) else name.name
        return self

    def with_pressure_rating(self, pressure_rating_psi: float) -> PressureNetworkBuilder:
        """검사에 사용할 관망 설계 압력 등급을 지정한다."""
        _positive(pressure_rating_psi, "pressure_rating_psi")
        self._pressure_rating = pressure_rating_psi
        return self

    def add_pipe_run(
        self, start: Point3D, end: Point3D, material: PipeMaterial = PipeMaterial.PVC,
        diameter_mm: float = 150.0, pressure_rating_psi: float = 150.0,
        start_fitting_id: str = "", end_fitting_id: str = "", *,
        start_appurtenance_id: str = "", end_appurtenance_id: str = "",
        part: PressurePipePart | None = None, name: str | None = None,
    ) -> PressureNetworkBuilder:
        """관 중심선의 직선 구간을 추가한다. 양 끝의 연결 ID는 선택 사항이다."""
        if not isinstance(start, Point3D) or not isinstance(end, Point3D):
            raise TypeError("Pipe centerline endpoints must be Point3D")
        if start == end:
            raise ValueError("Pipe centerline endpoints must be distinct")
        index = len(self._pipes)
        if part is None:
            part = PressurePipePart(
                material=material, nominal_diameter_mm=diameter_mm, inner_diameter_mm=diameter_mm,
                pressure_rating_psi=pressure_rating_psi,
            )
        self._pipes.append(PressurePipe(
            id=f"PP_{index:03d}", name=name if name is not None else f"PP-{index + 1:03d}",
            part=part, start_point=start, end_point=end, start_fitting_id=start_fitting_id,
            end_fitting_id=end_fitting_id, start_appurtenance_id=start_appurtenance_id,
            end_appurtenance_id=end_appurtenance_id,
        ))
        return self

    def add_fitting(
        self, location: Point3D, part: FittingPart, connected_pipe_ids: tuple[str, ...] = (), *,
        name: str | None = None,
    ) -> PressureNetworkBuilder:
        """피팅과 연결할 관의 ID를 추가한다."""
        if not isinstance(location, Point3D):
            raise TypeError("Fitting location must be Point3D")
        index = len(self._fittings)
        self._fittings.append(PressureFitting(
            f"PF_{index:03d}", name if name is not None else f"{part.fitting_type.value}-{index + 1:03d}",
            part, location, connected_pipe_ids,
        ))
        return self

    def add_bend(
        self, location: Point3D, diameter_mm: float = 150.0, angle_deg: float = 90.0,
        connected_pipe_ids: tuple[str, ...] = (), *, max_deflection_deg: float = 11.25,
    ) -> PressureNetworkBuilder:
        """지정한 방향 전환각의 엘보를 추가한다."""
        return self.add_fitting(location, FittingPart(
            diameter_mm=diameter_mm, angle_deg=angle_deg, max_deflection_deg=max_deflection_deg,
        ), connected_pipe_ids)

    def add_appurtenance(
        self, location: Point3D, part: AppurtenancePart, connected_pipe_ids: tuple[str, ...] = (), *,
        name: str | None = None,
    ) -> PressureNetworkBuilder:
        """밸브·소화전 등 부속품과 연결할 관의 ID를 추가한다."""
        if not isinstance(location, Point3D):
            raise TypeError("Appurtenance location must be Point3D")
        index = len(self._appurtenances)
        self._appurtenances.append(PressureAppurtenance(
            f"PA_{index:03d}", name if name is not None else f"{part.appurtenance_type.value}-{index + 1:03d}",
            part, location, connected_pipe_ids,
        ))
        return self

    def add_valve(
        self, location: Point3D, diameter_mm: float = 150.0, connected_pipe_ids: tuple[str, ...] = (),
    ) -> PressureNetworkBuilder:
        return self.add_appurtenance(location, AppurtenancePart(diameter_mm=diameter_mm), connected_pipe_ids)

    def build(self) -> PressureNetwork:
        pipes = tuple(
            replace(pipe, alignment_name=self._alignment_name, surface_name=self._surface_name)
            for pipe in self._pipes
        )
        network = PressureNetwork(
            name=self._name, pipes=pipes, fittings=tuple(self._fittings), appurtenances=tuple(self._appurtenances),
            parts_list_name=self._parts_list, reference_alignment=self._alignment_name,
            reference_surface=self._surface_name, pressure_rating_psi=self._pressure_rating,
        )
        return network if self._surface is None else network.with_cover_from(self._surface)
