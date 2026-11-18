# featureline/builder.py
from __future__ import annotations
from myalignment.featureline.feature_line import FeatureLine
from myalignment.featureline.vertex import FeatureLineVertex, FeatureLinePointType


class FeatureLineBuilder:
    """FeatureLine 선언적 빌더."""
    def __init__(self, name: str = "FeatureLine1"):
        self._name = name
        self._vertices: list[FeatureLineVertex] = []
        self._is_closed = False
        self._site_id = ""
        self._relative_surface = ""

    def add_vertex(
        self,
        x: float, y: float, z: float,
        point_type: FeatureLinePointType = FeatureLinePointType.PI,
    ) -> "FeatureLineBuilder":
        self._vertices.append(FeatureLineVertex(x, y, z, point_type))
        return self

    def add_elevation_point(self, x: float, y: float, z: float) -> "FeatureLineBuilder":
        """표고점(Elevation Point) 추가."""
        return self.add_vertex(x, y, z, FeatureLinePointType.ELEVATION)

    def add_pi_point(self, x: float, y: float, z: float) -> "FeatureLineBuilder":
        """PI점 추가."""
        return self.add_vertex(x, y, z, FeatureLinePointType.PI)

    def add_coords(
        self,
        coords: list[tuple[float, float, float]],
        point_type: FeatureLinePointType = FeatureLinePointType.PI,
    ) -> "FeatureLineBuilder":
        for x, y, z in coords:
            self._vertices.append(FeatureLineVertex(x, y, z, point_type))
        return self

    def close(self) -> "FeatureLineBuilder":
        self._is_closed = True
        return self

    def with_site(self, site_id: str) -> "FeatureLineBuilder":
        self._site_id = site_id
        return self

    def with_relative_surface(self, surface_name: str) -> "FeatureLineBuilder":
        self._relative_surface = surface_name
        return self

    def build(self) -> FeatureLine:
        if len(self._vertices) < 2:
            raise ValueError(f"FeatureLine은 ≥ 2점 필요: {len(self._vertices)}")
        return FeatureLine(
            name=self._name,
            vertices=tuple(self._vertices),
            is_closed=self._is_closed,
            site_id=self._site_id,
            relative_surface=self._relative_surface,
        )