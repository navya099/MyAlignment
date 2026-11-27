from dataclasses import replace

from cadgeom import Point2d
import pytest

from myalignment.alignment import Alignment, AlignmentBuilder
from myalignment.profile import Profile, ProfileBuilder, ProfileType
from myalignment.rail.rail_alignment import RailAlignment


def _geometry(model):
    return tuple(replace(entity, entity_id=0) for entity in model.entities)


def test_alignment_from_pi_coords_matches_builder_with_curves_and_profile():
    points = [(0, 0), Point2d(150, 0), (150, 150)]
    radii = [None, 40, None]
    lengths = [0, 12, 0]
    ground = Profile.from_points([(1000, 50), (1100, 53)], name="Ground")
    alignment = Alignment.from_pi_coords(
        iter(points), name="Route", radii=iter(radii), entry_lengths=iter(lengths),
        start_station=1000, profiles=iter([ground]),
    )
    builder = (
        AlignmentBuilder("Route").with_pi_coords(points).with_radii(radii)
        .with_spiral_lengths(lengths).with_start_station(1000).with_profile(ground)
    )
    assert _geometry(alignment) == _geometry(builder.build())
    assert alignment.eg_profile is ground
    assert len(alignment.entities) == 5


def test_alignment_from_pi_coords_accepts_straight_rail_and_reports_invalid_rows():
    alignment = RailAlignment.from_pi_coords([("10", "20"), (13, 24)], start_station=200)
    assert isinstance(alignment, RailAlignment)
    assert alignment.end_station == pytest.approx(205)
    with pytest.raises(ValueError, match="PI row 2"):
        Alignment.from_pi_coords([(0, 0), (1, float("nan"))])


def test_profile_reads_3500_csv_rows_and_interpolates_between_samples(tmp_path):
    path = tmp_path / "ground.csv"
    path.write_text(
        "STA;Z;note\n" + "".join(f"{1000 + 2 * i};{25 + i / 4};ground\n" for i in range(3500)),
        encoding="utf-8-sig",
    )
    ground = Profile.from_csv(path, name="Ground", station_column="STA", elevation_column="Z", delimiter=";")
    assert ground.profile_type is ProfileType.EG
    assert ground.name == "Ground"
    assert len(ground.entities) == 3499
    assert (ground.start_station, ground.end_station) == (1000, 7998)
    assert ground.elevation_at(5001) == pytest.approx(525.125)
    assert ground.elevation_at(7998) == pytest.approx(899.75)


def test_profile_points_matches_builder_and_bulk_append_is_atomic_on_bad_rows():
    points = [(10, 20), (15, 21), (25, 20)]
    expected = ProfileBuilder("Design", ProfileType.FG).add_tangent(10, 15, 20, 21).add_tangent(15, 25, 21, 20).build()
    profile = Profile.from_points(iter(points), name="Design", profile_type=ProfileType.FG)
    assert profile.profile_type is ProfileType.FG
    assert _geometry(profile) == _geometry(expected)
    builder = ProfileBuilder("Design", ProfileType.FG).add_tangent(10, 15, 20, 21)
    with pytest.raises(ValueError, match="row 3.*strictly increasing"):
        builder.add_points([(15, 21), (25, 20), (25, 19)])
    assert builder.build().end_station == 15
    assert _geometry(builder.add_points(iter(points[1:])).build()) == _geometry(expected)


@pytest.mark.parametrize(("rows", "error"), [
    ([(10, 20)], "At least two"),
    ([(10, 20), (5, 21)], "row 2.*strictly increasing"),
    ([(10, 20), (11, float("inf"))], "row 2.*finite"),
    ([(10, 20), (11,)], "row 2.*numeric"),
    ([(0, 0), "12"], "row 2.*numeric"),
])
def test_profile_rejects_invalid_sample_rows(rows, error):
    with pytest.raises(ValueError, match=error):
        Profile.from_points(rows)


def test_csv_rejects_missing_headers_and_reports_data_row(tmp_path):
    path = tmp_path / "invalid.csv"
    path.write_text("station,height\n0,10\n1,11\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one 'elevation' column"):
        Profile.from_csv(path)
    path.write_text("station,elevation\n0,10\n1,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Profile row 2"):
        Profile.from_csv(path)


