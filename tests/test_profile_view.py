import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.cant.curve import CantCriticalStation, CantCurve
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.profile import Profile, ProfileBuilder
from myalignment.profile.profiletype import ProfileType
from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.scene import Scene


def test_profile_view_grid_profiles_and_bands_export_to_dxf(tmp_path):
    design = ProfileBuilder("설계", ProfileType.FG).add_tangent(10, 90, 100, 108).build()
    ground = ProfileBuilder("현황").add_tangent(40, 75, 102, 103).build()
    style = ProfileViewStyle(
        grid_major_interval_station=30,
        grid_minor_interval_station=15,
        grid_major_interval_elevation=10,
        grid_minor_interval_elevation=5,
        vertical_exaggeration=2,
        band_location="top",
    )
    bands = [
        ProfileViewBand(BandType.PROFILE_DATA, gap=3),
        ProfileViewBand(BandType.PROFILE_DATA, gap=2, profile_names=("현황",)),
        ProfileViewBand(BandType.PROFILE_DATA, location="bottom", gap=1, profile_names=("설계",)),
    ]
    original = Scene(metadata={"project": "Rail"})
    scene = ProfileViewRenderer.render([Profile(), design, ground], "Main", style, bands, original)

    assert not original.primitives
    assert scene.metadata == {
        "project": "Rail", "alignment_name": "Main", "start_station": 10,
        "end_station": 90, "vertical_exaggeration": 2,
    }
    grid = [p for p in scene.primitives if p.style.layer == "C-PROF-GRID"]
    station_lines = {p.points[0].x: p.style.color for p in grid if p.points[0].x == p.points[1].x}
    assert station_lines == {15: 9, 30: 8, 45: 9, 60: 8, 75: 9, 90: 8}
    elevation_lines = {p.points[0].y: p.style.color for p in grid if p.points[0].y == p.points[1].y}
    assert elevation_lines == {190: 9, 200: 8, 210: 9, 220: 8}

    profile_lines = [p for p in scene.primitives if p.type is PrimitiveType.POLYLINE]
    assert [p.style.layer for p in profile_lines] == ["C-PROF-FG", "C-PROF-EG"]
    assert [p.points[-1].y for p in profile_lines] == [216, 206]

    band_lines = [p for p in scene.primitives if p.style.layer == "C-PROF-BAND" and p.type is PrimitiveType.LINE]
    assert [p.points[0].y for p in band_lines] == [232, 242, 188]
    labels = [p for p in scene.primitives if p.type is PrimitiveType.TEXT]
    assert [p.text for p in labels] == [
        "30 | 설계: 102.00", "60 | 설계: 105.00 | 현황: 102.57", "90 | 설계: 108.00",
        "60 | 현황: 102.57",
        "30 | 설계: 102.00", "60 | 설계: 105.00", "90 | 설계: 108.00",
    ]

    path = tmp_path / "profile-view.dxf"
    DxfWriter(scene).write(path)
    assert "60 | 설계: 105.00 | 현황: 102.57" in path.read_text("cp949")


def test_profile_view_geometry_and_cant_bands_use_model_data():
    profile = ProfileBuilder("Grade").add_tangent(0, 100, 10, 12).build()
    cant = CantCurve(start_station=0, end_station=100, critical_stations=(
        CantCriticalStation(station=0),
        CantCriticalStation(station=45, cant_value=0.105),
        CantCriticalStation(station=100),
    ))
    alignment = (
        AlignmentBuilder("Rail").with_pi_coords([(0, 0), (100, 0)])
        .as_rail_alignment(cant_curves=(cant,)).build()
    )
    bands = [
        ProfileViewBand(BandType.VERTICAL_GEOMETRY),
        ProfileViewBand(BandType.HORIZONTAL_GEOMETRY),
        ProfileViewBand(BandType.CANT_DATA),
    ]
    scene = ProfileViewRenderer.render([profile], alignment.name, ProfileViewStyle(), bands, alignment=alignment)
    labels = [p.text for p in scene.primitives if p.type is PrimitiveType.TEXT]
    assert labels[:3] == ["PVI", "PVI", "Line 100.00 m"]
    assert {"0 mm", "105 mm", "TI | P: Center", "TO | P: Center"} <= set(labels[3:])


def test_profile_view_validates_intervals_and_preserves_empty_scene():
    with pytest.raises(ValueError, match="grid_minor_interval_station"):
        ProfileViewStyle(grid_minor_interval_station=0)
    with pytest.raises(ValueError, match="gap"):
        ProfileViewBand(BandType.PROFILE_DATA, gap=-1)
    scene = Scene(metadata={"project": "Rail"})
    assert ProfileViewRenderer.render([Profile()], "Empty", ProfileViewStyle(), scene=scene) is scene
