from dataclasses import replace

import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.export.dxf_writer import DxfWriter
from myalignment.export.svg_writer import SvgWriter
from myalignment.profile.earthwork_band_generator import EarthworkBandGenerator
from myalignment.profile.earthwork_band_style import EarthworkBandStyle
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.profiletype import ProfileType
from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_split_config import ProfileViewSplitConfig
from myalignment.profile.view_split_method import ProfileViewSplitMethod
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.label_box import LabelBox
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.profile_view_split_composer import ProfileViewSplitComposer
from myalignment.render.stagger_presets import StaggerConfigPresets


BAND = ProfileViewBand(BandType.EARTHWORK)
LAYER = EarthworkBandStyle.standard().layer


def _tangent(name, begin, end, z1, z2, kind=ProfileType.FG):
    return ProfileBuilder(name, kind).add_tangent(begin, end, z1, z2).build()


def _layer_items(scene, layer=LAYER):
    return [p for p in scene.primitives if p.style.layer == layer]


def _text_center(text):
    anchor = text.points[0]
    return LabelBox.from_text(anchor.x, anchor.y, text.text, text.text_height).center_x


def test_samples_and_volumes_split_at_crossing_between_columns():
    fg = _tangent("FG", 0, 100, 6, 16)
    eg = _tangent("EG", 0, 100, 10, 10)
    style = EarthworkBandStyle(sample_interval=100)
    data = EarthworkBandGenerator.generate(fg, eg, style)
    cut, fill = data
    assert (cut.station, cut.fg_elevation, cut.eg_elevation, cut.diff, cut.cut, cut.fill, cut.area_type) == (
        0, 6, 10, -4, 4, 0, "cut",
    )
    assert (fill.station, fill.cut, fill.fill, fill.area_type) == (100, 0, 6, "fill")
    assert data.total_cut_volume == pytest.approx(800)
    assert data.total_fill_volume == pytest.approx(1800)
    assert data.net_volume == pytest.approx(1000)
    assert EarthworkBandGenerator.generate(fg, eg, style, road_width=0).total_cut_volume == 0


def test_crest_detects_fill_between_hidden_crossings():
    fg = ProfileBuilder("FG").add_symmetric_parabola(20, 10, 0.1, -0.1, 40).build()
    eg = _tangent("EG", 0, 40, 8.75, 8.75)
    data = EarthworkBandGenerator.generate(fg, eg, EarthworkBandStyle(sample_interval=50))
    assert [sample.area_type for sample in data] == ["cut", "cut"]
    assert data.total_cut_volume > 0
    assert data.total_fill_volume > 0


def test_common_range_clips_to_window_without_resetting_sample_grid():
    fg = _tangent("FG", 100, 200, 2, 2)
    eg = _tangent("EG", 125, 190, 2, 2)
    data = EarthworkBandGenerator.generate(fg, eg, station_range=(130, 185))
    assert data.station_range() == (130, 185)
    assert [point.station for point in data] == [130, 175, 185]
    assert all(sample.area_type == "none" for sample in data)
    assert data.total_cut_volume == data.total_fill_volume == 0
    assert not EarthworkBandGenerator.generate(fg, eg, station_range=(190, 200))
    assert not EarthworkBandGenerator.generate(fg, ProfileBuilder("Empty").build())


@pytest.mark.parametrize("step", [0, -1, float("nan"), float("inf")])
def test_invalid_sample_interval(step):
    with pytest.raises(ValueError, match="sample_interval"):
        EarthworkBandStyle(sample_interval=step)


