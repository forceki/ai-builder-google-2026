from dataclasses import replace
from datetime import date

import pytest
from litestar.exceptions import ClientException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.assessment import AssessmentController, ConditionsIn, FilesIn, SamplesIn, WaiverIn
from app.assessment.catalog import SLOTS, condition_hash, default_conditions
from app.assessment.dossier import SAMPLE_DOSSIER
from app.assessment.engine import (
    ACCEPTABLE,
    FAIL,
    INCOMPLETE,
    NOT_ACCEPTABLE,
    WARN,
    WITH_NOTES,
    assess,
    carbon_equivalent,
)
from app.assessment.sorting import sort_file
from app.db import Base, make_sessionmaker
from app.models import Project, User

TODAY = date(2026, 10, 18)
PLAN = {"mtc", "wps", "wpq", "drawing"}
SAMPLES = {s.id: list(s.sample) for s in SLOTS}


def run(present=PLAN, dossier=SAMPLE_DOSSIER, waivers=None, **cond):
    files = {slot: SAMPLES[slot] for slot in present}
    return assess({**default_conditions(), **cond}, files, dossier, TODAY, waivers)


def rules(r):
    return {(f.rule_id, f.item) for f in r.findings}


def section(r, sid):
    return next(s for s in r.sections if s.id == sid)


def without_w22(d=SAMPLE_DOSSIER):
    return replace(d, joints=[j for j in d.joints if j.id != "W-22"])


def test_sample_plan_fails_x06_on_overhead_fillet():
    r = run()
    assert r.mode == "PLAN" and r.verdict == NOT_ACCEPTABLE
    [f] = r.findings
    assert (f.id, f.rule_id, f.severity, f.item) == ("F-0001", "X-06", FAIL, "W-22")
    assert "overhead fillet" in f.statement
    assert f.clause == "ASME IX Table QW-461.9, 2023 edition"
    assert f.documents == ["WPQ-204.pdf", "HBK-PV-110_RevB_WeldMap.pdf"]
    assert "requalify welder 204" in f.fix


def test_plan_without_failures_is_acceptable_with_as_built_still_open():
    r = run(dossier=without_w22())
    assert r.verdict == ACCEPTABLE
    assert "as-built check is still open" in r.verdict_note
    assert r.criteria[-1]["status"] == "OPEN (PLAN)"


def test_warn_only_gives_acceptable_with_notes():
    hot = [replace(m, chemistry={**m.chemistry, "Mn": 1.6}) if m.heat == "4A7721" else m for m in SAMPLE_DOSSIER.materials]
    r = run(dossier=replace(without_w22(), materials=hot))
    assert ("S-MTC-02", "4A7721") in rules(r)
    assert r.findings[0].severity == WARN and r.verdict == WITH_NOTES


def test_waived_fail_gives_acceptable_with_notes():
    waiver = {"X-06:W-22": {"by": "QE", "reason": "Welder requalified in 4F, cert to follow", "at": "2026-10-18"}}
    r = run(waivers=waiver)
    assert r.verdict == WITH_NOTES
    assert r.findings[0].status == "waived" and r.counts == {"fail": 0, "warn": 0, "info": 0, "waived": 1}


def test_missing_document_makes_the_verdict_incomplete():
    r = run(present={"mtc", "wpq", "drawing"}, dossier=without_w22())
    assert r.verdict == INCOMPLETE
    assert section(r, "wps").rows is None and section(r, "wpq").rows is None


def test_production_without_wpq_is_a_high_alert_and_deemed_rejected():
    r = run(present={"mtc", "wps", "drawing"}, dossier=without_w22())  # production is the default purpose
    assert r.verdict == NOT_ACCEPTABLE and r.alerts
    f = next(f for f in r.findings if f.rule_id == "S-WPQ-00")
    assert f.severity == FAIL and f.statement.startswith("HIGH ALERT")


def test_investigation_does_not_need_wpq_and_weighs_welders_as_causes():
    r = run(present={"mtc", "wps", "drawing"}, dossier=without_w22(), purpose="investigation")
    assert r.verdict == ACCEPTABLE and not r.alerts  # nothing else is wrong; a missing WPQ is only recorded
    assert section(r, "wpq").status == "N/A"
    assert next(f for f in r.findings if f.rule_id == "S-WPQ-00").severity == "INFO"
    # with the WPQs, the welder not qualified overhead (W-22) is a warning, not the decision
    r = run(purpose="investigation")
    assert {f.severity for f in r.findings if f.rule_id == "X-06"} == {WARN}


