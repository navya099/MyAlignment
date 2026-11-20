import math

import pytest
from cadgeom import Point2d

from myalignment.alignment.alignment import Alignment
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.entity_collection import AlignmentEntityCollection
from myalignment.enitity.line_entity import LineEntity
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.enum.spiraltype import SpiralType
from myalignment.profile.band_style import GeometryBandStyle
from myalignment.profile.geometry_extractor import GeometryPointExtractor
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.geometry_band_renderer import HorizontalGeometryBandRenderer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.scene import Scene
from myalignment.utils import CurveDirection


def _alignment(with_spirals):
    entities = [LineEntity.create(Point2d(0, 0), Point2d(30, 0), 500)]

    def add_spiral():
        previous = entities[-1]
        entities.append(SpiralEntity.create(
            start_coord=previous.end_coord, start_azimuth=previous.end_azimuth,
            start_station=previous.end_station, radius=200, length=20,
            spiral_type=SpiralType.Clothoid, direction=CurveDirection.LEFT,
        ))

    if with_spirals:
        add_spiral()
    previous = entities[-1]
    entities.append(ArcEntity.create(
        start_coord=previous.end_coord, start_azimuth=previous.end_azimuth,
        start_station=previous.end_station, radius=200, delta=0.2,
        direction=CurveDirection.LEFT,
    ))
    if with_spirals:
        add_spiral()
    previous = entities[-1]
    end = Point2d(
        previous.end_coord.x + 30 * math.cos(previous.end_azimuth),
        previous.end_coord.y + 30 * math.sin(previous.end_azimuth),
    )
    entities.append(LineEntity.create(previous.end_coord, end, previous.end_station))
    return Alignment(name="Main", entities=AlignmentEntityCollection(tuple(entities)))


@pytest.mark.parametrize(
    "with_spirals, symbols, stations, radii",
    [
        (True, ["TS", "SC", "CS", "ST"], [530, 550, 590, 610], [0, 200, 200, 0]),
        (False, ["BC", "EC"], [530, 570], [200, 200]),
    ],
)
def test_geometry_points_preserve_stations_radii_and_tangents(with_spirals, symbols, stations, radii):
    alignment = _alignment(with_spirals)
    points = GeometryPointExtractor.extract(alignment)
    assert [p.point_type.value for p in points] == symbols
    assert [p.station for p in points] == pytest.approx(stations)
    assert [p.radius for p in points] == radii
    assert [p.tangent_in for p in points] == pytest.approx([e.end_azimuth for e in alignment.entities[:-1]])
    assert [p.tangent_out for p in points] == pytest.approx([e.start_azimuth for e in alignment.entities[1:]])
    assert points[0].is_curve_start and points[-1].is_curve_end
    assert all(p.is_spiral_point is with_spirals for p in points)


def test_pi_can_be_enabled_for_a_tangent_junction():
    alignment = (
        AlignmentBuilder().with_pi_coords([(0, 0), (20, 0), (40, 0), (40, 20)]).build()
    )
    point, = GeometryPointExtractor.extract(alignment)
    assert point.label == "PI"
    assert point.station == pytest.approx(40)
    default_scene = HorizontalGeometryBandRenderer.render(Scene(), alignment, 0, GeometryBandStyle())
    assert len(default_scene.primitives) == 2
    scene = HorizontalGeometryBandRenderer.render(
        Scene(), alignment, 0, GeometryBandStyle(visible_types=("PI",)),
    )
    assert [p.text for p in scene.primitives if p.type is PrimitiveType.TEXT] == ["PI"]


def test_profile_view_clips_and_stacks_styled_geometry_band():
    alignment = _alignment(True)
    profile = ProfileBuilder("Grade").add_tangent(540, 600, 10, 10).build()
    bands = [
        ProfileViewBand(BandType.HORIZONTAL_GEOMETRY, location="top", gap=2),
        ProfileViewBand(BandType.PROFILE_DATA, location="top", gap=1),
    ]
    style = GeometryBandStyle(
        band_height=5, tick_length=2, tick_color=3, text_color=1, layer="Geom",
        visible_types=("TS", "SC", "ST"),
    )
    scene = ProfileViewRenderer.render(
        [profile], alignment.name, ProfileViewStyle(vertical_exaggeration=2), bands,
        alignment=alignment, geometry_band_style=style,
    )
    primitives = [p for p in scene.primitives if p.style.layer == "Geom"]
    assert [p.points[0].y for p in primitives[:2]] == [44, 34]
    assert all([point.x for point in p.points] == [540, 600] for p in primitives[:2])
    assert [p.style.color for p in primitives[2:5]] == [3, 3, 6]
    labels = primitives[5:]
    assert [p.text for p in labels] == ["SC", "R=200"]
    assert labels[0].points[0].x == pytest.approx(550)
    assert all(p.rotation == math.pi / 2 and p.style.color == 1 for p in labels)
    assert next(p for p in scene.primitives if p.style.layer == "C-PROF-BAND").points[0].y == 56
