"""The data an assessment runs on: materials, procedures, welder qualifications, joints and as-built records.

Built from the extracted documents (app.assessment.adapter); SAMPLE_DOSSIER is the made-up demo data used when a
project has only sample file names. Any value a document did not state is None, and the rules treat it as missing.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Evidence:
    """Where a value was read: file, 1-based page and box [ymin, xmin, ymax, xmax] scaled 0–1000."""

    file: str
    page: int
    box: tuple[int, int, int, int] | None = None
    label: str = ""


Evidences = dict[str, Evidence]  # "record" for the whole record; specific fields by name (e.g. "tensile")


@dataclass(frozen=True)
class Material:
    heat: str
    spec: str | None
    p_no: str | None  # from the spec via QW/QB-422; None for non-ASME grades
    thickness_mm: float | None
    condition: str | None
    cert_type: str | None  # EN 10204 type, e.g. "3.1"
    chemistry: dict[str, float]  # C, Mn, Cr, Mo, V, Ni, Cu in wt%
    impact_temp_c: float | None = None
    impact_j: float | None = None
    tensile_mpa: float | None = None
    tensile_min_mpa: float | None = None
    signed: bool | None = None
    source: str | None = None  # file the record was read from
    evidence: Evidences = field(default_factory=dict)


@dataclass(frozen=True)
class Procedure:  # WPS with its supporting PQR
    id: str
    pqr: str | None
    processes: tuple[str, ...]
    p_no: str | None
    t_min_mm: float | None
    t_max_mm: float | None
    pwht: str | None  # qualified PWHT cycle, None = qualified without PWHT
    preheat_c: float | None
    hardness_hv10: float | None
    impact_temp_c: float | None
    pwht_band_c: tuple[float, float] | None = None  # qualified soak temperature range
    current_a: tuple[float, float] | None = None  # qualified welding current range
    pwht_joints: tuple[str, ...] = ()  # PWHT limited to these joints, empty = every joint welded to this WPS
    revision: str | None = None
    source: str | None = None
    evidence: Evidences = field(default_factory=dict)


@dataclass(frozen=True)
class WelderQual:  # WPQ
    welder: str
    id: str
    name: str
    processes: tuple[str, ...]
    test: str
    groove: tuple[str, ...]  # positions qualified: F, H, V, O
    fillet: tuple[str, ...]
    t_max_mm: float | None
    od_min_mm: float | None
    last_weld: date | None  # last use of the process (continuity); None = not recorded
    test_form: str = "pipe"  # pipe | plate; a plate test qualifies pipe of 610 mm OD and over only
    valid_until: date | None = None
    continuity_ok: bool | None = None  # document states continuity is maintained
    source: str | None = None
    evidence: Evidences = field(default_factory=dict)


@dataclass(frozen=True)
class Joint:
    id: str
    desc: str
    heat: str | None  # governing heat (first side with a certificate)
    thickness_mm: float | None
    od_mm: float | None
    position: str | None  # 1G…6G, 1F…4F; None = not on the drawing (all positions assumed)
    kind: str  # groove | fillet
    wps: str | None
    welder: str | None
    pressure: bool
    nde: str
    heats: tuple[str, ...] = ()
    pwht_required: bool | None = None  # the drawing / design asks for PWHT regardless of the code
    evidence: Evidences = field(default_factory=dict)


@dataclass(frozen=True)
class AsBuilt:  # one row of the as-built weld log
    welder: str
    wps: str
    heats: tuple[str, ...]  # heat number on each side of the joint
    weld_date: date | None = date(2026, 10, 12)
    deviation: str | None = None  # NCR / concession reference when the WPS differs from the plan
    current_a: float | None = None
    record_heats: dict[str, tuple[str, ...]] = field(default_factory=dict)  # heats per source record, for conflicts
    sources: tuple[str, ...] = ()  # files that record this weld
    evidence: Evidences = field(default_factory=dict)


@dataclass(frozen=True)
class PwhtChart:  # one furnace or local PWHT load
    load_id: str
    joints: tuple[str, ...]
    soak_c: float | None
    hold_min: float | None
    heat_rate_c_per_h: float | None  # above 425 °C
    cool_rate_c_per_h: float | None  # above 425 °C
    evidence: Evidences = field(default_factory=dict)


@dataclass(frozen=True)
class NdeReport:
    report_no: str
    joint: str
    method: str  # RT | UT | MT | PT | VT
    extent_pct: float | None
    result: str | None  # ACCEPT | REJECT
    level: str | None  # signing technician's level: II, III; None = unsigned
    drawing_rev: str | None = None
    source: str | None = None
    evidence: Evidences = field(default_factory=dict)


@dataclass(frozen=True)
class ThicknessReading:
    location: str
    heat: str | None
    measured_mm: float
    required_mm: float | None  # design minimum plus corrosion allowance, from the drawing
    evidence: Evidences = field(default_factory=dict)


@dataclass(frozen=True)
class Hydrotest:
    pressure_mpa: float | None
    hold_min: float | None
    metal_temp_c: float | None
    witness: str | None
    evidence: Evidences = field(default_factory=dict)


@dataclass(frozen=True)
class Dossier:
    materials: list[Material] = field(default_factory=list)
    procedures: dict[str, Procedure] = field(default_factory=dict)
    welders: dict[str, WelderQual] = field(default_factory=dict)
    joints: list[Joint] = field(default_factory=list)
    as_built: dict[str, AsBuilt] = field(default_factory=dict)
    pwht_charts: list[PwhtChart] = field(default_factory=list)
    nde_reports: list[NdeReport] = field(default_factory=list)
    thickness: list[ThicknessReading] = field(default_factory=list)
    hydrotest: Hydrotest | None = None
    drawing_no: str | None = None
    drawing_rev: str | None = None
    design_pressure_mpa: float | None = None
    drawing_evidence: Evidence | None = None  # the drawing's title block


SAMPLE_DOSSIER = Dossier(
    materials=[
        Material("4A7721", "SA-516 Gr.70", "1", 40, "Normalized", "3.1",
                 {"C": .18, "Mn": 1.10, "Cr": .02, "Mo": .01, "V": .002, "Ni": .02, "Cu": .03}, -29, 62),
        Material("5B2210", "SA-106 Gr.B", "1", 6.02, "As-rolled", "3.1",
                 {"C": .20, "Mn": .95, "Cr": .03, "Mo": .01, "V": .001, "Ni": .03, "Cu": .05}),
        Material("3C0954", "S355J2+N", "1", 12, "Normalized", "3.1",
                 {"C": .17, "Mn": 1.40, "Cr": .03, "Mo": .01, "V": .003, "Ni": .04, "Cu": .06}, -20, 48),
    ],
    procedures={
        "WPS-07": Procedure("WPS-07", "PQR-07", ("GTAW", "SMAW"), "1", 5, 50, "620 ± 15 °C · 1 h per 25 mm", 95, 208, -29,
                            (605, 635)),
        "WPS-09": Procedure("WPS-09", "PQR-09", ("FCAW",), "1", 5, 20, None, 10, 236, -20),
    },
    welders={
        "118": WelderQual("118", "WPQ-118", "A. Santoso", ("GTAW", "SMAW"), '6G pipe 6" · t 14.3 mm',
                          ("F", "H", "V", "O"), ("F", "H", "V", "O"), None, 73, date(2026, 9, 30)),
        "204": WelderQual("204", "WPQ-204", "R. Wibowo", ("FCAW",), "2G plate · t 10 mm",
                          ("F", "H"), ("F", "H"), 20, None, date(2026, 8, 14), "plate"),
    },
    joints=[
        Joint("W-11", "Shell long seam", "4A7721", 40, None, "3G", "groove", "WPS-07", "118", True, "RT 100%"),
        Joint("W-12", "Nozzle N1 to shell", "5B2210", 40, 114.3, "6G", "groove", "WPS-07", "118", True, "UT 100% + RT 10%"),
        Joint("W-14", "Shell circ seam", "4A7721", 40, None, "2G", "groove", "WPS-07", "118", True, "RT 100%"),
        Joint("W-17", "Skid beam fillet", "3C0954", 12, None, "2F", "fillet", "WPS-09", "204", False, "VT 100%"),
        Joint("W-22", "Skid beam fillet, overhead", "3C0954", 12, None, "4F", "fillet", "WPS-09", "204", False,
              "VT 100% + MT 10%"),
    ],
    as_built={
        "W-11": AsBuilt("118", "WPS-07", ("4A7721", "4A7721")),
        "W-12": AsBuilt("118", "WPS-07", ("5B2210", "4A7721")),
        "W-14": AsBuilt("131", "WPS-07", ("4A7721", "4A7721")),
        "W-17": AsBuilt("204", "WPS-09", ("3C0954", "3C0954")),
        "W-22": AsBuilt("204", "WPS-09", ("3C0954", "3C0961")),  # 3C0961 has no mill certificate
    },
    pwht_charts=[PwhtChart("L-01", ("W-11", "W-12", "W-14"), 618, 96, 120, 160)],
    nde_reports=[
        NdeReport("RT-019", "W-11", "RT", 100, "ACCEPT", "II"),
        NdeReport("UT-022", "W-12", "UT", 100, "ACCEPT", "II"),  # the planned RT 10% was not done
        NdeReport("RT-020", "W-14", "RT", 100, "ACCEPT", "II"),
        NdeReport("VT-031", "W-17", "VT", 100, "ACCEPT", "II"),
        NdeReport("VT-032", "W-22", "VT", 100, "ACCEPT", "II"),
        NdeReport("MT-033", "W-22", "MT", 10, "ACCEPT", "II"),
    ],
    thickness=[ThicknessReading("Shell course 1", "4A7721", 39.6, 36.2), ThicknessReading("Skid beam", "3C0954", 11.8, 10.5)],
    hydrotest=Hydrotest(2.1, 30, 15, "J. Hartono, Authorized Inspector"),
)


def _n(v, unit=" mm") -> str:
    return "?" if v is None else f"{v:g}{unit}"


def facts(dossier: Dossier, slot: str) -> list[str]:
    """One line per record, shown under a filled document slot."""
    if slot == "mtc":
        return [f"{m.heat} · {m.spec or '?'} · {_n(m.thickness_mm)} · P-No.{m.p_no or '?'}" for m in dossier.materials]
    if slot == "wps":
        return [f"{p.id} · {'+'.join(p.processes) or '?'} · "
                f"{'range not stated' if p.t_min_mm is None or p.t_max_mm is None else f'{p.t_min_mm:g}–{p.t_max_mm:g} mm'} · "
                f"{'PWHT' if p.pwht else 'no PWHT'}" for p in dossier.procedures.values()]
    if slot == "wpq":
        return [f"{q.welder} {q.name} · {'+'.join(q.processes) or '?'} · {q.test.split(' · ')[0]}" for q in dossier.welders.values()]
    if slot == "drawing":
        procs = sorted({j.wps for j in dossier.joints if j.wps})
        head = f"{dossier.drawing_no} rev {dossier.drawing_rev} · " if dossier.drawing_no else ""
        return [f"{head}{len(dossier.joints)} joints · {', '.join(j.id for j in dossier.joints)}",
                f"WPS used: {', '.join(procs) or 'not stated'}"]
    out = [f"Weld log: {len(dossier.as_built)} joints · welders, dates, heats"]
    out += [f"PWHT {c.load_id}: {', '.join(c.joints)} · {_n(c.soak_c, ' °C')} · {_n(c.hold_min, ' min')}" for c in dossier.pwht_charts]
    out += [f"NDE: {len(dossier.nde_reports)} reports" + (f" · thickness: {len(dossier.thickness)} readings" if dossier.thickness else "")]
    if dossier.hydrotest:
        out.append(f"Hydrotest: {_n(dossier.hydrotest.pressure_mpa, ' MPa')} · {_n(dossier.hydrotest.hold_min, ' min')}")
    return out