def test_mill_certificate_is_optional_and_only_warns():
    r = run(present={"wps", "wpq", "drawing"}, dossier=without_w22())
    assert r.verdict == WITH_NOTES
    assert [(f.rule_id, f.severity) for f in r.findings] == [("S-MTC-06", WARN)]
    assert section(r, "mat").status == "N/A" and section(r, "pwht").rows is not None
    r = run(present={"wps", "wpq", "drawing", "asbuilt"}, dossier=without_w22())
    assert not any(f.rule_id == "X-14" for f in r.findings)


def no_records(d=SAMPLE_DOSSIER):
    return replace(d, as_built={}, pwht_charts=[], nde_reports=[], thickness=[], hydrotest=None)


def test_final_set_assesses_missing_evidence_instead_of_waiting():
    # not ticked: a plan review; the as-built evidence isn't asked for yet
    r = run(present={"wps", "wpq", "drawing"}, dossier=no_records())
    assert r.mode == "PLAN" and not {"X-15", "X-20", "S-DOC-01"} & {f.rule_id for f in r.findings}
    # ticked: release record. PWHT is required (40 mm, P-No.1 assumed without a certificate) and was never recorded.
    r = run(present={"wps", "wpq", "drawing"}, dossier=no_records(), complete_set=True)
    assert r.mode == "AS-BUILT" and r.verdict == NOT_ACCEPTABLE
    sev = {(f.rule_id, f.item): f.severity for f in r.findings}
    assert sev[("S-MTC-06", "Mill certificates")] == WARN  # a missing certificate is a note
    assert sev[("X-15", "W-11 (as-built)")] == FAIL and sev[("X-20", "Hydrotest")] == FAIL
    assert sev[("S-DOC-01", "As-built document")] == FAIL
    assert not any(f.rule_id == "X-13" for f in r.findings)  # no weld log at all: one finding, not one per joint


def test_final_set_ranks_missing_documents_by_risk():
    r = run(present={"mtc", "wps"}, dossier=no_records(), complete_set=True)
    assert {f.item for f in r.findings if f.rule_id in ("S-DOC-01", "S-WPQ-00") and f.severity == FAIL} == {
        "WPQ", "Welding drawing", "As-built document"}
    assert r.verdict == NOT_ACCEPTABLE and all(c["status"] != "PENDING" for c in r.criteria)
    # impact testing selected: the certificate holds the evidence, so its absence blocks release
    r = run(present={"wps", "wpq", "drawing"}, dossier=no_records(), complete_set=True, supplementary=["IMPACT"])
    assert next(f for f in r.findings if f.rule_id == "S-MTC-06").severity == FAIL


def test_investigation_lists_missing_records_as_gaps_and_fails_only_breaches():
    r = run(dossier=no_records(without_w22()), purpose="investigation", complete_set=True)
    gaps = [f for f in r.findings if f.kind == "gap"]
    assert gaps and all(f.severity in (WARN, "INFO") for f in gaps)  # no RT report, no PWHT record, no hydrotest
    assert r.verdict == WITH_NOTES and "evidence gap" in r.verdict_note
    # a record that shows a breach is still a candidate cause
    chart = replace(SAMPLE_DOSSIER.pwht_charts[0], hold_min=20)
    r = run(dossier=replace(no_records(without_w22()), pwht_charts=[chart]), purpose="investigation", complete_set=True)
    assert r.verdict == NOT_ACCEPTABLE and any(f.rule_id == "X-15" and f.kind == "breach" for f in r.findings)
    # production: the same gaps block the release
    assert run(dossier=no_records(without_w22()), complete_set=True).verdict == NOT_ACCEPTABLE


def test_joint_without_wps_names_the_submitted_wps_that_could_cover_it():
    joints = [replace(j, wps=None) if j.id == "W-11" else j for j in without_w22().joints]
    r = run(dossier=replace(SAMPLE_DOSSIER, joints=joints))
    f = next(f for f in r.findings if f.rule_id == "S-WPS-01" and f.item == "W-11")
    assert "assigns no WPS" in f.statement and "WPS-07" in f.statement and "WPS-09" not in f.statement  # 40 mm > 20


