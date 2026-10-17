"""Build the traceability graph (heat -> part -> weld -> NDT) from extracted documents."""

from dataclasses import dataclass
from typing import Any

from app.models.document import DocType
from app.pipeline import normalize as n
from app.rules.types import Heat, HeatRef, NdtReport, Part, Procedure, Source, TraceGraph, Weld
from app.schemas import EXTRACTION_SCHEMAS
from app.schemas.inspection import InspectionRecords
from app.schemas.mtc import MaterialCertificates
from app.schemas.ndt import NdtReports
from app.schemas.production import ProductionRecords
from app.schemas.weld import WeldingRecords


@dataclass
class Extracted:
    filename: str
    doc_type: DocType
    data: Any  # an instance of EXTRACTION_SCHEMAS[doc_type]

    @classmethod
    def from_json(cls, filename: str, doc_type: DocType, data: dict) -> "Extracted":
        return cls(filename, doc_type, EXTRACTION_SCHEMAS[doc_type].model_validate(data))


def build_graph(docs: list[Extracted]) -> TraceGraph:
    g = TraceGraph()
    fitups: list[tuple[str, list[str]]] = []
    for doc in docs:
        src = lambda page, _f=doc.filename: Source(_f, page)  # noqa: E731
        match doc.data:
            case MaterialCertificates(certificates=certs):
                for c in certs:
                    h = n.heat_no(c.heat_no)
                    g.heats.setdefault(h, Heat(h, c.grade, src(c.page)))

            case ProductionRecords(parts=parts, pwht_records=pwht, fitups=fits):
                fitups += [(n.weld_id(f.weld_id), [n.part_no(p) for p in f.parts]) for f in fits]
                for p in parts:
                    no = n.part_no(p.part_no)
                    part = g.parts.setdefault(no, Part(no, p.description))
                    part.description = part.description or p.description
                    part.sources.append(src(p.page))
                    if p.heat_no:
                        ref = HeatRef(n.heat_no(p.heat_no), src(p.page))
                        if ref not in part.heat_refs:
                            part.heat_refs.append(ref)
                for r in pwht:
                    g.pwht_done.setdefault(n.weld_id(r.weld_id), src(r.page))

            case WeldingRecords(welds=welds, procedures=procs, qualifications=quals):
                for w in welds:
                    wid = n.weld_id(w.weld_id)
                    g.welds[wid] = Weld(
                        wid,
                        n.wps_id(w.wps) if w.wps else None,
                        n.welder_id(w.welder_id) if w.welder_id else None,
                        [n.part_no(p) for p in w.parts],
                        src(w.page),
                    )
                for p in procs:
                    pid = n.wps_id(p.wps_id)
                    g.procedures[pid] = Procedure(pid, p.pwht_required, src(p.page),
                                                  frozenset(n.weld_id(w) for w in p.pwht_welds))
                for q in quals:
                    g.qualified_welders.add(n.welder_id(q.welder_id))

            case NdtReports(reports=reports):
                for r in reports:
                    rid = n.report_no(r.report_no)
                    report = NdtReport(rid, n.ndt_method(r.method), [n.weld_id(w) for w in r.welds],
                                       r.result, r.signed, src(r.page))
                    # A register and the report itself may both list it; prefer the actual report.
                    if rid not in g.ndt_reports or not g.ndt_reports[rid].signed:
                        g.ndt_reports[rid] = report

            case InspectionRecords(ndt_requirements=reqs):
                for req in reqs:
                    methods = {n.ndt_method(m) for m in req.methods}
                    for w in req.welds:
                        key = "ALL" if w.strip().upper() == "ALL" else n.weld_id(w)
                        prev, _ = g.ndt_required.get(key, (set(), None))
                        g.ndt_required[key] = (prev | methods, src(req.page))

    for weld_id, part_nos in fitups:
        if weld := g.welds.get(weld_id):
            weld.parts += [p for p in part_nos if p not in weld.parts]
    return g


@dataclass
class MapNode:
    kind: str  # material | part | weld | ndt
    key: str
    label: str
    attributes: dict
    sources: list[Source]


@dataclass
class MapEdge:
    from_key: tuple[str, str]  # (kind, key)
    to_key: tuple[str, str]
    kind: str = "link"  # link | conflict


def to_map(g: TraceGraph) -> tuple[list[MapNode], list[MapEdge]]:
    """Nodes and edges for the workspace map, in column order heat -> part -> weld -> NDT."""
    nodes: list[MapNode] = []
    edges: list[MapEdge] = []

    for h in g.heats.values():
        nodes.append(MapNode("material", h.heat_no, f"HEAT {h.heat_no}", {"grade": h.grade}, [h.source]))
    for p in g.parts.values():
        nodes.append(MapNode("part", p.part_no, f"PART {p.part_no}",
                             {"description": p.description, "heat_nos": sorted(p.heat_nos)}, p.sources))
        conflict = len(p.heat_nos) > 1
        for h in sorted(p.heat_nos):
            if h in g.heats:
                edges.append(MapEdge(("material", h), ("part", p.part_no), "conflict" if conflict else "link"))
    for w in g.welds.values():
        nodes.append(MapNode("weld", w.weld_id, f"WELD {w.weld_id}",
                             {"wps": w.wps, "welder": w.welder_id, "parts": w.parts}, [w.source]))
        edges += [MapEdge(("part", p), ("weld", w.weld_id)) for p in w.parts if p in g.parts]
    for r in g.ndt_reports.values():
        nodes.append(MapNode("ndt", r.report_no, r.report_no,
                             {"method": r.method, "welds": r.welds, "result": r.result, "signed": r.signed}, [r.source]))
        edges += [MapEdge(("weld", w), ("ndt", r.report_no)) for w in r.welds if w in g.welds]
    return nodes, edges
