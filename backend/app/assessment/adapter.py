"""Turn extracted documents into the dossier the rules run on.

Identifiers are compared in a normal form so harmless formatting differences never become findings:
W01 = W-01 (weld), W409 = W-409 (welder), H-48213 = 48213 (heat). Values a document did not state stay None.
"""

import re
from dataclasses import dataclass
from datetime import date

from app.assessment.dossier import (
    AsBuilt,
    Dossier,
    Evidence,
    Hydrotest,
    Joint,
    Material,
    NdeReport,
    Procedure,
    PwhtChart,
    ThicknessReading,
    WelderQual,
)


@dataclass(frozen=True)
class ExtractedDoc:
    slot: str
    filename: str
    data: dict  # the slot schema's model_dump()


# Identifiers ---------------------------------------------------------------------------------------------------

def norm_id(value: str | None) -> str:
    """W01, W-01, w 01 → W-01; WPS07 → WPS-07. Letters, then the number without leading zeros, padded to 2."""
    if not value:
        return ""
    m = re.fullmatch(r"\s*([A-Za-z]+)[\s_-]*0*(\d+)\s*", value)
    if not m:
        return value.strip().upper()
    return f"{m.group(1).upper()}-{int(m.group(2)):02d}"


def norm_welder(value: str | None) -> str:
    if not value:
        return ""
    m = re.fullmatch(r"\s*([A-Za-z]*)[\s_-]*(\d+)\s*", value)
    return f"{m.group(1).upper()}-{m.group(2)}".lstrip("-") if m else value.strip().upper()


def norm_heat(value: str | None) -> str:
    """H-48213, 48213, ' 48213 ' → 48213; keeps letters that are part of the number (4A7721)."""
    if not value:
        return ""
    v = re.sub(r"[\s_-]", "", value.upper())
    v = re.sub(r"\(.*?\)", "", v)
    return v[1:] if re.fullmatch(r"H\d+", v) else v


