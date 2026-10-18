"""Formal assessment report: the assessment result wrapped with project information, conclusion, limitations,
references and the approval block."""

from datetime import date, datetime

from app.assessment.catalog import GOVERNING, PROFILES, SECTORS, SLOTS, SUPP_BY_ID
from app.assessment.engine import ACCEPTABLE, NOT_ACCEPTABLE, WITH_NOTES, standards_phrase

RULE_SET = "Hibanako.Assessment.WeldQualification"

REFS = {
    "ASME IX": "ASME BPVC Section IX, Welding, Brazing, and Fusing Qualifications",
    "ASME V": "ASME BPVC Section V, Nondestructive Examination",
    "ASME VIII-1": "ASME BPVC Section VIII, Division 1, Rules for Construction of Pressure Vessels",
    "ASME I": "ASME BPVC Section I, Rules for Construction of Power Boilers",
    "ASME II": "ASME BPVC Section II, Materials",
    "ASME B31.1": "ASME B31.1, Power Piping",
    "ASME B31.3": "ASME B31.3, Process Piping",
    "API 1104": "API 1104, Welding of Pipelines and Related Facilities",
    "IACS Rec. 47": "IACS Recommendation 47, Shipbuilding and Repair Quality Standard",
    "ABS": "ABS Guide for Shipbuilding and Repair Quality Standard for Hull Structures During Construction",
    "ISO 9606-1": "ISO 9606-1, Qualification testing of welders, Fusion welding, Steels",
    "AWS D1.1": "AWS D1.1, Structural Welding Code, Steel",
    "MIL-STD-1689": "MIL-STD-1689, Fabrication, Welding, and Inspection of Ships Structure",
    "AWS D1.8": "AWS D1.8, Structural Welding Code, Seismic Supplement",
    "AWS D14.1": "AWS D14.1, Specification for Welding of Industrial and Mill Cranes and Other Material Handling Equipment",
    "AWS D14.3": "AWS D14.3, Specification for Welding Earthmoving, Construction, and Agricultural Equipment",
    "EN 1090-2": "EN 1090-2, Execution of steel structures and aluminium structures, Technical requirements for steel structures",
    "EN 15085": "EN 15085, Railway applications, Welding of railway vehicles and components",
    "ISO 3834-2": "ISO 3834-2, Quality requirements for fusion welding of metallic materials, Comprehensive quality requirements",
    "ISO 5817": "ISO 5817, Welding, Fusion-welded joints in steel, Quality levels for imperfections",
    "ISO 15614-1": "ISO 15614-1, Specification and qualification of welding procedures, Welding procedure test, Steels",
    "MR0103": "NACE MR0103 / ISO 17945, Metallic materials resistant to sulfide stress cracking in corrosive petroleum "
              "refining environments",
    "MR0175": "NACE MR0175 / ISO 15156, Materials for use in H2S-containing environments in oil and gas production",
}
GOV_REFS = {"IACS Rec. 47 + class": ["IACS Rec. 47", "ABS"], "ISO 3834 + ISO 5817": ["ISO 3834-2", "ISO 5817"]}
SUPP_REFS = {"ISO3834": "ISO 3834-2", "EXC3": "EN 1090-2", "ISO5817B": "ISO 5817", "SEISMIC": "AWS D1.8",
             "MR0103": "MR0103", "MR0175": "MR0175"}


def report_no(project_no: str) -> str:
    digits = "".join(ch for ch in project_no.rsplit("-", 1)[-1] if ch.isdigit())
    return f"HBK-RR-{digits.zfill(3) or '000'}"


def _row(label: str, value, unit: str = "") -> dict:
    return {"label": label, "value": str(value), "unit": unit}