def test_joint_needing_pwht_without_a_wps_does_not_crash_the_run():
    # the real-document case: the drawing asks for PWHT but assigns no WPS, and this is the final set
    joints = [replace(j, wps=None, pwht_required=True) for j in without_w22().joints]
    r = run(dossier=replace(no_records(), joints=joints), complete_set=True)
    assert r.verdict == NOT_ACCEPTABLE
    assert not any(f.rule_id == "X-05" for f in r.findings)  # the missing WPS is S-WPS-01, not a PWHT finding
    assert any(f.rule_id == "S-WPS-01" for f in r.findings)


def test_unstated_pqr_hardness_is_a_gap_in_an_investigation():
    procs = {k: replace(p, hardness_hv10=None) for k, p in SAMPLE_DOSSIER.procedures.items()}
    r = run(dossier=replace(without_w22(), procedures=procs), supplementary=["MR0103"], purpose="investigation")
    f = next(f for f in r.findings if f.rule_id == "X-10" and f.item == "NACE MR0103")
    assert f.kind == "gap" and f.severity == WARN
    # a recorded hardness above the limit is a breach, and a candidate cause
    procs = {k: replace(p, hardness_hv10=260) for k, p in SAMPLE_DOSSIER.procedures.items()}
    r = run(dossier=replace(without_w22(), procedures=procs), supplementary=["MR0103"], purpose="investigation")
    assert any(f.rule_id == "X-10" and f.kind == "breach" and f.severity == FAIL for f in r.findings)


def test_joints_are_read_from_every_drawing():
    from app.assessment.adapter import ExtractedDoc, build_dossier

    ga = {"drawing_no": "GA-1", "revision": "1", "design_pressure_mpa": 1.6, "wall_thickness_mm": 22,
          "joints": [{"joint_id": "C#1", "description": "Shell to head", "wps": None, "page": 1, "confidence": "high"}]}
    detail = {"drawing_no": "DT-1", "revision": "1",
              "joints": [{"joint_id": "C#1", "wps": "WPS-150", "welder": "W12", "page": 1, "confidence": "high"},
                         {"joint_id": "N#1", "description": "Nozzle", "wps": "WPS-138", "page": 1, "confidence": "high"}]}
    d = build_dossier([ExtractedDoc("drawing", "ga.pdf", ga), ExtractedDoc("drawing", "detail.pdf", detail)])
    by = {j.id: j for j in d.joints}
    assert by["C#1"].wps == "WPS-150" and by["C#1"].desc == "Shell to head" and by["C#1"].thickness_mm == 22
    assert by["N#1"].wps == "WPS-138" and d.drawing_no == "GA-1"


def test_as_built_rechecks_the_actual_welder_on_the_weld_date():
    r = run(present=PLAN | {"asbuilt"})
    assert r.mode == "AS-BUILT"
    w14 = next(f for f in r.findings if f.item == "W-14 (as-built)")
    assert w14.rule_id == "X-13"
    assert "was not qualified on 12 Oct 2026 when W-14 was welded" in w14.statement
    assert ("X-13", "W-22 (as-built)") not in rules(r)  # same welder as planned: already X-06


ALL = PLAN | {"asbuilt"}


def test_as_built_sample_findings():
    r = run(present=ALL)
    assert rules(r) == {("X-16", "W-12"), ("X-13", "W-14 (as-built)"), ("X-06", "W-22"), ("X-14", "W-22 heat 3C0961")}
    assert "RT 100% required by the code, 0% performed" in next(f for f in r.findings if f.rule_id == "X-16").statement
    assert section(r, "asb_pwht").status == "PASS" and section(r, "asb_test").status == "PASS"


def test_pwht_chart_checked_against_governing_and_wps_band():
    short = replace(SAMPLE_DOSSIER.pwht_charts[0], hold_min=60, soak_c=600, heat_rate_c_per_h=200)
    r = run(present=ALL, dossier=replace(SAMPLE_DOSSIER, pwht_charts=[short]))
    texts = [f.statement for f in r.findings if f.rule_id == "X-15"]
    assert any("605–635 °C" in t for t in texts)  # WPS-07 band is tighter than the 595 °C code minimum
    assert any("96 min required for 40 mm" in t for t in texts)
    assert any("limits for 40 mm are 139 and 174" in t for t in texts)


