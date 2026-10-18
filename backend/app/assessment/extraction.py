"""Read assessment documents with Gemini: sort each file into a slot, then extract the slot's fields.

The model only reads. Every value is copied as printed (or null), with the page it came from; the rules engine
decides pass or fail. See the PRD, section 5, for what each slot must provide.
"""

from typing import Literal

from google.genai import types
from pydantic import BaseModel, Field

from app.ai.client import generate
from app.config import get_settings

Confidence = Literal["high", "low"]


class Record(BaseModel):
    page: int = Field(description="1-based page (or sheet) the values were read from")
    confidence: Confidence = Field(description='"low" if any value was hard to read, handwritten, ambiguous or inferred')


# Slot classification -------------------------------------------------------------------------------------------

SlotName = Literal["mtc", "wps", "wpq", "drawing", "asbuilt", "other", "none"]


class SlotGuess(BaseModel):
    slot: SlotName
    confidence: float = Field(ge=0, le=1, description="0–1: how sure the content shows this document type")
    legible: bool = Field(description="False if most of the document has no readable text")
    reason: str = Field(description="One short sentence naming what in the content decided the slot")


CLASSIFY_SYSTEM = """You sort welding fabrication quality documents into one slot by their CONTENT (not only the file name):
- mtc: mill / material test certificate (EN 10204 2.1, 2.2, 3.1, 3.2 or ASME MTR): heat number, chemistry, mechanical tests.
- wps: welding procedure specification and/or its PQR.
- wpq: welder performance qualification (welder ID, test position, process, validity) or a welder continuity log.
- drawing: welding drawing, isometric or weld map listing the joints (with NDE / PWHT notes).
- asbuilt: records of the work as done: weld log, fabrication record / traveler with heats, PWHT chart or record,
  NDE reports (RT, UT, MT, PT, VT), hardness reports, thickness surveys, hydrostatic test reports, as-built drawings.
- other: a quality document that is none of the above but belongs in the dossier (e.g. a dossier index or checklist).
- none: not a fabrication quality document (invoice, photo of something else, blank page).
Set legible false when the page has (almost) no readable text. Confidence below 0.5 means you are guessing."""


# Slot schemas --------------------------------------------------------------------------------------------------

class Element(BaseModel):
    symbol: str = Field(description="C, Mn, Si, P, S, Cr, Ni, Mo, Cu, V or Nb")
    percent: float = Field(description="Mass %")


class MtcHeat(Record):
    certificate_no: str | None
    cert_type: str | None = Field(description='EN 10204 type as printed, e.g. "3.1"; "MTR" for an ASME mill test report')
    heat_no: str = Field(description="One heat / cast number exactly as printed. A certificate covering several heats "
                                     "gives one record per heat, repeating the shared fields.")
    spec_grade: str | None = Field(description="Material specification and grade, e.g. ASTM A106 Gr.B, SA-516 Gr.70")
    product: str | None = Field(description="Product form and size as printed")
    thickness_mm: float | None = Field(description="Wall or plate thickness in mm if printed")
    condition: str | None = Field(description="Heat-treatment / delivery condition, e.g. Normalized, As-rolled")
    chemistry: list[Element] = Field(default_factory=list, description="Only the elements printed for this heat")
    yield_mpa: float | None
    tensile_mpa: float | None = Field(description="Tensile strength result for THIS heat")
    tensile_min_mpa: float | None = Field(description="Tensile strength requirement (minimum) printed next to the result")
    impact_temp_c: float | None = Field(description="Charpy test temperature in °C, if tested")
    impact_avg_j: float | None = Field(description="Charpy average energy in J, if tested")
    hardness: str | None = Field(description="Hardness result as printed, if any")
    signed: bool = Field(description="True if the authorised signatory field is filled (name, signature or stamp)")


class MtcDoc(BaseModel):
    heats: list[MtcHeat]


