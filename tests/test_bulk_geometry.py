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
