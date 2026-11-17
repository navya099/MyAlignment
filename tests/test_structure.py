# tests/structure/test_structure.py
import math
import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.structure.bridge import Bridge
from myalignment.structure.structurecollection import StructureCollection
from myalignment.structure.struturetype import StructureType
from myalignment.structure.tunnel import Tunnel


def test_bridge_create():
    b = Bridge.create("교량1", 100, 200, span_count=3, bridge_type="RC")
    assert b.name == "교량1"
    assert b.structure_type == StructureType.BRIDGE
    assert math.isclose(b.length, 100.0)
    assert b.span_count == 3
    assert b.bridge_type == "RC"


def test_tunnel_create():
    t = Tunnel.create("터널1", 500, 800, tunnel_type="NATM", diameter=10.0)
    assert t.structure_type == StructureType.TUNNEL
    assert math.isclose(t.length, 300.0)
    assert t.tunnel_type == "NATM"
    assert math.isclose(t.diameter, 10.0)


def test_invalid_station_range():
    with pytest.raises(ValueError):
        Bridge.create("잘못됨", 200, 100)   # end < start


def test_contains_station():
    b = Bridge.create("교량1", 100, 200)
    assert b.contains_station(100)    # 경계 포함
    assert b.contains_station(150)
    assert b.contains_station(200)    # 경계 포함
    assert not b.contains_station(99)
    assert not b.contains_station(201)


def test_overlaps_with():
    b1 = Bridge.create("B1", 100, 200)
    b2 = Bridge.create("B2", 150, 250)
    b3 = Bridge.create("B3", 300, 400)
    assert b1.overlaps_with(b2)
    assert not b1.overlaps_with(b3)


def test_overlap_length():
    b1 = Bridge.create("B1", 100, 200)
    b2 = Bridge.create("B2", 150, 250)
    assert math.isclose(b1.overlap_length(b2), 50.0)


def test_collection_get_by_type():
    b1 = Bridge.create("B1", 0, 100)
    b2 = Bridge.create("B2", 200, 300)
    t1 = Tunnel.create("T1", 400, 600)
    col = StructureCollection(structures=(b1, b2, t1))

    assert len(col.get_by_type(StructureType.BRIDGE)) == 2
    assert len(col.get_by_type(StructureType.TUNNEL)) == 1
    assert col.bridge_count == 2
    assert col.tunnel_count == 1


def test_collection_find_at_station():
    b = Bridge.create("B", 100, 200)
    t = Tunnel.create("T", 300, 500)
    col = StructureCollection(structures=(b, t))

    assert col.find_at_station(150) is b
    assert col.find_at_station(400) is t
    assert col.find_at_station(250) is None


def test_collection_structure_type_at():
    b = Bridge.create("B", 100, 200)
    col = StructureCollection(structures=(b,))

    assert col.structure_type_at(150) == StructureType.BRIDGE
    assert col.structure_type_at(250) is None   # 토공


def test_collection_sort_validation():
    b1 = Bridge.create("B1", 100, 200)
    b2 = Bridge.create("B2", 0, 100)   # 순서 뒤바뀜
    with pytest.raises(ValueError):
        StructureCollection(structures=(b1, b2))


def test_collection_add_returns_new():
    b1 = Bridge.create("B1", 0, 100)
    col = StructureCollection(structures=(b1,))
    b2 = Bridge.create("B2", 200, 300)
    col2 = col.add(b2)

    assert col is not col2
    assert len(col) == 1
    assert len(col2) == 2


def test_collection_total_length_by_type():
    b1 = Bridge.create("B1", 0, 100)
    b2 = Bridge.create("B2", 200, 350)
    t = Tunnel.create("T", 400, 700)
    col = StructureCollection(structures=(b1, b2, t))

    assert math.isclose(col.total_bridge_length, 250.0)
    assert math.isclose(col.total_tunnel_length, 300.0)


def test_alignment_bridge_count():
    a = (
        AlignmentBuilder()
        .with_pi_coords([(0, 0), (1000, 0)])
        .with_radii([None, None])
        .with_bridge("교량1", 100, 200)
        .with_bridge("교량2", 500, 600)
        .build()
    )
    assert a.bridge_count == 2
    assert a.tunnel_count == 0


def test_alignment_structure_type_at():
    a = (
        AlignmentBuilder()
        .with_pi_coords([(0, 0), (1000, 0)])
        .with_radii([None, None])
        .with_bridge("교량1", 100, 200)
        .with_tunnel("터널1", 500, 700)
        .build()
    )
    assert a.structure_type_at(150) == StructureType.BRIDGE
    assert a.structure_type_at(600) == StructureType.TUNNEL
    assert a.structure_type_at(300) is None   # 토공


def test_alignment_cost():
    a = (
        AlignmentBuilder()
        .with_pi_coords([(0, 0), (1000, 0)])
        .with_radii([None, None])
        .with_bridge("교량1", 100, 200)
        .build()
    )
    # 100m 교량 × 5,000,000원/m = 500,000,000
    assert a.cost > 0