def split_heats(value: str) -> list[str]:
    """'60231 (elbow) / 60232 (reducer)' → ['60231', '60232']."""
    return [norm_heat(h) for h in re.split(r"[/,;&]|\band\b", re.sub(r"\(.*?\)", "", value)) if norm_heat(h)]


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    v = value.strip()
    for pat, order in ((r"(\d{4})-(\d{1,2})-(\d{1,2})", "ymd"), (r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", "dmy")):
        m = re.search(pat, v)
        if m:
            a, b, c = (int(x) for x in m.groups())
            try:
                return date(a, b, c) if order == "ymd" else date(c, b, a)
            except ValueError:
                return None
    return None


# Material P-Numbers (ASME IX QW/QB-422), common carbon-steel grades -------------------------------------------

_GRADES = [  # (spec pattern after an optional SA-/A- prefix, P-No.)
    (r"106", "1"), (r"105", "1"), (r"234\s*WPB", "1"), (r"516", "1"), (r"53\b", "1"), (r"333", "1"),
    (r"350\s*LF2", "1"), (r"420\s*WPL6", "1"), (r"36\b", "1"), (r"572", "1"), (r"285", "1"),
    (r"335\s*P11", "4"), (r"335\s*P22", "5A"), (r"312", "8"), (r"240", "8"),
]
P_NUMBERS = [(rf"\b(?:A|SA|A/SA)[-\s]?{g}", p) for g, p in _GRADES] + [(r"API\s*5L", "1")]


def p_number(spec: str | None) -> str | None:
    if not spec:
        return None
    s = re.sub(r"(ASTM|ASME)\s*", "", spec.upper())
    s = "A" + s if re.match(r"^\d", s) else s
    return next((p for pat, p in P_NUMBERS if re.search(pat, s)), None)


def cert_type(value: str | None) -> str | None:
    if not value:
        return None
    m = re.search(r"([23])\.([12])", value)
    return f"{m.group(1)}.{m.group(2)}" if m else value.strip()


# Welder qualification ranges (QW-461.9, QW-452.1, QW-452.3) ----------------------------------------------------

# test position → (groove positions, fillet positions) qualified
QUALIFIED = {
    "1G": ("F", "F"), "2G": ("FH", "FH"), "3G": ("FV", "FHV"), "4G": ("FO", "FHO"),
    "5G": ("FVO", "FVO"), "6G": ("FHVO", "FHVO"), "2G+5G": ("FHVO", "FHVO"), "3G+4G": ("FVO", "FHVO"),
    "1F": ("", "F"), "2F": ("", "FH"), "3F": ("", "FHV"), "4F": ("", "FHO"), "5F": ("", "FHVO"),
}


def qualified_positions(test_position: str | None) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    if not test_position:
        return None
    key = re.sub(r"[\s&,]+", "+", test_position.upper()).replace("AND", "+")
    groove, fillet = QUALIFIED.get(key, QUALIFIED.get(key.split("+")[-1], ("", "")))
    return tuple(groove), tuple(fillet)


def diameter_min(test_od_mm: float | None) -> float | None:
    if test_od_mm is None:
        return None
    return test_od_mm if test_od_mm < 25 else 25.0 if test_od_mm <= 73 else 73.0


def thickness_max(test_t_mm: float | None) -> float | None:
    if test_t_mm is None:
        return None
    return None if test_t_mm >= 13 else 2 * test_t_mm


# Dossier ------------------------------------------------------------------------------------------------------

def _ev(filename: str, rec: dict, label: str, key: str = "box_2d") -> Evidence | None:
    page = rec.get("page")
    if not page:
        return None
    box = rec.get(key)
    box = tuple(max(0, min(1000, int(v))) for v in box) if isinstance(box, list) and len(box) == 4 else None
    if key != "box_2d" and box is None:
        return None  # a field without its own box falls back to the record's
    return Evidence(filename, int(page), box, label)


def _evs(filename: str, rec: dict, label: str, **fields: str) -> dict[str, Evidence]:
    """{"record": …, name: …} for the record and any field that has its own box (fields: name → box key)."""
    out = {"record": _ev(filename, rec, label)}
    for name, key in fields.items():
        out[name] = _ev(filename, rec, label, key)
    return {k: v for k, v in out.items() if v is not None}


def _range(lo: float | None, hi: float | None) -> tuple[float, float] | None:
    return (lo, hi) if lo is not None and hi is not None else None


def _nde_text(value: str | None) -> str:
    """'100 % radiography' / 'RT, 100 %' → 'RT 100%'."""
    if not value:
        return ""
    v = value.upper()
    out = []
    for method, words in (("RT", r"RT|RADIOGRAPH"), ("UT", r"UT|ULTRASONIC"), ("MT", r"MT|MAGNETIC"),
                          ("PT", r"PT|PENETRANT|DYE"), ("VT", r"VT|VISUAL")):
        m = re.search(rf"(?:(\d+(?:\.\d+)?)\s*%[^,;+]*?)?\b(?:{words})\w*\b(?:[^,;+\d]*?(\d+(?:\.\d+)?)\s*%)?", v)
        if m:
            pct = m.group(1) or m.group(2) or "100"
            out.append(f"{method} {float(pct):g}%")
    return " + ".join(out)


def build_dossier(docs: list[ExtractedDoc]) -> Dossier:
    by = {slot: [d for d in docs if d.slot == slot] for slot in ("mtc", "wps", "wpq", "drawing", "asbuilt")}

    materials: dict[str, Material] = {}
    for d in by["mtc"]:
        for h in d.data.get("heats", []):
            for heat in split_heats(h["heat_no"]):
                materials.setdefault(heat, Material(
                    heat=heat, spec=h.get("spec_grade"), p_no=p_number(h.get("spec_grade")),
                    thickness_mm=h.get("thickness_mm"), condition=h.get("condition"), cert_type=cert_type(h.get("cert_type")),
                    chemistry={e["symbol"].capitalize(): e["percent"] for e in h.get("chemistry", [])},
                    impact_temp_c=h.get("impact_temp_c"), impact_j=h.get("impact_avg_j"),
                    tensile_mpa=h.get("tensile_mpa"), tensile_min_mpa=h.get("tensile_min_mpa"), signed=h.get("signed"),
                    source=d.filename, evidence=_evs(d.filename, h, f"Certificate, heat {heat}",
                                                     tensile="tensile_box_2d", signature="signature_box_2d")))

    procedures: dict[str, Procedure] = {}
    for d in by["wps"]:
        for p in d.data.get("procedures", []):
            temp, tol = p.get("pwht_temp_c"), p.get("pwht_temp_tolerance_c")
            band = (temp - (tol or 15), temp + (tol or 15)) if temp is not None else None
            wid = norm_id(p["wps_no"])
            procedures[wid] = Procedure(
                id=wid, pqr=", ".join(p.get("pqr_nos") or []) or None, processes=tuple(x.upper() for x in p.get("processes", [])),
                p_no=(p.get("p_no") or "").replace("P-No.", "").strip() or None,
                t_min_mm=p.get("thickness_min_mm"), t_max_mm=p.get("thickness_max_mm"),
                pwht=(f"{temp:g} °C" + (f" · {p['pwht_hold_min']:g} min" if p.get("pwht_hold_min") else "")) if p.get("pwht") and temp
                else ("PWHT" if p.get("pwht") else None),
                preheat_c=p.get("preheat_min_c"), hardness_hv10=p.get("hardness_hv10"), impact_temp_c=p.get("impact_temp_c"),
                pwht_band_c=band if p.get("pwht") else None, current_a=_range(p.get("current_min_a"), p.get("current_max_a")),
                pwht_joints=tuple(norm_id(j) for j in p.get("pwht_joints", [])), revision=p.get("revision"), source=d.filename,
                evidence=_evs(d.filename, p, wid, current="current_box_2d", pwht="pwht_box_2d"))

    welders: dict[str, WelderQual] = {}
    for d in by["wpq"]:
        for q in d.data.get("welders", []):
            wid = norm_welder(q["welder_id"])
            listed = [x.upper() for x in q.get("qualified_positions", [])]
            pos = qualified_positions(q.get("test_position"))
            if listed and not pos:
                pos = qualified_positions("+".join(listed))
            groove, fillet = pos or ((), ())
            welders[wid] = WelderQual(
                welder=wid, id=q.get("wpq_no") or wid, name=q.get("name") or "", processes=tuple(x.upper() for x in q.get("processes", [])),
                test=" · ".join(x for x in (q.get("test_position"), q.get("test_form")) if x) or "not stated",
                groove=groove, fillet=fillet,
                t_max_mm=q.get("thickness_max_mm") if q.get("thickness_max_mm") is not None else thickness_max(q.get("test_thickness_mm")),
                od_min_mm=diameter_min(q.get("test_od_mm")), last_weld=parse_date(q.get("last_used")),
                test_form=q.get("test_form") or "pipe", valid_until=parse_date(q.get("valid_until")),
                continuity_ok=q.get("continuity_maintained"), source=d.filename,
                evidence=_evs(d.filename, q, f"WPQ, welder {wid}"))

    # As-built rows: the weld log and the fabrication record may both list a weld; keep both heat lists for conflicts.
    rows: dict[str, dict] = {}
    pwht: list[PwhtChart] = []
    nde: list[NdeReport] = []
    thickness: list[ThicknessReading] = []
    hydro: Hydrotest | None = None
    for d in by["asbuilt"]:
        data = d.data
        for r in data.get("weld_rows", []):
            jid = norm_id(r["joint_id"])
            row = rows.setdefault(jid, {"record_heats": {}, "sources": [], "evidence": {}})
            if d.filename not in row["sources"]:
                row["sources"].append(d.filename)
            e = _ev(d.filename, r, f"{jid} in the {r.get('source', 'record').replace('_', ' ')}")
            if e is not None:
                row["evidence"].setdefault(d.filename, e)
            heats = tuple(norm_heat(h) for h in r.get("heats", []) if norm_heat(h))
            if heats:
                row["record_heats"][f"{d.filename} ({r.get('source', 'record').replace('_', ' ')})"] = heats
            if r.get("source") == "weld_log" or "welder" not in row:
                for key, val in (("welder", norm_welder(r.get("welder"))), ("wps", norm_id(r.get("wps"))),
                                 ("weld_date", parse_date(r.get("weld_date"))), ("current_a", r.get("current_a"))):
                    if val:
                        row[key] = val
                if heats and (r.get("source") == "weld_log" or "heats" not in row):
                    row["heats"] = heats
        for p in data.get("pwht", []):
            load = p.get("load_id") or f"PWHT-{len(pwht) + 1}"
            pwht.append(PwhtChart(load, tuple(norm_id(j) for j in p.get("joints", [])), p.get("soak_c"), p.get("hold_min"),
                                  p.get("heat_rate_c_per_h"), p.get("cool_rate_c_per_h"),
                                  evidence=_evs(d.filename, p, f"PWHT record {load}")))
        for n in data.get("nde", []):
            nde.append(NdeReport(n["report_no"], norm_id(n["joint_id"]), n["method"].upper(), n.get("extent_pct"),
                                 n.get("result"), n.get("level"), n.get("drawing_revision"), d.filename,
                                 evidence=_evs(d.filename, n, f"{n['report_no']}")))
        for t in data.get("thickness", []):
            thickness.append(ThicknessReading(t["location"], norm_heat(t.get("heat")) or None, t["measured_mm"], t.get("required_mm"),
                                              evidence=_evs(d.filename, t, f"Thickness, {t['location']}")))
        for h in data.get("hydrotest", []):
            hydro = Hydrotest(h.get("pressure_mpa"), h.get("hold_min"), h.get("metal_temp_c"), h.get("witness"),
                              evidence=_evs(d.filename, h, "Hydrotest record"))

    as_built = {jid: AsBuilt(welder=r.get("welder", ""), wps=r.get("wps", ""), heats=r.get("heats", ()),
                             weld_date=r.get("weld_date"), current_a=r.get("current_a"), record_heats=r["record_heats"],
                             sources=tuple(r["sources"]), evidence=r["evidence"])
                for jid, r in rows.items()}

    # Joints come from the weld map; anything it does not say is filled from the as-built record of that weld.
    joints: list[Joint] = []
    drawing = by["drawing"][0].data if by["drawing"] else {}
    drawing_file = by["drawing"][0].filename if by["drawing"] else ""
    for dj in drawing.get("joints", []):
        jid = norm_id(dj["joint_id"])
        a = as_built.get(jid)
        heats = a.heats if a else ()
        heat = next((h for h in heats if h in materials), heats[0] if heats else None)
        pwht_by_wps = any(jid in p.pwht_joints for p in procedures.values())
        joints.append(Joint(
            id=jid, desc=dj.get("description") or "", heat=heat,
            thickness_mm=dj.get("thickness_mm") or drawing.get("wall_thickness_mm") or (materials[heat].thickness_mm if heat in materials else None),
            od_mm=dj.get("od_mm") or drawing.get("pipe_od_mm"), position=(dj.get("position") or "").upper() or None,
            kind=dj.get("kind") or "groove", wps=norm_id(dj.get("wps")) or (a.wps if a else None),
            welder=norm_welder(dj.get("welder")) or (a.welder if a else None), pressure=True,
            nde=_nde_text(dj.get("nde")) or _nde_text(drawing.get("general_nde")), heats=heats,
            pwht_required=True if dj.get("pwht_required") or pwht_by_wps else None,
            evidence=_evs(drawing_file, dj, f"{jid} on the weld map")))

    return Dossier(materials=list(materials.values()), procedures=procedures, welders=welders, joints=joints,
                   as_built=as_built, pwht_charts=pwht, nde_reports=nde, thickness=thickness, hydrotest=hydro,
                   drawing_no=drawing.get("drawing_no"), drawing_rev=drawing.get("revision"),
                   design_pressure_mpa=drawing.get("design_pressure_mpa"),
                   drawing_evidence=_ev(drawing_file, drawing, "Drawing title block") if drawing else None)
