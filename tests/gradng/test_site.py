# tests/grading/test_site.py
from myalignment.grading.criteria import SlopeFormat, Slope
from myalignment.grading.criteria_distance import SlopeToDistance
from myalignment.grading.footprint import Footprint, FootprintVertex
from myalignment.grading.grading import Grading
from myalignment.grading.site import Site, SiteBuilder, GradingGroupBuilder


def test_site_build():
    fp = Footprint(
        vertices=(FootprintVertex(0, 0, 100), FootprintVertex(100, 0, 100)),
    )
    criteria = SlopeToDistance(
        slope=Slope(value=2.0, format=SlopeFormat.RATIO),
        target_distance=20.0,
    )
    g = Grading(name="사면1", footprint=fp, criteria=criteria)

    group = (
        GradingGroupBuilder("그룹1")
        .add_grading(g)
        .build()
    )

    site = (
        SiteBuilder("부지1")
        .add_grading_group(group)
        .build()
    )

    assert site.name == "부지1"
    assert len(site.grading_groups) == 1
    assert site.total_daylight_length > 0