def test_joint_needing_pwht_missing_from_every_load():
    r = run(present=ALL, dossier=replace(SAMPLE_DOSSIER, pwht_charts=[]))
    assert {("X-15", "W-11 (as-built)"), ("X-15", "W-12 (as-built)"), ("X-15", "W-14 (as-built)")} <= rules(r)


def test_nde_rejected_or_unsigned_report_fails():
    reports = [replace(n, result="REJECT") if n.report_no == "RT-019" else replace(n, level=None) if n.report_no == "VT-031"
               else n for n in SAMPLE_DOSSIER.nde_reports]
    r = run(present=ALL, dossier=replace(SAMPLE_DOSSIER, nde_reports=reports))
    texts = [f.statement for f in r.findings if f.rule_id == "X-16"]
    assert any("RT-019 (RT) rejected" in t for t in texts) and any("VT-031 not signed" in t for t in texts)


def test_hydrotest_and_thickness():
    low = replace(SAMPLE_DOSSIER.hydrotest, pressure_mpa=1.9, witness=None)
    thin = [replace(SAMPLE_DOSSIER.thickness[0], measured_mm=35.0), SAMPLE_DOSSIER.thickness[1]]
    r = run(present=ALL, dossier=replace(SAMPLE_DOSSIER, hydrotest=low, thickness=thin))
    sev = {(f.rule_id, f.severity) for f in r.findings if f.rule_id in ("X-19", "X-20")}
    assert sev == {("X-19", FAIL), ("X-20", FAIL), ("X-20", WARN)}  # 1.9 < 1.3 × 1.6 MPa; no witness is a WARN


def test_weld_in_log_but_not_on_weld_map():
    log = {**SAMPLE_DOSSIER.as_built, "W-30": replace(SAMPLE_DOSSIER.as_built["W-11"], sources=("Weld_log.xlsx",))}
    r = run(present=ALL, dossier=replace(SAMPLE_DOSSIER, as_built=log))
    f = next(f for f in r.findings if f.item == "W-30 (as-built)")
    assert f.rule_id == "X-13" and f.documents[0] == "Weld_log.xlsx"


def test_wps_used_differs_from_plan_without_deviation():
    log = {**SAMPLE_DOSSIER.as_built, "W-11": replace(SAMPLE_DOSSIER.as_built["W-11"], wps="WPS-09")}
    r = run(present=ALL, dossier=replace(SAMPLE_DOSSIER, as_built=log))
    assert any(f.rule_id == "X-13" and "welded with WPS-09" in f.statement for f in r.findings)
    log["W-11"] = replace(log["W-11"], deviation="NCR-014")
    r = run(present=ALL, dossier=replace(SAMPLE_DOSSIER, as_built=log))
    assert not any("welded with WPS-09" in f.statement for f in r.findings)


def test_pwht_required_over_38_mm_under_asme_viii():
    w11 = next(row for row in section(run(), "pwht").rows if row[0].v == "W-11")
    assert w11[5].v == "REQUIRED" and w11[-1].v == "PASS"  # WPS-07 is qualified with PWHT


def test_pwht_required_but_wps_not_qualified_fails_x05():
    procs = {**SAMPLE_DOSSIER.procedures, "WPS-07": replace(SAMPLE_DOSSIER.procedures["WPS-07"], pwht=None)}
    r = run(dossier=replace(SAMPLE_DOSSIER, procedures=procs))
    assert {("X-05", "W-11"), ("X-05", "W-12"), ("X-05", "W-14")} <= rules(r)
    assert any("QW-407.1" in f.clause for f in r.findings)


