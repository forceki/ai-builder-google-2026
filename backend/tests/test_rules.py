from app.pipeline.mapper import build_graph
from app.rules import dossier_completeness, material_traceability, ndt_evidence, run_all, weld_linkage
from app.rules.types import Status
from app.schemas.production import ProductionRecords, PwhtEntry
from app.models.document import DocType
from app.pipeline.mapper import Extracted
from app.schemas.ndt import NdtReports
from app.specimen import ndt, specimen


def keyed(findings):
    return {(f.rule, f.item, f.status) for f in findings}


def test_material_traceability_rejects_heat_conflict():
    findings = material_traceability.run(build_graph(specimen()))
    assert keyed(findings) == {("R-MAT-02", "P-103", Status.REJECT)}
    assert {s.document for s in findings[0].sources} == {"Traveler_PS-3.pdf", "FAB-REC_031.pdf"}


def test_material_traceability_holds_missing_certificate():
    docs = specimen()
    docs[0].data.certificates = docs[0].data.certificates[1:]  # drop the 4A7721 certificate
    findings = material_traceability.run(build_graph(docs))
    assert ("R-MAT-01", "P-101", Status.HOLD) in keyed(findings)


def test_weld_linkage_passes_specimen():
    assert weld_linkage.run(build_graph(specimen())) == []


def test_weld_linkage_flags_unqualified_welder_and_unknown_wps():
    docs = specimen()
    welds = docs[3].data
    welds.qualifications = welds.qualifications[:1]  # only welder 118 qualified
    welds.welds[0].wps = "WPS-99"
    findings = keyed(weld_linkage.run(build_graph(docs)))
    assert ("R-WLD-01", "W-11", Status.HOLD) in findings
    assert ("R-WLD-02", "W-17", Status.HOLD) in findings
    assert ("R-WLD-02", "W-22", Status.HOLD) in findings


def test_ndt_evidence_holds_weld_without_report():
    assert keyed(ndt_evidence.run(build_graph(specimen()))) == {("R-NDT-03", "W-14", Status.HOLD)}


def test_ndt_evidence_rejects_rejected_report():
    docs = specimen() + [Extracted("NDT_late.pdf", DocType.NDT, NdtReports(reports=[
        ndt("UT-0340", "UT", ["W-14"], result="reject"),
    ]))]
    assert keyed(ndt_evidence.run(build_graph(docs))) == {("R-NDT-04", "W-14", Status.REJECT)}


def test_dossier_completeness_flags_pwht_and_signature():
    findings = keyed(dossier_completeness.run(build_graph(specimen())))
    assert findings == {("R-DOS-02", "W-22", Status.HOLD), ("R-DOS-04", "RT-0019", Status.HOLD)}


def test_evidence_clears_findings():
    docs = specimen() + [
        Extracted("NDT_UT-0340.pdf", DocType.NDT, NdtReports(reports=[ndt("UT-0340", "UT", ["W-14"])])),
        Extracted("NDT_RT-0019_signed.pdf", DocType.NDT, NdtReports(reports=[ndt("RT-0019", "RT", ["W-12"])])),
        Extracted("PWHT_Chart_W-22.pdf", DocType.PRODUCTION, ProductionRecords(
            parts=[], pwht_records=[PwhtEntry(page=1, confidence="high", weld_id="W-22", temperature_c=620)],
        )),
    ]
    results = {r.check: r.status for r in run_all(build_graph(docs))}
    assert results == {"C-01": Status.REJECT, "C-02": Status.PASS, "C-03": Status.PASS, "C-04": Status.PASS}


def test_run_all_matches_specimen_report():
    results = {r.check: (r.status, len(r.findings)) for r in run_all(build_graph(specimen()))}
    assert results == {
        "C-01": (Status.REJECT, 1),
        "C-02": (Status.PASS, 0),
        "C-03": (Status.HOLD, 1),
        "C-04": (Status.HOLD, 2),
    }
