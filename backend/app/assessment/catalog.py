"""Sectors, equipment types, governing standards, supplementary requirements and document slots.

Clause numbers and limits are summaries; an engineer must confirm them against the contract editions.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from math import inf

SECTORS = {"plant": "Plant", "ship": "Shipbuilding", "mfg": "Manufacturing"}


@dataclass(frozen=True)
class Profile:
    sector: str
    label: str
    governing: str  # default governing standard for this equipment type
    equipment: str


PROFILES: dict[str, Profile] = {
    "plant-vessel": Profile("plant", "Pressure vessel / skid", "ASME VIII-1", "Pressure vessel"),
    "plant-refinery": Profile("plant", "Oil & gas / refinery", "ASME B31.3", "Pressure vessel & process piping"),
    "plant-petrochem": Profile("plant", "Petrochemical", "ASME B31.3", "Pressure vessel & process piping"),
    "plant-power": Profile("plant", "Power generation", "ASME I", "Boiler & power piping"),
    "plant-pipeline": Profile("plant", "Pipeline", "API 1104", "Pipeline"),
    "ship-commercial": Profile("ship", "Commercial (class)", "IACS Rec. 47 + class", "Hull structure"),
    "ship-naval": Profile("ship", "Naval", "MIL-STD-1689", "Ship / submarine structure"),
    "mfg-structural": Profile("mfg", "Structural steel", "AWS D1.1", "Steel structure / frame"),
    "mfg-machinery": Profile("mfg", "Machinery & heavy equipment", "AWS D14.3", "Earthmoving / agricultural equipment"),
    "mfg-crane": Profile("mfg", "Cranes & material handling", "AWS D14.1", "Crane / lifting structure"),
    "mfg-rail": Profile("mfg", "Railway vehicles", "EN 15085", "Rail vehicle body / bogie"),
    "mfg-general": Profile("mfg", "General fabrication (ISO)", "ISO 3834 + ISO 5817", "Welded product"),
}
DEFAULT_PROFILE = {"plant": "plant-vessel", "ship": "ship-commercial", "mfg": "mfg-structural"}


@dataclass(frozen=True)
class Governing:
    sector: str
    qual: str  # welder and procedure qualification code
    nde: str
    # P-No.1 PWHT band (nominal thickness, mm): (no PWHT up to, exempt with >= 95 °C preheat up to).
    # Above the second value PWHT is mandatory; inf = never mandatory with preheat. None = the code does not mandate PWHT.
    pwht_mm: tuple[float, float] | None
    clause: str
    rule: str
    asme: bool = False
    # As-built limits (None = per contract / class, not checked by rule):
    soak_min_c: float | None = None  # P-No.1 minimum PWHT holding temperature
    rate_limits: bool = False  # heating/cooling rates above 425 °C limited (UCS-56(d) style)
    hydro_factor: float | None = None  # hydrotest pressure ≥ factor × design pressure (stress ratio 1)
    hydro_clause: str = ""
    full_rt_over_mm: float | None = None  # butt welds thicker than this need 100 % RT


GOVERNING: dict[str, Governing] = {
    "ASME VIII-1": Governing("plant", "ASME IX", "ASME V", (32, 38), "UCS-56, Table UCS-56-1",
                             "P-No.1 over 38 mm. 32 to 38 mm exempt only with preheat of 95 °C or more.", asme=True,
                             soak_min_c=595, rate_limits=True, hydro_factor=1.3, hydro_clause="UG-99",
                             full_rt_over_mm=38),
    # 2014+: P-No.1 exemptions in Table 331.1.3; not exempt when the designer or WPS specifies PWHT.
    "ASME B31.3": Governing("plant", "ASME IX", "ASME V", (25, inf), "Table 331.1.1, Table 331.1.3",
                            "P-No.1 not mandatory up to 25 mm; over 25 mm exempt with preheat of 95 °C or more.", asme=True,
                            soak_min_c=595, hydro_factor=1.5, hydro_clause="345.4.2"),
    # 2013+: aligned with VIII-1 UCS-56 for P-No.1.
    "ASME I": Governing("plant", "ASME IX", "ASME V", (32, 38), "PW-39, Table PW-39-1",
                        "P-No.1 over 38 mm. 32 to 38 mm exempt only with preheat of 95 °C or more.", asme=True,
                        soak_min_c=595, rate_limits=True, hydro_factor=1.5, hydro_clause="PG-99"),
    # Unverified for 2014+ editions, which list P-No.1 exemptions with carbon-content conditions; kept conservative.
    "ASME B31.1": Governing("plant", "ASME IX", "ASME V", (19, 19), "Table 132",
                            "P-No.1 over 19 mm (conservative; confirm the Table 132 exemptions of the edition).", asme=True,
                            soak_min_c=595, hydro_factor=1.5, hydro_clause="137.4"),
    "API 1104": Governing("plant", "API 1104", "API 1104 Sec. 11", None, "Company specification", "Not mandated by API 1104."),
    "IACS Rec. 47 + class": Governing("ship", "ISO 9606-1", "Class NDE plan", None, "Class rules",
                                      "Not mandated for hull structural steel."),
    "MIL-STD-1689": Governing("ship", "MIL-STD-1689", "MIL-STD-1689", None, "MIL-STD-1689", "Per base material class."),
    "AWS D1.1": Governing("mfg", "AWS D1.1 Clause 6", "AWS D1.1 Clause 8", None, "AWS D1.1 stress relief",
                          "Not mandated; required only by contract or design."),
    "EN 1090-2": Governing("mfg", "ISO 15614-1 / ISO 9606-1", "ISO 5817 per EXC", None, "EN 1011-2",
                           "Not mandated; per specification and EN 1011-2."),
    "AWS D14.1": Governing("mfg", "AWS D14.1", "AWS D14.1", None, "AWS D14.1", "Per specification."),
    "AWS D14.3": Governing("mfg", "AWS D14.3", "AWS D14.3", None, "AWS D14.3", "Per specification."),
    "EN 15085": Governing("mfg", "ISO 15614-1 / ISO 9606-1", "ISO 5817 per EN 15085-3", None, "EN 15085-4",
                          "Not mandated; per specification."),
    "ISO 3834 + ISO 5817": Governing("mfg", "ISO 15614-1 / ISO 9606-1", "ISO 5817", None, "EN 1011-2",
                                     "Not mandated; per specification and EN 1011-2."),
}


@dataclass(frozen=True)
class Supplementary:
    id: str
    label: str
    desc: str
    sectors: tuple[str, ...]


SUPPLEMENTARY: list[Supplementary] = [
    Supplementary("MR0103", "NACE MR0103 / ISO 17945", "Refinery sour service", ("plant",)),
    Supplementary("MR0175", "NACE MR0175 / ISO 15156", "Oil & gas sour service", ("plant",)),
    Supplementary("LETHAL", "Lethal service", "ASME VIII-1 UW-2(a)", ("plant",)),
    Supplementary("ISO3834", "ISO 3834-2", "Comprehensive welding quality", ("mfg", "ship")),
    Supplementary("EXC3", "EN 1090-2 EXC3", "Higher execution class", ("mfg",)),
    Supplementary("ISO5817B", "ISO 5817 level B", "Stringent imperfection limits", ("mfg", "ship")),
    Supplementary("FATIGUE", "Cyclically loaded", "AWS D1.1 fatigue provisions", ("mfg",)),
    Supplementary("SEISMIC", "AWS D1.8 seismic", "Demand-critical welds", ("mfg",)),
    Supplementary("IMPACT", "Impact tested", "Low-temperature toughness", ("plant", "ship", "mfg")),
]
SUPP_BY_ID = {s.id: s for s in SUPPLEMENTARY}


@dataclass(frozen=True)
class Slot:
    id: str
    label: str
    desc: str
    required: bool
    sample: tuple[str, ...]


SLOTS: list[Slot] = [
    Slot("mtc", "Mill certificate", "Grade, heat no., thickness, chemistry, impact test", False,
         ("MTC_4A7721.pdf", "MTC_5B2210.pdf", "MTC_3C0954.pdf")),
    Slot("wps", "WPS", "Welding procedure with its supporting PQR", False, ("WPS-07_PQR-07.pdf", "WPS-09_PQR-09.pdf")),
    Slot("wpq", "WPQ", "Welder performance qualification and continuity log", False, ("WPQ-118.pdf", "WPQ-204.pdf")),
    Slot("drawing", "Welding drawing", "Weld map: joints, WPS and welder assigned, NDE", False, ("HBK-PV-110_RevB_WeldMap.pdf",)),
    Slot("asbuilt", "As-built document", "Actual welders, PWHT charts, NDE done", False, ("ASB_PS-3_RevA.pdf",)),
    Slot("other", "Other documents", "Kept with the documents (e.g. a document index); not checked by the rules", False, ()),
]
SLOT_IDS = [s.id for s in SLOTS]

# What the assessment is for. Production: new work released for service, every welder must be qualified.
# Investigation: the equipment is already built and something failed; the welds can't be re-made, so welder
# qualification is background and the checks focus on material, PWHT / heat treatment, mechanical results and NDE.
PURPOSES = {
    "production": ("Production release", "New fabrication before it ships. Welder qualification is mandatory: without "
                   "a WPQ the work is deemed rejected."),
    "investigation": ("Failure investigation", "Equipment already built or in service. WPQ is optional; the checks look "
                      "for the cause in material, PWHT and heat treatment, mechanical results and NDE."),
}
DEFAULT_PURPOSE = "production"


def purpose_of(conditions: dict) -> str:
    p = conditions.get("purpose")
    return p if p in PURPOSES else DEFAULT_PURPOSE


def slot_required(slot: str, conditions: dict) -> bool:
    """Shown as REQUIRED: the WPQ in production. Missing, it raises a high alert and the run is deemed rejected."""
    return slot == "wpq" and purpose_of(conditions) == "production"


# Supplementary requirements that are about the material itself: without mill certificates they can't be shown.
MATERIAL_SUPP = {"IMPACT", "MR0103", "MR0175", "LETHAL"}


@dataclass(frozen=True)
class IfMissing:
    """What it means to release without a document, ranked by risk under the governing standard."""

    severity: str  # FAIL blocks release · WARN is a note for the reviewer
    risk: str  # HIGH | MEDIUM | LOW
    statement: str
    clause: str
    fix: str


def if_missing(slot: str, conditions: dict) -> IfMissing | None:
    gov_id = conditions.get("governing") or "ASME VIII-1"
    g = GOVERNING.get(gov_id, GOVERNING["ASME VIII-1"])
    supp = set(conditions.get("supplementary", []))
    if slot == "mtc":
        needs = sorted(SUPP_BY_ID[s].label for s in supp & MATERIAL_SUPP)
        clause = "UG-93 (material identification)" if gov_id == "ASME VIII-1" else (
            "Material certification per " + gov_id if g.asme else "EN 10204 3.1 per " + gov_id)
        if needs:
            return IfMissing("FAIL", "HIGH", f"No mill certificate submitted; {', '.join(needs)} can't be shown without the "
                             "material's test results.", clause, "Upload the EN 10204 3.1 certificates with the impact and "
                             "chemistry results.")
        return IfMissing("WARN", "LOW", "No mill certificate submitted; material grade, heats, P-No. and chemistry were "
                         "taken as listed on the drawing and not verified.", clause,
                         "Upload the EN 10204 3.1 certificates, or record why the material is accepted without them.")
    if slot == "wps":
        return IfMissing("FAIL", "HIGH", f"No WPS submitted; no joint can be shown to be welded to a procedure qualified "
                         f"per {g.qual}.", "ASME IX QW-200" if g.asme else g.qual,
                         "Upload the WPS and supporting PQR for every procedure on the weld map.")
    if slot == "wpq":
        if purpose_of(conditions) == "investigation":
            return IfMissing("INFO", "LOW", "No welder qualification submitted; not needed for a failure investigation, "
                             "the welds are already made. Welder qualification is not assessed.",
                             "ASME IX QW-300" if g.asme else g.qual, "Add the WPQs if a welder is a suspected cause.")
        return IfMissing("FAIL", "CRITICAL", f"HIGH ALERT: no welder qualification submitted. Production welds need "
                         f"qualified welders per {g.qual}; the work is deemed rejected until every WPQ is provided.",
                         "ASME IX QW-300" if g.asme else g.qual,
                         "Upload the WPQ and continuity record of every welder on the weld map.")
    if slot == "drawing":
        return IfMissing("FAIL", "HIGH", "No welding drawing submitted; the joints, their WPS and welder assignments and "
                         "the NDE extent can't be identified or verified.", f"{gov_id} weld map / QC system",
                         "Upload the weld map or welding drawing with its weld table.")
    if slot == "asbuilt":
        needed = ["weld log"]
        if g.pwht_mm or "LETHAL" in supp:
            needed.append("PWHT records where PWHT is required")
        needed.append(f"NDE reports ({g.nde})")
        if g.hydro_factor:
            needed.append(f"hydrotest record ({g.hydro_clause})")
        return IfMissing("FAIL", "HIGH", f"No as-built record submitted; release needs the {', '.join(needed)}.",
                         gov_id + (f" {g.hydro_clause}" if g.hydro_factor else ""),
                         "Upload the weld log, PWHT charts, NDE reports and test records of the finished work.")
    return None


EDITIONS = ["2023", "2021"]  # code editions the rules are written for; the newest is the default
RULE_PACK_VERSION = "RS-3.1"


def default_conditions() -> dict:
    return {"profile": "plant-vessel", "governing": "ASME VIII-1", "edition": EDITIONS[0], "supplementary": [],
            "design_pressure_mpa": 1.6, "design_temp_c": 210, "mdmt_c": -20, "upload_mode": "batch",
            "confirmed": False, "complete_set": False, "purpose": DEFAULT_PURPOSE}


def condition_hash(conditions: dict) -> str:
    """Identifies a condition set; the submission mode and the step-1 confirmation do not change any rule."""
    rule_inputs = {k: v for k, v in conditions.items() if k not in ("upload_mode", "confirmed")}
    rule_inputs["supplementary"] = sorted(rule_inputs.get("supplementary", []))
    return hashlib.sha256(json.dumps(rule_inputs, sort_keys=True).encode()).hexdigest()[:12]


def catalog() -> dict:
    """Everything the conditions step needs to render its choices."""
    return {
        "sectors": [{"id": k, "label": v, "default_profile": DEFAULT_PROFILE[k]} for k, v in SECTORS.items()],
        "profiles": [{"id": k, **asdict(p)} for k, p in PROFILES.items()],
        "governing": [{"id": k, **asdict(g), "pwht_mm": g.pwht_mm and [None if v == inf else v for v in g.pwht_mm]}
                      for k, g in GOVERNING.items()],
        "supplementary": [{**asdict(s), "sectors": list(s.sectors)} for s in SUPPLEMENTARY],
        "slots": [{**asdict(s), "sample": list(s.sample)} for s in SLOTS],
        "purposes": [{"id": k, "label": v[0], "desc": v[1]} for k, v in PURPOSES.items()],
        "editions": EDITIONS,
        "rule_pack": RULE_PACK_VERSION,
    }