def test_asme_viii_32_to_38_mm_exempt_only_with_preheat():
    thin = [replace(j, thickness_mm=35) if j.wps == "WPS-07" else j for j in without_w22().joints]
    r = run(dossier=replace(SAMPLE_DOSSIER, joints=thin))
    assert all(row[5].v == "NOT REQUIRED" for row in section(r, "pwht").rows if row[0].v in ("W-11", "W-14"))
    procs = {**SAMPLE_DOSSIER.procedures, "WPS-07": replace(SAMPLE_DOSSIER.procedures["WPS-07"], preheat_c=50)}
    r = run(dossier=replace(SAMPLE_DOSSIER, joints=thin, procedures=procs))
    assert all(row[5].v == "REQUIRED" for row in section(r, "pwht").rows if row[0].v in ("W-11", "W-14"))


def test_b31_3_exempts_p1_over_25_mm_with_preheat():
    r = run(profile="plant-refinery", governing="ASME B31.3", dossier=without_w22())
    w11 = next(row for row in section(r, "pwht").rows if row[0].v == "W-11")
    assert w11[3].v == "P-No.1, over 25 mm, exempt with 95 °C preheat" and w11[5].v == "NOT REQUIRED"
    procs = {**SAMPLE_DOSSIER.procedures, "WPS-07": replace(SAMPLE_DOSSIER.procedures["WPS-07"], preheat_c=50, pwht=None)}
    r = run(profile="plant-refinery", governing="ASME B31.3", dossier=replace(without_w22(), procedures=procs))
    assert ("X-05", "W-11") in rules(r)


def test_asme_i_follows_ucs_56_bands():
    r = run(profile="plant-power", governing="ASME I", dossier=without_w22())
    w11 = next(row for row in section(r, "pwht").rows if row[0].v == "W-11")
    assert w11[3].v == "P-No.1, 40 mm > 38 mm" and w11[4].v == "PW-39, Table PW-39-1"


def test_plate_tested_welder_is_not_qualified_on_small_pipe():
    joints = [replace(j, od_mm=219.1) if j.id == "W-17" else j for j in without_w22().joints]
    r = run(dossier=replace(SAMPLE_DOSSIER, joints=joints))
    f = next(f for f in r.findings if f.item == "W-17")
    assert f.rule_id == "X-06" and "below the 610 mm" in f.statement and "plate test" in f.statement


def test_ship_codes_do_not_mandate_pwht():
    r = run(profile="ship-commercial", governing="IACS Rec. 47 + class", dossier=without_w22())
    assert all(row[5].v == "NOT REQUIRED" for row in section(r, "pwht").rows)


def test_non_asme_clauses_carry_no_asme_edition():
    r = run(profile="ship-commercial", governing="IACS Rec. 47 + class")
    assert r.findings and all("edition" not in f.clause for f in r.findings)


def test_sour_service_hardness_x10():
    assert carbon_equivalent(SAMPLE_DOSSIER.materials[0].chemistry) == pytest.approx(0.373, abs=0.001)
    r = run(supplementary=["MR0175"], dossier=without_w22())
    assert r.verdict == ACCEPTABLE  # WPS-07 208 and WPS-09 236 HV10 are under 250
    r = run(supplementary=["MR0103"], dossier=without_w22())
    assert ("X-10", "NACE MR0103") in rules(r)  # WPS-09 236 HV10 is over 210


def test_impact_tested_needs_test_temperature_at_or_below_mdmt_x09():
    r = run(supplementary=["IMPACT"], mdmt_c=-20, dossier=without_w22())
    assert ("X-09", "5B2210") in rules(r)  # no impact test on the certificate
    assert ("X-09", "4A7721") not in rules(r)  # tested at -29 °C


def test_lethal_service_requires_pwht():
    r = run(supplementary=["LETHAL"], dossier=without_w22())
    assert all(row[3].v == "Lethal service" for row in section(r, "pwht").rows if row[0].v in ("W-11", "W-12", "W-14"))


def test_wps_thickness_range_x04():
    joints = [replace(j, thickness_mm=60) if j.id == "W-11" else j for j in without_w22().joints]
    r = run(dossier=replace(SAMPLE_DOSSIER, joints=joints))
    assert ("X-04", "W-11") in rules(r)


def test_welder_continuity_lapses_after_six_months_x07():
    r = assess(default_conditions(), {s: SAMPLES[s] for s in PLAN}, without_w22(), date(2027, 6, 1))
    assert any(f.rule_id == "X-07" for f in r.findings)


