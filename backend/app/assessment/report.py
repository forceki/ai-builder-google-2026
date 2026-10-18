"""Formal assessment report: a short, Pareto-ordered summary of one run, with evidence and documents as appendices."""

import re
from datetime import date, datetime

from app.assessment.catalog import GOVERNING, PROFILES, SECTORS, SLOTS, SUPP_BY_ID
from app.assessment.engine import ACCEPTABLE, FAIL, NOT_ACCEPTABLE, PASS, WARN, WITH_NOTES, standards_phrase

GOV_REFS = {"IACS Rec. 47 + class": ["IACS Rec. 47", "ABS"], "ISO 3834 + ISO 5817": ["ISO 3834-2", "ISO 5817"]}
SUPP_REFS = {"ISO3834": "ISO 3834-2", "EXC3": "EN 1090-2", "ISO5817B": "ISO 5817", "SEISMIC": "AWS D1.8",
             "MR0103": "MR0103", "MR0175": "MR0175"}


def report_no(project_no: str) -> str:
    digits = "".join(ch for ch in project_no.rsplit("-", 1)[-1] if ch.isdigit())
    return f"HBK-RR-{digits.zfill(3) or '000'}"


def _row(label: str, value, unit: str = "") -> dict:
    return {"label": label, "value": str(value), "unit": unit}


# Check area of each rule, for grouping findings and the Pareto table.
AREAS = [
    ("Material certificates", ("S-MTC", "X-01", "X-02")),
    ("Welding procedures (WPS / PQR)", ("S-WPS", "X-03", "X-04", "X-10", "X-12")),
    ("Welder qualification", ("X-06", "X-07")),
    ("PWHT", ("X-05", "X-15")),
    ("NDE", ("X-08", "X-11", "X-16", "X-22")),
    ("Traceability and weld records", ("X-13", "X-14", "S-ASB")),
    ("Impact testing", ("X-09",)),
    ("Thickness and pressure test", ("X-19", "X-20")),
    ("Drawing and design data", ("S-DRW",)),
    ("Supplementary requirements", ("S-SUP",)),
]


def area_of(rule_id: str) -> str:
    return next((name for name, prefixes in AREAS if rule_id.startswith(prefixes)), "Other")


def _item(item: str) -> str:
    return item.replace(" (as-built)", "")


def _group(findings: list[dict]) -> list[dict]:
    """One line per distinct problem: the same rule and wording on several joints becomes one line listing the joints."""
    groups: dict[tuple, dict] = {}
    for f in findings:
        text = re.sub(r"^[A-Z]+-\d+(?: \(as-built\))?: ", "", f["statement"])  # the item column names the joint
        key = (f["rule_id"], re.sub(r"\b[A-Z]+-\d+\b", "#", text))
        g = groups.setdefault(key, {"rule_id": f["rule_id"], "area": area_of(f["rule_id"]), "severity": f["severity"],
                                    "items": [], "finding": text, "requirement": f["clause"], "action": f["fix"],
                                    "evidence": [], "ids": [], "waived": f["status"] == "waived", "waiver": f.get("waiver")})
        if _item(f["item"]) not in g["items"]:
            g["items"].append(_item(f["item"]))
        g["ids"].append(f["id"])
        if len(g["items"]) > 1:  # several joints: the wording must not name just the first one
            g["finding"] = re.sub(rf"\b{re.escape(g['items'][0])}\b:? ?", "", g["finding"]).strip()
            g["finding"] = g["finding"][:1].upper() + g["finding"][1:]
        g["evidence"] += [e for e in f.get("evidence", []) if e not in g["evidence"]][:2]
    # Pareto: the problems that touch the most items first.
    return sorted(groups.values(), key=lambda g: (-len(g["items"]), g["area"], g["rule_id"]))


