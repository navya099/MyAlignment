import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.alignment.label_component import AlignmentLabelComponent
from myalignment.alignment.label_set import AlignmentLabelSet
from myalignment.alignment.label_style import AlignmentLabelStyle
from myalignment.alignment.label_type import AlignmentLabelType
from myalignment.alignment.station_equation import StationEquation
from myalignment.alignment.station_equation_collection import StationEquationCollection
from myalignment.alignment.station_equation_type import StationEquationType
from myalignment.render.alignment_label_renderer import AlignmentLabelRenderer
from myalignment.render.scene import Scene


def _alignment():
    return AlignmentBuilder().with_pi_coords([(10, 20), (310, 20)]).build()


def test_collection_add_lookup_and_remove_immutably():
    early, late = StationEquation(50, 100), StationEquation(125, 500)
    original = StationEquationCollection().add(late)
    equations = original.add(early)
    assert tuple(equations) == (early, late)
    assert early.delta == 50
    assert equations.get_at_raw(50.0000002) is early
    assert equations.equations_after(50) == (late,)
    assert equations.remove_at_raw(50) == equations.remove_at_index(0) == original
    with pytest.raises(ValueError, match="distinct"):
        equations.add(StationEquation(50, 10))
    with pytest.raises(ValueError, match="increasing"):
        StationEquationCollection((late, early))
    with pytest.raises(ValueError, match="finite"):
        StationEquation(float("nan"))
    with pytest.raises(IndexError):
        equations.remove_at_index(-1)


def test_multiple_equations_include_ahead_and_reject_skipped_stations():
    base = _alignment()
    alignment = base.add_station_equation(125, 500).add_station_equation(
        200, 900, StationEquationType.DECREASING,
    )
    assert not base.station_equations
    assert alignment.remove_station_equation(125).raw_to_display_station(130) == 130
    for raw, display in [(120, 120), (125, 500), (130, 505), (199, 574),
                         (200, 900), (215, 885), (300, 800)]:
        assert alignment.raw_to_display_station(raw) == display
        assert alignment.display_to_raw_station(display) == raw
    for display in (125, 499, 575, 799, 901):
        assert alignment.display_to_raw_stations(display) == ()
        with pytest.raises(ValueError, match="No raw station"):
            alignment.display_to_raw_station(display)


def test_inverse_exposes_duplicate_display_values_across_segments():
    alignment = _alignment().add_station_equation(100, 50)
    assert alignment.display_to_raw_stations(75) == (75, 125)
    with pytest.raises(ValueError, match="Ambiguous"):
        alignment.display_to_raw_station(75)
    assert alignment.display_to_raw_station(100) == 150


def test_station_labels_use_display_values_at_raw_geometry_locations():
    style = AlignmentLabelStyle(label_type=AlignmentLabelType.MAJOR_STATION, components=(
        AlignmentLabelComponent(contents="<[Raw Station]> / <[Station Value]>", offset_y=0),
    ))
    alignment = (
        _alignment().add_station_equation(100, 500)
        .add_station_equation(200, 900, StationEquationType.DECREASING)
        .with_label_set(AlignmentLabelSet(styles={style.label_type: style}))
    )
    scene = AlignmentLabelRenderer.render(Scene(), alignment)
    assert [p.text for p in scene.primitives] == [
        "0.00 / 0.00", "100.00 / 500.00", "200.00 / 900.00", "300.00 / 800.00",
    ]
    assert [(p.points[0].x, p.points[0].y) for p in scene.primitives] == [
        (10, 20), (110, 20), (210, 20), (310, 20),
    ]


def test_reversing_alignment_keeps_display_stations_at_the_same_coordinates():
    alignment = _alignment().add_station_equation(100, 500).add_station_equation(
        200, 900, StationEquationType.DECREASING,
    )
    reversed_alignment = alignment.reversed_alignment()
    for raw in (0, 50, 150, 250, 300):
        reverse_raw = 300 - raw
        assert reversed_alignment.point_at(reverse_raw).distance_to(alignment.point_at(raw)) < 1e-9
        assert reversed_alignment.raw_to_display_station(reverse_raw) == alignment.raw_to_display_station(raw)
    assert reversed_alignment.raw_to_display_station(200) == 100