def test_bulk_fg_creates_symmetric_and_asymmetric_vertical_curves():
    from myalignment.profile.profile_asymmetric_parabola import ProfileAsymmetricParabola
    from myalignment.profile.profile_symmetric_parabola import ProfileSymmetricParabola

    rows = [(0, 100), (100, 104, 60), (200, 99, (20, 30)), (300, 102)]
    ground = Profile.from_points([(0, 99), (300, 101)], name="Existing")
    fg = Profile.from_pvis(iter(rows), name="Design")
    axis = Alignment.from_pi_coords([(0, 0), (300, 0)], profiles=[fg, ground])
    assert axis.fg_profile is fg and axis.eg_profile is ground
    assert fg.pvi_count == 2 and len(fg.entities) == 5
    first, second = fg.entities[1], fg.entities[3]
    assert isinstance(first, ProfileSymmetricParabola)
    assert isinstance(second, ProfileAsymmetricParabola)
    assert (first.start_station, first.end_station, second.start_station, second.end_station) == (70, 130, 180, 230)
    assert fg.elevation_at(100) == pytest.approx(103.325)
    assert fg.elevation_at(200) == pytest.approx(99.48)
    checked = ProfileBuilder("Design", ProfileType.FG).add_pvis(rows).build(validate_grades=True)
    assert _geometry(checked) == _geometry(fg)


def test_adjacent_vertical_curves_can_touch_without_a_zero_length_tangent():
    profile = Profile.from_pvis([(0, 100), (100, 104, 50), (150, 102, 50), (225, 105)])
    left, right = profile.entities[1:3]
    assert left.end_station == right.start_station == 125
    assert left.end_elevation == pytest.approx(right.start_elevation)
    assert left.end_grade == pytest.approx(right.start_grade)
    assert len(profile.entities) == 4


def test_curve_can_reach_both_profile_endpoints_despite_decimal_rounding():
    profile = Profile.from_pvis([(0.1, 100), (0.2, 104, 0.2), (0.3, 102)])
    assert len(profile.entities) == 1
    assert (profile.start_station, profile.end_station) == (0.1, 0.3)
    assert profile.elevation_at(0.3) == pytest.approx(102)


@pytest.mark.parametrize(("rows", "error"), [
    ([(0, 100, 20), (100, 102)], "first and last"),
    ([(0, 100), (100, 105), (200, 102, 20)], "first and last"),
    ([(0, 100), (100, 105, 250), (200, 102)], "beyond an adjacent PVI"),
    ([(0, 100), (100, 105, 60), (150, 101, 60), (250, 104)], "overlap"),
    ([(0, 100), (100, 105, (20, 0)), (200, 102)], "finite and positive"),
    ([(0, 100), (100, 105, float("nan")), (200, 102)], "finite and positive"),
    ([(0, 100), (100, 105, 20), (200, 110)], "grade_in == grade_out"),
])
def test_invalid_fg_curve_definitions(rows, error):
    with pytest.raises(ValueError, match=error):
        Profile.from_pvis(rows)


def test_csv_can_import_fg_with_mixed_curve_specs(tmp_path):
    path = tmp_path / "design.csv"
    path.write_text(
        "station,elevation,L,Lin,Lout\n0,100,0,,\n100,104,60,,\n200,99,,20,30\n300,102,,,\n", encoding="utf-8",
    )
    profile = Profile.from_csv(path, curve_length_column="L", length_in_column="Lin", length_out_column="Lout")
    expected = Profile.from_pvis([(0, 100), (100, 104, 60), (200, 99, (20, 30)), (300, 102)])
    assert profile.profile_type is ProfileType.FG
    assert _geometry(profile) == _geometry(expected)
    assert Profile.from_csv(path).profile_type is ProfileType.EG

    path.write_text("station,elevation,L,Lin,Lout\n0,100,,,\n100,104,60,20,30\n200,99,,,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="row 2.*total length or both"):
        Profile.from_csv(path, curve_length_column="L", length_in_column="Lin", length_out_column="Lout")
    with pytest.raises(ValueError, match="must be set together"):
        Profile.from_csv(path, length_in_column="Lin")
