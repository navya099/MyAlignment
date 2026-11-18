# tests/quantity/test_report.py
from myalignment.quantity.report import QTOReport
from myalignment.quantity.material import Material, UnitType
from myalignment.quantity.takeoff import MaterialQuantity, TakeoffResult


def test_report_text():
    materials = (
        MaterialQuantity(
            material_name="아스팔트",
            unit_type=UnitType.VOLUME,
            total_quantity=100.0,
            total_cost=10_000_000,
        ),
        MaterialQuantity(
            material_name="콘크리트",
            unit_type=UnitType.VOLUME,
            total_quantity=50.0,
            total_cost=5_000_000,
        ),
    )
    result = TakeoffResult(material_quantities=materials)
    report = QTOReport(result=result)
    text = report.to_text()
    assert "아스팔트" in text
    assert "콘크리트" in text
    assert "15,000,000" in text


def test_report_dict():
    materials = (
        MaterialQuantity(
            material_name="아스팔트",
            unit_type=UnitType.VOLUME,
            total_quantity=100.0,
            total_cost=10_000_000,
        ),
    )
    result = TakeoffResult(material_quantities=materials)
    report = QTOReport(result=result)
    d = report.to_dict()
    assert d['total_cost'] == 10_000_000
    assert len(d['materials']) == 1