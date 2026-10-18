"""Welding assessment rules (PRD: Conditions, Document Intake and Validation Engine, sections 5–8).

The welding drawing's joint table is the spine: every cross-document rule starts from a joint and pulls the MTC, WPS,
PQR, WPQ and as-built rows it references. Each failed check becomes a Finding with a stable rule ID, a severity and the
clause that produced it:

    FAIL  blocks release          WARN  needs a reviewer decision          INFO  recorded only

Conclusion (computed, never written by the model): any open FAIL → NOT ACCEPTABLE; any open WARN or any waived
finding → ACCEPTABLE WITH NOTES; otherwise ACCEPTABLE. A required slot with no document → INCOMPLETE.

Rule IDs used here (PRD section 6, plus S-xx single-document and supplementary checks):
    S-MTC-01 certificate type      S-MTC-02 CE(IIW) > 0.43       S-WPS-01 WPS on drawing not submitted
    X-03 P-No. qualified by PQR    X-04 thickness in WPS range   X-05 PWHT determination vs WPS
    X-06 welder qualification      X-07 welder continuity        X-09 impact test vs MDMT
    X-10 NACE hardness             X-11 lethal service RT        X-13 as-built welder
    X-15 PWHT chart                S-SUP-01…05 supplementary evidence
"""

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from math import inf

from app.assessment.catalog import GOVERNING, PROFILES, SECTORS, SLOTS, SUPP_BY_ID, Governing
from app.assessment.dossier import Dossier, Joint, Material

# Positions each production position needs.
POSITIONS = {"1G": "F", "2G": "H", "3G": "V", "4G": "O", "5G": "FVO", "6G": "FHVO", "1F": "F", "2F": "H", "3F": "V", "4F": "O"}
POSITION_NAMES = {"F": "flat", "H": "horizontal", "V": "vertical", "O": "overhead"}
CONTINUITY_DAYS = 183  # 6 months, QW-322.1
CE_PREHEAT_REVIEW = 0.43
MR0103_HV10_MAX = 210  # ≈ 200 HBW, NACE SP0472
MR0175_HV10_MAX = 250  # weld and HAZ, ISO 15156-2 (22 HRC ≈ 248 HV is the base-metal limit)
PLATE_TEST_MIN_OD_MM = 610  # a plate test qualifies pipe of 610 mm OD and over only
PWHT_EXEMPT_PREHEAT_C = 95
DEFAULT_EDITION = "2023"

PASS, WARN, FAIL, PENDING, REQUIRED = "PASS", "WARN", "FAIL", "PENDING", "REQUIRED"
INFO = "INFO"
ACCEPTABLE, WITH_NOTES, NOT_ACCEPTABLE, INCOMPLETE = "ACCEPTABLE", "ACCEPTABLE WITH NOTES", "NOT ACCEPTABLE", "INCOMPLETE"
VERDICT_TONE = {ACCEPTABLE: "pass", WITH_NOTES: "warn", NOT_ACCEPTABLE: "reject", INCOMPLETE: "muted"}
SEVERITY_ORDER = {FAIL: 0, WARN: 1, INFO: 2}


@dataclass
class Cell:
    v: str
    tone: str = "ink"  # ink | pass | warn | reject | muted
    bold: bool = False


def cell(v, tone: str = "ink", bold: bool = False) -> Cell:
    return Cell(str(v), tone, bold)


def ok(passed: bool, severity: str = FAIL) -> str:
    return "ink" if passed else "warn" if severity == WARN else "reject"


def result(status: str) -> Cell:
    tone = {PASS: "pass", ACCEPTABLE: "pass", WARN: "warn", FAIL: "reject", REQUIRED: "ink"}.get(status, "muted")
    return Cell(status, tone, True)


def worst(*statuses: str) -> str:
    for s in (FAIL, WARN, PENDING):
        if s in statuses:
            return s
    return PASS


@dataclass
class Section:
    id: str
    title: str
    note: str
    headers: list[str]
    rows: list[list[Cell]] | None  # None = waiting on a document
    missing: str = ""

    @property
    def status(self) -> str:
        return PENDING if self.rows is None else worst(*(r[-1].v for r in self.rows))


@dataclass
class Finding:
    rule_id: str
    severity: str  # FAIL | WARN | INFO
    item: str  # joint ID, heat number or standard
    statement: str
    clause: str
    fix: str
    documents: list[str] = field(default_factory=list)
    id: str = ""  # F-0001…, assigned after sorting
    status: str = "open"  # open | waived
    waiver: dict | None = None

    @property
    def key(self) -> str:
        """Stable across re-runs, so a waiver follows the finding."""
        return f"{self.rule_id}:{self.item}"

    def as_dict(self) -> dict:
        return {**asdict(self), "key": self.key}


@dataclass
class Assessment:
    mode: str
    verdict: str
    verdict_tone: str
    verdict_note: str
    basis: str
    edition: str
    joints: int = 0
    findings: list[Finding] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    criteria: list[dict] = field(default_factory=list)
    counts: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["findings"] = [f.as_dict() for f in self.findings]
        for s, sec in zip(d["sections"], self.sections, strict=True):
            s["status"] = sec.status
        return d


def carbon_equivalent(ch: dict[str, float]) -> float:
    """IIW: CE = C + Mn/6 + (Cr+Mo+V)/5 + (Ni+Cu)/15."""
    g = lambda k: ch.get(k, 0.0)
    return g("C") + g("Mn") / 6 + (g("Cr") + g("Mo") + g("V")) / 5 + (g("Ni") + g("Cu")) / 15