def build_report(*, project_no: str, project_name: str, prepared_by: str, conditions: dict, documents: dict[str, list[str]],
                 result: dict, run_number: int, run_at: datetime, condition_hash: str, rule_pack: str) -> dict:
    """The formal report of one stored run. `result` is the run's stored Assessment.as_dict()."""
    today: date = run_at.date()
    present = {slot for slot, names in documents.items() if names}
    gov_id = conditions.get("governing") or "ASME VIII-1"
    g = GOVERNING.get(gov_id, GOVERNING["ASME VIII-1"])
    profile = PROFILES.get(conditions.get("profile", ""), PROFILES["plant-vessel"])
    supp = [SUPP_BY_ID[s] for s in conditions.get("supplementary", []) if s in SUPP_BY_ID]
    plan = result["mode"] == "PLAN"
    edition = conditions.get("edition", "")
    no = report_no(project_no)

    ref_keys = [*GOV_REFS.get(gov_id, [gov_id]), *(q.split(" Clause ")[0] for q in g.qual.split(" / ")),
                *(["ASME V", "ASME II"] if g.asme else []), *(SUPP_REFS[s.id] for s in supp if s.id in SUPP_REFS)]
    refs = [REFS.get(k, k) for k in dict.fromkeys(ref_keys)]

    verdict = result["verdict"]
    if verdict == ACCEPTABLE:
        conclusion = ("The welding plan meets the governing and supplementary standards. Fabrication may proceed. "
                      "Submit the as-built document for final verification." if plan
                      else "The finished work matches the qualified plan and meets the governing and supplementary standards.")
    elif verdict == WITH_NOTES:
        conclusion = ("No finding blocks fabrication. The warnings and waivers listed above need the reviewer's decision "
                      "and are part of this conclusion." if plan else
                      "No finding blocks release. The warnings and waivers listed above need the reviewer's decision.")
    elif verdict == NOT_ACCEPTABLE:
        conclusion = ("The welding plan does not meet the standards. Close the findings above before fabrication starts."
                      if plan else "The finished work does not meet the standards. Close the findings above before release.")
    else:
        conclusion = "One or more checks could not be completed because documents are missing."

    witness = ("Client / third-party inspector" if profile.sector == "mfg"
               else ("Navy inspector" if gov_id == "MIL-STD-1689" else "Class surveyor") if profile.sector == "ship"
               else "Authorized inspector")
    date_text = today.strftime("%d/%m/%Y")

    return {
        "report_no": no,
        "rule_set": f"{RULE_SET} ({rule_pack})",
        "mode": result["mode"],
        "title": "Hibanako Assessment Report",
        "subtitle": f"Assessment to {standards_phrase(gov_id, g)}. Welding Procedure and Welder Qualification.",
        "mode_line": "PLAN REVIEW · BEFORE FABRICATION · NO AS-BUILT DOCUMENT SUBMITTED" if plan
                     else "AS-BUILT VERIFICATION · FINISHED WORK AGAINST THE QUALIFIED PLAN",
        "info": [
            {"title": "Project Information", "rows": [
                _row("Assessment Name", no), _row("Project", project_no),
                _row("Assessment Type", "Plan review" if plan else "As-built verification"),
                _row("Assessment Date", date_text), _row("Run", f"#{run_number} · {run_at:%d/%m/%Y %H:%M} UTC"),
                _row("Created By", prepared_by)]},
            {"title": "Equipment Information", "rows": [
                _row("Equipment Name", project_name), _row("Equipment Type", profile.equipment),
                _row("Application", f"{SECTORS[profile.sector]} · {profile.label}"), _row("Governing Standard", f"{gov_id} ({edition} edition)" if edition else gov_id),
                _row("Welding Qualification", g.qual), _row("NDE Standard", g.nde),
                _row("Supplementary Requirements", " · ".join(s.label for s in supp) or "None")]},
            {"title": "Information for Assessment", "rows": [
                _row("Design Pressure", conditions.get("design_pressure_mpa", "—"), "MPa"),
                _row("Design Temperature", conditions.get("design_temp_c", "—"), "°C"),
                _row("Minimum Design Metal Temperature", conditions.get("mdmt_c", "—"), "°C"),
                _row("Joints on Welding Drawing", result["joints"], "EA"),
                _row("Documents Submitted", " · ".join(s.label for s in SLOTS if s.id in present) or "None"),
                _row("As-built Document", "True" if "asbuilt" in present else "False")]},
        ],
        "conclusion_label": "Plan Assessment Conclusion" if plan else "Assessment Conclusion",
        "conclusion": conclusion,
        "limitations": [
            "This is a plan review. No as-built document was submitted, so production welds, actual welders and PWHT charts "
            "are not verified." if plan else "As-built verification covers the joints on the welding drawing only.",
            "WPS and WPQ are assessed against the joints, thicknesses and positions on the welding drawing.",
            ("PWHT is determined from the mill certificate (P-Number, thickness) and the governing standard. "
             "Supplementary requirements may add PWHT or hardness limits."),
            ("If the design conditions, governing standard or supplementary requirements change, a reassessment should "
             "be undertaken."),
        ],
        "comments": "Clause references follow the latest edition of each standard. Please make sure the edition conforms with "
                    "the contract and the original design documents. Brinell hardness is converted from Vickers (HV10) by "
                    "approximation.",
        "warnings": "Values are extracted automatically from the submitted documents and checked by rule. The quality engineer "
                    "shall review every finding against the source documents before sign-off.",
        "references": refs,
        "approval": [
            {"role": "Prepared by", "name": prepared_by, "date": date_text},
            {"role": "Approved by", "name": "", "date": ""},
            {"role": witness, "name": "", "date": ""},
        ],
        "traceability": [
            _row("Rule pack", f"{RULE_SET} {rule_pack}"), _row("Condition set", condition_hash),
            _row("Code edition", edition or "—"), _row("Run", f"#{run_number} · {run_at:%Y-%m-%d %H:%M} UTC"),
            *(_row(next(s.label for s in SLOTS if s.id == slot), " · ".join(names)) for slot, names in documents.items() if names),
        ],
        "result": result,
    }
