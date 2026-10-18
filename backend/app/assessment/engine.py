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
from app.assessment.dossier import Dossier, Evidence, Joint, Material

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
    evidence: list[dict] = field(default_factory=list)  # [{file, page, box, label}] for snapshots of the source

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

    def find(rule_id, severity, item, statement, clause_, fix, documents, ev=None):
        findings.append(Finding(rule_id, severity, item, statement, clause_, fix, documents, evidence=ev or []))

    def once(rule_id, severity, item, statement, clause_, fix, documents, ev=None):
        """Report a document-level gap once, however many joints run into it."""
        if not any(f.rule_id == rule_id and f.item == item for f in findings):
            find(rule_id, severity, item, statement, clause_, fix, documents, ev)

    def evid(*parts) -> list[dict]:
        """Evidence for a finding: Evidence objects, records (their whole-record box) or (record, field) pairs."""
        out: list[dict] = []
        for part in parts:
            record, key = part if isinstance(part, tuple) else (part, "record")
            if record is None:
                continue
            ev = record if isinstance(record, Evidence) else (
                getattr(record, "evidence", {}).get(key) or getattr(record, "evidence", {}).get("record"))
            if ev is not None and asdict(ev) not in out:
                out.append(asdict(ev))
        return out

    def log_ev(jid: str) -> list[Evidence]:
        a = dossier.as_built.get(jid)
        return list(a.evidence.values()) if a else []

    def num(v, unit=" mm") -> str:
        return "—" if v is None else f"{v:g}{unit}"

    def src(record, slot: str, *refs: str) -> list[str]:
        source = getattr(record, "source", None)
        return [source] if source else docs(slot, *refs)

    # Design data on the drawing must match the conditions (PRD 5.4).
    if "drawing" in present and dossier.design_pressure_mpa is not None:
        cond_p = float(conditions.get("design_pressure_mpa") or 0)
        if abs(dossier.design_pressure_mpa - cond_p) > 0.01 * max(cond_p, 0.1):
            find("S-DRW-03", FAIL, "Design data", f"The drawing gives design pressure {dossier.design_pressure_mpa:g} MPa; "
                 f"the conditions say {cond_p:g} MPa.", clause("UG-116", "Design data"),
                 "Correct the design pressure in step 1 or on the drawing.", docs("drawing"), ev=evid(dossier.drawing_evidence))

    # Materials, per heat
    def material_row(m: Material) -> list[Cell]:
        ce = carbon_equivalent(m.chemistry) if m.chemistry else None
        cert_ok = m.cert_type in ("3.1", "3.2")
        ce_ok = ce is None or ce <= CE_PREHEAT_REVIEW
        cv_ok = not has("IMPACT") or (m.impact_temp_c is not None and m.impact_temp_c <= mdmt)
        tensile_ok = m.tensile_mpa is None or m.tensile_min_mpa is None or m.tensile_mpa >= m.tensile_min_mpa
        signed_ok = m.signed is not False
        mtc = src(m, "mtc", m.heat)
        if not cert_ok:
            find("S-MTC-01", FAIL, m.heat,
                 f"Certificate for heat {m.heat} does not state its EN 10204 type; type 3.1 or 3.2 is required."
                 if m.cert_type is None else
                 f"Certificate for heat {m.heat} is EN 10204 type {m.cert_type}; type 3.1 or 3.2 is required.",
                 "EN 10204", "Request an EN 10204 3.1 certificate from the supplier.", mtc, ev=evid(m))
        if not tensile_ok:
            find("S-MTC-04", FAIL, m.heat, f"Heat {m.heat} tensile strength {m.tensile_mpa:g} MPa is below the "
                 f"{m.tensile_min_mpa:g} MPa minimum of {m.spec or 'the specification'}.",
                 "Material specification" + (" (UG-93)" if g.asme else ""),
                 "Reject the material, or obtain a retest certificate that meets the specification.", mtc, ev=evid((m, "tensile")))
        if not signed_ok:
            find("S-MTC-03", WARN, m.heat, f"Certificate for heat {m.heat} not signed by the manufacturer's authorised inspector.", "EN 10204 §4", "Request a signed certificate.", mtc, ev=evid((m, "signature")))
        if g.asme and m.p_no is None and m.spec:
            find("S-MTC-05", WARN, m.heat, f"{m.spec} (heat {m.heat}) has no P-Number in the table; a non-listed material "
                 "needs a Code Case or a UG-10 reconciliation.", clause("ASME IX QW/QB-422; UG-10"),
                 "Confirm the P-No., or attach the UG-10 reconciliation or Code Case.", mtc, ev=evid(m))
        if not ce_ok:
            find("S-MTC-02", WARN, m.heat, f"Carbon equivalent {ce:.2f} for heat {m.heat} exceeds {CE_PREHEAT_REVIEW}; "
                 "preheat needs review.", "NACE SP0472, material spec", "Review the WPS preheat for this heat.", mtc, ev=evid(m))
        if not cv_ok:
            find("X-09", FAIL, m.heat,
                 f"Heat {m.heat} has no impact test; impact testing is required at MDMT {mdmt:g} °C." if m.impact_temp_c is None
                 else f"Heat {m.heat} was impact tested at {m.impact_temp_c:g} °C, warmer than MDMT {mdmt:g} °C.",
                 clause("UG-84, UCS-66", "Impact test requirement"),
                 "Provide Charpy results at or below MDMT, or use impact-tested material.", mtc, ev=evid(m))
        impact = "—" if m.impact_temp_c is None else f"{num(m.impact_j, ' J')} @ {m.impact_temp_c:g} °C"
        tensile = "—" if m.tensile_mpa is None else f"{m.tensile_mpa:g}" + (
            f" ≥ {m.tensile_min_mpa:g}" if m.tensile_min_mpa is not None else "") + " MPa"
        return [cell(m.heat, bold=True), cell(m.spec or "—"), cell(f"P-No.{m.p_no}" if m.p_no else "—", ok(m.p_no is not None, WARN)),
                cell(num(m.thickness_mm)), cell(m.condition or "—"), cell("—" if ce is None else f"{ce:.2f}", ok(ce_ok, WARN)),
                cell(impact, ok(cv_ok)), cell(tensile, ok(tensile_ok)),
                result(worst(PASS if cert_ok and cv_ok and tensile_ok else FAIL,
                             PASS if ce_ok and signed_ok and (m.p_no or not g.asme or not m.spec) else WARN))]

    sections.append(Section(
        "mat", "Material Information", "From mill certificates. P-Number per ASME IX QW/QB-422.",
        ["Heat", "Specification", "P-No.", "Thickness", "Condition", "CE (IIW)", "Impact", "Tensile", "Result"],
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
        elif g.pwht_mm and p_no == "1" and j.thickness_mm is None:
            basis = "Thickness not on the drawing"
            find("S-DRW-02", WARN, j.id, f"{j.id}: no thickness on the drawing; PWHT not determined.",
                 clause(g.clause), f"Add the governing thickness of {j.id} to the weld map.", docs("drawing"), ev=evid(j))
        elif g.pwht_mm and p_no == "1":
            t, (free, preheat_up_to) = j.thickness_mm, g.pwht_mm
            band = f"over {free:g} mm" if preheat_up_to == inf else f"{free:g}–{preheat_up_to:g} mm"
            if t <= free:
                basis = f"P-No.1, {t:g} mm ≤ {free:g} mm"
            elif t <= preheat_up_to:
                required = not (wps and (wps.preheat_c or 0) >= PWHT_EXEMPT_PREHEAT_C)
                basis = f"P-No.1, {band} without 95 °C preheat" if required else f"P-No.1, {band}, exempt with 95 °C preheat"
            else:
                required, basis = True, f"P-No.1, {t:g} mm > {preheat_up_to:g} mm"
        else:
            basis = g.rule
        if not required and j.pressure and has("MR0103") and wps and (wps.hardness_hv10 or 0) > MR0103_HV10_MAX:
            required, basis, ref = True, "Weld hardness above 200 HBW (MR0103)", "NACE MR0103"
        if not required and j.pwht_required:
            required, basis, ref = True, "Drawing / WPS note", "Design"
        pwht[j.id] = (required, basis, ref)

    def pwht_row(j: Joint) -> list[Cell]:
        required, basis, ref = pwht[j.id]
        wps = dossier.procedures.get(j.wps)
        # A WPS that was not submitted is reported once (S-WPS-01); its PWHT is unknown, not failed.
        qualified = None if "wps" not in present or wps is None else bool(wps.pwht)
        status = PENDING if qualified is None else PASS if (qualified or not required) else FAIL
        if status == FAIL:
            find("X-05", FAIL, j.id, f"{j.id}: PWHT is required ({basis}) but {j.wps} is not qualified with PWHT; adding "
                 "PWHT is an essential variable.", clause(f"{ref}; ASME IX QW-407.1"),
                 f"Assign a WPS qualified with PWHT to {j.id}, or qualify {j.wps} with PWHT.",
                 docs("wps", j.wps) + docs("drawing"), ev=evid(j, (wps, "pwht")))
        m = materials.get(j.heat)
        return [cell(j.id, bold=True), cell(m.spec if m and m.spec else "—"), cell(num(j.thickness_mm)), cell(basis), cell(ref),
                cell(REQUIRED if required else "NOT REQUIRED", "ink" if required else "muted", True),
                cell(("WPS not submitted" if "wps" in present else "WPS pending") if qualified is None
                     else (wps.pwht if wps and wps.pwht else "No PWHT")), result(status)]

    sections.append(Section(
        "pwht", "PWHT Determination", f"Governing rule ({gov_id}): {g.rule}",
        ["Joint", "Material", "Governing t", "Basis", "Clause", "Determination", "WPS PWHT", "Result"],
        [pwht_row(j) for j in joints] if {"mtc", "drawing"} <= present else None,
        "Mill certificate and welding drawing are needed to determine PWHT."))

    # WPS, per joint (X-03, X-04, X-10, X-09)
    def wps_row(j: Joint) -> list[Cell]:
        w = dossier.procedures.get(j.wps) if j.wps else None
        if w is None:
            find("S-WPS-01", FAIL, j.id, f"{j.id}: {j.wps} not submitted." if j.wps else f"{j.id}: no WPS assigned.", clause("ASME IX QW-200"),
                 f"Upload {j.wps} with its PQR, or assign a submitted WPS." if j.wps else f"Assign a WPS to {j.id}.",
                 docs("drawing") + list(getattr(dossier.as_built.get(j.id), "sources", ())), ev=evid(j, *log_ev(j.id)))
            return [cell(j.id, bold=True), cell(j.wps or "None", "reject", True), *(cell("—") for _ in range(4)), result(FAIL)]
        m = materials.get(j.heat)
        wdocs = src(w, "wps", j.wps, w.pqr or "")
        if not w.pqr:
            once("S-WPS-03", FAIL, j.wps, f"{j.wps} names no supporting PQR.", clause("ASME IX QW-200.2"),
                 f"Upload the PQR supporting {j.wps}.", wdocs, ev=evid(w))
        if w.p_no is None:
            once("S-WPS-02", WARN, f"{j.wps} P-No.", f"{j.wps} does not state the base metal P-Number.",
                 clause("ASME IX QW-403"), f"Add the P-Number to {j.wps}.", wdocs, ev=evid(w))
        if w.t_min_mm is None or w.t_max_mm is None:
            once("S-WPS-02", WARN, f"{j.wps} thickness", f"{j.wps} does not state its qualified thickness range.",
                 clause("ASME IX Table QW-451.1"), f"Add the thickness range qualified by the PQR to {j.wps}.", wdocs, ev=evid(w))
        p_ok = m is None or m.p_no is None or w.p_no is None or w.p_no == m.p_no
        t_ok = j.thickness_mm is None or w.t_min_mm is None or w.t_max_mm is None or w.t_min_mm <= j.thickness_mm <= w.t_max_mm
        pw_ok = not pwht[j.id][0] or bool(w.pwht)
        sour_hv = hv_limit is not None and j.pressure
        h_ok = not sour_hv or (w.hardness_hv10 is not None and w.hardness_hv10 <= hv_limit)
        cv_ok = not has("IMPACT") or not j.pressure or (w.impact_temp_c is not None and w.impact_temp_c <= mdmt)
        if not p_ok:
            find("X-03", FAIL, j.id, f"{j.id}: {j.wps} ({w.pqr}) qualifies P-No.{w.p_no}; the material is "
                 f"P-No.{m.p_no if m else '?'}.", clause("ASME IX QW-403.11, QW-424"),
                 f"Use a WPS whose PQR covers P-No.{m.p_no if m else '?'}.", wdocs + docs("mtc", j.heat), ev=evid(w, j, m))
        if not t_ok:
            find("X-04", FAIL, j.id, f"{j.id}: {j.thickness_mm:g} mm is outside the {j.wps} range "
                 f"{w.t_min_mm:g}–{w.t_max_mm:g} mm.", clause("ASME IX Table QW-451.1"),
                 f"Use a WPS qualified for {j.thickness_mm:g} mm.", wdocs + docs("drawing"), ev=evid(w, j))
        if not h_ok:
            find("X-10", FAIL, j.id, f"{j.id}: no PQR hardness survey ({w.pqr or j.wps}); required for sour service." if w.hardness_hv10
                 is None else f"{j.id}: {w.pqr} hardness {w.hardness_hv10:g} HV10 exceeds the sour-service limit "
                 f"of {hv_limit} HV10.", "ISO 15156-2, ISO 17945",
                 "Provide a PQR hardness survey within the limit, or add PWHT.", wdocs, ev=evid(w))
        if not cv_ok:
            find("X-09", FAIL, f"{j.id} PQR", f"{j.id}: {w.pqr or j.wps} has no impact test; MDMT is {mdmt:g} °C." if
                 w.impact_temp_c is None else f"{j.id}: {w.pqr} impact test at {w.impact_temp_c:g} °C is warmer than MDMT "
                 f"{mdmt:g} °C.", clause("UCS-67, ASME IX QW-170"), "Qualify a PQR with Charpy tests at or below MDMT.", wdocs, ev=evid(w))
        rng = "not stated" if w.t_min_mm is None or w.t_max_mm is None else f"{w.t_min_mm:g}–{w.t_max_mm:g}"
        return [cell(j.id, bold=True), cell(f"{j.wps} / {w.pqr or 'no PQR'}"),
                cell(f"P{(m.p_no if m else None) or '?'} → P{w.p_no or '?'}", ok(p_ok)),
                cell(f"{num(j.thickness_mm)} in {rng}", ok(t_ok)),
                cell("Qualified" if w.pwht else "None", ok(pw_ok)),
                cell(num(w.hardness_hv10, " HV10") if sour_hv else "N/A", ok(h_ok)),
                result(PASS if p_ok and t_ok and pw_ok and h_ok and cv_ok else FAIL)]

    sections.append(Section(
        "wps", "WPS Review",
        f"Essential variables per {'ASME IX QW-250' if g.asme else g.qual}, checked against each joint on the welding drawing.",
        ["Joint", "WPS / PQR", "P-No.", "Thickness", "PWHT", "Hardness", "Result"],
        [wps_row(j) for j in joints] if {"wps", "drawing"} <= present else None, "WPS and welding drawing are needed."))

    # WPQ, per joint (X-06 qualification, X-07 continuity)
    def welder_check(j: Joint, welder: str, on: date, as_built: bool) -> tuple[list[Finding], list[Cell]]:
        on = on or today
        q = dossier.welders.get(welder) if welder else None
        w = dossier.procedures.get(j.wps) if j.wps else None
        rule_q, item = ("X-13", f"{j.id} (as-built)") if as_built else ("X-06", j.id)
        was = "was" if as_built else "is"
        when = f" on {on:%d %b %Y} when {j.id} was welded" if as_built else ""
        if not welder:
            return [Finding(rule_q, FAIL, item, f"{j.id}: no welder is recorded.", clause("ASME IX QW-301"),
                            f"Record the welder of {j.id}.", docs("asbuilt" if as_built else "drawing"), evidence=evid(j, *log_ev(j.id)))], \
                [cell("None", "reject", True), *(cell("—") for _ in range(5))]
        if q is None:
            return [Finding(rule_q, FAIL, item, f"Welder {welder} {was} not qualified{when}: no WPQ on file.",
                            clause("ASME IX QW-301"), f"Provide the WPQ of welder {welder}, or re-weld {j.id} with a "
                            "qualified welder.", docs("asbuilt" if as_built else "drawing"), evidence=evid(j, *log_ev(j.id)))], \
                [cell(f"Welder {welder}", "reject", True), *(cell("—") for _ in range(5))]
        processes = w.processes if w else ()
        pr_ok = all(p in q.processes for p in processes)
        if j.position is None:
            # PRD edge case: no position on the weld map → all positions assumed, with a warning.
            once("S-DRW-01", WARN, "Weld map positions", "Weld map gives no welding positions; all positions assumed (6G / 4F).", clause("ASME IX Table QW-461.9"),
                 "Add the production position of each joint to the weld map.", docs("drawing"), ev=evid(dossier.drawing_evidence))
        need = POSITIONS.get(j.position or "", "") or "FHVO"  # no position on the map: all positions
        quals = q.fillet if j.kind == "fillet" else q.groove
        po_ok = all(x in quals for x in need)
        t_ok = q.t_max_mm is None or j.thickness_mm is None or j.thickness_mm <= q.t_max_mm
        # QW-452.3 / QW-461.9: a plate test qualifies pipe of 610 mm OD and over only.
        od_min = PLATE_TEST_MIN_OD_MM if q.test_form == "plate" else q.od_min_mm
        d_ok = not j.od_mm or not od_min or j.od_mm >= od_min
        expired = q.valid_until is not None and on > q.valid_until
        days = (on - q.last_weld).days if q.last_weld else None
        c_ok = not expired and (days <= CONTINUITY_DAYS if days is not None else q.continuity_ok is not False)
        qdocs = src(q, "wpq", q.id, welder)
        out: list[Finding] = []
        if not po_ok:
            pos = j.position or "all positions"
            out.append(Finding(rule_q, FAIL, item, f"Welder {welder} ({q.id}, {q.test}) {was} not qualified for "
                               f"{', '.join(POSITION_NAMES[x] for x in need)} {j.kind} welding ({pos}){when}.",
                               clause("ASME IX Table QW-461.9"),
                               f"Assign a welder qualified for {pos}, or requalify welder {welder} in {pos}.",
                               qdocs + docs("drawing"), evidence=evid(q, j, *(log_ev(j.id) if as_built else []))))
        elif not pr_ok:
            out.append(Finding(rule_q, FAIL, item, f"Welder {welder} {was} not qualified for {' + '.join(processes)}{when}.",
                               clause("ASME IX QW-351"), f"Assign a welder qualified for {' + '.join(processes)}.", qdocs, evidence=evid(q, j, *(log_ev(j.id) if as_built else []))))
        elif not t_ok:
            out.append(Finding(rule_q, FAIL, item, f"{j.id}: {j.thickness_mm:g} mm exceeds the {q.t_max_mm:g} mm qualified "
                               f"for welder {welder}{when}.", clause("ASME IX QW-452.1"),
                               f"Assign a welder qualified for {j.thickness_mm:g} mm.", qdocs, evidence=evid(q, j, *(log_ev(j.id) if as_built else []))))
        elif not d_ok:
            out.append(Finding(rule_q, FAIL, item, f"{j.id}: pipe OD {j.od_mm:g} mm is below the {od_min:g} mm qualified "
                               f"for welder {welder}{when}" + (" (plate test)." if q.test_form == "plate" else "."),
                               clause("ASME IX QW-452.3, Table QW-461.9"),
                               f"Assign a welder qualified for OD {j.od_mm:g} mm.", qdocs, evidence=evid(q, j, *(log_ev(j.id) if as_built else []))))
        if expired:
            out.append(Finding("X-07", FAIL, item, f"Welder {welder} qualification ({q.id}) expired {q.valid_until:%d %b %Y}"
                               + (f", before the weld date {on:%d %b %Y}." if as_built else "."),
                               clause("ASME IX QW-322"), f"Requalify welder {welder}, or assign a qualified welder.", qdocs, evidence=evid(q)))
        elif not c_ok:
            out.append(Finding("X-07", FAIL, item, f"Welder {welder} continuity lapsed: last use {q.last_weld:%d %b %Y}, "
                               f"{days} days before {'the weld date' if as_built else 'the assessment date'}." if days is not None
                               else f"Welder {welder}: continuity is not maintained.",
                               clause("ASME IX QW-322.1"),
                               f"Provide a continuity record within 6 months, or requalify welder {welder}.", qdocs, evidence=evid(q)))
        cont = (f"Expired {q.valid_until:%d %b %Y}" if expired else f"{days} days" if days is not None
                else "Maintained" if q.continuity_ok else "Not recorded")
        cells = [cell(f"{welder} · {q.id}", bold=True), cell(" + ".join(processes) or "—", ok(pr_ok)),
                 cell(f"{j.position or 'all'} ({''.join(quals) or '—'})", ok(po_ok)),
                 cell("Unlimited" if q.t_max_mm is None else f"≤ {q.t_max_mm:g} mm", ok(t_ok)),
                 cell(f"{j.od_mm:g} ≥ {od_min:g}" if j.od_mm and od_min else "N/A", ok(d_ok)),
                 cell(cont, ok(c_ok))]
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
            find(rule_id, status, label, f"{need}: {text or 'not recorded'}; limit {limit}.", ref, fix, docs(slot))
        rows.append([cell(label, bold=True), cell(need), cell(limit),
                     cell(text if have else pending_text, "ink" if have else "muted"), result(status)])

    max_hv = inf if any(p.hardness_hv10 is None for p in procs) else max((p.hardness_hv10 for p in procs), default=0)
    hv_text = ", ".join(f"{p.pqr or p.id}: {num(p.hardness_hv10, ' HV10')}" for p in procs)
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
                 ", ".join(f"{p.pqr or p.id} @ {num(p.impact_temp_c, ' °C')}" for p in procs),
                 all(p.impact_temp_c is not None and p.impact_temp_c <= mdmt for p in procs),
                 "WPS pending", clause("UCS-67, ASME IX QW-170"), "Qualify a PQR with Charpy tests at or below MDMT.", "wps")
    if has("ISO3834"):
        # No certificate slot yet, so this needs a reviewer decision until one can be submitted.
        evidence("S-SUP-01", "ISO 3834-2", "Manufacturer certification, welding coordinator (ISO 14731)", "Certificate on file",
                 True, "Not in submitted documents", None, "", "ISO 3834-2", "Attach the ISO 3834-2 certificate.", "wps")
    if has("EXC3"):
        evidence("S-SUP-02", "EN 1090-2 EXC3", "WPS qualified by procedure test", "ISO 15614-1", have_wps,
                 ", ".join(p.pqr or f"{p.id}: no PQR" for p in procs), all(p.pqr for p in procs), "WPS pending", "EN 1090-2 §7.4.1",
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
                 ", ".join(f"{p.pqr or p.id} tested @ {num(p.impact_temp_c, ' °C')}" for p in procs),
                 all(p.impact_temp_c is not None and p.impact_temp_c <= -18 for p in procs),
                 "WPS pending", "AWS D1.8 §6.3", "Use filler metal with 27 J at -18 °C.", "wps")
    if rows:
        sections.append(Section("supp", "Supplementary Requirements", "Selected in addition to the governing standard.",
                                ["Standard", "Requirement", "Limit", "Evidence", "Result"], rows))

    # As-built verification: what was done, checked against the plan and the governing standard.
    if mode == "AS-BUILT" and joints:
        asb_docs = docs("asbuilt")

        # X-13 weld log (actual welder on the weld date, WPS used) and X-14 heats welded
        def weld_docs(jid: str) -> list[str]:
            a = dossier.as_built.get(jid)
            return list(a.sources) if a and a.sources else asb_docs

        on_map = {j.id for j in joints}
        for jid in dossier.as_built:
            if jid not in on_map:
                find("X-13", FAIL, f"{jid} (as-built)", f"{jid} welded but not on the weld map; no NDE or PWHT planned.", "QC system", f"Add {jid} to the weld map with its NDE and PWHT, or explain "
                     "the extra weld with an NCR.", weld_docs(jid) + docs("drawing"), ev=evid(*log_ev(jid)))

        def weld_log_row(j: Joint) -> list[Cell]:
            a = dossier.as_built.get(j.id)
            if a is None:
                find("X-13", FAIL, f"{j.id} (as-built)", f"{j.id} on the weld map but not in the weld log.",
                     "QC system", f"Add {j.id} to the weld log with welder, date and WPS.", asb_docs, ev=evid(j))
                return [cell(j.id, bold=True), cell(j.welder or "—"), cell("—", "reject"), *(cell("—") for _ in range(4)), result(FAIL)]
            out, _ = welder_check(j, a.welder, a.weld_date, as_built=True)
            # The planned welder's qualification is already X-06; only a continuity result the plan did not show is new.
            planned_x07 = any(f.rule_id == "X-07" and f.item == j.id for f in findings)
            out = [f for f in out if a.welder != j.welder or (f.rule_id == "X-07" and not planned_x07)]
            findings.extend(out)
            w_used = dossier.procedures.get(a.wps)
            cur_ok = a.current_a is None or not w_used or not w_used.current_a or (
                w_used.current_a[0] <= a.current_a <= w_used.current_a[1])
            if not cur_ok:
                find("S-ASB-01", FAIL, f"{j.id} (as-built)", f"{j.id} was welded at {a.current_a:g} A; {a.wps} allows "
                     f"{w_used.current_a[0]:g}–{w_used.current_a[1]:g} A.", clause("ASME IX QW-409, WPS", "WPS"),
                     f"Raise an NCR for {j.id}: re-qualify the procedure for the current used, or cut out and re-weld.",
                     weld_docs(j.id) + src(w_used, "wps", a.wps), ev=evid(*log_ev(j.id), (w_used, "current")))
            conflict = len({frozenset(h) for h in a.record_heats.values()}) > 1
            if conflict:
                listed = "; ".join(f"{re.sub(r'^.*[(](.*)[)]$', r'\1', name)} {' + '.join(h)}" for name, h in a.record_heats.items())
                find("X-14", FAIL, f"{j.id} heats", f"{j.id}: heat records disagree ({listed}).",
                     "UG-77, UG-93" if g.asme else "Material traceability",
                     f"Verify the hard-stamped heat numbers at {j.id} and correct the record.", weld_docs(j.id), ev=evid(*log_ev(j.id)))
            wps_ok = a.wps == j.wps or bool(a.deviation)
            if not wps_ok:
                find("X-13", FAIL, f"{j.id} (as-built)", f"{j.id} was welded with {a.wps}; the plan assigns {j.wps} and no "
                     "deviation is recorded.", "QC system", f"Record an approved deviation (NCR) or re-qualify {j.id}.",
                     weld_docs(j.id), ev=evid(*log_ev(j.id)))
            w = dossier.procedures.get(a.wps)
            heats_ok = True
            heats_seen = dict.fromkeys(h for hs in (a.record_heats.values() or [a.heats]) for h in hs) or dict.fromkeys(a.heats)
            for h in heats_seen:
                m = materials.get(h)
                if m is None:
                    heats_ok = False
                    find("X-14", FAIL, f"{j.id} heat {h}", f"Heat {h} (welded at {j.id}) has no mill certificate.",
                         "UG-77, UG-93" if g.asme else "Material traceability",
                         f"Upload the EN 10204 3.1 certificate for heat {h}, or replace the material.", weld_docs(j.id), ev=evid(*log_ev(j.id)))
                elif w and m.p_no and w.p_no and m.p_no != w.p_no:
                    heats_ok = False
                    find("X-14", FAIL, f"{j.id} heat {h}", f"Heat {h} is P-No.{m.p_no}; {a.wps} ({w.pqr}) qualifies "
                         f"P-No.{w.p_no} only.", clause("ASME IX QW-403.11"), f"Use a WPS whose PQR covers P-No.{m.p_no}.",
                         weld_docs(j.id) + src(m, "mtc", h), ev=evid(*log_ev(j.id), m))
            changed = a.welder != j.welder
            heats_ok = heats_ok and not conflict
            passed = not out and wps_ok and heats_ok and cur_ok
            return [cell(j.id, bold=True), cell(j.welder or "—"), cell(a.welder or "—", "reject" if changed else "ink", changed),
                    cell(f"{a.weld_date:%d %b %Y}" if a.weld_date else "—"),
                    cell((a.wps or "—") + (f" ({a.deviation})" if a.deviation else "") +
                         (f" · {a.current_a:g} A" if a.current_a is not None else ""), ok(wps_ok and cur_ok)),
                    cell(" + ".join(heats_seen) or "—", ok(heats_ok)), cell("Yes" if not out else "No", ok(not out)),
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
                find("X-15", FAIL, f"{jid} (as-built)", f"{jid}: PWHT required ({basis[0].lower() + basis[1:]}); no PWHT record.",
                     clause("UCS-56(d), Table UCS-56-1", g.clause), f"Provide the PWHT chart and load list covering {jid}.",
                     weld_docs(jid), ev=evid(by_joint.get(jid), *log_ev(jid)))
                pwht_rows.append([cell("—"), cell(jid, "reject", True), *(cell("—") for _ in range(4)), result(FAIL)])
        for c in dossier.pwht_charts:
            load = [by_joint[jid] for jid in c.joints if jid in by_joint]
            t = max((jj.thickness_mm or 0 for jj in load), default=0)
            hold_req = max(15.0, 60 * t / 25)
            soak_min = g.soak_min_c
            bands = [dossier.procedures[jj.wps].pwht_band_c for jj in load
                     if jj.wps in dossier.procedures and dossier.procedures[jj.wps].pwht_band_c]
            lo = max([soak_min or 0, *(b[0] for b in bands)])
            hi = min([b[1] for b in bands], default=None)
            soak_ok = c.soak_c is not None and c.soak_c >= lo and (hi is None or c.soak_c <= hi)
            hold_ok = c.hold_min is not None and c.hold_min >= hold_req
            heat_max = max(56.0, min(222.0, 222 * 25 / t)) if t else 222.0
            cool_max = max(56.0, min(278.0, 278 * 25 / t)) if t else 278.0
            rates_ok = not g.rate_limits or c.heat_rate_c_per_h is None or c.cool_rate_c_per_h is None or (
                c.heat_rate_c_per_h <= heat_max and c.cool_rate_c_per_h <= cool_max)
            item = f"PWHT {c.load_id}"
            band = f"{lo:g}–{hi:g} °C" if hi is not None else f"≥ {lo:g} °C"
            if not soak_ok:
                find("X-15", FAIL, item, f"Load {c.load_id} soaked at {num(c.soak_c, ' °C')}; required {band} (governing standard "
                     "and WPS band).", clause("Table UCS-56-1; ASME IX QW-407", g.clause),
                     "Repeat the PWHT within the qualified band.", asb_docs, ev=evid(c))
            if not hold_ok:
                find("X-15", FAIL, item, f"Load {c.load_id} held {num(c.hold_min, ' min')}; {hold_req:g} min required for "
                     f"{t:g} mm (1 h per 25 mm, 15 min minimum).", clause("Table UCS-56-1", g.clause),
                     "Extend the hold time and record a new chart.", asb_docs, ev=evid(c))
            if not rates_ok:
                find("X-15", FAIL, item, f"Load {c.load_id} heated at {c.heat_rate_c_per_h:g} °C/h and cooled at "
                     f"{c.cool_rate_c_per_h:g} °C/h above 425 °C; limits for {t:g} mm are {heat_max:.0f} and {cool_max:.0f} °C/h.",
                     clause("UCS-56(d)"), "Repeat the PWHT within the rate limits.", asb_docs, ev=evid(c))
            pwht_rows.append([
                cell(c.load_id, bold=True), cell(", ".join(c.joints)), cell(f"{num(c.soak_c, ' °C')} (req. {band})", ok(soak_ok)),
                cell(f"{num(c.hold_min, ' min')} (req. {hold_req:g})", ok(hold_ok)),
                cell(f"{num(c.heat_rate_c_per_h, '')} / {num(c.cool_rate_c_per_h, '')} °C/h" +
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
            if g.full_rt_over_mm and j.pressure and j.kind == "groove" and (j.thickness_mm or 0) > g.full_rt_over_mm:
                required["RT"] = 100.0
                code_note = f"RT 100% ({j.thickness_mm:g} mm > {g.full_rt_over_mm:g} mm)"
            reports = [r for r in dossier.nde_reports if r.joint == j.id]
            done: dict[str, float] = {}
            for r in reports:
                done[r.method] = done.get(r.method, 0) + (100.0 if r.extent_pct is None else r.extent_pct)
            short = {m: p for m, p in required.items() if done.get(m, 0) < p}
            rejected = [r for r in reports if r.result == "REJECT"]
            for r in reports:
                if r.result is None:
                    find("X-16", WARN, f"{j.id} {r.report_no}", f"{j.id}: {r.report_no} states no result.",
                         clause("ASME V", g.nde), f"Have {r.report_no} completed with an accept / reject result.", [r.source] if r.source else asb_docs, ev=evid(r))
                if r.drawing_rev and dossier.drawing_rev and _norm(r.drawing_rev).removeprefix("REV") != _norm(dossier.drawing_rev).removeprefix("REV"):
                    find("X-22", WARN, f"{r.report_no} revision", f"{r.report_no} refers to drawing revision "
                         f"{r.drawing_rev}; the submitted drawing is revision {dossier.drawing_rev}.", "QC system",
                         f"Confirm {r.report_no} was examined to the current revision, or re-issue it.",
                         [r.source] if r.source else asb_docs, ev=evid(r, dossier.drawing_evidence))
            unsigned = [r for r in reports if r.level not in ("II", "III")]
            ndocs = [r.source for r in reports if r.source] or weld_docs(j.id)
            for m, p in short.items():
                why = "required by the code" if code_note and m == "RT" and planned.get("RT", 0) < 100 else "planned"
                find("X-16", FAIL, j.id, f"{j.id}: {m} {p:g}% {why}, {done.get(m, 0):g}% performed.",
                     clause("UW-11, UW-52; ASME V", g.nde), f"Perform the missing {m} on {j.id} and upload the report.", ndocs, ev=evid(j, *reports))
            for r in rejected:
                find("X-16", FAIL, j.id, f"{j.id}: {r.report_no} ({r.method}) rejected; no repair or re-examination recorded.",
                     clause("UW-51, UW-52", g.nde), f"Repair {j.id} and re-examine it.", ndocs, ev=evid(r))
            for r in unsigned:
                find("X-16", FAIL, j.id, f"{j.id}: {r.report_no} not signed by a Level II or III technician.",
                     clause("ASME V T-120", g.nde), "Have the report signed by a Level II or III technician.", ndocs, ev=evid(r))
            passed = not short and not rejected and not unsigned
            fmt = lambda d: " + ".join(f"{m} {p:g}%" for m, p in d.items()) or "—"
            return [cell(j.id, bold=True), cell(fmt(planned)), cell(code_note or "As planned"), cell(fmt(done), ok(not short)),
                    cell(", ".join(f"{r.report_no} {r.result or '?'} L{r.level or '?'}" for r in reports) or "None",
                         ok(not rejected and not unsigned)), result(PASS if passed else FAIL)]

        sections.append(Section("asb_nde", "NDE Records", f"Extent performed against the plan and {g.nde}; every report "
                                "accepted and signed by Level II or III.",
                                ["Joint", "Planned", "Required by code", "Performed", "Reports", "Result"],
                                [nde_row(j) for j in joints]))

        # X-19 thickness and X-20 hydrotest
        test_rows: list[list[Cell]] = []
        for tr in dossier.thickness:
            t_ok = tr.required_mm is None or tr.measured_mm >= tr.required_mm
            if not t_ok:
                find("X-19", FAIL, tr.location, f"{tr.location} (heat {tr.heat}) measured {tr.measured_mm:g} mm, below the "
                     f"required {tr.required_mm:g} mm including corrosion allowance.", clause("UG-16, UG-22", "Design"),
                     "Request a design recalculation or replace the part.", asb_docs, ev=evid(tr))
            test_rows.append([cell(f"Thickness · {tr.location}", bold=True), cell(f"≥ {num(tr.required_mm)}"),
                              cell(f"{tr.measured_mm:g} mm", ok(t_ok)), result(PASS if t_ok else FAIL)])
        if g.hydro_factor:
            design_p = float(conditions.get("design_pressure_mpa") or 0)
            need = round(g.hydro_factor * design_p, 2)
            ht = dossier.hydrotest
            hclause = clause(g.hydro_clause)
            if ht is None:
                find("X-20", FAIL, "Hydrotest", "No hydrotest record.", hclause,
                     "Upload the hydrotest record with pressure, hold time and witness.", [], ev=[])
                test_rows.append([cell("Hydrotest", bold=True), cell(f"≥ {need:g} MPa"), cell("Not recorded", "reject"),
                                  result(FAIL)])
            else:
                p_ok = ht.pressure_mpa is not None and ht.pressure_mpa >= need
                w_ok = bool(ht.witness)
                temp_ok = ht.metal_temp_c is None or ht.metal_temp_c >= mdmt + 17
                if not p_ok:
                    find("X-20", FAIL, "Hydrotest", f"Test pressure {num(ht.pressure_mpa, ' MPa')} is below {need:g} MPa "
                         f"({g.hydro_factor:g} × design {design_p:g} MPa, stress ratio 1).", hclause,
                         "Repeat the hydrotest at the required pressure.", asb_docs, ev=evid(ht))
                if not w_ok:
                    find("X-20", WARN, "Hydrotest", "The hydrotest record has no witness signature.", hclause,
                         "Have the inspector sign the hydrotest record.", asb_docs, ev=evid(ht))
                if not temp_ok:
                    find("X-20", WARN, "Hydrotest", f"Metal temperature {ht.metal_temp_c:g} °C is below MDMT + 17 °C "
                         f"({mdmt + 17:g} °C) recommended during the test.", hclause,
                         "Confirm the brittle-fracture assessment for the test temperature.", asb_docs, ev=evid(ht))
                test_rows.append([cell("Hydrotest", bold=True),
                                  cell(f"≥ {need:g} MPa · witness · metal ≥ {mdmt + 17:g} °C"),
                                  cell(f"{num(ht.pressure_mpa, ' MPa')} · {num(ht.hold_min, ' min')} · {num(ht.metal_temp_c, ' °C')} · "
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