def test_basis_names_each_standard_once():
    assert run().basis.split(" · ")[:1] == ["Production release"]
    assert run().basis.split(" · ")[3] == "ASME VIII-1 with ASME IX and ASME V (2023)"
    r = run(profile="mfg-structural", governing="AWS D1.1", dossier=without_w22())
    assert r.basis.split(" · ")[3] == "AWS D1.1 (2023)"


def test_conditions_validated():
    with pytest.raises(ValidationError):
        ConditionsIn(profile="plant-vessel", governing="ASME VIII-1", supplementary=["EXC3"])
    with pytest.raises(ValidationError):
        ConditionsIn(profile="plant-vessel", governing="AWS D1.1")
    with pytest.raises(ValidationError):
        ConditionsIn(profile="plant-vessel", governing="ASME VIII-1", edition="1998")


def test_condition_hash_ignores_submission_mode_and_order():
    c = default_conditions()
    assert condition_hash(c) == condition_hash({**c, "upload_mode": "single", "confirmed": True})
    assert condition_hash({**c, "supplementary": ["A", "B"]}) == condition_hash({**c, "supplementary": ["B", "A"]})
    assert condition_hash(c) != condition_hash({**c, "mdmt_c": -30})


@pytest.mark.parametrize(("name", "slot"), [
    ("MTC_4A7721.pdf", "mtc"), ("WPS-07_PQR-07.pdf", "wps"), ("WPQ-118.pdf", "wpq"), ("WQ-310.pdf", "wpq"),
    ("HBK-PV-110_RevB_WeldMap.pdf", "drawing"), ("ASB_PS-3_RevA.pdf", "asbuilt"),
    ("MTC_9Z0001_EN10204-2.1.pdf", None), ("WPS-11_draft.docx", None), ("WPS-11_draft.pdf", None),
    ("IMG_4471.jpg", None), ("Invoice_PO-2231.pdf", None),
])
def test_sort_by_file_name(name, slot):
    assert sort_file(name).slot == slot


class FakeQueue:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, tuple]] = []

    async def enqueue(self, job: str, *args: str, delay: int = 0) -> None:
        self.jobs.append((job, args))


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with make_sessionmaker(engine)() as s:
        yield s
    await engine.dispose()


async def test_api_flow(session):
    user = User(email="qe@a.com", name="QE", role="Quality engineer", password_hash="-")
    session.add(user)
    await session.flush()
    session.add(Project(no="PRJ-1", name="Skid", owner_id=user.id))
    await session.flush()
    api = AssessmentController(owner=None)
    call = lambda h, **kw: h.fn(api, db=session, user=user, project_no="PRJ-1", **kw)

    out = await call(AssessmentController.get_assessment)
    assert out.state == "draft" and out.missing == [] and not out.ready  # every slot is optional, but one is needed
    with pytest.raises(ClientException):
        await call(AssessmentController.run)  # no document yet

    out = await call(AssessmentController.add_files, queue=FakeQueue(), data=FilesIn(names=["MTC_4A7721.pdf", "IMG_4471.jpg"]))
    assert [(f.name, f.slot) for f in out.files] == [("MTC_4A7721.pdf", "mtc"), ("IMG_4471.jpg", None)]
    out = await call(AssessmentController.load_samples, data=SamplesIn())
    assert out.unresolved == ["IMG_4471.jpg"] and not out.ready
    with pytest.raises(ClientException):
        await call(AssessmentController.run)  # a rejected file is still unresolved

    await call(AssessmentController.remove_files, name="IMG_4471.jpg", slot=None)
    out = await call(AssessmentController.remove_files, slot="asbuilt", name=None)
    assert out.state == "ready" and out.mode == "PLAN"
    with pytest.raises(ClientException):
        await call(AssessmentController.get_report)  # no run yet

    out = await call(AssessmentController.run)
    assert out.state == "complete" and out.run.number == 1 and out.run.conclusion == NOT_ACCEPTABLE
    [f] = out.run.result["findings"]
    assert f["key"] == "X-06:W-22"

    with pytest.raises(ClientException):
        await call(AssessmentController.set_waiver, key="X-06:W-22", data=WaiverIn(status="waived"))  # no reason
    out = await call(AssessmentController.set_waiver, key="X-06:W-22",
                     data=WaiverIn(status="waived", reason="Requalified in 4F"))
    assert out.run.conclusion == WITH_NOTES and out.run.result["findings"][0]["waiver"]["by"] == "QE, Quality engineer"

    rep = await call(AssessmentController.get_report)
    assert rep["report_no"] == "HBK-RR-001" and rep["verdict"] == WITH_NOTES and not rep["stale"]
    assert rep["references"][:3] == ["ASME VIII-1", "ASME IX", "ASME V"]
    assert rep["counts"] == {"nc": 0, "obs": 0, "waived": 1} and rep["waived"][0]["items"] == ["W-22"]
    assert out.condition_hash in rep["footer"]

    out = await call(AssessmentController.set_conditions,
                     data=ConditionsIn(profile="plant-vessel", governing="ASME VIII-1", mdmt_c=-30))
    assert out.state == "stale" and out.stale_reasons == ["Conditions changed"]

    out = await call(AssessmentController.run)  # the waiver follows the finding into the re-run
    assert out.state == "complete" and out.run.number == 2 and out.run.conclusion == WITH_NOTES


