import pytest

from app.pipeline import normalize as n


@pytest.mark.parametrize("raw,expected", [
    ("4A7721", "4A7721"), ("Heat 4a-7721", "4A7721"), ("HT NO: 3C 0954", "3C0954"), ("cast # 5B.2210", "5B2210"),
])
def test_heat_no(raw, expected):
    assert n.heat_no(raw) == expected


@pytest.mark.parametrize("raw,expected", [("W-14", "W-14"), ("w14", "W-14"), ("W 014", "W-14"), ("W_22", "W-22")])
def test_weld_id(raw, expected):
    assert n.weld_id(raw) == expected


def test_part_and_report_padding():
    assert n.part_no("p101") == "P-101"
    assert n.part_no("P-7") == "P-007"
    assert n.report_no("ut331") == "UT-0331"
    assert n.wps_id("WPS 7") == "WPS-07"


@pytest.mark.parametrize("raw,expected", [
    ("UT", "UT"), ("Ultrasonic", "UT"), ("phased array", "UT"), ("Radiography", "RT"), ("MPI", "MT"),
    ("dye penetrant", "PT"), ("Visual", "VT"),
])
def test_ndt_method(raw, expected):
    assert n.ndt_method(raw) == expected


def test_welder_id():
    assert n.welder_id("Welder ID 118") == "118"