def standards_phrase(gov_id: str, g: Governing) -> str:
    names: list[str] = []
    for s in (gov_id, g.qual, g.nde):
        # "AWS D1.1 Clause 6" repeats "AWS D1.1"; "ASME V" is not part of "ASME VIII-1".
        if not any(s == x or s.startswith(x + " ") or x.startswith(s + " ") for x in names):
            names.append(s)
    return names[0] if len(names) == 1 else f"{names[0]} with {' and '.join(names[1:])}"


def conclude(findings: list[Finding], pending: bool) -> str:
    open_ = [f for f in findings if f.status == "open"]
    if any(f.severity == FAIL for f in open_):
        return NOT_ACCEPTABLE
    if pending:
        return INCOMPLETE
    if any(f.severity == WARN for f in open_) or any(f.status == "waived" for f in findings):
        return WITH_NOTES
    return ACCEPTABLE


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def assess(conditions: dict, files: dict[str, list[str]], dossier: Dossier, today: date | None = None,
           waivers: dict[str, dict] | None = None) -> Assessment:
    """files: document names per slot; waivers: {finding key: {by, reason, at}}."""
    today = today or date.today()
    waivers = waivers or {}
    present = {slot for slot, names in files.items() if names}
    gov_id = conditions.get("governing") or "ASME VIII-1"
    g = GOVERNING.get(gov_id, GOVERNING["ASME VIII-1"])
    edition = str(conditions.get("edition") or DEFAULT_EDITION)
    supp = [s for s in conditions.get("supplementary", []) if s in SUPP_BY_ID]
    has = supp.__contains__
    mdmt = float(conditions.get("mdmt_c", -20))
    hv_limit = MR0103_HV10_MAX if has("MR0103") else MR0175_HV10_MAX if has("MR0175") else None
    mode = "AS-BUILT" if "asbuilt" in present else "PLAN"
    materials = {m.heat: m for m in dossier.materials}
    joints: list[Joint] = dossier.joints if "drawing" in present else []
    sections: list[Section] = []
    findings: list[Finding] = []

    def clause(asme: str, other: str | None = None) -> str:
        """ASME clauses carry the edition; other codes cite their qualification standard."""
        return f"{asme}, {edition} edition" if g.asme else (other or g.qual)

    def docs(slot: str, *refs: str) -> list[str]:
        names = files.get(slot, [])
        hits = [n for n in names if any(_norm(r) and _norm(r) in _norm(n) for r in refs)]
        return hits or names

    def find(rule_id, severity, item, statement, clause_, fix, documents):
        findings.append(Finding(rule_id, severity, item, statement, clause_, fix, documents))

    # Materials, per heat
    def material_row(m: Material) -> list[Cell]:
        ce = carbon_equivalent(m.chemistry)
        cert_ok = m.cert_type in ("3.1", "3.2")
        ce_ok = ce <= CE_PREHEAT_REVIEW
        cv_ok = not has("IMPACT") or (m.impact_temp_c is not None and m.impact_temp_c <= mdmt)
        mtc = docs("mtc", m.heat)
        if not cert_ok:
            find("S-MTC-01", FAIL, m.heat, f"Certificate for heat {m.heat} is EN 10204 type {m.cert_type}; type 3.1 or 3.2 "
                 "is required.", "EN 10204", "Request an EN 10204 3.1 certificate from the supplier.", mtc)
        if not ce_ok:
            find("S-MTC-02", WARN, m.heat, f"Carbon equivalent {ce:.2f} for heat {m.heat} exceeds {CE_PREHEAT_REVIEW}; "
                 "preheat needs review.", "NACE SP0472, material spec", "Review the WPS preheat for this heat.", mtc)
        if not cv_ok:
            find("X-09", FAIL, m.heat,
                 f"Heat {m.heat} has no impact test; impact testing is required at MDMT {mdmt:g} °C." if m.impact_temp_c is None
                 else f"Heat {m.heat} was impact tested at {m.impact_temp_c:g} °C, warmer than MDMT {mdmt:g} °C.",
                 clause("UG-84, UCS-66", "Impact test requirement"),
                 "Provide Charpy results at or below MDMT, or use impact-tested material.", mtc)
        impact = "—" if m.impact_temp_c is None else f"{m.impact_j:g} J @ {m.impact_temp_c:g} °C"
        return [cell(m.heat, bold=True), cell(m.spec), cell(f"P-No.{m.p_no}"), cell(f"{m.thickness_mm:g} mm"),
                cell(m.condition), cell(f"{ce:.2f}", ok(ce_ok, WARN)), cell(impact, ok(cv_ok)),
                result(worst(PASS if cert_ok and cv_ok else FAIL, PASS if ce_ok else WARN))]

    sections.append(Section(
        "mat", "Material Information", "From mill certificates. P-Number per ASME IX QW/QB-422.",
        ["Heat", "Specification", "P-No.", "Thickness", "Condition", "CE (IIW)", "Impact", "Result"],
        [material_row(m) for m in dossier.materials] if "mtc" in present else None, "Mill certificate not submitted."))

    # X-05 PWHT determination, per joint
    pwht: dict[str, tuple[bool, str, str]] = {}
    for j in joints:
        m = materials.get(j.heat)
        p_no = m.p_no if m else None
        wps = dossier.procedures.get(j.wps)
        required, basis, ref = False, "", g.clause
        if not j.pressure:
            basis, ref = "Non-pressure attachment", "—"
        elif has("LETHAL") and gov_id == "ASME VIII-1":
            required, basis, ref = True, "Lethal service", "UW-2(a)"
        elif g.pwht_mm and p_no == "1":
            t, (free, preheat_up_to) = j.thickness_mm, g.pwht_mm
            band = f"over {free:g} mm" if preheat_up_to == inf else f"{free:g}–{preheat_up_to:g} mm"
            if t <= free:
                basis = f"P-No.1, {t:g} mm ≤ {free:g} mm"
            elif t <= preheat_up_to:
                required = not (wps and wps.preheat_c >= PWHT_EXEMPT_PREHEAT_C)
                basis = f"P-No.1, {band} without 95 °C preheat" if required else f"P-No.1, {band}, exempt with 95 °C preheat"
            else:
                required, basis = True, f"P-No.1, {t:g} mm > {preheat_up_to:g} mm"
        else:
            basis = g.rule
        if not required and j.pressure and has("MR0103") and wps and wps.hardness_hv10 > MR0103_HV10_MAX:
            required, basis, ref = True, "Weld hardness above 200 HBW (MR0103)", "NACE MR0103"
        pwht[j.id] = (required, basis, ref)

    def pwht_row(j: Joint) -> list[Cell]:
        required, basis, ref = pwht[j.id]
        wps = dossier.procedures.get(j.wps)
        qualified = None if "wps" not in present else bool(wps and wps.pwht)
        status = PENDING if qualified is None else PASS if (qualified or not required) else FAIL
        if status == FAIL:
            find("X-05", FAIL, j.id, f"{j.id}: PWHT is required ({basis}) but {j.wps} is not qualified with PWHT; adding "
                 "PWHT is an essential variable.", clause(f"{ref}; ASME IX QW-407.1"),
                 f"Assign a WPS qualified with PWHT to {j.id}, or qualify {j.wps} with PWHT.",
                 docs("wps", j.wps) + docs("drawing"))
        m = materials.get(j.heat)
        return [cell(j.id, bold=True), cell(m.spec if m else "—"), cell(f"{j.thickness_mm:g} mm"), cell(basis), cell(ref),
                cell(REQUIRED if required else "NOT REQUIRED", "ink" if required else "muted", True),
                cell("WPS pending" if qualified is None else (wps.pwht if wps and wps.pwht else "No PWHT")), result(status)]

    sections.append(Section(
        "pwht", "PWHT Determination", f"Governing rule ({gov_id}): {g.rule}",
        ["Joint", "Material", "Governing t", "Basis", "Clause", "Determination", "WPS PWHT", "Result"],
        [pwht_row(j) for j in joints] if {"mtc", "drawing"} <= present else None,
        "Mill certificate and welding drawing are needed to determine PWHT."))

    # WPS, per joint (X-03, X-04, X-10, X-09)
    def wps_row(j: Joint) -> list[Cell]:
        w = dossier.procedures.get(j.wps)
        if w is None:
            find("S-WPS-01", FAIL, j.id, f"{j.id}: {j.wps} is assigned on the drawing but was not submitted.",
                 clause("ASME IX QW-200"), f"Upload {j.wps} with its PQR, or change the WPS on the drawing.", docs("drawing"))
            return [cell(j.id, bold=True), cell(j.wps, "reject", True), *(cell("—") for _ in range(4)), result(FAIL)]
        m = materials.get(j.heat)
        p_ok = m is not None and w.p_no == m.p_no
        t_ok = w.t_min_mm <= j.thickness_mm <= w.t_max_mm
        pw_ok = not pwht[j.id][0] or bool(w.pwht)
        sour_hv = hv_limit is not None and j.pressure
        h_ok = not sour_hv or w.hardness_hv10 <= hv_limit
        cv_ok = not has("IMPACT") or not j.pressure or w.impact_temp_c <= mdmt
        wdocs = docs("wps", j.wps, w.pqr)
        if not p_ok:
            find("X-03", FAIL, j.id, f"{j.id}: {j.wps} ({w.pqr}) qualifies P-No.{w.p_no}; the material is "
                 f"P-No.{m.p_no if m else '?'}.", clause("ASME IX QW-403.11, QW-424"),
                 f"Use a WPS whose PQR covers P-No.{m.p_no if m else '?'}.", wdocs + docs("mtc", j.heat))
        if not t_ok:
            find("X-04", FAIL, j.id, f"{j.id}: {j.thickness_mm:g} mm is outside the {j.wps} range "
                 f"{w.t_min_mm:g}–{w.t_max_mm:g} mm.", clause("ASME IX Table QW-451.1"),
                 f"Use a WPS qualified for {j.thickness_mm:g} mm.", wdocs + docs("drawing"))
        if not h_ok:
            find("X-10", FAIL, j.id, f"{j.id}: {w.pqr} hardness {w.hardness_hv10:g} HV10 exceeds the sour-service limit "
                 f"of {hv_limit} HV10.", "ISO 15156-2, ISO 17945",
                 "Provide a PQR hardness survey within the limit, or add PWHT.", wdocs)
        if not cv_ok:
            find("X-09", FAIL, f"{j.id} PQR", f"{j.id}: {w.pqr} impact test at {w.impact_temp_c:g} °C is warmer than MDMT "
                 f"{mdmt:g} °C.", clause("UCS-67, ASME IX QW-170"), "Qualify a PQR with Charpy tests at or below MDMT.", wdocs)
        return [cell(j.id, bold=True), cell(f"{j.wps} / {w.pqr}"), cell(f"P{m.p_no if m else '?'} → P{w.p_no}", ok(p_ok)),
                cell(f"{j.thickness_mm:g} mm in {w.t_min_mm:g}–{w.t_max_mm:g}", ok(t_ok)),
                cell("Qualified" if w.pwht else "None", ok(pw_ok)),
                cell(f"{w.hardness_hv10:g} HV10" if sour_hv else "N/A", ok(h_ok)),
                result(PASS if p_ok and t_ok and pw_ok and h_ok and cv_ok else FAIL)]

    sections.append(Section(
        "wps", "WPS Review",
        f"Essential variables per {'ASME IX QW-250' if g.asme else g.qual}, checked against each joint on the welding drawing.",
        ["Joint", "WPS / PQR", "P-No.", "Thickness", "PWHT", "Hardness", "Result"],
        [wps_row(j) for j in joints] if {"wps", "drawing"} <= present else None, "WPS and welding drawing are needed."))

    # WPQ, per joint (X-06 qualification, X-07 continuity)
    def welder_check(j: Joint, welder: str, on: date, as_built: bool) -> tuple[list[Finding], list[Cell]]:
        q = dossier.welders.get(welder)
        w = dossier.procedures.get(j.wps)
        rule_q, item = ("X-13", f"{j.id} (as-built)") if as_built else ("X-06", j.id)
        was = "was" if as_built else "is"
        when = f" on {on:%d %b %Y} when {j.id} was welded" if as_built else ""
        if q is None:
            return [Finding(rule_q, FAIL, item, f"Welder {welder} {was} not qualified{when}: no WPQ on file.",
                            clause("ASME IX QW-301"), f"Provide the WPQ of welder {welder}, or re-weld {j.id} with a "
                            "qualified welder.", docs("asbuilt" if as_built else "drawing"))], \
                [cell(f"Welder {welder}", "reject", True), *(cell("—") for _ in range(5))]
        processes = w.processes if w else ()
        pr_ok = all(p in q.processes for p in processes)
        need = POSITIONS.get(j.position, "")
        quals = q.fillet if j.kind == "fillet" else q.groove
        po_ok = all(x in quals for x in need)
        t_ok = q.t_max_mm is None or j.thickness_mm <= q.t_max_mm
        # QW-452.3 / QW-461.9: a plate test qualifies pipe of 610 mm OD and over only.
        od_min = PLATE_TEST_MIN_OD_MM if q.test_form == "plate" else q.od_min_mm
        d_ok = not j.od_mm or not od_min or j.od_mm >= od_min
        days = (on - q.last_weld).days
        c_ok = days <= CONTINUITY_DAYS
        qdocs = docs("wpq", q.id, welder)
        out: list[Finding] = []
        if not po_ok:
            out.append(Finding(rule_q, FAIL, item, f"Welder {welder} ({q.id}, {q.test}) {was} not qualified for "
                               f"{', '.join(POSITION_NAMES[x] for x in need)} {j.kind} welding ({j.position}){when}.",
                               clause("ASME IX Table QW-461.9"),
                               f"Assign a welder qualified for {j.position}, or requalify welder {welder} in {j.position}.",
                               qdocs + docs("drawing")))
        elif not pr_ok:
            out.append(Finding(rule_q, FAIL, item, f"Welder {welder} {was} not qualified for {' + '.join(processes)}{when}.",
                               clause("ASME IX QW-351"), f"Assign a welder qualified for {' + '.join(processes)}.", qdocs))
        elif not t_ok:
            out.append(Finding(rule_q, FAIL, item, f"{j.id}: {j.thickness_mm:g} mm exceeds the {q.t_max_mm:g} mm qualified "
                               f"for welder {welder}{when}.", clause("ASME IX QW-452.1"),
                               f"Assign a welder qualified for {j.thickness_mm:g} mm.", qdocs))
        elif not d_ok:
            out.append(Finding(rule_q, FAIL, item, f"{j.id}: pipe OD {j.od_mm:g} mm is below the {od_min:g} mm qualified "
                               f"for welder {welder}{when}" + (" (plate test)." if q.test_form == "plate" else "."),
                               clause("ASME IX QW-452.3, Table QW-461.9"),
                               f"Assign a welder qualified for OD {j.od_mm:g} mm.", qdocs))
        if not c_ok:
            out.append(Finding("X-07", FAIL, item, f"Welder {welder} continuity lapsed: last use {q.last_weld:%d %b %Y}, "
                               f"{days} days before {'the weld date' if as_built else 'the assessment date'}.",
                               clause("ASME IX QW-322.1"),
                               f"Provide a continuity record within 6 months, or requalify welder {welder}.", qdocs))
        cells = [cell(f"{welder} · {q.id}", bold=True), cell(" + ".join(processes) or "—", ok(pr_ok)),
                 cell(f"{j.position} ({''.join(quals)})", ok(po_ok)),
                 cell("Unlimited" if q.t_max_mm is None else f"≤ {q.t_max_mm:g} mm", ok(t_ok)),
                 cell(f"{j.od_mm:g} ≥ {od_min:g}" if j.od_mm and od_min else "N/A", ok(d_ok)),
                 cell(f"{days} days", ok(c_ok))]
        return out, cells

    def wpq_row(j: Joint) -> list[Cell]:
        out, cells = welder_check(j, j.welder, today, as_built=False)
        findings.extend(out)
        return [cell(j.id, bold=True), *cells, result(FAIL if out else PASS)]

    sections.append(Section(
        "wpq", "WPQ Review",
        f"Welder qualification per {'ASME IX QW-300' if g.asme else g.qual} against the WPS and the joint on the drawing. "
        "Continuity limit: 6 months.",
        ["Joint", "Welder", "Process", "Position", "Thickness", "Diameter", "Continuity", "Result"],
        [wpq_row(j) for j in joints] if {"wpq", "wps", "drawing"} <= present else None,
        "WPQ, WPS and welding drawing are needed."))

    # Supplementary requirements
    rows: list[list[Cell]] = []
    procs = list(dossier.procedures.values())
    have_wps, have_dwg = "wps" in present, "drawing" in present

    def evidence(rule_id: str, label: str, need: str, limit: str, have: bool, text: str, passed: bool | None,
                 pending_text: str, ref: str, fix: str, slot: str, severity: str = FAIL):
        status = PENDING if not have else WARN if passed is None else PASS if passed else severity
        if status in (FAIL, WARN):
            find(rule_id, status, label, f"{label}: {need.lower()}: {text} (limit {limit}).", ref, fix, docs(slot))
        rows.append([cell(label, bold=True), cell(need), cell(limit),
                     cell(text if have else pending_text, "ink" if have else "muted"), result(status)])

    max_hv = max((p.hardness_hv10 for p in procs), default=0)
    hv_text = ", ".join(f"{p.pqr}: {p.hardness_hv10:g} HV10" for p in procs)
    if has("MR0103"):
        evidence("X-10", "NACE MR0103", "Weld deposit hardness, wetted joints", "≤ 200 HBW", have_wps, hv_text,
                 max_hv <= MR0103_HV10_MAX, "WPS pending", "ISO 17945, NACE SP0472",
                 "Provide a PQR hardness survey within 200 HBW, or add PWHT.", "wps")
    if has("MR0175"):
        evidence("X-10", "NACE MR0175", "Weld and HAZ hardness", f"≤ 22 HRC ({MR0175_HV10_MAX} HV10)", have_wps, hv_text,
                 max_hv <= MR0175_HV10_MAX, "WPS pending", "ISO 15156-2",
                 "Provide a PQR hardness survey within 22 HRC, or add PWHT.", "wps")
    if has("LETHAL"):
        butt = [j for j in dossier.joints if j.pressure and j.kind == "groove"]
        evidence("X-11", "Lethal service", "Full radiography of butt welds", "RT 100%", have_dwg,
                 ", ".join(f"{j.id}: {j.nde}" for j in butt), all("RT 100%" in j.nde for j in butt), "Drawing pending",
                 clause("UW-2(a), UW-11(a)"), "Specify RT 100% on every Category A and B butt weld.", "drawing")
    if has("IMPACT"):
        evidence("X-09", "Impact tested", "PQR toughness", f"Test temp ≤ MDMT {mdmt:g} °C", have_wps,
                 ", ".join(f"{p.pqr} @ {p.impact_temp_c:g} °C" for p in procs), all(p.impact_temp_c <= mdmt for p in procs),
                 "WPS pending", clause("UCS-67, ASME IX QW-170"), "Qualify a PQR with Charpy tests at or below MDMT.", "wps")
    if has("ISO3834"):
        # No certificate slot yet, so this needs a reviewer decision until one can be submitted.
        evidence("S-SUP-01", "ISO 3834-2", "Manufacturer certification, welding coordinator (ISO 14731)", "Certificate on file",
                 True, "Not in submitted documents", None, "", "ISO 3834-2", "Attach the ISO 3834-2 certificate.", "wps")
    if has("EXC3"):
        evidence("S-SUP-02", "EN 1090-2 EXC3", "WPS qualified by procedure test", "ISO 15614-1", have_wps,
                 ", ".join(p.pqr for p in procs), all(p.pqr for p in procs), "WPS pending", "EN 1090-2 §7.4.1",
                 "Qualify each WPS by an ISO 15614-1 procedure test.", "wps")
    if has("ISO5817B"):
        evidence("S-SUP-03", "ISO 5817 level B", "Imperfection acceptance on drawing NDE plan", "Level B", have_dwg,
                 "NDE on every joint" if all(j.nde for j in dossier.joints) else "Joints without NDE",
                 all(j.nde for j in dossier.joints), "Drawing pending", "ISO 5817", "Add NDE to every joint.", "drawing")
    if has("FATIGUE"):
        butt = [j for j in dossier.joints if j.kind == "groove"]
        evidence("S-SUP-04", "Cyclically loaded", "Weld profile and NDE for cyclic loading", "Volumetric NDE on butt welds",
                 have_dwg, ", ".join(f"{j.id}: {j.nde}" for j in butt), all(("RT" in j.nde or "UT" in j.nde) for j in butt),
                 "Drawing pending", "AWS D1.1 Part C, client spec", "Specify RT or UT on every butt weld.", "drawing", WARN)
    if has("SEISMIC"):
        evidence("S-SUP-05", "AWS D1.8", "Filler toughness, demand-critical welds", "27 J @ -18 °C", have_wps,
                 ", ".join(f"{p.pqr} tested @ {p.impact_temp_c:g} °C" for p in procs), all(p.impact_temp_c <= -18 for p in procs),
                 "WPS pending", "AWS D1.8 §6.3", "Use filler metal with 27 J at -18 °C.", "wps")
    if rows:
        sections.append(Section("supp", "Supplementary Requirements", "Selected in addition to the governing standard.",
                                ["Standard", "Requirement", "Limit", "Evidence", "Result"], rows))

    # As-built verification: what was done, checked against the plan and the governing standard.
    if mode == "AS-BUILT" and joints:
        asb_docs = docs("asbuilt")

        # X-13 weld log (actual welder on the weld date, WPS used) and X-14 heats welded
        def weld_log_row(j: Joint) -> list[Cell]:
            a = dossier.as_built.get(j.id)
            if a is None:
                find("X-13", FAIL, f"{j.id} (as-built)", f"{j.id} is on the welding drawing but not in the as-built weld log.",
                     "QC system", f"Add {j.id} to the weld log with welder, date and WPS.", asb_docs)
                return [cell(j.id, bold=True), cell(j.welder), cell("—", "reject"), *(cell("—") for _ in range(4)), result(FAIL)]
            out, _ = welder_check(j, a.welder, a.weld_date, as_built=True)
            # The planned welder's qualification is already X-06; only continuity at the weld date is new.
            out = [f for f in out if a.welder != j.welder or f.rule_id == "X-07"]
            findings.extend(out)
            wps_ok = a.wps == j.wps or bool(a.deviation)
            if not wps_ok:
                find("X-13", FAIL, f"{j.id} (as-built)", f"{j.id} was welded with {a.wps}; the plan assigns {j.wps} and no "
                     "deviation is recorded.", "QC system", f"Record an approved deviation (NCR) or re-qualify {j.id}.", asb_docs)
            w = dossier.procedures.get(a.wps)
            heats_ok = True
            for h in a.heats:
                m = materials.get(h)
                if m is None:
                    heats_ok = False
                    find("X-14", FAIL, f"{j.id} heat {h}", f"Heat {h} was welded at {j.id} but has no mill certificate.",
                         "UG-77, UG-93" if g.asme else "Material traceability",
                         f"Upload the EN 10204 3.1 certificate for heat {h}, or replace the material.", asb_docs)
                elif w and m.p_no != w.p_no:
                    heats_ok = False
                    find("X-14", FAIL, f"{j.id} heat {h}", f"Heat {h} is P-No.{m.p_no}; {a.wps} ({w.pqr}) qualifies "
                         f"P-No.{w.p_no} only.", clause("ASME IX QW-403.11"), f"Use a WPS whose PQR covers P-No.{m.p_no}.",
                         asb_docs + docs("mtc", h))
            changed = a.welder != j.welder
            passed = not out and wps_ok and heats_ok
            return [cell(j.id, bold=True), cell(j.welder), cell(a.welder, "reject" if changed else "ink", changed),
                    cell(f"{a.weld_date:%d %b %Y}"), cell(a.wps + (f" ({a.deviation})" if a.deviation else ""), ok(wps_ok)),
                    cell(" + ".join(a.heats), ok(heats_ok)), cell("Yes" if not out else "No", ok(not out)),
                    result(PASS if passed else FAIL)]

        sections.append(Section("asb", "As-built Weld Log", "Actual welder on the weld date, WPS used and heats welded, "
                                "compared with the qualified plan.",
                                ["Joint", "Planned welder", "Actual welder", "Weld date", "WPS used", "Heats", "Qualified",
                                 "Result"], [weld_log_row(j) for j in joints]))

        # X-15 PWHT records against the governing standard and the WPS
        by_joint = {j.id: j for j in joints}
        pwht_rows: list[list[Cell]] = []
        charted = {jid for c in dossier.pwht_charts for jid in c.joints}
        for jid, (required, basis, _ref) in pwht.items():
            if required and jid not in charted:
                find("X-15", FAIL, f"{jid} (as-built)", f"{jid} requires PWHT ({basis}) but appears in no PWHT load.",
                     clause("UCS-56(d), Table UCS-56-1", g.clause), f"Provide the PWHT chart and load list covering {jid}.",
                     asb_docs)
                pwht_rows.append([cell("—"), cell(jid, "reject", True), *(cell("—") for _ in range(4)), result(FAIL)])
        for c in dossier.pwht_charts:
            load = [by_joint[jid] for jid in c.joints if jid in by_joint]
            t = max((jj.thickness_mm for jj in load), default=0)
            hold_req = max(15.0, 60 * t / 25)
            soak_min = g.soak_min_c
            bands = [dossier.procedures[jj.wps].pwht_band_c for jj in load
                     if jj.wps in dossier.procedures and dossier.procedures[jj.wps].pwht_band_c]
            lo = max([soak_min or 0, *(b[0] for b in bands)])
            hi = min([b[1] for b in bands], default=None)
            soak_ok = c.soak_c >= lo and (hi is None or c.soak_c <= hi)
            hold_ok = c.hold_min >= hold_req
            heat_max = max(56.0, min(222.0, 222 * 25 / t)) if t else 222.0
            cool_max = max(56.0, min(278.0, 278 * 25 / t)) if t else 278.0
            rates_ok = not g.rate_limits or (c.heat_rate_c_per_h <= heat_max and c.cool_rate_c_per_h <= cool_max)
            item = f"PWHT {c.load_id}"
            band = f"{lo:g}–{hi:g} °C" if hi is not None else f"≥ {lo:g} °C"
            if not soak_ok:
                find("X-15", FAIL, item, f"Load {c.load_id} soaked at {c.soak_c:g} °C; required {band} (governing standard "
                     "and WPS band).", clause("Table UCS-56-1; ASME IX QW-407", g.clause),
                     "Repeat the PWHT within the qualified band.", asb_docs)
            if not hold_ok:
                find("X-15", FAIL, item, f"Load {c.load_id} held {c.hold_min:g} min; {hold_req:g} min required for "
                     f"{t:g} mm (1 h per 25 mm, 15 min minimum).", clause("Table UCS-56-1", g.clause),
                     "Extend the hold time and record a new chart.", asb_docs)
            if not rates_ok:
                find("X-15", FAIL, item, f"Load {c.load_id} heated at {c.heat_rate_c_per_h:g} °C/h and cooled at "
                     f"{c.cool_rate_c_per_h:g} °C/h above 425 °C; limits for {t:g} mm are {heat_max:.0f} and {cool_max:.0f} °C/h.",
                     clause("UCS-56(d)"), "Repeat the PWHT within the rate limits.", asb_docs)
            pwht_rows.append([
                cell(c.load_id, bold=True), cell(", ".join(c.joints)), cell(f"{c.soak_c:g} °C (req. {band})", ok(soak_ok)),
                cell(f"{c.hold_min:g} min (req. {hold_req:g})", ok(hold_ok)),
                cell(f"{c.heat_rate_c_per_h:g} / {c.cool_rate_c_per_h:g} °C/h" +
                     (f" (max {heat_max:.0f} / {cool_max:.0f})" if g.rate_limits else ""), ok(rates_ok)),
                cell("Chart on file"), result(PASS if soak_ok and hold_ok and rates_ok else FAIL)])
        if pwht_rows:
            sections.append(Section("asb_pwht", "PWHT Records", f"Every joint needing PWHT must be in a load; soak, hold and "
                                    f"rates per {gov_id} and the WPS band.",
                                    ["Load", "Joints", "Soak", "Hold", "Heating / cooling", "Record", "Result"], pwht_rows))

        # X-16 NDE performed against the plan and the governing standard
        def nde_row(j: Joint) -> list[Cell]:
            planned = {m: float(p) for m, p in re.findall(r"(RT|UT|MT|PT|VT)\s*(\d+(?:\.\d+)?)\s*%", j.nde)}
            required = dict(planned)
            code_note = ""
            if g.full_rt_over_mm and j.pressure and j.kind == "groove" and j.thickness_mm > g.full_rt_over_mm:
                required["RT"] = 100.0
                code_note = f"RT 100% ({j.thickness_mm:g} mm > {g.full_rt_over_mm:g} mm)"
            reports = [r for r in dossier.nde_reports if r.joint == j.id]
            done: dict[str, float] = {}
            for r in reports:
                done[r.method] = done.get(r.method, 0) + r.extent_pct
            short = {m: p for m, p in required.items() if done.get(m, 0) < p}
            rejected = [r for r in reports if r.result != "ACCEPT"]
            unsigned = [r for r in reports if r.level not in ("II", "III")]
            ndocs = asb_docs
            for m, p in short.items():
                why = "required by the code" if code_note and m == "RT" and planned.get("RT", 0) < 100 else "planned"
                find("X-16", FAIL, j.id, f"{j.id}: {m} {p:g}% {why}, {done.get(m, 0):g}% performed.",
                     clause("UW-11, UW-52; ASME V", g.nde), f"Perform the missing {m} on {j.id} and upload the report.", ndocs)
            for r in rejected:
                find("X-16", FAIL, j.id, f"{j.id}: {r.report_no} ({r.method}) is rejected with no repair re-examination.",
                     clause("UW-51, UW-52", g.nde), f"Repair {j.id} and re-examine it.", ndocs)
            for r in unsigned:
                find("X-16", FAIL, j.id, f"{j.id}: {r.report_no} is not signed by a Level II or III technician.",
                     clause("ASME V T-120", g.nde), "Have the report signed by a Level II or III technician.", ndocs)
            passed = not short and not rejected and not unsigned
            fmt = lambda d: " + ".join(f"{m} {p:g}%" for m, p in d.items()) or "—"
            return [cell(j.id, bold=True), cell(fmt(planned)), cell(code_note or "As planned"), cell(fmt(done), ok(not short)),
                    cell(", ".join(f"{r.report_no} {r.result} L{r.level or '?'}" for r in reports) or "None",
                         ok(not rejected and not unsigned)), result(PASS if passed else FAIL)]

        sections.append(Section("asb_nde", "NDE Records", f"Extent performed against the plan and {g.nde}; every report "
                                "accepted and signed by Level II or III.",
                                ["Joint", "Planned", "Required by code", "Performed", "Reports", "Result"],
                                [nde_row(j) for j in joints]))

        # X-19 thickness and X-20 hydrotest
        test_rows: list[list[Cell]] = []
        for tr in dossier.thickness:
            t_ok = tr.measured_mm >= tr.required_mm
            if not t_ok:
                find("X-19", FAIL, tr.location, f"{tr.location} (heat {tr.heat}) measured {tr.measured_mm:g} mm, below the "
                     f"required {tr.required_mm:g} mm including corrosion allowance.", clause("UG-16, UG-22", "Design"),
                     "Request a design recalculation or replace the part.", asb_docs)
            test_rows.append([cell(f"Thickness · {tr.location}", bold=True), cell(f"≥ {tr.required_mm:g} mm"),
                              cell(f"{tr.measured_mm:g} mm", ok(t_ok)), result(PASS if t_ok else FAIL)])
        if g.hydro_factor:
            design_p = float(conditions.get("design_pressure_mpa") or 0)
            need = round(g.hydro_factor * design_p, 2)
            ht = dossier.hydrotest
            hclause = clause(g.hydro_clause)
            if ht is None:
                find("X-20", FAIL, "Hydrotest", "No hydrotest record was submitted.", hclause,
                     "Upload the hydrotest record with pressure, hold time and witness.", asb_docs)
                test_rows.append([cell("Hydrotest", bold=True), cell(f"≥ {need:g} MPa"), cell("Not recorded", "reject"),
                                  result(FAIL)])
            else:
                p_ok = ht.pressure_mpa >= need
                w_ok = bool(ht.witness)
                temp_ok = ht.metal_temp_c >= mdmt + 17
                if not p_ok:
                    find("X-20", FAIL, "Hydrotest", f"Test pressure {ht.pressure_mpa:g} MPa is below {need:g} MPa "
                         f"({g.hydro_factor:g} × design {design_p:g} MPa, stress ratio 1).", hclause,
                         "Repeat the hydrotest at the required pressure.", asb_docs)
                if not w_ok:
                    find("X-20", WARN, "Hydrotest", "The hydrotest record has no witness signature.", hclause,
                         "Have the inspector sign the hydrotest record.", asb_docs)
                if not temp_ok:
                    find("X-20", WARN, "Hydrotest", f"Metal temperature {ht.metal_temp_c:g} °C is below MDMT + 17 °C "
                         f"({mdmt + 17:g} °C) recommended during the test.", hclause,
                         "Confirm the brittle-fracture assessment for the test temperature.", asb_docs)
                test_rows.append([cell("Hydrotest", bold=True),
                                  cell(f"≥ {need:g} MPa · witness · metal ≥ {mdmt + 17:g} °C"),
                                  cell(f"{ht.pressure_mpa:g} MPa · {ht.hold_min:g} min · {ht.metal_temp_c:g} °C · "
                                       f"{ht.witness or 'no witness'}", ok(p_ok and w_ok and temp_ok, FAIL if not p_ok else WARN)),
                                  result(FAIL if not p_ok else WARN if not (w_ok and temp_ok) else PASS)])
        if test_rows:
            sections.append(Section("asb_test", "Thickness and Hydrotest", "Measured thickness against the drawing minimum; "
                                    f"hydrotest per {gov_id}" + (f" {g.hydro_clause}." if g.hydro_clause else "."),
                                    ["Item", "Requirement", "Recorded", "Result"], test_rows))

    # Waivers, ordering and IDs: FAIL first, then WARN, grouped by item.
    for f in findings:
        if f.key in waivers:
            f.status, f.waiver = "waived", waivers[f.key]
    findings.sort(key=lambda f: (f.status != "open", SEVERITY_ORDER[f.severity], f.item, f.rule_id))
    for i, f in enumerate(findings, 1):
        f.id = f"F-{i:04d}"

    by_id = {s.id: s for s in sections}
    status = lambda sid: by_id[sid].status if sid in by_id else "N/A"
    criteria = [
        ("Material certificates meet the governing and supplementary standards", status("mat")),
        ("A qualified WPS covers every joint on the welding drawing", status("wps")),
        ("Every welder is qualified for the assigned joints", status("wpq")),
        ("PWHT requirement is met by the qualified WPS", status("pwht")),
        ("Supplementary requirements are met", status("supp")),
        ("As-built weld log matches the qualified plan", "OPEN (PLAN)" if mode == "PLAN" else status("asb")),
        ("PWHT records meet the governing standard", "OPEN (PLAN)" if mode == "PLAN" else status("asb_pwht")),
        ("NDE performed meets the plan and the governing standard", "OPEN (PLAN)" if mode == "PLAN" else status("asb_nde")),
        ("Thickness and hydrotest meet the design", "OPEN (PLAN)" if mode == "PLAN" else status("asb_test")),
    ]
    pending = any(v == PENDING for _, v in criteria) or bool(missing_required(present))
    verdict = conclude(findings, pending)
    note = {
        NOT_ACCEPTABLE: "Resolve every open FAIL before fabrication or release.",
        INCOMPLETE: "Some checks are waiting on documents.",
        WITH_NOTES: "No open FAIL. Warnings and waivers need the reviewer's decision and are listed in the report.",
        ACCEPTABLE: "The plan meets the requirements and fabrication may proceed. The as-built check is still open."
        if mode == "PLAN" else "The finished work matches the qualified plan.",
    }[verdict]

    profile = PROFILES.get(conditions.get("profile", ""), PROFILES["plant-vessel"])
    supp_text = "".join(f" · {SUPP_BY_ID[s].label}" for s in supp)
    basis = (f"{SECTORS[profile.sector]} · {profile.label} · {standards_phrase(gov_id, g)} ({edition}){supp_text} · "
             f"Design {conditions.get('design_pressure_mpa', '—')} MPa / {conditions.get('design_temp_c', '—')} °C · "
             f"MDMT {mdmt:g} °C")
    open_ = [f for f in findings if f.status == "open"]
    counts = {"fail": sum(f.severity == FAIL for f in open_), "warn": sum(f.severity == WARN for f in open_),
              "info": sum(f.severity == INFO for f in open_), "waived": sum(f.status == "waived" for f in findings)}

    return Assessment(
        mode=mode, verdict=verdict, verdict_tone=VERDICT_TONE[verdict], verdict_note=note, basis=basis, edition=edition,
        joints=len(joints), findings=findings, sections=sections, counts=counts,
        criteria=[{"label": label, "status": v,
                   "tone": {PASS: "pass", FAIL: "reject", WARN: "warn"}.get(v, "muted")} for label, v in criteria],
    )


def missing_required(present: set[str]) -> list[str]:
    return [s.label for s in SLOTS if s.required and s.id not in present]