class WpsProcedure(Record):
    wps_no: str
    revision: str | None
    pqr_nos: list[str] = Field(default_factory=list)
    processes: list[str] = Field(default_factory=list, description="Welding processes, e.g. GTAW, SMAW, FCAW")
    p_no: str | None = Field(description='Base metal P-Number, e.g. "1"')
    thickness_min_mm: float | None = Field(description="Qualified base metal thickness range, minimum, if stated")
    thickness_max_mm: float | None = Field(description="Qualified base metal thickness range, maximum, if stated")
    positions: list[str] = Field(default_factory=list)
    preheat_min_c: float | None
    current_min_a: float | None
    current_max_a: float | None
    pwht: bool = Field(description="True if the WPS includes post-weld heat treatment")
    pwht_temp_c: float | None = Field(description="PWHT holding temperature, or the middle of the range, in °C")
    pwht_temp_tolerance_c: float | None = Field(description="± tolerance on the PWHT temperature, if stated")
    pwht_hold_min: float | None
    pwht_joints: list[str] = Field(default_factory=list,
                                   description='Weld IDs if PWHT is limited to certain welds (e.g. "W-04 only"); else empty')
    hardness_hv10: float | None = Field(description="Maximum PQR hardness in HV10, if a hardness survey is shown")
    impact_temp_c: float | None = Field(description="PQR Charpy test temperature, if shown")


class WpsDoc(BaseModel):
    procedures: list[WpsProcedure]


class WelderQualification(Record):
    welder_id: str
    name: str | None
    wpq_no: str | None
    processes: list[str] = Field(default_factory=list)
    test_position: str | None = Field(description="Test position as printed, e.g. 6G, 2G, 3F")
    test_form: Literal["pipe", "plate"] | None = Field(description="Whether the test coupon was pipe or plate, if stated")
    test_thickness_mm: float | None
    test_od_mm: float | None
    qualified_positions: list[str] = Field(default_factory=list,
                                           description="Positions listed as qualified (if the document lists a range)")
    thickness_max_mm: float | None = Field(description="Maximum qualified thickness if printed")
    p_no: str | None
    test_date: str | None = Field(description="YYYY-MM-DD")
    valid_until: str | None = Field(description="Expiry date as YYYY-MM-DD, if stated")
    last_used: str | None = Field(description="Last date the process was used (continuity log), YYYY-MM-DD, if stated")
    continuity_maintained: bool | None = Field(description="True if the document states continuity is maintained")


class WpqDoc(BaseModel):
    welders: list[WelderQualification]


class DrawingJoint(Record):
    joint_id: str
    description: str | None
    kind: Literal["groove", "fillet"] | None = Field(description="groove for butt welds, fillet for fillet welds")
    position: str | None = Field(description="Production position (1G…6G, 1F…4F) if shown for this joint")
    thickness_mm: float | None = Field(description="Joint / wall thickness for this joint if shown")
    od_mm: float | None
    wps: str | None
    welder: str | None
    nde: str | None = Field(description='NDE required for this joint as printed, e.g. "RT 100%"')
    pwht_required: bool | None = Field(description="True if the drawing says this joint needs PWHT")


class DrawingDoc(Record):
    drawing_no: str | None
    revision: str | None
    code: str | None
    design_pressure_mpa: float | None = Field(description="Design pressure converted to MPa (1 bar = 0.1 MPa)")
    design_temp_c: float | None
    wall_thickness_mm: float | None = Field(description="General wall thickness stated on the drawing")
    pipe_od_mm: float | None = Field(description="Main pipe outside diameter in mm (6in = 168.3, 4in = 114.3)")
    general_nde: str | None = Field(description='NDE note covering every joint, e.g. "100 % radiography" → "RT 100%"')
    joints: list[DrawingJoint]


class WeldLogRow(Record):
    joint_id: str
    welder: str | None
    wps: str | None
    weld_date: str | None = Field(description="YYYY-MM-DD")
    heats: list[str] = Field(default_factory=list, description="Heat numbers of both sides, as printed")
    current_a: float | None = Field(description="Welding current recorded, in A")
    source: Literal["weld_log", "fabrication_record"] = Field(description="Which kind of record this row came from")


