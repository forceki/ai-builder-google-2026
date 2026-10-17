from app.pipeline.mapper import build_graph, to_map
from app.specimen import specimen


def test_graph_links_records_across_documents():
    g = build_graph(specimen())
    assert set(g.heats) == {"4A7721", "5B2210", "7D4410", "3C0954"}
    assert g.parts["P-103"].heat_nos == {"3C0954", "3C0945"}  # traveler vs fabrication record
    assert g.welds["W-14"].parts == ["P-101", "P-104"]
    assert g.ndt_reports["UT-0331"].method == "UT"
    assert g.procedures["WPS-09"].pwht_required


def test_map_marks_heat_conflict():
    nodes, edges = to_map(build_graph(specimen()))
    kinds = {(n.kind, n.key) for n in nodes}
    assert ("weld", "W-14") in kinds and ("ndt", "RT-0019") in kinds
    conflict = [e for e in edges if e.kind == "conflict"]
    assert [(e.from_key, e.to_key) for e in conflict] == [(("material", "3C0954"), ("part", "P-103"))]
    # W-14 has no NDT edge: no report references it.
    assert not [e for e in edges if e.from_key == ("weld", "W-14")]