async def test_upload_reads_documents_and_runs_on_them(session, monkeypatch):
    from litestar.datastructures import UploadFile

    from app import storage
    from app.api.assessment import DocumentUpload
    from app.models import Document
    from app.models.document import DocStatus

    async def put(*_a, **_k):
        return None

    monkeypatch.setattr(storage, "put", put)
    user = User(email="qe@b.com", name="QE", role="Quality engineer", password_hash="-")
    session.add(user)
    await session.flush()
    session.add(Project(no="PRJ-2", name="Spool", owner_id=user.id))
    await session.flush()
    api, queue = AssessmentController(owner=None), FakeQueue()
    call = lambda h, **kw: h.fn(api, db=session, user=user, project_no="PRJ-2", **kw)

    await call(AssessmentController.load_samples, data=SamplesIn())
    out = await call(AssessmentController.upload_document, queue=queue,
                     data=DocumentUpload(file=UploadFile("application/pdf", "Notes.docx", file_data=b"x")))
    assert [(f.name, f.slot, f.reason[:6]) for f in out.files] == [("Notes.docx", None, "FMT-01")]  # samples gave way

    out = await call(AssessmentController.upload_document, queue=queue,
                     data=DocumentUpload(file=UploadFile("image/png", "MTC_1.png", file_data=b"png")))
    assert out.reading == ["MTC_1.png"] and not out.ready and queue.jobs[-1][0] == "assess_document"

    doc = await session.get(Document, __import__("uuid").UUID(out.files[-1].document_id))
    doc.status, doc.slot, doc.slot_confidence, doc.slot_reason = DocStatus.EXTRACTED, "mtc", 0.7, "Probably a mill certificate"
    doc.extraction = {"heats": [{"heat_no": "H-48213", "spec_grade": "ASTM A106 Gr.B", "cert_type": "EN 10204 3.1",
                                 "chemistry": [], "signed": True, "page": 1, "confidence": "high"}]}
    await session.flush()
    out = await call(AssessmentController.get_assessment)
    mtc = next(f for f in out.files if f.name == "MTC_1.png")
    assert mtc.slot == "mtc" and mtc.needs_confirm and not out.sample_data
    assert next(s for s in out.slots if s.id == "mtc").facts == ["48213 · ASTM A106 Gr.B · ? · P-No.1"]

    out = await call(AssessmentController.add_files, queue=queue, data=FilesIn(names=["MTC_1.png"], slot="mtc"))
    assert not next(f for f in out.files if f.name == "MTC_1.png").needs_confirm  # confirmed without re-reading
    out = await call(AssessmentController.add_files, queue=queue, data=FilesIn(names=["MTC_1.png"], slot="wps"))
    assert out.reading == ["MTC_1.png"]  # a different slot reads it again with that schema
    out = await call(AssessmentController.remove_files, name="MTC_1.png", slot=None)
    assert out.files[0].name == "Notes.docx" and await session.get(Document, doc.id) is None