def test_render_rows_align_to_raw_stations_and_export(tmp_path):
    axis = (
        AlignmentBuilder("Main").with_pi_coords([(0, 0), (100, 0)])
        .with_start_station(100).build().add_station_equation(130, 300)
    )
    fg = _tangent("Design", 100, 200, 6, 16)
    eg = _tangent("Existing", 140, 195, 12, 12, ProfileType.EG)
    view_style = ProfileViewStyle(vertical_exaggeration=2)
    style = replace(EarthworkBandStyle.detailed(), sample_interval=25, band_gap=3)
    bands = [
        ProfileViewBand(BandType.EARTHWORK, profile_names=("Design", "Existing"), gap=2),
        ProfileViewBand(BandType.PROFILE_DATA),
    ]
    scene = ProfileViewRenderer.render(
        [eg, fg], axis.name, view_style, bands, alignment=axis, earthwork_band_style=style,
        fg_profile_name="Unused", eg_profile_name="Unused",
        stagger_config=StaggerConfigPresets.up_increment(), render_labels=False,
    )
    items = _layer_items(scene)
    texts = [p for p in items if p.type is PrimitiveType.TEXT]
    assert {"STA", "FG", "EG", "CUT", "FILL", "Δ", "—", "-2.00", "+0.50"} <= {p.text for p in texts}
    displayed, = [p for p in texts if p.text == "310.0"]
    assert _text_center(displayed) == pytest.approx(140)
    lines = [p for p in items if p.type is PrimitiveType.LINE]
    assert min(p.x for line in lines for p in line.points) == 140
    assert max(p.x for line in lines for p in line.points) == 195
    assert max(p.y for line in lines for p in line.points) == (6 - 5 - 2) * 2
    bottom = min(p.y for line in lines for p in line.points)
    next_band = next(p for p in _layer_items(scene, ProfileViewRenderer.BAND_LAYER) if p.type is PrimitiveType.LINE)
    assert next_band.points[0].y == bottom - style.band_gap * 2

    dxf = tmp_path / "earthwork.dxf"
    DxfWriter(scene).write(dxf)
    assert LAYER in dxf.read_text("cp949")
    svg = SvgWriter(scene).to_string()
    assert "310.0" in svg and LAYER in svg


def test_split_top_band_clips_to_each_panel_and_uses_profile_types():
    fg = _tangent("Design", 100, 200, 6, 16)
    eg = _tangent("Existing", 125, 190, 10, 10, ProfileType.EG)
    view_style = ProfileViewStyle(vertical_exaggeration=3)
    config = ProfileViewSplitConfig(
        method=ProfileViewSplitMethod.MANUAL, manual_split_stations=(160,),
        columns=2, overlap_station=0,
    )
    style = EarthworkBandStyle.minimal()
    bands = [ProfileViewBand(BandType.EARTHWORK, location="top")]
    composed = ProfileViewSplitComposer.compose(
        [eg, fg], "Main", view_style, config, bands=bands, earthwork_band_style=style,
    )
    texts = [p for p in _layer_items(composed) if p.type is PrimitiveType.TEXT]
    assert {"FG", "EG", "Δ"}.isdisjoint(p.text for p in texts)
    values = [(p.text, _text_center(p)) for p in texts if p.text in {"125.0", "160.0", "175.0", "190.0"}]
    panel1, panel2 = composed.metadata["panels"]
    dx1, dx2 = panel1["translation"][0], panel2["translation"][0]
    assert [value for value, _ in values] == ["125.0", "160.0", "160.0", "175.0", "190.0"]
    assert [x for _, x in values] == pytest.approx([125 + dx1, 160 + dx1, 160 + dx2, 175 + dx2, 190 + dx2])

    single = ProfileViewRenderer.render([fg, eg], "Main", view_style, bands, earthwork_band_style=style)
    lines = [p for p in _layer_items(single) if p.type is PrimitiveType.LINE]
    assert min(p.y for line in lines for p in line.points) == (16 + 5) * 3


def test_missing_profile_or_empty_style_leaves_other_bands_in_place():
    fg = _tangent("Design", 0, 100, 10, 10)
    eg = _tangent("Existing", 0, 100, 12, 12, ProfileType.EG)
    disabled = EarthworkBandStyle(show_station=False, show_fg=False, show_eg=False, show_cut=False, show_fill=False)
    other = ProfileViewBand(BandType.PROFILE_DATA)
    band = replace(BAND, gap=20)
    for profiles, style in (([fg], None), ([fg, eg], disabled)):
        expected = ProfileViewRenderer.render(profiles, "Main", ProfileViewStyle(), [other])
        actual = ProfileViewRenderer.render(
            profiles, "Main", ProfileViewStyle(), [band, other], earthwork_band_style=style,
        )
        assert actual == expected