def build_report(*, project_no: str, project_name: str, prepared_by: str, conditions: dict, documents: dict[str, list[str]],
                 result: dict, run_number: int, run_at: datetime, condition_hash: str, rule_pack: str) -> dict:
    """The formal report of one stored run. `result` is the run's stored Assessment.as_dict()."""
    today: date = run_at.date()
    gov_id = conditions.get("governing") or "ASME VIII-1"
    g = GOVERNING.get(gov_id, GOVERNING["ASME VIII-1"])
    profile = PROFILES.get(conditions.get("profile", ""), PROFILES["plant-vessel"])
    supp = [SUPP_BY_ID[s] for s in conditions.get("supplementary", []) if s in SUPP_BY_ID]
    plan = result["mode"] == "PLAN"
    edition = conditions.get("edition", "")
    no = report_no(project_no)
    code = f"{standards_phrase(gov_id, g)}" + (f", {edition} edition" if edition else "")

    findings = result["findings"]
    issues = _group([f for f in findings if f["status"] == "open" and f["severity"] == FAIL])
    observations = _group([f for f in findings if f["status"] == "open" and f["severity"] != FAIL])
    waived = _group([f for f in findings if f["status"] == "waived"])
    for i, x in enumerate(issues + observations + waived, 1):
        x["no"] = i

    verdict = result["verdict"]
    n_nc, n_obs = len(issues), len(observations)
    conclusion = {
        ACCEPTABLE: "Acceptable. Fabrication may proceed; as-built verification is outstanding." if plan
        else "Acceptable for release.",
        WITH_NOTES: f"Acceptable subject to the {n_obs + len(waived)} observation(s) and waiver(s) listed.",
        NOT_ACCEPTABLE: f"Not acceptable. {n_nc} nonconformance(s) to be closed before "
                        f"{'fabrication' if plan else 'release'}.",
    }.get(verdict, "Incomplete. Required documents are missing.")

    # Results by check area, Pareto order: areas with the most nonconformances first.
    areas = []
    total = sum(len(x["items"]) for x in issues) or 1
    for name, _ in AREAS:
        nc = sum(len(x["items"]) for x in issues if x["area"] == name)
        obs = sum(len(x["items"]) for x in observations if x["area"] == name)
        if nc or obs:
            areas.append({"area": name, "nc": nc, "obs": obs, "result": FAIL if nc else WARN})
    areas.sort(key=lambda a: (-a["nc"], -a["obs"]))
    cum = 0
    for a in areas:
        cum += a["nc"]
        a["cum_pct"] = round(100 * cum / total) if a["nc"] else None
    checked = {area_of(f["rule_id"]) for f in findings} | {a["area"] for a in areas}
    clean = [c["label"] for c in result["criteria"] if c["status"] == PASS]

    witness = ("Client / third-party inspector" if profile.sector == "mfg"
               else ("Navy inspector" if gov_id == "MIL-STD-1689" else "Class surveyor") if profile.sector == "ship"
               else "Authorized inspector")
    date_text = today.strftime("%d %b %Y")
    ref_keys = [*GOV_REFS.get(gov_id, [gov_id]), *(q.split(" Clause ")[0] for q in g.qual.split(" / ")),
                *(["ASME V", "ASME II"] if g.asme else []), *(SUPP_REFS[s.id] for s in supp if s.id in SUPP_REFS)]
    refs = [k.replace("MR0103", "NACE MR0103").replace("MR0175", "NACE MR0175") for k in dict.fromkeys(ref_keys)]

    return {
        "report_no": no,
        "mode": result["mode"],
        "title": "Welding Assessment Report",
        "subtitle": f"{'Plan review' if plan else 'As-built verification'} · {code}",
        "header": [
            _row("Project", f"{project_no} · {project_name}"),
            _row("Equipment", f"{profile.equipment} ({SECTORS[profile.sector]}, {profile.label})"),
            _row("Code", code),
            _row("Supplementary", ", ".join(s.label for s in supp) or "None"),
            _row("Design data", f"{conditions.get('design_pressure_mpa', '—')} MPa · {conditions.get('design_temp_c', '—')} °C · "
                                f"MDMT {conditions.get('mdmt_c', '—')} °C"),
            _row("Scope", f"{result['joints']} joints · {'plan review, before fabrication' if plan else 'as-built verification'}"),
            _row("Date", date_text),
            _row("Prepared by", prepared_by),
        ],
        "verdict": verdict,
        "verdict_tone": result["verdict_tone"],
        "conclusion": conclusion,
        "counts": {"nc": n_nc, "obs": n_obs, "waived": len(waived)},
        "issues": issues,
        "observations": observations,
        "waived": waived,
        "areas": areas,
        "clean_checks": clean if checked else [],
        "references": refs,
        "documents": [{"slot": next(s.label for s in SLOTS if s.id == slot), "files": names}
                      for slot, names in documents.items() if names],
        "approval": [
            {"role": "Prepared by", "name": prepared_by, "date": date_text},
            {"role": "Approved by", "name": "", "date": ""},
            {"role": witness, "name": "", "date": ""},
        ],
        "footer": f"Rule set {rule_pack} · run {run_number}, {run_at:%Y-%m-%d %H:%M} UTC · conditions {condition_hash}",
        "result": result,
    }