def test_intake_rejects_2_2_certificates_and_drawings_without_joints():
    from app.assessment.extraction import DrawingDoc, MtcDoc
    from app.assessment.intake import intake_rejection

    mtc = MtcDoc.model_validate({"heats": [{"heat_no": "9Z0001", "cert_type": "EN 10204 2.2", "certificate_no": None,
        "spec_grade": None, "product": None, "thickness_mm": None, "condition": None, "yield_mpa": None,
        "tensile_mpa": None, "tensile_min_mpa": None, "impact_temp_c": None, "impact_avg_j": None, "hardness": None,
        "signed": True, "page": 1, "confidence": "high"}]})
    assert intake_rejection("mtc", mtc).startswith("MTC-01")
    drawing = DrawingDoc.model_validate({"drawing_no": "X", "revision": "A", "code": None, "design_pressure_mpa": None,
        "design_temp_c": None, "wall_thickness_mm": None, "pipe_od_mm": None, "general_nde": None, "joints": [],
        "page": 1, "confidence": "high"})
    assert intake_rejection("drawing", drawing).startswith("DRW-01")


def test_drawing_pipe_od_fills_joints_only_when_the_weld_table_lists_none():
    from app.assessment.adapter import ExtractedDoc, build_dossier

    def drawing(*ods):
        joints = [{"joint_id": f"W-{i}", "od_mm": od, "page": 1, "confidence": "high"} for i, od in enumerate(ods, 1)]
        return [ExtractedDoc("drawing", "map.pdf", {"pipe_od_mm": 168.3, "joints": joints})]

    # spool: one pipe size for every joint, given once on the drawing
    assert [j.od_mm for j in build_dossier(drawing(None, None)).joints] == [168.3, 168.3]
    # vessel: the table gives the nozzle's OD; the skid fillet with none is not on pipe
    assert [j.od_mm for j in build_dossier(drawing(2440, 168.3, None)).joints] == [2440, 168.3, None]


def test_snapshot_crops_the_box_and_keeps_the_row_label():
    import io

    from PIL import Image

    from app.assessment.snapshot import NoPreview, snapshot

    page = Image.new("RGB", (1000, 1000), "white")
    buf = io.BytesIO()
    page.save(buf, format="PNG")
    full = Image.open(io.BytesIO(snapshot("scan.png", buf.getvalue(), 1, None)))
    assert full.size == (1000, 1000)
    row = Image.open(io.BytesIO(snapshot("scan.png", buf.getvalue(), 1, (400, 400, 420, 800))))
    # one row: from the page margin (5 %) to the box + 12 %, 4 % above and below
    assert row.size == (870, 100)
    with pytest.raises(NoPreview):
        snapshot("log.xlsx", b"", 1, None)


async def test_snapshot_endpoint_only_serves_this_assessments_documents(session):
    from litestar.exceptions import NotFoundException

    user = User(email="qe@c.com", name="QE", role="Quality engineer", password_hash="-")
    session.add(user)
    await session.flush()
    session.add(Project(no="PRJ-3", name="Other", owner_id=user.id))
    await session.flush()
    api = AssessmentController(owner=None)
    with pytest.raises(NotFoundException):
        await AssessmentController.get_snapshot.fn(api, db=session, user=user, project_no="PRJ-3",
                                                   file="MTC_4A7721.pdf", page=1, box=None)


def test_report_groups_findings_pareto_style():
    from datetime import datetime

    from app.assessment.report import build_report

    r = run(present=ALL)
    findings = r.as_dict()["findings"]
    extra = {**findings[0], "item": "W-12", "id": "F-0099", "key": "X-16:W-12b"}  # same problem on another joint
    result = {**r.as_dict(), "findings": [*findings, extra]}
    rep = build_report(project_no="PRJ-7", project_name="Skid", prepared_by="QE", conditions=default_conditions(),
                       documents={"mtc": ["a.pdf"]}, result=result, run_number=1, run_at=datetime(2026, 10, 18, 9),
                       condition_hash="abc", rule_pack="RS-3.1")
    assert rep["verdict"] == NOT_ACCEPTABLE and rep["conclusion"].startswith("Not acceptable.")
    nde = next(i for i in rep["issues"] if i["rule_id"] == "X-16")
    assert nde["area"] == "NDE" and not nde["finding"].startswith("W-12:")
    assert rep["areas"][0]["nc"] >= rep["areas"][-1]["nc"]  # Pareto order
    assert [i["no"] for i in rep["issues"]] == list(range(1, len(rep["issues"]) + 1))
