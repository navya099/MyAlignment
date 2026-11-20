from dataclasses import replace

import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.cant.curve import CantCriticalStation, CantCurve, CantPivotMethod
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.cant_band_extractor import CantBandSegmentExtractor
from myalignment.profile.cant_band_style import CantBandStyle
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.cant_band_renderer import CantBandRenderer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.scene import Scene


def _curve():
    return CantCurve(
        start_station=10, end_station=90, pivot_method=CantPivotMethod.LEFT_RAIL,
        critical_stations=tuple(CantCriticalStation(station, value) for station, value in (
            (20, 0), (40, -.12), (60, -.12), (80, 0),
        )),
    )


def test_extractor_classifies_negative_cant_and_converts_metres_to_mm():
    segments = CantBandSegmentExtractor.extract([_curve()])
    assert [s.region_type.name for s in segments] == [
        "NORMAL", "TRANSITION_IN", "FULL_SUPERELEVATION", "TRANSITION_OUT", "NORMAL",
    ]
    transition = segments[1]
    assert (transition.start_station, transition.end_station, transition.cant_change) == (20, 40, 120)
    assert transition.cant_at(25) == pytest.approx(30)
    assert transition.cant_at(15) == 0
    assert transition.cant_at(45) == 120
    assert transition.pivot_method is CantPivotMethod.LEFT_RAIL


def test_extractor_splits_signed_cant_at_zero():
    curve = CantCurve(critical_stations=(CantCriticalStation(10, .06), CantCriticalStation(40, -.12)))
    transition_out, transition_in = CantBandSegmentExtractor.extract([curve])
    assert transition_out.region_type.name == "TRANSITION_OUT"
    assert transition_in.region_type.name == "TRANSITION_IN"
    assert transition_out.end_station == transition_in.start_station == 20
    assert transition_out.end_cant == transition_in.start_cant == 0


def test_profile_view_clips_cant_band_by_station_and_exports_labels(tmp_path):
    rail = (
        AlignmentBuilder("Rail").with_pi_coords([(0, 0), (100, 0)])
        .as_rail_alignment(cant_curves=[_curve()]).build()
    )
    profile = ProfileBuilder().add_tangent(30, 70, 10, 10).build()
    bands = [
        ProfileViewBand(BandType.CANT_DATA, location="top", gap=2),
        ProfileViewBand(BandType.PROFILE_DATA, location="top", gap=1),
    ]
    style = CantBandStyle(unit="m", text_color=2, transition_color=4)
    scene = ProfileViewRenderer.render(
        [profile], "Rail", ProfileViewStyle(vertical_exaggeration=2), bands,
        alignment=rail, cant_band_style=style,
    )
    band = [p for p in scene.primitives if p.style.layer == style.layer]
    assert all(30 <= pt.x <= 70 for p in band for pt in p.points)
    labels = {(p.points[0].x, p.text): p for p in band if p.type is PrimitiveType.TEXT}
    assert labels[(30, "0.060 m")].style.color == 2
    assert labels[(70, "0.060 m")].style.color == 2
    assert labels[(35, "TI | P: LeftRail")].style.color == 4
    assert labels[(50, "FC | P: LeftRail")].style.color == 1
    assert (65, "TO | P: LeftRail") in labels
    assert next(p for p in scene.primitives if p.style.layer == "C-PROF-BAND").points[0].y == 50
    path = tmp_path / "cant.dxf"
    DxfWriter(scene).write(path)
    assert "\nFC | P: LeftRail\n" in path.read_text("cp949")

    quiet = CantBandRenderer.render(
        Scene(), rail, 0, replace(style, show_cant_value=False, show_region_label=False, show_pivot=False),
    )
    assert quiet.primitives and all(p.type is PrimitiveType.LINE for p in quiet.primitives)


def test_rail_without_cant_data_leaves_scene_intact():
    rail = AlignmentBuilder().with_pi_coords([(0, 0), (100, 0)]).as_rail_alignment().build()
    scene = Scene()
    assert CantBandRenderer.render(scene, rail, 0, CantBandStyle()) is scene