class PwhtRecord(Record):
    load_id: str | None
    joints: list[str]
    soak_c: float | None
    hold_min: float | None
    heat_rate_c_per_h: float | None
    cool_rate_c_per_h: float | None


class NdeReportRow(Record):
    report_no: str
    joint_id: str
    method: str = Field(description="RT, UT, MT, PT or VT")
    extent_pct: float | None
    result: Literal["ACCEPT", "REJECT"] | None
    level: str | None = Field(description='Signing technician level, e.g. "II"; null when unsigned')
    drawing_revision: str | None = Field(description="Drawing revision the report refers to, if printed")


class ThicknessRow(Record):
    location: str
    heat: str | None
    measured_mm: float
    required_mm: float | None


class HydrotestRow(Record):
    pressure_mpa: float | None = Field(description="Test pressure converted to MPa (1 bar = 0.1 MPa)")
    hold_min: float | None
    metal_temp_c: float | None
    witness: str | None = Field(description="Witness name or signature; null if blank")


class AsBuiltDoc(BaseModel):
    weld_rows: list[WeldLogRow] = Field(default_factory=list)
    pwht: list[PwhtRecord] = Field(default_factory=list)
    nde: list[NdeReportRow] = Field(default_factory=list)
    thickness: list[ThicknessRow] = Field(default_factory=list)
    hydrotest: list[HydrotestRow] = Field(default_factory=list)


class OtherDoc(BaseModel):
    title: str | None


SCHEMAS: dict[str, type[BaseModel]] = {"mtc": MtcDoc, "wps": WpsDoc, "wpq": WpqDoc, "drawing": DrawingDoc,
                                       "asbuilt": AsBuiltDoc, "other": OtherDoc}

EXTRACT_SYSTEM = """You extract fields from welding fabrication quality documents for a rule-based release check.
Release decisions are made from what you return, so accuracy matters more than completeness:
- Copy identifiers (heat numbers, weld IDs, report, WPS and welder numbers) exactly as printed.
- Never infer, correct or complete a value. If a value is not on the page, return null (or an empty list).
- Convert units only where the field says so (bar → MPa, inch → mm); otherwise keep the printed number.
- Set confidence "low" for a record when any value is handwritten, hard to read or ambiguous.
- A signature is present when the field holds a name, signature, initials or stamp; it is absent when blank, a dash
  or "(not signed)".
- Read tables row by row; values in one row belong to the same record.
Return every matching record in the document."""

HINTS = {
    "mtc": "Extract every heat on the certificate(s). Give the tensile result and requirement for each heat.",
    "wps": "Extract every WPS (with its PQR references) in the document.",
    "wpq": "Extract every welder qualification in the document.",
    "drawing": "Extract the drawing header and every joint on the weld map. Apply general notes (e.g. '100 % "
               "radiography', 'W-04 requires PWHT') to the joints they name.",
    "asbuilt": "Extract every weld log or fabrication record row, PWHT record, NDE report, thickness reading and "
               "hydrotest record in the document.",
    "other": "Return the document title.",
}


async def classify_slot(parts: list[types.Part]) -> SlotGuess:
    s = get_settings()
    return await generate(purpose="assess-class", model=s.fast_model, system=CLASSIFY_SYSTEM,
                          parts=[*parts, types.Part.from_text(text="Sort this document.")], schema=SlotGuess,
                          thinking=s.classify_thinking)


async def extract_slot(slot: str, parts: list[types.Part]) -> BaseModel:
    s = get_settings()
    return await generate(purpose=f"assess-{slot}", model=s.extract_model, system=EXTRACT_SYSTEM,
                          parts=[*parts, types.Part.from_text(text=HINTS[slot])], schema=SCHEMAS[slot],
                          thinking=s.extract_thinking)
